#!/usr/bin/env python3
"""w2_runs.py — 把 W2 运行时契约跑成真实轨迹（M3-C，落 results/w2_runs.jsonl）

**这个脚本不产生任务完成率、不产生分数、不调用任何 LLM。**
docs/m3-plan.md 候选 C 的原始定义："用 runtime_loop + docker_sandbox + call_guard
跑 8 个手工构造的动作序列，输出 results/w2_runs.jsonl（不只表头）"，
并且明确约束："不能叫 agent benchmark —— 名字会骗人，结果不会"。
本机 LLM API key 全部 unset（见 m3-plan.md 的弹药实测表），
所以这里测的每一件事都是**基础设施的行为**，不是 agent 的智能。

每个 run 的字段与八字段轨迹表对齐（docs/W2-runtime.md Schema 二），
外加 disclosure 块说明"这个 run 到底测了什么"。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from runtime_loop import RuntimeLoop, ContractError  # noqa: E402
import call_guard  # noqa: E402
import docker_sandbox  # noqa: E402

RESULTS = HERE.parent / "results" / "w2_runs.jsonl"

# 8 个手写动作序列。action 元组 = (动作名, 原始模型输出文本)，
# 交给 call_guard 解析的是"文本"，不是结构体——因为真实场景中 agent 调工具
# 必须经过文本解析这一关（R 线 call_guard 的存在理由）。
RUNS = [
    {"id": "T01", "title": "目录观测", "snapshot": "toolkit",
     "actions": [("fs.read", '{"tool": "fs.read", "args": {"path": "."}}')]},
    {"id": "T02", "title": "统计文件", "snapshot": "toolkit",
     "actions": [("fs.read", '{"tool": "fs.read", "args": {"path": "."}}'),
                 ("fs.stat", '{"tool": "fs.stat", "args": {"path": "runtime_loop.py"}}')]},
    {"id": "T03", "title": "围栏包裹的调用", "snapshot": "toolkit",
     "actions": [("fs.read", '```json\n{"tool": "fs.read", "args": {"path": "."}}\n```')]},
    {"id": "T04", "title": "危险调用被拦", "snapshot": "toolkit",
     "actions": [("shell.exec", '{"tool": "shell.exec", "args": {"cmd": "rm -rf /tmp/x"}}')]},
    {"id": "T05", "title": "向 schema 外传参", "snapshot": "toolkit",
     "actions": [("fs.write", '{"tool": "fs.write", "args": {"path": "/etc/passwd", "data": "x"}}')]},
    {"id": "T06", "title": "净空输出", "snapshot": "toolkit",
     "actions": [("fs.read", '我来帮你读取文件：{"tool": "fs.read", "args": {"path": "."}} 这就去读')]},
    {"id": "T07", "title": "无动作只说", "snapshot": "toolkit",
     "actions": [("noop", "抱歉，我现在无法访问文件系统。")]},
    {"id": "T08", "title": "越界步数", "snapshot": "toolkit", "max_steps": 1,
     "actions": [("fs.read", '{"tool": "fs.read", "args": {"path": "."}}'),
                 ("fs.stat", '{"tool": "fs.stat", "args": {"path": "."}}')]},
]

# 危险工具名黑名单（与 call_guard 的 R1 判定无关，这里是**序列层**的策略）：
# parse_call 只回答"是不是合法 JSON 调用"，不回答"该不该执行"。
DANGEROUS = ("shell.exec", "fs.write", "net.fetch", "proc.spawn")


def run_one(spec: dict, snapshot_dir: Path) -> dict:
    """跑一个动作序列，返回与轨迹八字段对齐的记录 + disclosure。"""
    loop = RuntimeLoop(snapshot_dir, max_steps=spec.get("max_steps", 8),
                       seed=f"W3-{spec['id']}")
    rec: dict = {"run_id": spec["id"], "title": spec["title"],
                 "snapshot_id": None, "steps_total": 0}
    try:
        obs = loop.reset(spec["snapshot_id"] if "snapshot_id" in spec else f"TOOLKIT-{spec['id']}")
        rec["snapshot_id"] = obs["snapshot_id"]
        rec["entries_observed"] = obs["entries"]
    except ContractError as e:
        return {**rec, "verdict": "CONTRACT_ABORT", "error": str(e),
                "tool_calls": [], "latency_log": [], "evidence": None}

    t_calls, t_lat = [], []
    violations = []
    for act_name, raw in spec["actions"]:
        parsed = call_guard.parse_call(raw)
        # 序列层策略：危险动作不执行，但要留下记录（fail-closed 而非 fail-silent）
        if parsed["ok"] and parsed["tool"] in DANGEROUS:
            violations.append({"step": len(t_calls) + 1, "tool": parsed["tool"],
                              "kind": "DANGEROUS_TOOL", "policy": "refuse"})
            t_calls.append({"step": len(t_calls) + 1, "tool": parsed["tool"],
                            "ok": False, "error_kind": "POLICY_REFUSED",
                            "error": f"{parsed['tool']} 在 RUN 策略黑名单内，未执行"})
            continue
        if not parsed["ok"]:
            violations.append({"step": len(t_calls) + 1, "tool": act_name,
                              "kind": parsed["error_kind"], "policy": "refuse"})
            t_calls.append({"step": len(t_calls) + 1, "tool": act_name,
                            "ok": False, "error_kind": parsed["error_kind"],
                            "error": parsed["error"]})
            continue
        t0 = time.perf_counter()
        try:
            obs_step = loop.step(parsed["tool"])
        except ContractError as e:
            # 越界/无 step 权：这是**契约层**中止，与上面的策略拒绝不同源
            violations.append({"step": len(t_calls) + 1, "tool": parsed["tool"],
                              "kind": "CONTRACT", "policy": "abort", "error": str(e)})
            t_lat.append({"step": len(t_calls) + 1,
                          "ms": round((time.perf_counter() - t0) * 1000, 2)})
            break
        dt = (time.perf_counter() - t0) * 1000
        t_calls.append({"step": obs_step["step"], "tool": parsed["tool"], "ok": True,
                        "args": parsed["args"], "observed": obs_step["observed"],
                        "read_only": True})
        t_lat.append({"step": obs_step["step"], "ms": round(dt, 2)})

    try:
        done = loop.done()
        rec.update({"verdict": done["verdict"], "trace_id": done["trace_id"],
                    "evidence": done["evidence"], "prompt_log": done["prompt_log"],
                    "tool_calls": done["tool_calls"], "latency_log": done["latency_log"],
                    "run_id_full": done["run_id"]})
    except ContractError as e:
        rec.update({"verdict": "CONTRACT_ABORT", "error": str(e),
                    "tool_calls": t_calls, "latency_log": t_lat})

    rec["steps_total"] = len([c for c in rec.get("tool_calls", []) if c.get("ok")])
    rec["violations"] = violations
    # AG-W2-3 语义澄清（诚实边界）：
    #   policy-refused 的动作**没有走 loop.step()**，因此不进 runtime 的
    #   tool_calls/latency_log —— 这不是"日志丢失"，而是"runtime 确实没执行它"。
    #   这些记录放在 rec["violations"]，由上层（评委/报表）自行判定，
    #   不伪造进 runtime 轨迹，否则会污染「轨迹=实际发生的事」这个契约。
    rec["disclosure"] = {
        "measures": "运行时契约行为：动作解析成功率、策略拒绝、契约中止、digest 不变性",
        "does_not_measure": "任务完成率、检索质量、agent 智能（无任何 LLM 被调用）",
        "llm_called": False,
        "sandbox": "约定级快照只读（docker R6 已在 check_runtime_gates.py 单独证明）",
        "log_semantics": "policy-refused 动作只在 violations 里，不进 tool_calls/latency_log",
    }
    return rec


def main() -> None:
    snap = HERE
    recs = [run_one(spec, snap) for spec in RUNS]

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = sum(1 for r in recs if r["verdict"] == "OK")
    ab = sum(1 for r in recs if r["verdict"] == "CONTRACT_ABORT")
    ref = sum(len(r["violations"]) for r in recs)
    print(f"[w2] {len(recs)} runs → verdict OK={ok} ABORT={ab}，violations={ref}（分辨率 "
          f"{ref}/{sum(len(r.get('tool_calls', [])) + len(r.get('violations', [])) for r in recs):.0f}）")
    for r in recs:
        v = ",".join(x["kind"] for x in r["violations"]) or "-"
        print(f"  {r['run_id']} {r['verdict']:14s} steps_ok={r['steps_total']} viol={v}")
    print(f"[w2] wrote {RESULTS}")

    # 非空性反证：这个工具必须能报告失败。若全部 verdict=OK，说明门没咬住。
    if ok == len(recs) and ref == 0:
        raise SystemExit("全部 run 无拒绝无中止 → 拒绝路径未被观察到，w2_runs 不可信")


if __name__ == "__main__":
    main()
