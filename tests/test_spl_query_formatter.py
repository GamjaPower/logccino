import re
import pytest

def format_splunk_query(raw_query: str) -> str:
    r"""
    Python reference implementation of the Splunk SPL Command + \ auto-formatter
    matching core/api/routes/dashboard.py formatSplunkQuery()
    """
    if not raw_query:
        return ""
    trimmed = raw_query.strip()

    # 1. Normalize linebreaks and whitespace outside quotes into single space
    normalized = ""
    in_d = False
    in_s = False
    esc = False
    for ch in trimmed:
        if esc:
            normalized += ch
            esc = False
            continue
        if ch == "\\":
            esc = True
            normalized += ch
            continue
        if ch == '"' and not in_s:
            in_d = not in_d
            normalized += ch
            continue
        if ch == "'" and not in_d:
            in_s = not in_s
            normalized += ch
            continue
        if in_d or in_s:
            normalized += ch
            continue
        if ch in ("\r", "\n", "\t"):
            normalized += " "
            continue
        normalized += ch

    single_line = re.sub(r"\s+", " ", normalized).strip()

    # 2. Stateful SPL parser with 4-space indentation per bracket depth
    formatted = ""
    bracket_depth = 0
    indent_step = "    "
    in_double = False
    in_single = False
    escape = False

    i = 0
    while i < len(single_line):
        ch = single_line[i]
        if escape:
            formatted += ch
            escape = False
            i += 1
            continue
        if ch == "\\":
            escape = True
            formatted += ch
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            formatted += ch
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            formatted += ch
            i += 1
            continue
        if in_double or in_single:
            formatted += ch
            i += 1
            continue

        if ch == "[":
            bracket_depth += 1
            formatted = formatted.rstrip()
            formatted += "\n" + (indent_step * bracket_depth) + "[ "
            while i + 1 < len(single_line) and single_line[i + 1] == " ":
                i += 1
            i += 1
            continue

        if ch == "]":
            formatted = formatted.rstrip()
            formatted += " ]"
            bracket_depth = max(0, bracket_depth - 1)
            i += 1
            continue

        if ch == "|":
            formatted = formatted.rstrip()
            current_indent = indent_step * bracket_depth
            formatted += "\n" + current_indent + "| "
            while i + 1 < len(single_line) and single_line[i + 1] == " ":
                i += 1
            i += 1
            continue

        formatted += ch
        i += 1

    multi_line = formatted.strip()
    if trimmed == multi_line:
        return single_line
    return multi_line


def test_basic_pipeline_split():
    raw = "source = main | stats count() as total by host | where total > 5"
    res = format_splunk_query(raw)
    expected = (
        "source = main\n"
        "| stats count() as total by host\n"
        "| where total > 5"
    )
    assert res == expected

def test_join_subsearch_indentation():
    raw = "source = main | stats count() as sec by host | join type=left host [ source = app | stats count() as app by host ] | where sec > 0"
    res = format_splunk_query(raw)
    expected = (
        "source = main\n"
        "| stats count() as sec by host\n"
        "| join type=left host\n"
        "    [ source = app\n"
        "    | stats count() as app by host ]\n"
        "| where sec > 0"
    )
    assert res == expected

def test_nested_subsearches_deep():
    raw = "source = main | join host [ source = app | join user_id [ source = auth | stats count ] ]"
    res = format_splunk_query(raw)
    expected = (
        "source = main\n"
        "| join host\n"
        "    [ source = app\n"
        "    | join user_id\n"
        "        [ source = auth\n"
        "        | stats count ] ]"
    )
    assert res == expected

def test_quotes_protection():
    raw = 'source = main | eval status=if(code == 200, "PASS|OK", "FAIL|ERR") | rex "\\[(?<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)\\]"'
    res = format_splunk_query(raw)
    # The pipe inside "PASS|OK" must NOT become a new line
    assert '"PASS|OK"' in res
    assert '"\\[(?<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)\\]"' in res
    lines = res.split("\n")
    assert len(lines) == 3
    assert lines[1].startswith("| eval status=")
    assert lines[2].startswith('| rex ')

def test_toggle_behavior():
    original = "source = main | stats count by host | join host [ source = app | stats count ]"
    formatted = format_splunk_query(original)
    assert "\n" in formatted

    # Running again on exact formatted output toggles back to single line
    toggled_single = format_splunk_query(formatted)
    assert "\n" not in toggled_single
    assert "source = main | stats count by host | join host [ source = app | stats count ]" == toggled_single

    # Running on single line expands back to formatted
    re_expanded = format_splunk_query(toggled_single)
    assert re_expanded == formatted

def test_messy_pasted_query_normalization():
    messy = (
        "source = main \n\n"
        "  |  stats count()   by host\n\t"
        "| join type=left host [\n"
        "    source = app\n"
        "  | stats sum(b) by host\n"
        " ]\n"
        "| where host = 'bastion-gateway' "
    )
    clean = format_splunk_query(messy)
    expected = (
        "source = main\n"
        "| stats count() by host\n"
        "| join type=left host\n"
        "    [ source = app\n"
        "    | stats sum(b) by host ]\n"
        "| where host = 'bastion-gateway'"
    )
    assert clean == expected
