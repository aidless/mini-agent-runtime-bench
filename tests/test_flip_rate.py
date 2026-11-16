"""Offline checks for the scripted flip-rate pipeline.

No model, no network. The assertions call the real recomputation.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import compute_flip_rate as flip  # noqa: E402
from scripted_policies import (  # noqa: E402
    POLICIES,
    TASK_SPECS,
    apply_op,
    task_record,
)


def _load_runtime_gates():
    spec = importlib.util.spec_from_file_location(
        "check_runtime_gates", TOOLS / "check_runtime_gates.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_copy_matches_task_specs_and_gold():
    text = flip.render_tasks_jsonl()
    tasks = flip.load_tasks(text)
    assert len(tasks) == len(TASK_SPECS)
    assert 10 <= len(tasks) <= 30
    for entry, task in zip(TASK_SPECS, tasks):
        assert task["task_id"] == entry["task_id"]
        assert task["gold_answer"] == apply_op(entry["spec"])
        assert task["task_text"] == task_record(entry)["task_text"]
        assert task["trace_id"] == "freeze-w1"
        assert task["evidence"].endswith("manifest.json")


def test_deterministic_policies_do_not_flip_and_flaky_does():
    tasks = flip.load_tasks(flip.render_tasks_jsonl())
    rows = {row["policy"]: row for row in flip.summarize(flip.build_traces(tasks))}
    assert set(rows) == set(POLICIES)
    assert rows["correct"]["flips"] == 0
    assert rows["correct"]["stable_verdict"] == "PASS"
    assert rows["seed_perturbed"]["flips"] == 0
    assert rows["seed_perturbed"]["stable_verdict"] == "FAIL"
    assert rows["flaky"]["flips"] == rows["flaky"]["replays"] == len(tasks)
    assert rows["flaky"]["stable_verdict"] == "mixed"
    assert rows["flaky"]["flips"] > 0


def test_populated_csv_requires_trace_ids_and_evidence():
    tasks = flip.load_tasks(flip.render_tasks_jsonl())
    traces = flip.build_traces(tasks)
    rows = flip.summarize(traces)
    csv_text = flip.render_csv(rows)
    traces_text = flip.render_traces(traces)
    assert flip.validate_csv_against_traces(csv_text, traces_text) == []
    broken = csv_text.replace(rows[0]["trace_ids"], "", 1)
    problems = flip.validate_csv_against_traces(broken, traces_text)
    assert problems
    missing_evidence = csv_text.replace(
        "results/scripted_traces.jsonl", "none", 1
    )
    assert flip.validate_csv_against_traces(missing_evidence, traces_text)


def test_committed_artifacts_match_recompute():
    problems = flip.commit_problems()
    assert problems == [], problems


def test_empty_sentinel_is_not_rewritten_by_the_pipeline():
    sentinel = (ROOT / "results" / "flip_rate_empty.csv").read_text(encoding="utf-8")
    assert sentinel.strip().splitlines() == [
        "trace_id,task_id,condition,run_id,flip_occurred,flip_type,evidence_path,notes"
    ]


def test_docker_gate_skips_with_reason_when_image_unavailable():
    import docker_sandbox as ds

    reason = ds.docker_skip_reason()
    if reason is None:
        assert ds.local_image_present()
    else:
        assert "does not pull" in reason or "not available" in reason
        gates = _load_runtime_gates()
        assert gates.r6_sandbox_isolation() == "skip"
