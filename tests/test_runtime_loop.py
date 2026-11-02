"""Offline tests for the W2 runtime loop (tools/runtime_loop.py).

These exercise the REAL RuntimeLoop class against a real (small) snapshot
directory. No model, no network, no Docker. Each assertion tests actual
runtime behavior, not a mock.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from runtime_loop import ContractError, RuntimeLoop, replay  # noqa: E402


def _make_snapshot(tmp):
    d = Path(tmp) / "snap"
    d.mkdir()
    (d / "task.txt").write_text("task body", encoding="utf-8")
    (d / "answer.txt").write_text("42", encoding="utf-8")
    return d


def test_reset_then_step_done_produces_8_fields():
    with tempfile.TemporaryDirectory() as tmp:
        snap = _make_snapshot(tmp)
        loop = RuntimeLoop(snap, max_steps=4)
        rec = loop.run()
        # eight required fields (AG-W2-3)
        for k in ("run_id", "snapshot_id", "prompt_log", "tool_calls",
                  "latency_log", "verdict", "trace_id", "evidence"):
            assert rec.get(k) not in (None, "", [], {}), f"missing {k}"
        assert rec["verdict"] == "OK"


def test_digest_changes_are_detected_tampered():
    with tempfile.TemporaryDirectory() as tmp:
        snap = _make_snapshot(tmp)
        loop = RuntimeLoop(snap, max_steps=4)
        loop.reset()
        loop.step()  # at least one step so the 8-field check is satisfied
        # modify the snapshot after reset -> done() must report TAMPERED
        (snap / "task.txt").write_text("task body CHANGED", encoding="utf-8")
        rec = loop.done()
        assert rec["verdict"] == "TAMPERED"


def test_step_beyond_max_steps_raises_contract_error():
    with tempfile.TemporaryDirectory() as tmp:
        snap = _make_snapshot(tmp)
        loop = RuntimeLoop(snap, max_steps=1)
        loop.reset()
        loop.step()
        # second step exceeds max_steps=1 -> ContractError (AG-W2-2, fail-closed)
        try:
            loop.step()
            assert False, "expected ContractError"
        except ContractError:
            pass


def test_reset_is_single_use():
    with tempfile.TemporaryDirectory() as tmp:
        snap = _make_snapshot(tmp)
        loop = RuntimeLoop(snap)
        loop.reset()
        try:
            loop.reset()  # second reset -> ContractError (AG-W2-1)
            assert False, "expected ContractError"
        except ContractError:
            pass


def test_replay_is_deterministic_same_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        snap = _make_snapshot(tmp)
        v1 = replay(snap, max_steps=3)
        v2 = replay(snap, max_steps=3)
        assert v1["verdict"] == v2["verdict"]  # AG-W2-4
        assert v1["trace_id"] == v2["trace_id"]


def test_step_after_done_raises():
    with tempfile.TemporaryDirectory() as tmp:
        snap = _make_snapshot(tmp)
        loop = RuntimeLoop(snap, max_steps=3)
        loop.run()
        try:
            loop.step()
            assert False, "expected ContractError"
        except ContractError:
            pass
