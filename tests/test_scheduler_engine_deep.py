import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.scheduler.engine import SavedSearchScheduler, scheduler_engine
from core.scheduler.models import SavedSearch, SavedSearchCreate, SavedSearchUpdate, AlertRecord

def test_evaluate_condition_all_operators():
    s = SavedSearchScheduler()
    # gt (>):
    assert s.evaluate_condition(5, "gt", 3.0) is True
    assert s.evaluate_condition(3, "gt", 3.0) is False
    assert s.evaluate_condition(2, "gt", 3.0) is False

    # gte (>=):
    assert s.evaluate_condition(3, "gte", 3.0) is True
    assert s.evaluate_condition(4, "gte", 3.0) is True
    assert s.evaluate_condition(2, "gte", 3.0) is False

    # lt (<):
    assert s.evaluate_condition(2, "lt", 3.0) is True
    assert s.evaluate_condition(3, "lt", 3.0) is False

    # lte (<=):
    assert s.evaluate_condition(3, "lte", 3.0) is True
    assert s.evaluate_condition(2, "lte", 3.0) is True
    assert s.evaluate_condition(4, "lte", 3.0) is False

    # eq (==):
    assert s.evaluate_condition(0, "eq", 0.0) is True
    assert s.evaluate_condition(1, "eq", 0.0) is False

    # neq (!=):
    assert s.evaluate_condition(1, "neq", 0.0) is True
    assert s.evaluate_condition(0, "neq", 0.0) is False

    # Unknown operator:
    assert s.evaluate_condition(5, "unknown_op", 3.0) is False

def test_saved_search_crud():
    scheduler = SavedSearchScheduler()
    
    # 1. Create
    req = SavedSearchCreate(
        name="Test Memory Spike Alert",
        description="Detects high memory events",
        ppl_query="source = logccino-logs-* | where memory > 90",
        interval_seconds=45,
        condition_operator="gt",
        condition_threshold=5.0,
        severity="HIGH",
        webhook_url="https://hooks.example.com/test",
        enabled=True
    )
    created = scheduler.create(req)
    assert created.id in scheduler._searches
    assert created.name == "Test Memory Spike Alert"
    assert created.interval_seconds == 45

    # 2. Update
    up_req = SavedSearchUpdate(
        name="Updated Memory Spike Alert",
        condition_threshold=10.0,
        severity="CRITICAL"
    )
    updated = scheduler.update(created.id, up_req)
    assert updated.name == "Updated Memory Spike Alert"
    assert updated.condition_threshold == 10.0
    assert updated.severity == "CRITICAL"

    # 3. Get
    got = scheduler.get(created.id)
    assert got.id == created.id

    # 4. Delete
    deleted = scheduler.delete(created.id)
    assert deleted is True
    assert scheduler.get(created.id) is None
    assert scheduler.delete("non-existent-id") is False

def test_execute_saved_search_mocked_results():
    async def _run():
        scheduler = SavedSearchScheduler()
        search = SavedSearch(
            id="test-exec-1",
            name="Execution Test Search",
            ppl_query="source = logccino-logs-* | head 10",
            interval_seconds=60,
            condition_operator="gt",
            condition_threshold=2.0,
            severity="HIGH",
            enabled=True
        )

        # 1. Triggered case (5 hits > 2 threshold)
        with patch.object(scheduler.executor, "execute_ppl", return_value={"hits": [1, 2, 3, 4, 5]}), \
             patch.object(scheduler.executor, "format_ppl_response", return_value=[{"msg": f"log{i}"} for i in range(5)]), \
             patch.object(scheduler, "index_alert_to_opensearch", new_callable=AsyncMock):
            
            alert = await scheduler.execute_saved_search(search)
            assert alert.triggered is True
            assert alert.result_count == 5
            assert search.last_status == "TRIGGERED"

        # 2. OK case (1 hit <= 2 threshold)
        with patch.object(scheduler.executor, "execute_ppl", return_value={"hits": [1]}), \
             patch.object(scheduler.executor, "format_ppl_response", return_value=[{"msg": "log0"}]):
            
            alert2 = await scheduler.execute_saved_search(search)
            assert alert2.triggered is False
            assert alert2.result_count == 1
            assert search.last_status == "OK"

        # 3. Error case
        with patch.object(scheduler.executor, "execute_ppl", side_effect=Exception("PPL syntax error at line 1")):
            alert3 = await scheduler.execute_saved_search(search)
            assert alert3.triggered is False
            assert search.last_status == "ERROR"
            assert "syntax error" in search.last_error

    asyncio.run(_run())

def test_alert_history_max_capacity_and_filtering():
    scheduler = SavedSearchScheduler()
    scheduler._alert_history.clear()

    for i in range(120):
        scheduler._alert_history.insert(0, AlertRecord(
            id=f"alert-{i}",
            saved_search_id="s1",
            saved_search_name="Search",
            timestamp="2026-11-17T00:00:00Z",
            severity="HIGH",
            ppl_query="query",
            result_count=i,
            threshold=10.0,
            operator="gt",
            triggered=(i % 2 == 0)
        ))
        if len(scheduler._alert_history) > 100:
            scheduler._alert_history.pop()

    assert len(scheduler._alert_history) == 100

    # Triggered only filter
    triggered_list = scheduler.get_alert_history(limit=50, triggered_only=True)
    assert len(triggered_list) == 50
    assert all(a.triggered for a in triggered_list)

def test_webhook_alert_dispatch():
    async def _run():
        scheduler = SavedSearchScheduler()
        search = SavedSearch(
            id="s-webhook",
            name="Webhook Search",
            ppl_query="query",
            interval_seconds=60,
            webhook_url="https://hooks.slack.com/test",
            enabled=True
        )
        alert = AlertRecord(
            id="a1",
            saved_search_id="s-webhook",
            saved_search_name="Webhook Search",
            timestamp="2026-11-17T00:00:00Z",
            severity="CRITICAL",
            ppl_query="query",
            result_count=10,
            threshold=0.0,
            operator="gt",
            triggered=True
        )

        # 1. No webhook
        search_no_hook = SavedSearch(id="s2", name="No hook", ppl_query="q", interval_seconds=60, webhook_url=None)
        ok, msg = await scheduler.send_webhook_alert(search_no_hook, alert)
        assert ok is False
        assert "No webhook" in msg

        # 2. Mock 200 response
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            ok2, msg2 = await scheduler.send_webhook_alert(search, alert)
            assert ok2 is True
            assert "HTTP 200" in msg2

        # 3. Mock 500 error response
        with patch("httpx.AsyncClient.post") as mock_post2:
            mock_resp2 = MagicMock()
            mock_resp2.status_code = 500
            mock_resp2.text = "Internal Server Error"
            mock_post2.return_value = mock_resp2

            ok3, msg3 = await scheduler.send_webhook_alert(search, alert)
            assert ok3 is False
            assert "HTTP 500" in msg3

    asyncio.run(_run())
