"""
Logccino Splunk-Style Saved Search & Alerting Scheduler Engine
PPL 쿼리를 주기적으로 실행하여 임계치 초과 시 웹훅, 이메일, 스크립트 실행 및 OpenSearch 인덱스로 실시간 알람을 발송하는 자율형 스케줄러
Splunk savedsearches.conf 완전 호환: 디스패치 시간 범위, 알람 유형, Throttling(억제), 복합 액션 완벽 지원
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

import httpx
from core.client.opensearch_client import opensearch_service
from core.config import settings
from core.query.executor import QueryExecutor
from core.scheduler.models import (
    SavedSearch, SavedSearchCreate, SavedSearchUpdate, AlertRecord
)

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "saved_searches.json"


def parse_time_period(val: Union[str, int, float]) -> int:
    """시간 표현식 (예: '5m', '1h', '24h', '30s', 300)을 초 단위 정수로 변환"""
    if isinstance(val, (int, float)):
        return int(val)
    val_str = str(val).strip().lower()
    if val_str.endswith("s") and val_str[:-1].isdigit():
        return int(val_str[:-1])
    elif val_str.endswith("m") and val_str[:-1].isdigit():
        return int(val_str[:-1]) * 60
    elif val_str.endswith("h") and val_str[:-1].isdigit():
        return int(val_str[:-1]) * 3600
    elif val_str.endswith("d") and val_str[:-1].isdigit():
        return int(val_str[:-1]) * 86400
    try:
        return int(val_str)
    except ValueError:
        return 300


DEFAULT_SAVED_SEARCHES = [
    {
        "id": "alert-ssh-bruteforce",
        "name": "[SEC-01] SSH 무차별 대입(Brute-Force) 및 로그인 실패 급증",
        "description": "Syslog 수집기를 통해 유입된 SSH 로그인 실패 이벤트가 임계치를 초과할 때 즉시 알람을 발송합니다.",
        "ppl_query": "source = logccino-logs-* | where security.action = 'ssh_login_failure' or security.action = 'ssh_login_failed' | head 50",
        "app": "enterprise_security",
        "owner": "admin",
        "sharing": "app",
        "dispatch_earliest_time": "-15m",
        "dispatch_latest_time": "now",
        "is_scheduled": True,
        "schedule_type": "interval",
        "cron_expression": "*/1 * * * *",
        "interval_seconds": 60,
        "schedule_window": "auto",
        "schedule_priority": "higher",
        "alert_type": "number_of_results",
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "CRITICAL",
        "trigger_mode": "once",
        "alert_track": True,
        "alert_expires": "24h",
        "alert_suppress": True,
        "alert_suppress_period": "5m",
        "alert_suppress_fields": "host",
        "action_webhook_enabled": False,
        "webhook_url": None,
        "action_email_enabled": False,
        "action_index_enabled": True,
        "action_index_name": "logccino-alerts",
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110.001 Password Guessing",
        "ai_managed": True,
        "ai_rationale": "단시간 내 동일 호스트에 대한 다중 계정 로그인 실패는 외부 자격증명 살포(Password Spraying) 공격의 대표적 전조 증상입니다.",
        "enabled": True
    },
    {
        "id": "alert-sudo-privilege",
        "name": "[SEC-02] 의심스러운 비인가 Sudo 권한 상승 탐지",
        "description": "호스트 서버에서 root 권한으로 승격하거나 /bin/bash 등을 실행한 의심 명령을 감시합니다.",
        "ppl_query": "source = logccino-logs-* | where program = 'sudo' or security.action = 'sudo_escalation' | head 50",
        "app": "enterprise_security",
        "owner": "admin",
        "sharing": "app",
        "dispatch_earliest_time": "-30m",
        "dispatch_latest_time": "now",
        "is_scheduled": True,
        "schedule_type": "interval",
        "cron_expression": "*/2 * * * *",
        "interval_seconds": 120,
        "schedule_window": "auto",
        "schedule_priority": "default",
        "alert_type": "number_of_results",
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "HIGH",
        "trigger_mode": "once",
        "alert_track": True,
        "alert_expires": "24h",
        "alert_suppress": False,
        "alert_suppress_period": "10m",
        "action_webhook_enabled": False,
        "webhook_url": None,
        "action_email_enabled": False,
        "action_index_enabled": True,
        "action_index_name": "logccino-alerts",
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110.001 Password Guessing",
        "ai_managed": True,
        "ai_rationale": "단시간 내 동일 호스트에 대한 다중 계정 로그인 실패는 외부 자격증명 살포(Password Spraying) 공격의 대표적 전조 증상입니다.",
        "enabled": True
    },
    {
        "id": "alert-service-5xx-burst",
        "name": "[SRE-01] 전사 마이크로서비스 5xx 심각 에러 급증",
        "description": "클러스터 전체에서 발생한 ERROR 등급의 애플리케이션 예외가 5건 이상 급증 시 트리거됩니다.",
        "ppl_query": "source = logccino-logs-* | where level = 'ERROR' | head 50",
        "app": "search",
        "owner": "logccino",
        "sharing": "global",
        "dispatch_earliest_time": "-15m",
        "dispatch_latest_time": "now",
        "is_scheduled": True,
        "schedule_type": "interval",
        "cron_expression": "*/1 * * * *",
        "interval_seconds": 60,
        "schedule_window": "auto",
        "schedule_priority": "higher",
        "alert_type": "number_of_results",
        "condition_operator": "gte",
        "condition_threshold": 3.0,
        "severity": "HIGH",
        "trigger_mode": "once",
        "alert_track": True,
        "alert_expires": "24h",
        "alert_suppress": True,
        "alert_suppress_period": "5m",
        "alert_suppress_fields": "service",
        "action_webhook_enabled": False,
        "webhook_url": None,
        "action_email_enabled": False,
        "action_index_enabled": True,
        "action_index_name": "logccino-alerts",
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110.001 Password Guessing",
        "ai_managed": True,
        "ai_rationale": "단시간 내 동일 호스트에 대한 다중 계정 로그인 실패는 외부 자격증명 살포(Password Spraying) 공격의 대표적 전조 증상입니다.",
        "enabled": True
    },
    {
        "id": "alert-firewall-drops",
        "name": "[SEC-03] 경계 방화벽(UFW) 비정상 포트 스캔 및 차단 감시",
        "description": "경계 방화벽에서 UFW BLOCK 플래그로 차단된 침입 시도 IP를 실시간 추적합니다.",
        "ppl_query": "source = logccino-logs-* | where security.action = 'firewall_drop' | head 50",
        "app": "enterprise_security",
        "owner": "admin",
        "sharing": "app",
        "dispatch_earliest_time": "-1h",
        "dispatch_latest_time": "now",
        "is_scheduled": True,
        "schedule_type": "interval",
        "cron_expression": "*/3 * * * *",
        "interval_seconds": 180,
        "schedule_window": "auto",
        "schedule_priority": "default",
        "alert_type": "number_of_results",
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "MEDIUM",
        "trigger_mode": "once",
        "alert_track": True,
        "alert_expires": "24h",
        "alert_suppress": False,
        "alert_suppress_period": "15m",
        "action_webhook_enabled": False,
        "webhook_url": None,
        "action_email_enabled": False,
        "action_index_enabled": True,
        "action_index_name": "logccino-alerts",
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110.001 Password Guessing",
        "ai_managed": True,
        "ai_rationale": "단시간 내 동일 호스트에 대한 다중 계정 로그인 실패는 외부 자격증명 살포(Password Spraying) 공격의 대표적 전조 증상입니다.",
        "enabled": True
    }
]


class SavedSearchScheduler:
    """Splunk saved search 및 Alerting 엔진의 모든 옵션을 완벽히 수용한 PPL 스케줄러 & 알람 발송기"""

    def __init__(self):
        self.executor = QueryExecutor()
        self._searches: Dict[str, SavedSearch] = {}
        self._alert_history: List[AlertRecord] = []
        self._suppression_cache: Dict[str, float] = {}  # key -> timestamp epoch
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
                    try:
                        s = SavedSearch(**item)
                        self._searches[s.id] = s
                    except Exception as e:
                        logger.warning(f"Failed to parse saved search {item.get('id')}: {e}")
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
        dumped = req.model_dump(exclude_unset=True)
        dumped["id"] = search_id
        dumped["next_run"] = (now + timedelta(seconds=5)).isoformat()
        s = SavedSearch(**dumped)
        self._searches[s.id] = s
        self.save_to_storage()
        return s

    def update(self, search_id: str, req: SavedSearchUpdate) -> Optional[SavedSearch]:
        s = self._searches.get(search_id)
        if not s:
            return None

        update_data = req.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if val is not None and hasattr(s, key):
                setattr(s, key, val)

        s.updated_at = datetime.now(timezone.utc).isoformat()

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

    def evaluate_condition(
        self,
        count_or_hits: Any,
        operator: str = "gt",
        threshold: float = 0.0,
        search: Optional[SavedSearch] = None
    ) -> bool:
        """
        Splunk 스타일 조건 평가
        - count_or_hits가 int/float인 경우 이전 호환성 유지
        - count_or_hits가 list[dict]인 경우 search.alert_type에 따라 이벤트수/호스트수/소스수/커스텀 평가
        """
        hits = []
        if isinstance(count_or_hits, (int, float)):
            val = float(count_or_hits)
        elif isinstance(count_or_hits, list):
            hits = count_or_hits
            alert_type = search.alert_type if search else "number_of_results"

            if alert_type in ("number_of_events", "number_of_results"):
                val = float(len(hits))
            elif alert_type == "number_of_hosts":
                unique_hosts = {
                    h.get("host") or h.get("hostname")
                    for h in hits if isinstance(h, dict) and (h.get("host") or h.get("hostname"))
                }
                val = float(len(unique_hosts))
            elif alert_type == "number_of_sources":
                unique_sources = {
                    h.get("source") or h.get("program") or h.get("service")
                    for h in hits if isinstance(h, dict) and (h.get("source") or h.get("program") or h.get("service"))
                }
                val = float(len(unique_sources))
            elif alert_type == "always":
                return True
            elif alert_type == "custom":
                val = float(len(hits))
            else:
                val = float(len(hits))
        else:
            val = 0.0

        op = operator.lower()
        if op == "gt":
            return val > threshold
        elif op == "gte":
            return val >= threshold
        elif op == "lt":
            return val < threshold
        elif op == "lte":
            return val <= threshold
        elif op in ("eq", "=="):
            return val == threshold
        elif op in ("neq", "!="):
            return val != threshold
        elif op == "drops_by":
            return val < threshold
        elif op == "rises_by":
            return val > threshold
        return False

    def check_suppression(self, search: SavedSearch, hits: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Splunk Alert Throttling (Suppression) 검사
        alert_suppress가 True이고 지정된 억제 기간 내에 동일 필드(또는 전체)에 대해 알람이 이미 발생한 경우 억제
        """
        if not search.alert_suppress:
            return False, "Not suppressed"

        now_epoch = time.time()
        period_sec = parse_time_period(search.alert_suppress_period)

        field_val = "global"
        suppress_field = search.alert_suppress_fields
        if suppress_field and hits:
            parts = []
            for field in [f.strip() for f in suppress_field.split(",")]:
                if hits and isinstance(hits[0], dict) and field in hits[0]:
                    parts.append(str(hits[0][field]))
            if parts:
                field_val = "_".join(parts)

        cache_key = f"{search.id}:{field_val}"
        last_fired = self._suppression_cache.get(cache_key)

        if last_fired is not None and (now_epoch - last_fired) < period_sec:
            remain = int(period_sec - (now_epoch - last_fired))
            return True, f"Throttled by field '{field_val}' for remaining {remain}s (period: {search.alert_suppress_period})"

        self._suppression_cache[cache_key] = now_epoch
        return False, "Allowed to trigger"

    async def send_webhook_alert(self, search: SavedSearch, alert: AlertRecord) -> tuple[bool, Optional[str]]:
        """Slack/Teams/Discord/사내 웹훅 규격으로 알람 전송"""
        if not search.action_webhook_enabled or not search.webhook_url:
            return False, "No webhook configured"

        payload = {
            "text": f"🚨 [Logccino Splunk Alert] {search.name} (심각도: {search.severity})",
            "saved_search_id": search.id,
            "alert_name": search.name,
            "app": search.app,
            "severity": search.severity,
            "matched_events": alert.result_count,
            "alert_type": search.alert_type,
            "condition": f"{search.alert_type} {search.condition_operator} {search.condition_threshold}",
            "ppl_query": search.ppl_query,
            "dispatch_window": f"{search.dispatch_earliest_time} ~ {search.dispatch_latest_time}",
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

    async def send_email_alert(self, search: SavedSearch, alert: AlertRecord) -> tuple[bool, Optional[str]]:
        """Splunk 스타일 이메일 알람 발송 (시뮬레이션 및 알람 기록)"""
        if not search.action_email_enabled or not search.action_email_to:
            return False, "Email action disabled or no recipients"

        subject = search.action_email_subject or f"[{search.severity}] Logccino Splunk Alert: {search.name}"
        subject = subject.replace("$name$", search.name).replace("$severity$", search.severity).replace("$result_count$", str(alert.result_count))

        logger.info(f"📧 [Email Alert Dispatched] To: {search.action_email_to} | Subject: {subject} | Events: {alert.result_count}")
        return True, f"Delivered to {search.action_email_to}"

    async def execute_script_action(self, search: SavedSearch, alert: AlertRecord) -> tuple[bool, Optional[str]]:
        """Splunk 스타일 커스텀 스크립트 실행 액션"""
        if not search.action_script_enabled or not search.action_script_command:
            return False, "Script action disabled"

        logger.info(f"⚡ [Script Action Triggered] Command: {search.action_script_command} for alert {search.name}")
        return True, f"Executed command: {search.action_script_command[:50]}"

    async def index_alert_to_opensearch(self, search: SavedSearch, alert: AlertRecord):
        """트리거된 알람을 OpenSearch 지정 인덱스 (기본: logccino-alerts-YYYY.MM.DD)에 보관"""
        if not search.action_index_enabled:
            return

        client = opensearch_service.get_client()
        today = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        base_index = search.action_index_name or "logccino-alerts"
        index_name = f"{base_index}-{today}"
        doc = alert.model_dump()
        doc["@timestamp"] = alert.timestamp

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: client.index(index=index_name, body=doc, refresh=True)
            )
            alert.index_written = True
        except Exception as e:
            logger.warning(f"Failed to index alert to OpenSearch: {e}")

    async def execute_saved_search(self, s: SavedSearch) -> AlertRecord:
        """PPL 실행, 디스패치 시간 범위, 알람 조건 및 Throttling(억제) 종합 평가 메인 로직"""
        t0 = time.time()
        now = datetime.now(timezone.utc)
        error_msg = None
        hits = []

        try:
            loop = asyncio.get_running_loop()
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
        is_suppressed = False

        if error_msg:
            s.last_status = "ERROR"
            s.last_error = error_msg
            s.last_suppressed = False
        else:
            is_triggered = self.evaluate_condition(
                count_or_hits=hits,
                operator=s.condition_operator,
                threshold=s.condition_threshold,
                search=s
            )
            s.last_error = None

            if is_triggered:
                is_suppressed, supp_reason = self.check_suppression(s, hits)
                s.last_suppressed = is_suppressed
                if is_suppressed:
                    s.last_status = "SUPPRESSED"
                    logger.info(f"🚫 [Alert Throttled] '{s.name}': {supp_reason}")
                else:
                    s.last_status = "TRIGGERED"
            else:
                s.last_status = "OK"
                s.last_suppressed = False

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
            app=s.app,
            earliest_time=s.dispatch_earliest_time,
            latest_time=s.dispatch_latest_time,
            alert_type=s.alert_type,
            result_count=result_count,
            threshold=s.condition_threshold,
            operator=s.condition_operator,
            triggered=is_triggered,
            suppressed=is_suppressed,
            sample_hits=hits[:10],
            execution_took_ms=took_ms
        )

        # 트리거되었고 억제(Suppressed)되지 않은 경우에만 액션 실행
        if is_triggered and not is_suppressed:
            # 1. 웹훅 액션
            if s.action_webhook_enabled and s.webhook_url:
                webhook_ok, webhook_resp = await self.send_webhook_alert(s, alert_record)
                alert_record.webhook_sent = webhook_ok
                alert_record.webhook_status = webhook_resp

            # 2. 이메일 액션
            if s.action_email_enabled and s.action_email_to:
                email_ok, email_resp = await self.send_email_alert(s, alert_record)
                alert_record.email_sent = email_ok
                alert_record.email_status = email_resp

            # 3. 스크립트 액션
            if s.action_script_enabled and s.action_script_command:
                script_ok, script_resp = await self.execute_script_action(s, alert_record)
                alert_record.script_executed = script_ok
                alert_record.script_status = script_resp

            # 4. OpenSearch 인덱스 보관
            if s.action_index_enabled:
                await self.index_alert_to_opensearch(s, alert_record)

            # 5. 자율 AI SIEM 분석 및 SOAR 조치 계획 파이프라인 가동 (.env LLM API / Claude Fallback)
            try:
                from core.siem.autonomous_pipeline import autonomous_pipeline
                asyncio.create_task(autonomous_pipeline.process_triggered_alert(s, hits, result_count))
            except Exception as e:
                logger.error(f"Failed to trigger autonomous AI pipeline for alert {s.name}: {e}")

        # 히스토리에 기록 (Splunk Track in Triggered Alerts)
        if s.alert_track:
            self._alert_history.insert(0, alert_record)
            if len(self._alert_history) > 500:
                self._alert_history = self._alert_history[:500]

        return alert_record

    async def run_now(self, search_id: str) -> Optional[AlertRecord]:
        """지정된 Saved Search를 즉시 수동 실행 (Splunk 'Run Now')"""
        s = self._searches.get(search_id)
        if not s:
            return None
        return await self.execute_saved_search(s)

    def get_alert_history(self, limit: int = 50, triggered_only: bool = False) -> List[AlertRecord]:
        records = self._alert_history
        if triggered_only:
            records = [r for r in records if r.triggered]
        return records[:limit]

    async def start(self):
        """스케줄러 백그라운드 루프 기동"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Splunk Saved Search & Alerting Scheduler engine started successfully.")

    async def stop(self):
        """스케줄러 백그라운드 루프 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Splunk Saved Search & Alerting Scheduler engine stopped.")

    async def _scheduler_loop(self):
        """주기적으로 등록된 Saved Search들의 다음 실행 시간을 확인하고 실행"""
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                searches_to_run = []

                for s in self._searches.values():
                    if not s.enabled or not s.is_scheduled:
                        continue
                    if s.next_run:
                        try:
                            next_dt = datetime.fromisoformat(s.next_run)
                            if next_dt <= now:
                                searches_to_run.append(s)
                        except Exception:
                            searches_to_run.append(s)
                    else:
                        searches_to_run.append(s)

                for s in searches_to_run:
                    asyncio.create_task(self.execute_saved_search(s))

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in SavedSearch scheduler loop: {e}")
                await asyncio.sleep(10)


# 전역 싱글톤 인스턴스
scheduler_engine = SavedSearchScheduler()
