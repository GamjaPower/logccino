"""
Logccino Splunk-Style Saved Search & Alerting Scheduler Engine
PPL 쿼리를 주기적으로 실행하여 임계치 초과 시 웹훅 및 내부 인덱스로 실시간 알람을 발송하는 자율형 스케줄러
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx
from core.client.opensearch_client import opensearch_service
from core.config import settings
from core.query.executor import QueryExecutor
from core.scheduler.models import (
    SavedSearch, SavedSearchCreate, SavedSearchUpdate, AlertRecord
)

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "saved_searches.json"

DEFAULT_SAVED_SEARCHES = [
    {
        "id": "alert-ssh-bruteforce",
        "name": "[SEC-01] SSH 무차별 대입(Brute-Force) 및 로그인 실패 급증",
        "description": "Syslog 수집기를 통해 유입된 SSH 로그인 실패 이벤트가 임계치를 초과할 때 즉시 알람을 발송합니다.",
        "ppl_query": "source = logccino-logs-* | where security.action = 'ssh_login_failure' or security.action = 'ssh_login_failed' | head 50",
        "interval_seconds": 60,
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "CRITICAL",
        "webhook_url": None,
        "enabled": True
    },
    {
        "id": "alert-sudo-privilege",
        "name": "[SEC-02] 의심스러운 비인가 Sudo 권한 상승 탐지",
        "description": "호스트 서버에서 root 권한으로 승격하거나 /bin/bash 등을 실행한 의심 명령을 감시합니다.",
        "ppl_query": "source = logccino-logs-* | where program = 'sudo' or security.action = 'sudo_escalation' | head 50",
        "interval_seconds": 120,
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "HIGH",
        "webhook_url": None,
        "enabled": True
    },
    {
        "id": "alert-service-5xx-burst",
        "name": "[SRE-01] 전사 마이크로서비스 5xx 심각 에러 급증",
        "description": "클러스터 전체에서 발생한 ERROR 등급의 애플리케이션 예외가 5건 이상 급증 시 트리거됩니다.",
        "ppl_query": "source = logccino-logs-* | where level = 'ERROR' | head 50",
        "interval_seconds": 60,
        "condition_operator": "gte",
        "condition_threshold": 3.0,
        "severity": "HIGH",
        "webhook_url": None,
        "enabled": True
    },
    {
        "id": "alert-firewall-drops",
        "name": "[SEC-03] 경계 방화벽(UFW) 비정상 포트 스캔 및 차단 감시",
        "description": "경계 방화벽에서 UFW BLOCK 플래그로 차단된 침입 시도 IP를 실시간 추적합니다.",
        "ppl_query": "source = logccino-logs-* | where security.action = 'firewall_drop' | head 50",
        "interval_seconds": 180,
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "MEDIUM",
        "webhook_url": None,
        "enabled": True
    }
]


class SavedSearchScheduler:
    """Splunk saved search 기능을 완벽히 모방한 PPL 스케줄러 & 알람 발송기"""

    def __init__(self):
        self.executor = QueryExecutor()
        self._searches: Dict[str, SavedSearch] = {}
        self._alert_history: List[AlertRecord] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.load_from_storage()

    def load_from_storage(self):
        """저장소(JSON 파일)에서 Saved Search 설정 로드, 없을 시 기본 프리셋 생성"""
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                for item in data:
                    s = SavedSearch(**item)
                    self._searches[s.id] = s
                logger.info(f"Loaded {len(self._searches)} saved searches from {DATA_FILE}")
                return
            except Exception as e:
                logger.warning(f"Failed to read {DATA_FILE}: {e}. Initializing default searches.")

        # 기본 프리셋 생성
        now = datetime.now(timezone.utc)
        for idx, item in enumerate(DEFAULT_SAVED_SEARCHES):
            s = SavedSearch(
                **item,
                next_run=(now + timedelta(seconds=10 + idx * 5)).isoformat()
            )
            self._searches[s.id] = s
        self.save_to_storage()

    def save_to_storage(self):
        """현재 Saved Search 설정을 JSON 파일로 영구 저장"""
        try:
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [s.model_dump() for s in self._searches.values()]
            DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save searches to {DATA_FILE}: {e}")

    def get_all(self) -> List[SavedSearch]:
        return list(self._searches.values())

    def get(self, search_id: str) -> Optional[SavedSearch]:
        return self._searches.get(search_id)

    def create(self, req: SavedSearchCreate) -> SavedSearch:
        search_id = f"alert-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        s = SavedSearch(
            id=search_id,
            name=req.name,
            description=req.description,
            ppl_query=req.ppl_query,
            interval_seconds=req.interval_seconds,
            condition_operator=req.condition_operator,
            condition_threshold=req.condition_threshold,
            severity=req.severity,
            webhook_url=req.webhook_url,
            enabled=req.enabled,
            next_run=(now + timedelta(seconds=5)).isoformat()
        )
        self._searches[s.id] = s
        self.save_to_storage()
        return s

    def update(self, search_id: str, req: SavedSearchUpdate) -> Optional[SavedSearch]:
        s = self._searches.get(search_id)
        if not s:
            return None

        update_data = req.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if val is not None:
                setattr(s, key, val)

        if not s.enabled:
            s.last_status = "DISABLED"
        else:
            if s.last_status == "DISABLED":
                s.last_status = "PENDING"
                s.next_run = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()

        self.save_to_storage()
        return s

    def delete(self, search_id: str) -> bool:
        if search_id in self._searches:
            del self._searches[search_id]
            self.save_to_storage()
            return True
        return False

    def evaluate_condition(self, count: int, operator: str, threshold: float) -> bool:
        """Splunk 스타일 트리거 조건 평가"""
        if operator == "gt":
            return count > threshold
        elif operator == "gte":
            return count >= threshold
        elif operator == "lt":
            return count < threshold
        elif operator == "lte":
            return count <= threshold
        elif operator == "eq":
            return count == threshold
        elif operator == "neq":
            return count != threshold
        return False

    async def send_webhook_alert(self, search: SavedSearch, alert: AlertRecord) -> tuple[bool, Optional[str]]:
        """Slack/Teams/Discord/사내 웹훅 규격으로 알람 전송"""
        if not search.webhook_url:
            return False, "No webhook configured"

        payload = {
            "text": f"🚨 [Logccino Splunk Alert] {search.name} (심각도: {search.severity})",
            "saved_search_id": search.id,
            "alert_name": search.name,
            "severity": search.severity,
            "matched_events": alert.result_count,
            "condition": f"count {search.condition_operator} {search.condition_threshold}",
            "ppl_query": search.ppl_query,
            "timestamp": alert.timestamp,
            "sample_logs": alert.sample_hits[:5]
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(search.webhook_url, json=payload)
                if res.status_code in (200, 201, 204):
                    return True, f"HTTP {res.status_code}"
                else:
                    return False, f"HTTP {res.status_code}: {res.text[:100]}"
        except Exception as e:
            return False, str(e)

    async def index_alert_to_opensearch(self, alert: AlertRecord):
        """트리거된 알람을 OpenSearch 'logccino-alerts-YYYY.MM.DD' 인덱스에 보관"""
        client = opensearch_service.get_client()
        today = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        index_name = f"logccino-alerts-{today}"
        doc = alert.model_dump()
        doc["@timestamp"] = alert.timestamp

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: client.index(index=index_name, body=doc, refresh=True)
            )
        except Exception as e:
            logger.warning(f"Failed to index alert to OpenSearch: {e}")

    async def execute_saved_search(self, s: SavedSearch) -> AlertRecord:
        """PPL 실행 및 알람 조건 평가 메인 로직"""
        t0 = time.time()
        now = datetime.now(timezone.utc)
        error_msg = None
        hits = []

        try:
            loop = asyncio.get_running_loop()
            # PPL 쿼리 실행
            ppl_res = await loop.run_in_executor(
                None,
                lambda: self.executor.execute_ppl(s.ppl_query)
            )
            hits = self.executor.format_ppl_response(ppl_res)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing saved search '{s.name}': {e}")

        took_ms = int((time.time() - t0) * 1000)
        result_count = len(hits)
        is_triggered = False

        if error_msg:
            s.last_status = "ERROR"
            s.last_error = error_msg
        else:
            is_triggered = self.evaluate_condition(
                count=result_count,
                operator=s.condition_operator,
                threshold=s.condition_threshold
            )
            s.last_status = "TRIGGERED" if is_triggered else "OK"
            s.last_error = None

        s.last_run = now.isoformat()
        s.last_result_count = result_count
        s.next_run = (now + timedelta(seconds=s.interval_seconds)).isoformat()
        self.save_to_storage()

        # 알람 레코드 생성
        alert_record = AlertRecord(
            id=f"alert-run-{uuid.uuid4().hex[:8]}",
            saved_search_id=s.id,
            saved_search_name=s.name,
            timestamp=now.isoformat(),
            severity=s.severity,
            ppl_query=s.ppl_query,
            result_count=result_count,
            threshold=s.condition_threshold,
            operator=s.condition_operator,
            triggered=is_triggered,
            sample_hits=hits[:10],
            execution_took_ms=took_ms
        )

        # 트리거된 경우 웹훅 발송 및 인덱싱
        if is_triggered:
            webhook_ok, webhook_resp = await self.send_webhook_alert(s, alert_record)
            alert_record.webhook_sent = webhook_ok
            alert_record.webhook_status = webhook_resp
            await self.index_alert_to_opensearch(alert_record)

        # 메모리 큐에 보관 (최대 100건)
        self._alert_history.insert(0, alert_record)
        if len(self._alert_history) > 100:
            self._alert_history.pop()

        return alert_record

    async def run_now(self, search_id: str) -> Optional[AlertRecord]:
        """수동 즉시 실행 (Splunk 'Run Now' 기능)"""
        s = self._searches.get(search_id)
        if not s:
            return None
        return await self.execute_saved_search(s)

    def get_alert_history(self, limit: int = 50, triggered_only: bool = False) -> List[AlertRecord]:
        if triggered_only:
            filtered = [a for a in self._alert_history if a.triggered]
            return filtered[:limit]
        return self._alert_history[:limit]

    async def _scheduler_loop(self):
        """비동기 스케줄러 메인 백그라운드 틱 루프"""
        logger.info("Logccino PPL Saved Search Scheduler loop started.")
        while self._running:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                for search in list(self._searches.values()):
                    if not search.enabled:
                        continue
                    # 실행 주기 도래 여부 검사
                    if search.next_run is None or search.next_run <= now_iso:
                        try:
                            await self.execute_saved_search(search)
                        except Exception as ex:
                            logger.error(f"Failed to run scheduled search {search.id}: {ex}")
            except Exception as e:
                logger.error(f"Error in scheduler tick loop: {e}")

            # 5초 간격으로 스케줄 점검
            await asyncio.sleep(5)

    def start(self):
        """스케줄러 시작"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("SavedSearchScheduler background daemon initialized.")

    def stop(self):
        """스케줄러 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("SavedSearchScheduler background daemon stopped.")


# 싱글톤 인스턴스
scheduler_engine = SavedSearchScheduler()
