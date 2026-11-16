import asyncio
from unittest.mock import MagicMock
from core.ai.assistant import ai_assistant
from core.query.builder import QueryBuilder
from core.query.executor import QueryExecutor
from core.ingestion.parser import LogParser

def test_log_parser():
    raw = '{"time": "2026-11-17T06:00:00Z", "level": "error", "message": "Connection refused", "service": "payment"}'
    parsed = LogParser.parse_record(raw)
    assert parsed["level"] == "ERROR"
    assert parsed["service"] == "payment"
    assert parsed["message"] == "Connection refused"
    print("Log parser test passed!")

def test_query_builder():
    dsl = QueryBuilder.build_search_query(
        query_string="Connection refused",
        level="ERROR",
        service="payment",
        start_time="2026-11-16T00:00:00Z",
        size=30
    )
    assert "query" in dsl
    assert "bool" in dsl["query"]
    filters = dsl["query"]["bool"]["filter"]
    # Check level and service filter
    levels = [f["term"]["level"] for f in filters if "term" in f and "level" in f["term"]]
    services = [f["term"]["service"] for f in filters if "term" in f and "service" in f["term"]]
    assert "ERROR" in levels
    assert "payment" in services
    print("QueryBuilder test passed!")

def test_natural_query_planning():
    query_text = "결제 서비스에서 발생한 타임아웃 에러 찾아줘"
    plan = asyncio.run(ai_assistant.plan_query_from_natural_language(query_text))

    assert "ppl_query" in plan, "PPL query must be generated"
    assert "source = logccino-logs-*" in plan["ppl_query"]
    assert "dsl_query" in plan, "OpenSearch native Query DSL must be generated"
    assert "query" in plan["dsl_query"]
    print(f"Natural query planning test passed! PPL: {plan['ppl_query']}")

def test_executor_ppl_to_dsl_fallback():
    executor = QueryExecutor()
    # Mocking client to simulate PPL failure
    mock_client = MagicMock()
    mock_client.transport.perform_request.side_effect = Exception("PPL plugin not found (404)")
    mock_client.search.return_value = {
        "took": 5,
        "hits": {
            "total": {"value": 1},
            "hits": [{"_source": {"service": "payment", "message": "timeout error", "level": "ERROR"}}]
        }
    }
    executor.client = mock_client

    ppl = "source = logccino-logs-* | where level = 'ERROR'"
    dsl = {"query": {"match_all": {}}}

    result = executor.execute_with_fallback(ppl_query=ppl, dsl_query=dsl)
    assert result["mode"] == "dsl_fallback", "Should seamlessly fallback to DSL when PPL fails"
    assert result["total"] == 1
    assert result["hits"][0]["service"] == "payment"
    print("PPL to native DSL fallback test passed!")

def test_executor_ppl_success():
    executor = QueryExecutor()
    mock_client = MagicMock()
    mock_client.transport.perform_request.return_value = {
        "schema": [{"name": "@timestamp", "type": "timestamp"}, {"name": "message", "type": "string"}],
        "datarows": [["2026-11-17T07:00:00Z", "Payment timeout error"]]
    }
    executor.client = mock_client

    ppl = "source = logccino-logs-* | where level = 'ERROR'"
    dsl = {"query": {"match_all": {}}}

    result = executor.execute_with_fallback(ppl_query=ppl, dsl_query=dsl)
    assert result["mode"] == "ppl", "Should use PPL when available and successful"
    assert result["total"] == 1
    assert result["hits"][0]["message"] == "Payment timeout error"
    print("PPL execution success test passed!")

def test_mcp_config_helper():
    from core.mcp.config_helper import get_all_mcp_configs
    configs = get_all_mcp_configs("http://logccino.company.internal/sse")
    assert "claude_desktop_remote_k8s_aws" in configs
    mcp_cfg = configs["claude_desktop_remote_k8s_aws"]["mcpServers"]["logccino"]
    assert "command" in mcp_cfg
    assert "args" in mcp_cfg
    assert "http://logccino.company.internal/sse" in mcp_cfg["args"]
    print("MCP config helper test passed!")

if __name__ == "__main__":
    test_log_parser()
    test_query_builder()
    test_natural_query_planning()
    test_executor_ppl_to_dsl_fallback()
    test_executor_ppl_success()
    test_mcp_config_helper()
    print("\nAll tests passed successfully!")
