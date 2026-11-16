#!/usr/bin/env python3
"""Recompute the scripted-policy flip rate and fail if committed files drift.

Flip = the replay verdict differs from the baseline verdict.
One repeat per task. Judge = exact string match against the frozen gold
answer. Policies are the functions in ``scripted_policies.py``. No LLM is
called. ``results/flip_rate_empty.csv`` stays header-only; it is not a zero.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

from scripted_policies import (
    POLICIES,
    SEED_PERTURBED_SEED,
    TASK_SPECS,
    answer_for,
    judge,
    task_record,
)

REPO = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO / "snapshots" / "w1" / "tasks.jsonl"
MANIFEST_PATH = REPO / "snapshots" / "w1" / "manifest.json"
TRACES_PATH = REPO / "results" / "scripted_traces.jsonl"
CSV_PATH = REPO / "results" / "flip_rate.csv"
SUMMARY_PATH = REPO / "results" / "flip_rate_summary.json"
README_PATH = REPO / "README.md"
EMPTY_CSV = REPO / "results" / "flip_rate_empty.csv"
EVIDENCE_PATH = "results/scripted_traces.jsonl"

CSV_FIELDS = (
    "policy",
    "flips",
    "replays",
    "stable_verdict",
    "trace_ids",
    "evidence_path",
    "notes",
)

MEASURED_START = "<!-- measured:start -->"
MEASURED_END = "<!-- measured:end -->"
# Result-shaped numbers outside the measured block are drift, even when the
# block itself matches. Structural ids such as W1 are not this shape.
RESULT_LEAK_RE = re.compile(
    r"\d+\s*%|\b\d+\.\d+\b|\b[Nn]\s*=\s*\d+|\d+\s+of\s+\d+|\d+\s*/\s*\d+|"
    r"\b(?:flips|replays|tasks)\s*=\s*\d+"
)
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_tasks_jsonl() -> str:
    lines = [_dumps(task_record(entry)) for entry in TASK_SPECS]
    return "\n".join(lines) + "\n"


def load_tasks(text: str) -> list[dict]:
    tasks = []
    for line in text.splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    return tasks


def render_manifest(tasks_text: str) -> str:
    per_task = {}
    for line in tasks_text.splitlines():
        if not line.strip():
            continue
        task = json.loads(line)
        per_task[task["task_id"]] = _sha256(line.encode("utf-8"))
    manifest = {
        "algorithm": "sha256",
        "copy_frozen": True,
        "created_at": task_record(TASK_SPECS[0])["created_at"],
        "per_task_sha256": per_task,
        "source_ref": task_record(TASK_SPECS[0])["source_ref"],
        "task_count": len(per_task),
        "tasks_file": "snapshots/w1/tasks.jsonl",
        "tasks_sha256": _sha256(tasks_text.encode("utf-8")),
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _trace(policy: str, task: dict, role: str, run_index: int) -> dict:
    answer = answer_for(policy, task, run_index)
    return {
        "answer": answer,
        "evidence": EVIDENCE_PATH,
        "gold_answer": task["gold_answer"],
        "judge": "exact_string_match",
        "llm_called": False,
        "policy": policy,
        "policy_kind": "scripted",
        "reads_task_text": False,
        "role": role,
        "run_id": f"run-{policy}-{task['task_id']}-{role}",
        "run_index": run_index,
        "seed": SEED_PERTURBED_SEED if policy == "seed_perturbed" else None,
        "snapshot_id": task["snapshot_id"],
        "task_id": task["task_id"],
        "trace_id": f"tr-{policy}-{task['task_id']}-{role}",
        "verdict": judge(answer, task["gold_answer"]),
    }


def build_traces(tasks: list[dict]) -> list[dict]:
    traces = []
    for policy in POLICIES:
        for task in tasks:
            traces.append(_trace(policy, task, "baseline", 0))
            traces.append(_trace(policy, task, "replay", 1))
    return traces


def render_traces(traces: list[dict]) -> str:
    return "".join(_dumps(rec) + "\n" for rec in traces)


def _notes(policy: str) -> str:
    if policy == "correct":
        return (
            "scripted; executes spec; exact string match; "
            "llm_called=no; not an agent score"
        )
    if policy == "seed_perturbed":
        return (
            f"scripted; seed {SEED_PERTURBED_SEED} held fixed; "
            "stable wrong answer; llm_called=no; not an agent score"
        )
    if policy == "flaky":
        return (
            "scripted; alternates by run index by construction; "
            "llm_called=no; not an agent score"
        )
    raise ValueError(policy)


def summarize(traces: list[dict]) -> list[dict]:
    by_id = {rec["trace_id"]: rec for rec in traces}
    rows = []
    for policy in POLICIES:
        replays = [
            rec for rec in traces
            if rec["policy"] == policy and rec["role"] == "replay"
        ]
        flips = 0
        verdicts = set()
        ids = []
        for rec in replays:
            base = by_id[rec["trace_id"].replace("-replay", "-baseline")]
            verdicts.add(base["verdict"])
            verdicts.add(rec["verdict"])
            if rec["verdict"] != base["verdict"]:
                flips += 1
            ids.append(rec["trace_id"])
        stable = next(iter(verdicts)) if len(verdicts) == 1 else "mixed"
        rows.append({
            "policy": policy,
            "flips": flips,
            "replays": len(replays),
            "stable_verdict": stable,
            "trace_ids": ";".join(ids),
            "evidence_path": EVIDENCE_PATH,
            "notes": _notes(policy),
        })
    return rows


def render_csv(rows: list[dict]) -> str:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row[k] for k in CSV_FIELDS})
    return buf.getvalue()


def render_summary(rows: list[dict], tasks_text: str) -> str:
    payload = {
        "definition": (
            "flip means replay verdict != baseline verdict; "
            "one repeat; exact string match; scripted policies execute spec "
            "and do not read task text; not an LLM agent"
        ),
        "judge": "exact_string_match",
        "llm_called": False,
        "policies": [
            {
                "flips": row["flips"],
                "policy": row["policy"],
                "replays": row["replays"],
                "stable_verdict": row["stable_verdict"],
            }
            for row in rows
        ],
        "task_count": len(load_tasks(tasks_text)),
        "tasks_sha256": _sha256(tasks_text.encode("utf-8")),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _policy_row(rows: list[dict], name: str) -> dict:
    for row in rows:
        if row["policy"] == name:
            return row
    raise KeyError(name)


def render_measured_block(rows: list[dict]) -> str:
    correct = _policy_row(rows, "correct")
    seeded = _policy_row(rows, "seed_perturbed")
    flaky = _policy_row(rows, "flaky")
    tasks = correct["replays"]
    lines = [
        MEASURED_START,
        f"tasks={tasks}",
        (
            f"policy=correct flips={correct['flips']} replays={correct['replays']} "
            f"stable_verdict={correct['stable_verdict']}"
        ),
        (
            f"policy=seed_perturbed flips={seeded['flips']} replays={seeded['replays']} "
            f"seed={SEED_PERTURBED_SEED} stable_verdict={seeded['stable_verdict']}"
        ),
        (
            f"policy=flaky flips={flaky['flips']} replays={flaky['replays']} "
            f"stable_verdict={flaky['stable_verdict']}"
        ),
        "judge=exact_string_match",
        "llm_called=no",
        (
            f"headline: On {tasks} hand-authored frozen tasks, one exact-match "
            f"repeat each, verdicts flip {correct['flips']} of {correct['replays']} "
            f"for the correct policy, {seeded['flips']} of {seeded['replays']} for "
            f"the seed_perturbed policy with seed {SEED_PERTURBED_SEED} held fixed, "
            f"and {flaky['flips']} of {flaky['replays']} for the flaky policy that "
            "alternates by run index."
        ),
        (
            "limits: scripted policies only; they execute the frozen spec and do "
            "not read the task text; not an LLM-agent score; exact string match; "
            "one repeat; a zero flip count is stability, including stable failure; "
            "the flaky policy flips by construction; the task set is a tiny "
            "hand-authored pipeline demo."
        ),
        MEASURED_END,
    ]
    return "\n".join(lines)


def extract_measured_block(readme: str) -> str | None:
    start = readme.find(MEASURED_START)
    end = readme.find(MEASURED_END)
    if start < 0 or end < 0 or end < start:
        return None
    return readme[start:end + len(MEASURED_END)]


def derived_texts(tasks_text: str) -> dict[str, str]:
    tasks = load_tasks(tasks_text)
    traces = build_traces(tasks)
    rows = summarize(traces)
    return {
        "tasks": tasks_text,
        "manifest": render_manifest(tasks_text),
        "traces": render_traces(traces),
        "csv": render_csv(rows),
        "summary": render_summary(rows, tasks_text),
        "measured": render_measured_block(rows),
    }


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def validate_csv_against_traces(
    csv_text: str, traces_text: str, require_files: bool = False
) -> list[str]:
    """Populated flip-rate rows are valid only with trace ids and evidence."""
    errors = []
    if not csv_text.strip():
        return ["flip_rate.csv is empty"]
    reader = csv.DictReader(io.StringIO(csv_text))
    if tuple(reader.fieldnames or ()) != CSV_FIELDS:
        return [f"flip_rate.csv header drift: {reader.fieldnames}"]
    by_id = {}
    for line in traces_text.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if not rec.get("trace_id") or not rec.get("evidence"):
            errors.append("trace is missing trace_id or evidence")
            continue
        if rec["evidence"] in ("", "none"):
            errors.append(f"trace {rec['trace_id']} has empty evidence")
        by_id[rec["trace_id"]] = rec
    seen_policies = []
    task_ids = {rec["task_id"] for rec in by_id.values()}
    for row in reader:
        policy = row["policy"]
        seen_policies.append(policy)
        evidence = row["evidence_path"].strip()
        if not evidence or evidence in ("none", "null"):
            errors.append(f"{policy}: evidence_path missing")
            continue
        if require_files and not (REPO / evidence).is_file():
            errors.append(f"{policy}: evidence file missing: {evidence}")
        raw_ids = [x for x in row["trace_ids"].split(";") if x]
        if not raw_ids:
            errors.append(f"{policy}: trace_ids empty")
            continue
        if len(raw_ids) != len(set(raw_ids)):
            errors.append(f"{policy}: duplicate trace ids")
        if str(len(raw_ids)) != row["replays"]:
            errors.append(f"{policy}: replays does not match trace id count")
        flips = 0
        covered = set()
        verdicts = set()
        for tid in raw_ids:
            rec = by_id.get(tid)
            if rec is None:
                errors.append(f"{policy}: trace id not in evidence: {tid}")
                continue
            if rec.get("role") != "replay" or rec.get("policy") != policy:
                errors.append(f"{policy}: {tid} is not a replay of this policy")
            if not str(tid).endswith("-replay"):
                errors.append(f"{policy}: {tid} is not a replay id")
                continue
            base_id = tid[: -len("replay")] + "baseline"
            base = by_id.get(base_id)
            if base is None:
                errors.append(f"{policy}: baseline missing for {tid}")
                continue
            verdicts.add(base["verdict"])
            verdicts.add(rec["verdict"])
            if rec["verdict"] != base["verdict"]:
                flips += 1
            covered.add(rec["task_id"])
        if str(flips) != row["flips"]:
            errors.append(f"{policy}: flips {row['flips']} != counted {flips}")
        stable = next(iter(verdicts)) if len(verdicts) == 1 else "mixed"
        if verdicts and row["stable_verdict"] != stable:
            errors.append(
                f"{policy}: stable_verdict {row['stable_verdict']} != {stable}"
            )
        if covered and covered != task_ids:
            errors.append(f"{policy}: replay task ids do not cover the frozen set")
    if tuple(seen_policies) != POLICIES:
        errors.append(f"policy row set drift: {seen_policies}")
    return errors


def commit_problems() -> list[str]:
    """Return drift and honesty problems. Empty list means the commit matches."""
    errors = []
    expected_tasks = render_tasks_jsonl()
    tasks_text = _read(TASKS_PATH)
    if tasks_text != expected_tasks:
        errors.append(
            "snapshots/w1/tasks.jsonl drifted from the frozen TASK_SPECS copy"
        )
        tasks_text = expected_tasks if not tasks_text else tasks_text
    texts = derived_texts(tasks_text if tasks_text == expected_tasks else expected_tasks)
    # Compare committed bytes to the regeneration of the COPY that is on disk
    # when the copy matches TASK_SPECS. If the copy drifted, that error is enough.
    if tasks_text == expected_tasks:
        pairs = (
            (MANIFEST_PATH, texts["manifest"], "snapshots/w1/manifest.json"),
            (TRACES_PATH, texts["traces"], "results/scripted_traces.jsonl"),
            (CSV_PATH, texts["csv"], "results/flip_rate.csv"),
            (SUMMARY_PATH, texts["summary"], "results/flip_rate_summary.json"),
        )
        for path, expected, label in pairs:
            actual = _read(path)
            if actual != expected:
                errors.append(f"{label} drifted from recomputation")
        errors.extend(validate_csv_against_traces(
            texts["csv"], texts["traces"], require_files=True
        ))
        readme = _read(README_PATH)
        found = extract_measured_block(readme)
        if found is None:
            errors.append("README.md is missing the measured block")
        elif found != texts["measured"]:
            errors.append("README.md measured block drifted from recomputation")
        else:
            outside = FENCE_RE.sub(" ", readme.replace(found, " "))
            leak = RESULT_LEAK_RE.search(outside)
            if leak:
                errors.append(
                    "README.md result number outside the measured block: "
                    + leak.group(0)
                )
    empty = _read(EMPTY_CSV).splitlines()
    if empty != [
        "trace_id,task_id,condition,run_id,flip_occurred,flip_type,evidence_path,notes"
    ]:
        errors.append("flip_rate_empty.csv must stay header-only")
    return errors


def write_outputs() -> None:
    tasks_text = render_tasks_jsonl()
    texts = derived_texts(tasks_text)
    TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASKS_PATH.write_text(texts["tasks"], encoding="utf-8")
    MANIFEST_PATH.write_text(texts["manifest"], encoding="utf-8")
    TRACES_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACES_PATH.write_text(texts["traces"], encoding="utf-8")
    CSV_PATH.write_text(texts["csv"], encoding="utf-8")
    SUMMARY_PATH.write_text(texts["summary"], encoding="utf-8")
    print(texts["measured"])
    print(f"[flip] wrote {TASKS_PATH}")
    print(f"[flip] wrote {MANIFEST_PATH}")
    print(f"[flip] wrote {TRACES_PATH}")
    print(f"[flip] wrote {CSV_PATH}")
    print(f"[flip] wrote {SUMMARY_PATH}")


def main(argv: list[str]) -> int:
    if "--write" in argv:
        write_outputs()
        return 0
    if "--check" in argv or len(argv) == 1:
        problems = commit_problems()
        if problems:
            print("FAIL flip-rate recomputation:")
            for item in problems:
                print(f"  - {item}")
            print("\nexpected measured block:")
            print(render_measured_block(summarize(build_traces(
                load_tasks(render_tasks_jsonl())
            ))))
            return 1
        rows = summarize(build_traces(load_tasks(render_tasks_jsonl())))
        bits = ", ".join(
            f"{row['policy']} {row['flips']}/{row['replays']}" for row in rows
        )
        print(f"PASS flip-rate recomputed: {bits}")
        return 0
    print("usage: compute_flip_rate.py --check|--write", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
