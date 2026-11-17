import time
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class CEPRuleDefinition(BaseModel):
    rule_id: str
    name: str
    window_seconds: int = 60
    threshold_count: int = 5
    group_by_field: str = "src_ip"
    severity: str = "high"
    description: str = ""

class CEPTravelAlert(BaseModel):
    alert_id: str
    rule_id: str
    rule_name: str
    severity: str
    key: str
    matched_count: int
    window_seconds: int
    detected_at: str
    sample_messages: List[str] = Field(default_factory=list)

class InMemoryStreamCEPEngine:
    def __init__(self):
        self.rules: Dict[str, CEPRuleDefinition] = {}
        self.predicates: Dict[str, Callable[[Dict[str, Any]], bool]] = {}
        self.windows: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.total_processed_events: int = 0
        self.total_triggered_alerts: int = 0
        self._init_default_rules()

    def _init_default_rules(self):
        self.register_rule(
            rule=CEPRuleDefinition(
                rule_id="cep_ssh_bruteforce",
                name="실시간 스트림 SSH 무차별 대입 탐지 (CEP)",
                window_seconds=60,
                threshold_count=5,
                group_by_field="src_ip",
                severity="critical",
                description="동일 출발지 IP에서 60초 내 5회 이상 인증 실패 감지"
            ),
            predicate=lambda ev: "failed password" in str(ev.get("message", "")).lower() or ev.get("event_type") == "ssh_failed"
        )

        self.register_rule(
            rule=CEPRuleDefinition(
                rule_id="cep_port_scan",
                name="실시간 고속 포트 스캔 탐지 (CEP)",
                window_seconds=30,
                threshold_count=8,
                group_by_field="src_ip",
                severity="high",
                description="동일 IP에서 30초 내 8회 이상의 비인가 포트 노크 탐지"
            ),
            predicate=lambda ev: "scan" in str(ev.get("message", "")).lower() or ev.get("event_type") == "port_scan"
        )

        self.register_rule(
            rule=CEPRuleDefinition(
                rule_id="cep_sudo_abuse",
                name="단시간 Sudo 권한 획득 이상 폭증 (CEP)",
                window_seconds=20,
                threshold_count=3,
                group_by_field="user",
                severity="high",
                description="동일 사용자에 의한 20초 내 3회 이상의 연속 sudo 실행"
            ),
            predicate=lambda ev: "sudo" in str(ev.get("message", "")).lower() or ev.get("event_type") == "sudo_failed"
        )

    def register_rule(self, rule: CEPRuleDefinition, predicate: Callable[[Dict[str, Any]], bool]):
        self.rules[rule.rule_id] = rule
        self.predicates[rule.rule_id] = predicate

    def process_event(self, event: Dict[str, Any]) -> List[CEPTravelAlert]:
        self.total_processed_events += 1
        now = time.time()
        triggered_alerts = []

        for r_id, rule in self.rules.items():
            pred = self.predicates.get(r_id)
            if not pred or not pred(event):
                continue

            group_val = str(event.get(rule.group_by_field) or event.get("host") or "unknown")
            dq = self.windows[r_id][group_val]
            dq.append((now, event))

            cutoff = now - rule.window_seconds
            while dq and dq[0][0] < cutoff:
                dq.popleft()

            if len(dq) >= rule.threshold_count:
                samples = [str(item[1].get("message", item[1])) for item in list(dq)[-3:]]
                matched_cnt = len(dq)
                dq.clear()
                self.total_triggered_alerts += 1

                alert = CEPTravelAlert(
                    alert_id=f"cep-alert-{int(now * 1000)}",
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    key=f"{rule.group_by_field}={group_val}",
                    matched_count=matched_cnt,
                    window_seconds=rule.window_seconds,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    sample_messages=samples
                )
                triggered_alerts.append(alert)

        return triggered_alerts

    def get_metrics(self) -> Dict[str, Any]:
        active_buckets_cnt = sum(len(sub) for sub in self.windows.values())
        return {
            "total_processed_events": self.total_processed_events,
            "total_triggered_alerts": self.total_triggered_alerts,
            "registered_rules_count": len(self.rules),
            "active_tracking_buckets": active_buckets_cnt
        }

cep_stream_engine = InMemoryStreamCEPEngine()
