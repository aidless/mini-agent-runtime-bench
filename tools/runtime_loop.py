#!/usr/bin/env python3
"""W2 运行时最小闭环雏形（M2）：把 docs/W2-runtime.md 的契约做成可执行代码。

契约来源：docs/W2-runtime.md（reset/step/done 三接口 + 四必填字段 + AG-W2-1..4）。

设计纪律（与契约逐条对应）：
  AG-W2-1 禁依赖 A 线实现：本文件 stdlib only，不 import 任何 A 线模块。
  AG-W2-2 单步有界：step_timeout + max_steps 双上界，超限即中止（fail-closed）。
  AG-W2-3 日志完备：prompt_log / tool_calls / latency_log 随 step 同步产生，
           不得事后补写；done() 时校验八字段齐全，缺一即拒产轨迹。
  AG-W2-4 确定性重放：同 snapshot_id + 同扰动条件必须产出同一 verdict。

诚实边界（写进 docs/m2-runtime-loop.md）：
  这不是 bench —— 没有任务定义、没有评分、没有翻转率分子分母。
  verdict 来自"被检快照是否被改动"的自洽性判定，不来自任何 LLM 或裁判。
  沙箱是约定级（只读快照），执行未托管给 docker_sandbox.py。

基础设施，不含 bench 语义、不产生任何 bench 数字。
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

# 轨迹八字段（docs/W2-runtime.md Schema 二）
REQUIRED_FIELDS = (
    "run_id", "snapshot_id", "prompt_log", "tool_calls",
    "latency_log", "verdict", "trace_id", "evidence",
)


class ContractError(RuntimeError):
    """契约违例（与业务错误区分，便于审计判定）。"""


def _digest(path):
    """目录/文件内容摘要（只读，不改动被检对象）。"""
    p = Path(path)
    if p.is_file():
        return hashlib.sha256(p.read_bytes()).hexdigest()
    h = hashlib.sha256()
    for f in sorted(p.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(p)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


class RuntimeLoop:
    """最小闭环：reset() → step()* → done() → 轨迹记录。"""

    def __init__(self, snapshot_path, max_steps=8, step_timeout=5.0,
                 seed="M2"):
        self.snapshot_path = Path(snapshot_path)
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self.seed = seed
        self.run_id = None
        self.snapshot_id = None
        self._snap_digest = None
        self._steps = []
        self._prompt_log = []
        self._tool_calls = []
        self._latency_log = []
        self._consumed = False       # reset 一次性（契约：一次运行只绑一个快照）
        self._finished = False

    def run(self):
        """一次最小闭环：reset → 观测若干步 → done → 轨迹记录。"""
        self.reset()
        while True:
            try:
                self.step()
            except ContractError:
                break
            if len(self._steps) >= 2:
                break
        return self.done()

    # ---- Schema 一：闭环三接口 -------------------------------------------
    def reset(self, snapshot_id=None):
        """绑定一个冻结快照，返回初始观测。中途不得换题（_consumed 保证）。"""
        if self._consumed:
            raise ContractError("reset 只允许调用一次：不得中途换快照")
        if not self.snapshot_path.exists():
            raise ContractError(f"快照不存在: {self.snapshot_path}")
        self._consumed = True
        self.snapshot_id = snapshot_id or f"SNAP-{self.seed}-001"
        self._snap_digest = _digest(self.snapshot_path)
        self.run_id = f"run-{self.seed}-{self._snap_digest[:8]}"
        obs = {"snapshot_id": self.snapshot_id,
               "entries": sorted(x.name for x in self.snapshot_path.iterdir())
               if self.snapshot_path.is_dir() else [self.snapshot_path.name],
               "digest_head": self._snap_digest[:12]}
        self._prompt_log.append(f"reset snapshot_id={self.snapshot_id}")
        return obs

    def step(self, action="fs.read"):
        """单步：记录动作声明 + 实际只读观测；有界（超时/超步数即中止）。"""
        if self._finished:
            raise ContractError("done() 之后不得再 step()")
        if not self._consumed:
            raise ContractError("未 reset() 不得 step()")
        if len(self._steps) >= self.max_steps:
            raise ContractError(
                f"超出步数上界 max_steps={self.max_steps}（AG-W2-2）")
        t0 = time.perf_counter()
        if self.step_timeout <= 0:
            raise ContractError(f"step_timeout={self.step_timeout} 非正（AG-W2-2）")
        # 只读动作：仅观测清单，不写、不改、不联网
        observed = self._observe()
        dt = (time.perf_counter() - t0) * 1000.0
        if dt > self.step_timeout * 1000.0:
            raise ContractError(f"单步超时 {dt:.1f}ms > {self.step_timeout * 1000:.0f}ms（AG-W2-2）")
        n = len(self._steps) + 1
        self._steps.append(n)
        self._prompt_log.append(f"step {n} action={action}")
        self._tool_calls.append({"step": n, "tool": action, "ok": True,
                                 "observed": observed,
                                 "read_only": True})
        self._latency_log.append({"step": n, "ms": round(dt, 1)})
        return {"step": n, "action": action, "observed": observed}

    def _observe(self):
        if self.snapshot_path.is_dir():
            return sorted(x.name for x in self.snapshot_path.iterdir())
        return [self.snapshot_path.name]

    def done(self):
        """终态 verdict（文字结论，非分数）+ 八字段完备性校验（AG-W2-3）。"""
        if self._finished:
            raise ContractError("done() 只允许一次")
        self._finished = True
        changed = _digest(self.snapshot_path) != self._snap_digest
        verdict = "TAMPERED" if changed else "OK"
        rec = {
            "run_id": self.run_id,
            "snapshot_id": self.snapshot_id,
            "prompt_log": "\n".join(self._prompt_log),
            "tool_calls": self._tool_calls,
            "latency_log": self._latency_log,
            "verdict": verdict,
            "trace_id": f"tr-{self.run_id}",
            "evidence": f"snapshot_digest={self._snap_digest[:12]} "
                        f"steps={len(self._steps)}",
        }
        missing = [k for k in REQUIRED_FIELDS
                   if rec.get(k) in (None, "", [], {})]
        if missing:
            raise ContractError(f"AG-W2-3 日志不完备，缺字段: {missing}")
        return rec


def replay(snapshot_path, **kw):
    """AG-W2-4：同 snapshot_id + 同扰动条件重放，返回 verdict。"""
    return RuntimeLoop(snapshot_path, **kw).run()


def _selftest():
    """非空性反证：门必须能失败（延续 R5 纪律）。"""
    base = Path(__file__).resolve().parent
    results = []

    # 1) 确定性：同快照重放，verdict 必须一致
    v = {RuntimeLoop(base, seed="DET").run()["verdict"] for _ in range(3)}
    results.append(("确定性重放 verdict 一致", len(v) == 1))

    # 2) 完备性：抽掉 latency_log 必须被拒
    loop = RuntimeLoop(base, seed="CMP")
    loop.reset(); loop.step()
    loop._latency_log = []
    try:
        loop.done()
        results.append(("缺 latency_log 必须拒产轨迹", False))
    except ContractError as e:
        results.append(("缺 latency_log 必须拒产轨迹", "latency_log" in str(e)))

    # 3) 有界性：max_steps=1 时第 2 步必须中止
    loop = RuntimeLoop(base, max_steps=1, seed="BND")
    loop.reset(); loop.step()
    try:
        loop.step()
        results.append(("超步数必须中止", False))
    except ContractError:
        results.append(("超步数必须中止", True))

    # 4) reset 一次性
    loop = RuntimeLoop(base, seed="RST")
    loop.reset()
    try:
        loop.reset()
        results.append(("reset 不得二次调用", False))
    except ContractError:
        results.append(("reset 不得二次调用", True))

    ok = all(r for _, r in results)
    for name, r in results:
        print(f"  {'PASS' if r else 'FAIL'}  {name}")
    print("SELFTEST:", "PASS" if ok else "FAIL（门失效，须修）")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    loop = RuntimeLoop(Path(__file__).resolve().parent)
    print("[loop] reset", loop.reset()["snapshot_id"])
    print("[loop] step 1", loop.step())
    print("[loop] step 2", loop.step("fs.stat"))
    rec = loop.done()
    print("[loop] done  verdict=%s steps=%d evidence=%s"
          % (rec["verdict"], len(rec["tool_calls"]), rec["evidence"]))
    print(json.dumps(rec, ensure_ascii=False, indent=2))
