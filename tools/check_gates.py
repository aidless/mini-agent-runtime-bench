"""C-line gates A1-A3: fail closed, stdlib only.

A1 structure: exactly the expected file set present (no drift, no extras).
A2 docs: W1/W2/W3 + placeholder spec non-empty; README declares TBD/empty;
    README is reviewable (vision/pillars/non-goals/contract/gates/roadmap);
    W1/W2/W3 are independently reviewable (schema + anti-gaming + acceptance).
A3 isolation & honesty: no unallowlisted evolve/gsm8k/rag_demo references;
    no import of A-line in code; no absolute parent paths in prose;
    flip_rate_empty.csv holds header only (zero data rows = zero invented
    numbers) with byte-exact header; no invented numeric claims
    (percentages, sample sizes, metric assignments, decimals-as-results)
    in README/docs/results outside TBD/allow-number lines.

This script is infrastructure (assertions only, stdlib only). It implements
zero bench semantics and is therefore not bench implementation code.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXPECTED = {
    "LICENSE", "README.md", ".gitignore",
    "docs/gates-A1-A3.md", "docs/resume-placeholder-spec.md",
    "docs/W1-environment.md", "docs/W2-runtime.md", "docs/W3-experience.md",
    "results/flip_rate_empty.csv", "results/README.md",
    "tools/check_gates.py",  # this gate itself (infrastructure, zero bench code)
    "PHASE_LOG.md",  # phase gate log (process record, zero bench code)
    # P3-HARDEN runtime gates (infrastructure, zero bench code; no bench numbers)
    "tools/sandbox_validator.py",   # 安执：策略校验器
    "tools/golden_attacks.json",    # 安执 golden 集（危险/合法调用，纯数据）
    "tools/call_guard.py",          # 解析守卫（畸形输入零崩溃）
    "tools/agent_scoring.py",       # 三分/选人/记忆块（确定性纯函数）
    "tools/check_runtime_gates.py", # 上述三者的 fail-closed 门（含非空性反证）
    "docs/p3-runtime-gates.md",     # 运行门说明（无杜撰数字）
}

CSV_HEADER = "trace_id,task_id,condition,run_id,flip_occurred,flip_type,evidence_path,notes"

# Scope note: honesty & coupling prose scans cover the evidence-facing
# surfaces only (README + docs + results). LICENSE (legal boilerplate),
# PHASE_LOG.md (process record) and *.py (infrastructure) are out of scope.
PROSE_SCOPE = ["README.md"] + sorted(
    str(p.relative_to(REPO)) for p in (REPO / "docs").glob("*.md")
) + ["results/README.md", "results/flip_rate_empty.csv"]

COUPLING_TOKENS = ("evolve", "gsm8k", "rag_demo")
ABS_PATH_TOKENS = ("/home/", "/root/", "/data1", "Administrator")
# A prohibition line names the forbidden thing without depending on it.
# Such lines (and explicit allow-coupling markers) are exempt from the
# coupling scan; everything else with a coupling token fails.
COUPLING_EXEMPT = ("allow-coupling", "禁", "禁止", "不得", "严禁",
                   "NOT", "never", "forbidden", "prohibit")
IMPORT_ALINE_RE = re.compile(r"(?i)\bimport\b.*(A\s*线|A-line)")
HONESTY_RES = (
    re.compile(r"\d+\s*%"),  # percentage claim, e.g. 90%
    re.compile(r"\b[Nn]\s*=\s*\d+"),  # sample-size claim, e.g. N=30
    re.compile(r"\b\d+\.\d+\b"),  # decimal-as-result, e.g. 0.95
    re.compile(r"(?i)(accuracy|flip[\s_-]?rate|latency|score|f1|auc|"
               r"p[\s_-]?value|准确率|翻转率|延迟|得分)\s*[:=]\s*\d"),
)
HONESTY_EXEMPT = ("TBD", "allow-number")


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    actual = {str(p.relative_to(REPO)) for p in REPO.rglob("*") if p.is_file()}
    actual = {a for a in actual if ".git/" not in a and "__pycache__" not in a}
    if actual != EXPECTED:
        fail(f"A1 file set drift: extra={sorted(actual - EXPECTED)} "
             f"missing={sorted(EXPECTED - actual)}")
    print(f"PASS [A1] structure: {len(EXPECTED)} files present, no drift")

    for d in ["docs/W1-environment.md", "docs/W2-runtime.md",
              "docs/W3-experience.md",
              "docs/resume-placeholder-spec.md", "results/README.md"]:
        if not (REPO / d).read_text(encoding="utf-8").strip():
            fail(f"A2 empty doc: {d}")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    if "TBD" not in readme and "empty" not in readme:
        fail("A2 README must declare TBD/empty status")
    print("PASS [A2] docs: W1/W2/W3 + placeholder spec + results contract complete")

    lines = readme.splitlines()
    if len(lines) < 30:
        fail(f"A2-readme facade: README only {len(lines)} lines (<30), "
             "expand to reviewable depth")
    for kw in ("愿景", "W1", "W2", "W3", "非目标", "空仓契约",
               "门禁", "路线图", "check_gates"):
        if kw not in readme:
            fail(f"A2-readme facade: README missing required section '{kw}'")
    print("PASS [A2-readme] README is reviewable "
          "(vision/pillars/non-goals/contract/gates/roadmap)")

    for d in ("docs/W1-environment.md", "docs/W2-runtime.md",
              "docs/W3-experience.md"):
        text = (REPO / d).read_text(encoding="utf-8")
        if len(text) < 1000:
            fail(f"A2-pillars facade: {d} only {len(text)} chars (<1000)")
        for kw in ("字段", "schema"):
            if kw in text:
                break
        else:
            fail(f"A2-pillars facade: {d} missing schema (字段表)")
        if "反作弊" not in text and "anti-gaming" not in text:
            fail(f"A2-pillars facade: {d} missing anti-gaming")
        if "验收" not in text:
            fail(f"A2-pillars facade: {d} missing acceptance criteria")
        if "TBD" not in text or "trace_id" not in text:
            fail(f"A2-pillars facade: {d} must carry TBD + trace_id contract")
        n_rules = sum(1 for ln in text.splitlines()
                      if re.match(r"\s*-\s*\*\*AG-W", ln))
        if n_rules < 3:
            fail(f"A2-pillars facade: {d} has {n_rules} anti-gaming "
                 "rules (<3)")
    print("PASS [A2-pillars] W1/W2/W3 independently reviewable "
          "(schema + anti-gaming>=3 + acceptance)")

    for rel in PROSE_SCOPE:
        for ln in (REPO / rel).read_text(encoding="utf-8").splitlines():
            low = ln.lower()
            if any(t in low for t in COUPLING_TOKENS) and \
                    not any(m in ln for m in COUPLING_EXEMPT):
                fail(f"A3 isolation breach (unallowlisted coupling) in "
                     f"{rel}: {ln.strip()[:80]}")
            if IMPORT_ALINE_RE.search(ln) and \
                    not any(m in ln for m in COUPLING_EXEMPT):
                fail(f"A3 isolation breach (import A-line) in {rel}: "
                     f"{ln.strip()[:80]}")
            for pat in ABS_PATH_TOKENS:
                if pat in ln:
                    fail(f"A3 isolation breach '{pat}' in {rel}")
    for p in (REPO / "tools").glob("*.py"):
        for ln in p.read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if s.startswith(("import ", "from ")) and \
                    any(t in s.lower() for t in COUPLING_TOKENS):
                fail(f"A3 code coupling in {p.name}: {s[:80]}")
    rows = (REPO / "results" / "flip_rate_empty.csv").read_text(
        encoding="utf-8").strip().splitlines()
    if len(rows) != 1 or not rows[0].startswith("trace_id,"):
        fail("A3 csv must hold header only (zero data rows)")
    print("PASS [A3] zero coupling, no abs paths, header-only csv")

    header = rows[0].strip()
    if header != CSV_HEADER:
        fail(f"A3-header drift: got '{header}'")
    print("PASS [A3-header] flip_rate_empty.csv header matches contract")

    for rel in PROSE_SCOPE:
        for i, ln in enumerate(
                (REPO / rel).read_text(encoding="utf-8").splitlines(), 1):
            if any(m in ln for m in HONESTY_EXEMPT):
                continue
            for rx in HONESTY_RES:
                if rx.search(ln):
                    fail(f"A3-honesty invented number in {rel}:{i}: "
                         f"{ln.strip()[:80]}")
    print("PASS [A3-honesty] no invented numbers in README/docs/results")

    print("\nGATES A1-A3 PASS: pre-W1 empty repo honest")


if __name__ == "__main__":
    main()
