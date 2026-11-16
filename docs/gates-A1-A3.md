# Gates A1-A3

- A1 structure: expected file set present, no drift, no extras (LICENSE, README, .gitignore, PHASE_LOG, gate script, docs set, results csv + contract). Exact set is asserted in `tools/check_gates.py` EXPECTED.
- A2 docs: W1/W2/W3 + placeholder spec + results contract non-empty; README declares TBD/empty and is reviewable (vision/pillars/non-goals/contract/gates/roadmap); W1/W2/W3 independently reviewable (schema field table + anti-gaming rules + acceptance criteria, TBD + trace_id contract).
- A3 isolation & honesty: no unallowlisted A-line coupling references, no A-line imports in code, no parent absolute paths, `flip_rate_empty.csv` header-only with byte-exact header, no invented numeric claims in README/docs/results/FAILURE_MODES/PREREG (TBD and allow-number lines exempt; the README measured block is exempt only when it matches a fresh recomputation). Populated `results/flip_rate.csv` rows pass only with trace ids that resolve into `results/scripted_traces.jsonl` and an evidence path that exists.
- Gate script: `tools/check_gates.py` (infrastructure only, zero bench implementation code).
