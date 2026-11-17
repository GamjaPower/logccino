import pytest
from fastapi.testclient import TestClient

from core.api.app import app
from core.ingestion.pii_masker import pii_masker
from core.security.integrity import integrity_engine
from core.detection.cep_stream import cep_stream_engine, CEPRuleDefinition
from core.soar.playbook_runner import visual_soar_engine
from core.apps.connector_store import connector_store
from core.mcp.tools import mcp_tools

@pytest.fixture
def client():
    return TestClient(app)

def test_pii_masking_engine():
    raw_text = "사용자 홍길동 900101-1234567 카드 4518-1234-5678-9012 폰 010-1234-5678 메일 test@example.com"
    masked = pii_masker.mask_text(raw_text)
    assert "900101-1******" in masked
    assert "4518-****-****-9012" in masked
    assert "010-****-5678" in masked
    assert "t***@example.com" in masked

    findings = pii_masker.detect_pii(raw_text)
    types = [f["type"] for f in findings]
    assert "RRN" in types
    assert "CARD" in types
    assert "PHONE" in types
    assert "EMAIL" in types

    nested_rec = {
        "user": {"name": "홍길동", "contact": "010-9876-5432"},
        "logs": ["주민번호 850101-2345678 접속 성공"]
    }
    masked_rec = pii_masker.mask_record(nested_rec)
    assert masked_rec["user"]["contact"] == "010-****-5432"
    assert "850101-2******" in masked_rec["logs"][0]

def test_cryptographic_log_integrity_worm():
    integrity_engine.chain.clear()
    logs_b0 = [
        "2026-11-17T10:00:00Z sshd[101]: login attempt",
        "2026-11-17T10:00:05Z ufw[201]: drop packet"
    ]
    block0 = integrity_engine.seal_block(logs_b0)
    assert block0.block_index == 0
    assert block0.prev_hash == "0" * 64
    assert len(block0.block_hash) == 64

    logs_b1 = ["2026-11-17T10:05:00Z sudo[301]: admin privilege"]
    block1 = integrity_engine.seal_block(logs_b1)
    assert block1.block_index == 1
    assert block1.prev_hash == block0.block_hash

    res = integrity_engine.verify_chain()
    assert res["is_valid"] is True
    assert res["total_blocks"] == 2

    original_root = block1.merkle_root
    block1.merkle_root = "tampered_fake_merkle_root"
    tampered_res = integrity_engine.verify_chain()
    assert tampered_res["is_valid"] is False
    assert tampered_res["tampered_block_index"] == 1
    block1.merkle_root = original_root

def test_in_memory_stream_cep_engine():
    cep_stream_engine.windows.clear()
    alerts = []
    for i in range(1, 5):
        ev = {
            "event_type": "ssh_failed",
            "src_ip": "198.51.100.99",
            "message": f"Failed password for admin attempt {i}"
        }
        res = cep_stream_engine.process_event(ev)
        assert len(res) == 0

    ev5 = {
        "event_type": "ssh_failed",
        "src_ip": "198.51.100.99",
        "message": "Failed password for admin attempt 5"
    }
    res5 = cep_stream_engine.process_event(ev5)
    assert len(res5) == 1
    assert res5[0].rule_id == "cep_ssh_bruteforce"
    assert res5[0].matched_count == 5
    assert "src_ip=198.51.100.99" in res5[0].key

    metrics = cep_stream_engine.get_metrics()
    assert metrics["total_triggered_alerts"] >= 1
    assert metrics["registered_rules_count"] >= 3

def test_visual_soar_playbook_runner_hitl():
    ctx = {
        "incident_id": "INC-TEST-001",
        "src_ip": "198.51.100.42",
        "user": "sst96"
    }
    execution = visual_soar_engine.trigger_playbook("pb_ssh_bruteforce_remediation", ctx)
    assert execution.status == "waiting_approval"
    assert execution.approval_token is not None
    assert len(execution.step_history) == 4

    run_id = execution.run_id
    token = execution.approval_token
    approved_exec = visual_soar_engine.approve_step(run_id, token, approved=True, notes="승인 완료")
    assert approved_exec.status == "completed"
    assert len(approved_exec.step_history) == 7

def test_logpresso_connector_store():
    catalog = connector_store.list_available_connectors()
    assert len(catalog) >= 3
    app_ids = [c.app_id for c in catalog]
    assert "connector_ahnlab_v3" in app_ids
    assert "connector_fortinet_fortigate" in app_ids

    install_res = connector_store.install_connector("connector_ahnlab_v3")
    assert install_res["status"] == "installed"
    assert install_res["rules_registered"] >= 1

    installed_list = connector_store.list_installed_connectors()
    assert any(c.app_id == "connector_ahnlab_v3" for c in installed_list)

    uninstall_res = connector_store.uninstall_connector("connector_ahnlab_v3")
    assert uninstall_res["status"] == "uninstalled"

def test_logpresso_rest_api_endpoints(client):
    r_pii = client.post("/api/v1/siem/pii/mask-text", json={"text": "010-1234-5678 및 900101-1234567"})
    assert r_pii.status_code == 200
    assert "010-****-5678" in r_pii.json()["masked"]
    assert "900101-1******" in r_pii.json()["masked"]

    r_seal = client.post("/api/v1/siem/integrity/seal-block", json={"records": ["event 1", "event 2"]})
    assert r_seal.status_code == 200
    assert "block_hash" in r_seal.json()

    r_verify = client.get("/api/v1/siem/integrity/verify")
    assert r_verify.status_code == 200
    assert r_verify.json()["is_valid"] is True

    r_cep = client.post("/api/v1/siem/cep/process-event", json={"event": {"event_type": "ssh_failed", "src_ip": "1.1.1.1", "message": "Failed password"}})
    assert r_cep.status_code == 200
    assert r_cep.json()["processed"] is True

    r_store = client.get("/api/v1/siem/connectors/store")
    assert r_store.status_code == 200
    assert len(r_store.json()) >= 3

def test_logpresso_mcp_tools():
    pii_res = mcp_tools.mask_pii("주민번호 920512-1928374")
    assert "920512-1******" in pii_res["masked"]

    b_res = mcp_tools.seal_log_integrity_block(["test log a", "test log b"])
    assert "merkle_root" in b_res

    v_res = mcp_tools.verify_log_integrity()
    assert v_res["is_valid"] is True

    c_res = mcp_tools.list_connector_store()
    assert len(c_res) >= 3
