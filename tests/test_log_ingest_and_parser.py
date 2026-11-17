import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.ingestion.parser import LogParser
from core.ingestion.pipeline import IngestionPipeline

client = TestClient(app)

def test_log_parser_dict_variations():
    # 1. @timestamp & level & msg
    d1 = {"@timestamp": "2026-11-17T01:00:00Z", "level": "warn", "msg": "CPU high", "host": "srv1", "service": "auth"}
    p1 = LogParser.parse_record(d1)
    assert p1["@timestamp"] == "2026-11-17T01:00:00Z"
    assert p1["level"] == "WARN"
    assert p1["message"] == "CPU high"
    assert p1["host"] == "srv1"
    assert p1["service"] == "auth"

    # 2. time & severity & message
    d2 = {"time": "2026-11-17T02:00:00Z", "severity": "error", "message": "Disk full", "app": "db"}
    p2 = LogParser.parse_record(d2)
    assert p2["@timestamp"] == "2026-11-17T02:00:00Z"
    assert p2["level"] == "ERROR"
    assert p2["message"] == "Disk full"
    assert p2["service"] == "db"

    # 3. Extra custom attributes preserved
    d3 = {"time": "2026-11-17T03:00:00Z", "level": "info", "message": "ok", "custom_id": 999, "tags": ["prod", "kr"]}
    p3 = LogParser.parse_record(d3)
    assert p3["attributes"]["custom_id"] == 999
    assert p3["attributes"]["tags"] == ["prod", "kr"]

def test_log_parser_string_json():
    raw_str = json.dumps({
        "timestamp": "2026-11-17T04:00:00Z",
        "loglevel": "debug",
        "message": "Cache hit",
        "cache_key": "user:123"
    })
    parsed = LogParser.parse_record(raw_str, host="worker-01", service="cache-svc")
    assert parsed["sourcetype"] == "json"
    assert parsed["level"] == "DEBUG"
    assert parsed["message"] == "Cache hit"
    assert parsed["attributes"]["cache_key"] == "user:123"

def test_log_parser_plain_text_inference():
    # ERROR inference
    p_err = LogParser.parse_record("Database Connection Fatal Error on port 5432")
    assert p_err["level"] == "ERROR"
    assert "Database Connection" in p_err["message"]

    # WARN inference
    p_warn = LogParser.parse_record("[WARNING] Memory usage exceeded 85%")
    assert p_warn["level"] == "WARN"

    # DEBUG inference
    p_debug = LogParser.parse_record("debug: entering method processPayment()")
    assert p_debug["level"] == "DEBUG"

    # Default INFO inference
    p_info = LogParser.parse_record("HTTP 200 GET /healthz 12ms")
    assert p_info["level"] == "INFO"

def test_ingestion_pipeline_index_naming():
    pipeline = IngestionPipeline(index_prefix="test-logs")
    # Custom index
    assert pipeline.get_target_index(custom_index="main") == "main"
    assert pipeline.get_target_index(custom_index="security-alerts") == "security-alerts"

    # Date-based index
    dt = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)
    target = pipeline.get_target_index(dt=dt)
    assert target == "test-logs-2026.11.17"

def test_ingestion_pipeline_empty_records():
    pipeline = IngestionPipeline()
    res = pipeline.ingest_records([])
    assert res["success"] == 0
    assert res["failed"] == 0

def test_ingestion_pipeline_bulk_mocked():
    with patch("core.ingestion.pipeline.bulk") as mock_bulk:
        mock_bulk.return_value = (3, 0)
        pipeline = IngestionPipeline(index_prefix="logccino-logs")
        records = [
            {"message": "log1", "index": "main"},
            {"message": "log2"},
            {"message": "log3", "index": "security"}
        ]
        res = pipeline.ingest_records(records, target_index="logccino-logs-default")
        assert res["success"] == 3
        assert res["failed"] == 0

        # Verify bulk actions
        assert mock_bulk.call_count == 1
        actions = mock_bulk.call_args[0][1]
        assert len(actions) == 3
        assert actions[0]["_index"] == "main"
        assert actions[1]["_index"] == "logccino-logs-default"
        assert actions[2]["_index"] == "security"

def test_api_ingest_batch_endpoint():
    payload = {
        "logs": [
            {
                "message": "Payment service initialized",
                "service": "billing",
                "level": "INFO",
                "host": "prod-srv-01",
                "attributes": {"cluster": "kr-west-1"}
            },
            {
                "message": "Payment transaction timeout",
                "service": "billing",
                "level": "ERROR",
                "host": "prod-srv-02"
            }
        ]
    }
    res = client.post("/api/v1/ingest/batch", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "success" in data
    assert data["success"] >= 2

def test_api_ingest_syslog_to_main_index():
    payload = {
        "events": [
            {
                "timestamp": "2026-11-17T07:00:00Z",
                "facility": "auth",
                "severity": "crit",
                "host": "firewall-gw",
                "app_name": "iptables",
                "message": "DROP INPUT from 198.51.100.22 port 445",
                "event_type": "security"
            }
        ]
    }
    res = client.post("/api/v1/ingest/syslog?target_index=main", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "success")
    assert data["ingested"] == 1
    assert data["target_index"] == "main"
