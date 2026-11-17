import pytest
from core.query.join_engine import SplunkJoinEngine, JoinSpec

def test_is_join_query_variations():
    # Valid join queries
    assert SplunkJoinEngine.is_join_query("source = main | join host [ source = app ]") is True
    assert SplunkJoinEngine.is_join_query("source = main\n| JOIN type=left host\n  [ source = app ]") is True
    assert SplunkJoinEngine.is_join_query("source = main | stats count() | join type=outer host, service [ source = logs ] | head 10") is True

    # Non-join queries
    assert SplunkJoinEngine.is_join_query("source = main | stats count() by host") is False
    assert SplunkJoinEngine.is_join_query("source = main | where message = 'please join the meeting'") is False
    assert SplunkJoinEngine.is_join_query("") is False
    assert SplunkJoinEngine.is_join_query(None) is False

def test_parse_join_query_default_inner():
    q = "source = main | stats count by host | join host [ source = app | stats sum(bytes) by host ]"
    spec = SplunkJoinEngine.parse_join_query(q)
    assert spec is not None
    assert spec.join_type == "inner"
    assert spec.keys == ["host"]
    assert "source = main" in spec.left_query
    assert "source = app" in spec.right_query
    assert spec.post_pipe is None

def test_parse_join_query_explicit_types_and_keys():
    for jtype in ["left", "right", "outer", "inner"]:
        q = f"source = main | join type={jtype} host, service [ source = app ]"
        spec = SplunkJoinEngine.parse_join_query(q)
        assert spec is not None
        assert spec.join_type == jtype
        assert spec.keys == ["host", "service"]

def test_parse_join_query_nested_subsearches():
    nested_q = "source = main | join host [ source = app | join user_id [ source = auth | stats count ] ]"
    spec = SplunkJoinEngine.parse_join_query(nested_q)
    assert spec is not None
    assert spec.join_type == "inner"
    assert spec.keys == ["host"]
    assert "source = app | join user_id [ source = auth | stats count ]" in spec.right_query

def test_parse_join_query_with_post_pipe():
    q = "source = main | join type=left host [ source = app ] | where sec > 10 | head 5 | sort - count"
    spec = SplunkJoinEngine.parse_join_query(q)
    assert spec is not None
    assert spec.join_type == "left"
    assert spec.post_pipe == "where sec > 10 | head 5 | sort - count"

def test_parse_join_query_invalid_syntax():
    assert SplunkJoinEngine.parse_join_query("source = main | head 10") is None
    assert SplunkJoinEngine.parse_join_query("source = main | join host [ unclosed subquery") is None
    assert SplunkJoinEngine.parse_join_query("source = main | join host") is None

def test_hash_join_inner():
    left = [
        {"host": "h1", "sec": 10},
        {"host": "h2", "sec": 20},
        {"host": "h3", "sec": 30}
    ]
    right = [
        {"host": "h2", "app": 200},
        {"host": "h3", "app": 300},
        {"host": "h4", "app": 400}
    ]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="inner")
    assert len(res) == 2
    hosts = [r["host"] for r in res]
    assert "h2" in hosts and "h3" in hosts
    assert "h1" not in hosts and "h4" not in hosts

def test_hash_join_left():
    left = [
        {"host": "h1", "sec": 10},
        {"host": "h2", "sec": 20}
    ]
    right = [
        {"host": "h2", "app": 200}
    ]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="left")
    assert len(res) == 2
    h1 = next(r for r in res if r["host"] == "h1")
    h2 = next(r for r in res if r["host"] == "h2")
    assert h1.get("app") is None
    assert h2.get("app") == 200

def test_hash_join_right():
    left = [
        {"host": "h2", "sec": 20}
    ]
    right = [
        {"host": "h2", "app": 200},
        {"host": "h3", "app": 300}
    ]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="right")
    assert len(res) == 2
    h2 = next(r for r in res if r["host"] == "h2")
    h3 = next(r for r in res if r["host"] == "h3")
    assert h2.get("sec") == 20
    assert h3.get("sec") is None
    assert h3.get("app") == 300

def test_hash_join_full_outer():
    left = [{"host": "h1", "sec": 10}]
    right = [{"host": "h2", "app": 20}]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="outer")
    assert len(res) == 2
    hosts = [r["host"] for r in res]
    assert "h1" in hosts and "h2" in hosts

def test_hash_join_duplicates_many_to_many():
    left = [
        {"host": "h1", "item": "A"},
        {"host": "h1", "item": "B"}
    ]
    right = [
        {"host": "h1", "val": 1},
        {"host": "h1", "val": 2}
    ]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="inner")
    assert len(res) == 4

def test_hash_join_multi_key_and_none():
    left = [
        {"host": "h1", "env": "prod", "val": 1},
        {"host": "h1", "env": "dev", "val": 2},
        {"host": "h2", "env": None, "val": 3}
    ]
    right = [
        {"host": "h1", "env": "prod", "tag": "active"},
        {"host": "h1", "env": "qa", "tag": "inactive"},
        {"host": "h2", "env": None, "tag": "unknown"}
    ]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host", "env"], how="inner")
    assert len(res) == 2
    r_prod = next(r for r in res if r["host"] == "h1")
    assert r_prod["env"] == "prod" and r_prod["tag"] == "active"
    r_none = next(r for r in res if r["host"] == "h2")
    assert r_none["env"] is None and r_none["tag"] == "unknown"

def test_hash_join_field_collision_resolution():
    left = [{"host": "h1", "status": "UP", "count": 10}]
    right = [{"host": "h1", "status": "HEALTHY", "count": 20}]
    res = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="inner")
    assert len(res) == 1
    rec = res[0]
    assert rec["status"] == "UP"
    assert rec["count"] == 10
    assert rec["right_status"] == "HEALTHY"
    assert rec["right_count"] == 20

def test_apply_post_pipe():
    records = [
        {"host": "h1", "val": 30},
        {"host": "h2", "val": 10},
        {"host": "h3", "val": 20},
        {"host": "h4", "val": 50}
    ]
    # head
    head_res = SplunkJoinEngine.apply_post_pipe(records, "head 2")
    assert len(head_res) == 2
    assert head_res[0]["host"] == "h1"

    # tail
    tail_res = SplunkJoinEngine.apply_post_pipe(records, "tail 2")
    assert len(tail_res) == 2
    assert tail_res[-1]["host"] == "h4"

    # sort ascending & descending
    sorted_asc = SplunkJoinEngine.apply_post_pipe(records, "sort val")
    assert [r["val"] for r in sorted_asc] == [10, 20, 30, 50]

    sorted_desc = SplunkJoinEngine.apply_post_pipe(records, "sort -val")
    assert [r["val"] for r in sorted_desc] == [50, 30, 20, 10]

    # fields
    fields_res = SplunkJoinEngine.apply_post_pipe(records, "fields host")
    assert all("val" not in r and "host" in r for r in fields_res)
