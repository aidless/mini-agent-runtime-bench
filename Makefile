# --- acceptance_backfill (EVAL_ACCEPTANCE_STANDARD.md P4) ---
# 证据来源: ci.yml
# 命令逐字取自该来源，未增删任何参数。
# 归一: python → python3（本机无 python 别名，实测 Error 127）
.PHONY: eval check

eval:
	python3 -m pytest tests/ -q

# Offline. Recomputes the README measured block and fails on drift.
# R6/R7 container steps SKIP with a reason when Docker or the local image
# is missing; they do not pull. REQUIRE_DOCKER=1 turns that skip into failure.
check:
	python3 tools/check_gates.py
	python3 tools/runtime_loop.py --selftest
	python3 tools/compute_flip_rate.py --check
	python3 tools/check_runtime_gates.py
	python3 tools/run_offline_tests.py
