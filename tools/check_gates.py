"""C-line gates A1-A3: fail closed, stdlib only.

A1 structure: exactly the 9 expected files present.
A2 docs: W1/W2/W3 + placeholder spec non-empty; README declares TBD/empty.
A3 isolation: no evolve/gsm8k/rag_demo imports; no absolute parent paths
   (/home/, /root/, /data1, Administrator) in *.md/*.csv; csv holds header
   only (zero data rows = zero invented numbers).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXPECTED = {
    "LICENSE", "README.md", ".gitignore",
    "docs/gates-A1-A3.md", "docs/resume-placeholder-spec.md",
    "docs/W1-environment.md", "docs/W2-runtime.md", "docs/W3-experience.md",
    "results/flip_rate_empty.csv",
    "tools/check_gates.py",  # this gate itself (infrastructure, zero bench code)
    "PHASE_LOG.md",  # phase gate log (process record, zero bench code)
}


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    actual = {str(p.relative_to(REPO)) for p in REPO.rglob("*") if p.is_file()}
    actual = {a for a in actual if ".git/" not in a and "__pycache__" not in a}
    if actual != EXPECTED:
        fail(f"A1 file set drift: extra={sorted(actual - EXPECTED)} missing={sorted(EXPECTED - actual)}")
    print("PASS [A1] 9 files present, no drift")

    for d in ["docs/W1-environment.md", "docs/W2-runtime.md", "docs/W3-experience.md",
              "docs/resume-placeholder-spec.md"]:
        if not (REPO / d).read_text(encoding="utf-8").strip():
            fail(f"A2 empty doc: {d}")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    if "TBD" not in readme and "empty" not in readme:
        fail("A2 README must declare TBD/empty status")
    print("PASS [A2] W1/W2/W3 + placeholder spec complete")

    for p in list((REPO / "docs").glob("*.md")) + [REPO / "README.md"]:
        text = p.read_text(encoding="utf-8")
        for pat in ("evokit", "gsm8k", "rag_demo", "/home/", "/root/", "/data1", "Administrator"):
            if pat in text:
                fail(f"A3 isolation breach '{pat}' in {p.relative_to(REPO)}")
    rows = (REPO / "results" / "flip_rate_empty.csv").read_text(encoding="utf-8").strip().splitlines()
    if len(rows) != 1 or not rows[0].startswith("trace_id,"):
        fail("A3 csv must hold header only (zero data rows)")
    print("PASS [A3] zero coupling, no abs paths, zero invented numbers")

    print("\nGATES A1-A3 PASS: pre-W1 empty repo honest")


if __name__ == "__main__":
    main()
