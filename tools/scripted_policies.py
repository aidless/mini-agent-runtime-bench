#!/usr/bin/env python3
"""Scripted policies for the flip-rate pipeline.

These functions are not LLM agents. They execute the frozen ``spec`` on each
task and ignore ``task_text``. A correct result here shows that the metric
pipeline can tell a deterministic function from a function that alternates by
run index. It does not show that any agent can read or solve the task text.

``seed_perturbed`` uses one fixed seed on both the baseline run and the
replay, so a nonzero seed makes both answers wrong in the same way.
``flaky`` returns the spec result on even run indexes and a corrupted answer
on odd ones. That alternation is the policy definition, not sampled noise.
"""

from __future__ import annotations

FROZEN_AT = "2026-11-16T00:00:00Z"
SOURCE_REF = (
    "hand-authored in this repository; not copied from an external benchmark"
)
EVIDENCE = "snapshots/w1/manifest.json"
FREEZE_TRACE_ID = "freeze-w1"
SEED_PERTURBED_SEED = 7

# Logical source of the frozen set. snapshots/w1/tasks.jsonl is the COPY that
# is hashed; compute_flip_rate.py refuses drift between this table and that file.
TASK_SPECS = (
    {"task_id": "t01", "spec": {"op": "add", "a": 2, "b": 3}},
    {"task_id": "t02", "spec": {"op": "add", "a": 10, "b": 1}},
    {"task_id": "t03", "spec": {"op": "sub", "a": 9, "b": 4}},
    {"task_id": "t04", "spec": {"op": "mul", "a": 6, "b": 7}},
    {"task_id": "t05", "spec": {"op": "absdiff", "a": 4, "b": 9}},
    {"task_id": "t06", "spec": {"op": "min2", "a": 8, "b": 3}},
    {"task_id": "t07", "spec": {"op": "max2", "a": 8, "b": 3}},
    {"task_id": "t08", "spec": {"op": "strlen", "s": "abcd"}},
    {"task_id": "t09", "spec": {"op": "reverse", "s": "cat"}},
    {"task_id": "t10", "spec": {"op": "upper", "s": "ok"}},
    {"task_id": "t11", "spec": {"op": "count_char", "s": "banana", "ch": "a"}},
    {"task_id": "t12", "spec": {"op": "concat", "a": "ab", "b": "cd"}},
)

POLICIES = ("correct", "seed_perturbed", "flaky")


def apply_op(spec: dict) -> str:
    """Deterministic result of a frozen spec. Raises on an unknown op."""
    op = spec["op"]
    if op == "add":
        return str(int(spec["a"]) + int(spec["b"]))
    if op == "sub":
        return str(int(spec["a"]) - int(spec["b"]))
    if op == "mul":
        return str(int(spec["a"]) * int(spec["b"]))
    if op == "absdiff":
        return str(abs(int(spec["a"]) - int(spec["b"])))
    if op == "min2":
        return str(min(int(spec["a"]), int(spec["b"])))
    if op == "max2":
        return str(max(int(spec["a"]), int(spec["b"])))
    if op == "strlen":
        return str(len(spec["s"]))
    if op == "reverse":
        return spec["s"][::-1]
    if op == "upper":
        return spec["s"].upper()
    if op == "count_char":
        ch = spec["ch"]
        if len(ch) != 1:
            raise ValueError("count_char requires a single character")
        return str(spec["s"].count(ch))
    if op == "concat":
        return str(spec["a"]) + str(spec["b"])
    raise ValueError(f"unknown op: {op}")


def render_task_text(spec: dict) -> str:
    """Canonical task text. Policies do not parse this; the checker does."""
    op = spec["op"]
    if op == "add":
        return f"Add {spec['a']} and {spec['b']}. Answer with the integer only."
    if op == "sub":
        return (
            f"Subtract {spec['b']} from {spec['a']}. "
            "Answer with the integer only."
        )
    if op == "mul":
        return (
            f"Multiply {spec['a']} by {spec['b']}. "
            "Answer with the integer only."
        )
    if op == "absdiff":
        return (
            f"Absolute difference of {spec['a']} and {spec['b']}. "
            "Answer with the integer only."
        )
    if op == "min2":
        return (
            f"Minimum of {spec['a']} and {spec['b']}. "
            "Answer with the integer only."
        )
    if op == "max2":
        return (
            f"Maximum of {spec['a']} and {spec['b']}. "
            "Answer with the integer only."
        )
    if op == "strlen":
        return (
            f"Length of the string {spec['s']}. "
            "Answer with the integer only."
        )
    if op == "reverse":
        return f"Reverse the string {spec['s']}. Answer with the string only."
    if op == "upper":
        return (
            f"Uppercase the string {spec['s']}. "
            "Answer with the string only."
        )
    if op == "count_char":
        return (
            f"Count the character {spec['ch']} in {spec['s']}. "
            "Answer with the integer only."
        )
    if op == "concat":
        return (
            f"Concatenate {spec['a']} and {spec['b']}. "
            "Answer with the string only."
        )
    raise ValueError(f"unknown op: {op}")


def task_record(entry: dict) -> dict:
    spec = entry["spec"]
    task_id = entry["task_id"]
    return {
        "created_at": FROZEN_AT,
        "evidence": EVIDENCE,
        "gold_answer": apply_op(spec),
        "snapshot_id": f"w1-{task_id}",
        "source_ref": SOURCE_REF,
        "spec": spec,
        "task_id": task_id,
        "task_text": render_task_text(spec),
        "trace_id": FREEZE_TRACE_ID,
    }


def answer_for(policy: str, task: dict, run_index: int) -> str:
    """Return the scripted answer. ``run_index`` is 0 for baseline, 1 for replay."""
    base = apply_op(task["spec"])
    if policy == "correct":
        return base
    if policy == "seed_perturbed":
        # Seed is held fixed across baseline and replay (see SEED_PERTURBED_SEED).
        if SEED_PERTURBED_SEED == 0:
            return base
        return base + "S"
    if policy == "flaky":
        if run_index % 2 == 0:
            return base
        return base + "X"
    raise ValueError(f"unknown policy: {policy}")


def judge(answer: str, gold: str) -> str:
    """Exact string match. Not an independent judge."""
    return "PASS" if answer == gold else "FAIL"
