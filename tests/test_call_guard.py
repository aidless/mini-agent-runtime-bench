"""Offline tests for the call guard parser (tools/call_guard.py).

These exercise the REAL parse_call function. No model, no network. The parser
is deliberately fail-closed: any malformed input must return ok=False, never
raise.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from call_guard import parse_call  # noqa: E402


def test_valid_call_parses_tool_and_args():
    r = parse_call('{"tool": "fs.read", "args": {"path": "/x"}}')
    assert r["ok"] is True
    assert r["tool"] == "fs.read"
    assert r["args"] == {"path": "/x"}


def test_empty_input_is_rejected():
    assert parse_call("")["ok"] is False
    assert parse_call(None)["ok"] is False


def test_non_json_is_rejected():
    assert parse_call("not json at all")["ok"] is False


def test_trailing_comma_is_tolerated():
    r = parse_call('{"tool": "fs.read", "args": {"a": 1,},}')
    assert r["ok"] is True
    assert r["tool"] == "fs.read"


def test_fence_wrapped_json_is_stripped():
    r = parse_call('```json\n{"tool": "fs.read", "args": {}}\n```')
    assert r["ok"] is True
    assert r["tool"] == "fs.read"


def test_never_raises_on_garbage():
    for bad in (123, ["x"], {"tool": 5}, "{{{{", '{"tool": "a", "args": []}'):
        r = parse_call(bad)
        assert r["ok"] is False, f"should reject {bad!r}"
        assert "error_kind" in r
