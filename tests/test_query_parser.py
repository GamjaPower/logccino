from core.query.spl_parser import SplunkToPPLTranslator
from core.ingestion.parser import LogParser

def test_splunk_to_ppl():
    spl = "search service=auth level=ERROR | stats count by host"
    ppl = SplunkToPPLTranslator.translate(spl)
    assert "source = logccino-logs-*" in ppl
    assert "stats count by host" in ppl
    print(f"SPL translation test passed: {ppl}")

def test_log_parser():
    raw = '{"time": "2026-11-17T06:00:00Z", "level": "error", "message": "Connection refused", "service": "payment"}'
    parsed = LogParser.parse_record(raw)
    assert parsed["level"] == "ERROR"
    assert parsed["service"] == "payment"
    assert parsed["message"] == "Connection refused"
    print("Log parser test passed!")

if __name__ == "__main__":
    test_splunk_to_ppl()
    test_log_parser()
