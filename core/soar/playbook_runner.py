import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class WorkflowNode(BaseModel):
    id: str
    name: str
    node_type: str
    next_node_ids: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

class VisualPlaybookDefinition(BaseModel):
    playbook_id: str
    name: str
    description: str
    entry_node_id: str
    nodes: Dict[str, WorkflowNode] = Field(default_factory=dict)

class StepExecutionRecord(BaseModel):
    node_id: str
    node_name: str
    node_type: str
    status: str
    output: Dict[str, Any] = Field(default_factory=dict)
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PlaybookExecution(BaseModel):
    run_id: str
    playbook_id: str
    status: str
    current_node_id: Optional[str] = None
    approval_token: Optional[str] = None
    approval_details: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    step_history: List[StepExecutionRecord] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

class VisualSOAREngine:
    def __init__(self):
        self.playbooks: Dict[str, VisualPlaybookDefinition] = {}
        self.executions: Dict[str, PlaybookExecution] = {}
        self._init_default_playbooks()

    def _init_default_playbooks(self):
        pb1 = VisualPlaybookDefinition(
            playbook_id="pb_ssh_bruteforce_remediation",
            name="SSH 브루트포스 5단계 능동 대응 플레이북 (Maestro 호환)",
            description="AI 트리아지 -> CTI 평판 조회 -> 분석가 승인 -> 방화벽 DROP 및 세션 강제 종료",
            entry_node_id="node_trigger",
            nodes={
                "node_trigger": WorkflowNode(
                    id="node_trigger",
                    name="Alert Trigger Ingest",
                    node_type="trigger",
                    next_node_ids=["node_ai_triage"]
                ),
                "node_ai_triage": WorkflowNode(
                    id="node_ai_triage",
                    name="AI Autonomous Triage (CoT)",
                    node_type="ai_triage",
                    next_node_ids=["node_cti_lookup"]
                ),
                "node_cti_lookup": WorkflowNode(
                    id="node_cti_lookup",
                    name="IOC Reputation Query",
                    node_type="cti_lookup",
                    next_node_ids=["node_approval"]
                ),
                "node_approval": WorkflowNode(
                    id="node_approval",
                    name="Analyst Human-in-the-Loop Gate",
                    node_type="approval_gate",
                    next_node_ids=["node_active_response"],
                    config={"require_role": "TIER1_ANALYST", "timeout_sec": 3600}
                ),
                "node_active_response": WorkflowNode(
                    id="node_active_response",
                    name="Active Response Enforcement",
                    node_type="active_action",
                    next_node_ids=["node_notify"],
                    config={"action_type": "block_ip", "vendor": "UFW"}
                ),
                "node_notify": WorkflowNode(
                    id="node_notify",
                    name="Slack / Webhook Notification",
                    node_type="notify",
                    next_node_ids=[]
                )
            }
        )
        self.playbooks[pb1.playbook_id] = pb1

    def trigger_playbook(self, playbook_id: str, initial_context: Dict[str, Any]) -> PlaybookExecution:
        pb = self.playbooks.get(playbook_id)
        if not pb:
            raise ValueError(f"Playbook {playbook_id} not found")

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        execution = PlaybookExecution(
            run_id=run_id,
            playbook_id=playbook_id,
            status="running",
            current_node_id=pb.entry_node_id,
            context=initial_context.copy()
        )
        self.executions[run_id] = execution
        self._run_steps(execution)
        return execution

    def _run_steps(self, execution: PlaybookExecution):
        pb = self.playbooks[execution.playbook_id]

        while execution.status == "running" and execution.current_node_id:
            node = pb.nodes.get(execution.current_node_id)
            if not node:
                execution.status = "completed"
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                break

            if node.node_type == "approval_gate":
                execution.status = "waiting_approval"
                execution.approval_token = f"tok-{uuid.uuid4().hex[:16]}"
                execution.approval_details = {
                    "node_id": node.id,
                    "prompt": f"방화벽 차단 및 격리 조치에 대한 승인이 필요합니다. (대상: {execution.context.get('src_ip', '198.51.100.42')})",
                    "requires_role": node.config.get("require_role", "TIER1_ANALYST")
                }
                rec = StepExecutionRecord(
                    node_id=node.id,
                    node_name=node.name,
                    node_type=node.node_type,
                    status="paused_waiting_approval",
                    output={"token": execution.approval_token}
                )
                execution.step_history.append(rec)
                break

            out_data = self._execute_node_logic(node, execution.context)
            rec = StepExecutionRecord(
                node_id=node.id,
                node_name=node.name,
                node_type=node.node_type,
                status="success",
                output=out_data
            )
            execution.step_history.append(rec)
            execution.context.update(out_data)

            if node.next_node_ids:
                execution.current_node_id = node.next_node_ids[0]
            else:
                execution.current_node_id = None
                execution.status = "completed"
                execution.completed_at = datetime.now(timezone.utc).isoformat()

    def _execute_node_logic(self, node: WorkflowNode, context: Dict[str, Any]) -> Dict[str, Any]:
        ntype = node.node_type
        if ntype == "trigger":
            return {"ingested_alert": context.get("incident_id", "INC-ALERT-01")}
        elif ntype == "ai_triage":
            from core.siem.engine import siem_engine
            res = siem_engine.triage.triage_incident(context)
            return {"ai_verdict": res.adjusted_severity, "is_fp": res.is_false_positive, "cot": res.reasoning_chain}
        elif ntype == "cti_lookup":
            from core.siem.engine import siem_engine
            ip = context.get("src_ip", "198.51.100.42")
            rag = siem_engine.intel.query_unstructured_cti_rag(ip)
            return {"cti_threat": rag.is_known_threat, "cti_intel": rag.actionable_intel_summary}
        elif ntype == "active_action":
            from core.siem.engine import siem_engine
            target = context.get("src_ip", "198.51.100.42")
            act = siem_engine.soar.execute_active_response("block_ip", target, simulate_only=False)
            return {"active_action_status": act.status, "vendor": act.vendor_executed}
        elif ntype == "notify":
            return {"notification_sent": True, "channel": "Slack-SecOps-Alerts"}
        return {}

    def approve_step(self, run_id: str, token: str, approved: bool, notes: str = "") -> PlaybookExecution:
        execution = self.executions.get(run_id)
        if not execution:
            raise ValueError("Execution run not found")
        if execution.status != "waiting_approval" or execution.approval_token != token:
            raise ValueError("Invalid approval state or token mismatch")

        pb = self.playbooks[execution.playbook_id]
        curr_node = pb.nodes[execution.current_node_id]

        if not approved:
            execution.status = "rejected_by_analyst"
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            execution.step_history.append(StepExecutionRecord(
                node_id=curr_node.id,
                node_name=curr_node.name,
                node_type="approval_gate",
                status="rejected",
                output={"notes": notes}
            ))
            return execution

        execution.step_history.append(StepExecutionRecord(
            node_id=curr_node.id,
            node_name=curr_node.name,
            node_type="approval_gate",
            status="approved",
            output={"notes": notes}
        ))

        if curr_node.next_node_ids:
            execution.current_node_id = curr_node.next_node_ids[0]
            execution.status = "running"
            self._run_steps(execution)
        else:
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc).isoformat()

        return execution

    def list_executions(self) -> List[PlaybookExecution]:
        return list(self.executions.values())

visual_soar_engine = VisualSOAREngine()
