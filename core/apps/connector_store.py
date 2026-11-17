from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ConnectorManifest(BaseModel):
    app_id: str
    name: str
    vendor: str
    version: str = "1.0.0"
    category: str = "security"
    description: str = ""
    icon: str = "shield"
    collector_type: str = "syslog"
    ecs_mapping: Dict[str, str] = Field(default_factory=dict)
    detection_rules: List[Dict[str, Any]] = Field(default_factory=list)
    playbook_ids: List[str] = Field(default_factory=list)

class LogpressoStyleConnectorStore:
    def __init__(self):
        self._store: Dict[str, ConnectorManifest] = {}
        self._installed: Dict[str, ConnectorManifest] = {}
        self._init_catalog()

    def _init_catalog(self):
        v3 = ConnectorManifest(
            app_id="connector_ahnlab_v3",
            name="AhnLab V3 Endpoint Security 커넥터",
            vendor="AhnLab Inc.",
            version="2.1.0",
            category="edr",
            description="안랩 V3 백신 진단 로그, 랜섬웨어 격리 및 실시간 EDR 침해 지표 수집",
            icon="shield-check",
            collector_type="syslog",
            ecs_mapping={
                "v3_action": "event.action",
                "virus_name": "threat.technique.name",
                "infected_path": "file.path",
                "pc_ip": "source.ip"
            },
            detection_rules=[
                {
                    "rule_id": "rule_v3_ransomware",
                    "name": "V3 랜섬웨어 행위 차단 알람",
                    "ppl": "source = main | where message like '%V3%' and message like '%Ransomware%'",
                    "severity": "critical"
                }
            ],
            playbook_ids=["pb_ssh_bruteforce_remediation"]
        )

        fortinet = ConnectorManifest(
            app_id="connector_fortinet_fortigate",
            name="Fortinet FortiGate 차세대 방화벽 커넥터",
            vendor="Fortinet",
            version="1.8.0",
            category="firewall",
            description="포티게이트 트래픽 로그, IPS 시그니처 차단 및 VPN 인증 이벤트 수집",
            icon="server",
            collector_type="syslog",
            ecs_mapping={
                "srcip": "source.ip",
                "dstip": "destination.ip",
                "action": "event.action",
                "attack": "threat.tactic.name"
            },
            detection_rules=[
                {
                    "rule_id": "rule_fortigate_ips_drop",
                    "name": "FortiGate IPS Exploit 차단 이벤트",
                    "ppl": "source = main | where message like '%fortigate%' and message like '%drop%'",
                    "severity": "high"
                }
            ],
            playbook_ids=[]
        )

        aws_gd = ConnectorManifest(
            app_id="connector_aws_guardduty",
            name="AWS GuardDuty 클라우드 위협 커넥터",
            vendor="Amazon Web Services",
            version="1.4.0",
            category="cloud",
            description="AWS 계정 내 비정상 API 호출, 암호화폐 채굴 인스턴스 탐지 이벤트 수집",
            icon="cloud",
            collector_type="webhook",
            ecs_mapping={
                "finding_type": "threat.technique.name",
                "resource_id": "host.name"
            },
            detection_rules=[
                {
                    "rule_id": "rule_guardduty_crypto",
                    "name": "AWS GuardDuty 비인가 가상화폐 채굴 탐지",
                    "ppl": "source = main | where message like '%CryptoCurrency%'",
                    "severity": "critical"
                }
            ],
            playbook_ids=[]
        )

        for c in [v3, fortinet, aws_gd]:
            self._store[c.app_id] = c

    def list_available_connectors(self) -> List[ConnectorManifest]:
        return list(self._store.values())

    def get_connector(self, app_id: str) -> Optional[ConnectorManifest]:
        return self._store.get(app_id)

    def install_connector(self, app_id: str) -> Dict[str, Any]:
        manifest = self._store.get(app_id)
        if not manifest:
            raise ValueError(f"Connector {app_id} not found in store catalog")

        self._installed[app_id] = manifest
        from core.apps.manager import app_manager
        from core.apps.models import InstallAppRequest

        req = InstallAppRequest(
            id=manifest.app_id,
            name=manifest.name,
            description=manifest.description,
            version=manifest.version,
            author=manifest.vendor,
            icon=manifest.icon,
            category=manifest.category,
            enabled=True
        )
        if not app_manager.get_app(manifest.app_id):
            app_manager.install_app(req)
        else:
            app_manager.toggle_app(manifest.app_id, enabled=True)

        rules_installed = len(manifest.detection_rules)
        return {
            "status": "installed",
            "app_id": app_id,
            "name": manifest.name,
            "rules_registered": rules_installed,
            "vendor": manifest.vendor,
            "installed_at": datetime.now(timezone.utc).isoformat()
        }

    def list_installed_connectors(self) -> List[ConnectorManifest]:
        return list(self._installed.values())

    def uninstall_connector(self, app_id: str) -> Dict[str, Any]:
        if app_id in self._installed:
            del self._installed[app_id]
        from core.apps.manager import app_manager
        app_manager.uninstall_app(app_id)
        return {"status": "uninstalled", "app_id": app_id}

connector_store = LogpressoStyleConnectorStore()
