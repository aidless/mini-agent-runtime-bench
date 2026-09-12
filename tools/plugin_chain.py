#!/usr/bin/env python3
"""C 线插件执行链（TaskWeaver「安全执行」迁移的**执行侧**）。

首轮 P3 只落了策略校验层（`sandbox_validator.py`），插件链未接。本轮补上执行链：
**每一步调用前都必须先过安执校验**，任一被拒即整链中止（fail-closed）。

设计要点：
  - `execute_chain(steps, policy, executor)`：逐步校验 → 执行 → 记 trace
  - 校验不通过：**不执行该步**、整链中止，并指认命中的规则
  - `executor` 为**显式注入**：本机无真实插件运行时，默认执行器只记录调用
    （不是「假装执行成功」——它明确标记为 stub），真实后端可注入替换
  - 全链 trace 可审计：每步 {step, tool, allowed, rule, executed}

诚实边界：本模块交付的是**门控正确性**，不是「插件真的能跑」；默认执行器为 stub，
`real_executor_available()` 恒为 False 时不得据本模块声称任何能力。
零依赖：标准库 only。
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from sandbox_validator import validate_call  # noqa: E402
import docker_sandbox  # noqa: E402

__all__ = ["stub_executor", "docker_executor", "execute_chain",
           "real_executor_available"]


def real_executor_available():
    """本机是否有**真实**容器执行后端。

    诚实纠正：P3 首轮曾以「本机无条件」把容器沙箱记为未迁移；能力探测
    （`capability_probe.py`）实测本机 Docker 可用（见 `docker_sandbox.py`），
    故此函数改为**真实探测**，不再恒为 False。
    """
    return docker_sandbox.sandbox_available()


def stub_executor(step):
    """默认执行器：只记录调用，不做任何真实副作用。

    显式命名为 stub —— 避免把「没执行」伪装成「执行成功」。
    """
    return {"stub": True, "tool": step.get("tool"),
            "args": step.get("args", {}), "effect": "none"}


def docker_executor(step, workdir=None, timeout=None):
    """真实执行器：把**已通过安执校验**的只读工具映射为容器内命令。

    只读工具白名单内映射；写类/外联类工具即使被调用也**不会**被映射
    （它们本就会在 `execute_chain` 的校验层被拒）。
    返回 {"ok", "stdout", "exit_code", "sandbox": True, ...}。
    """
    if not real_executor_available():
        raise RuntimeError("容器沙箱不可用：请改用 stub_executor 或先修环境")
    tool = (step or {}).get("tool")
    args = (step or {}).get("args", {}) or {}
    path = str(args.get("path", "."))
    if tool == "read_file":
        cmd = f"cat '{path}'"
    elif tool == "list_dir":
        cmd = f"ls -la '{path}'"
    elif tool == "grep":
        pat = str(args.get("pattern", ""))
        cmd = f"grep -rn -- '{pat}' '{path}' || true"
    elif tool in ("stat", "hash_file"):
        cmd = f"sha256sum '{path}'"
    else:
        cmd = f"echo 'unsupported tool: {tool}' >&2; exit 3"
    kw = {"workdir": workdir}
    if timeout is not None:
        kw["timeout"] = timeout
    out = docker_sandbox.run_in_sandbox(cmd, **kw)
    out["sandbox"] = True
    out["tool"] = tool
    return out


def execute_chain(steps, policy=None, executor=None):
    """逐步执行插件链，每步先过安执校验。

    参数：
      steps    : [{"tool": str, "args": {...}}, ...]
      policy   : 传给 sandbox_validator.validate_call 的策略（None=默认最严）
      executor : callable(step) -> result；None 时用 stub_executor

    返回：
      {"completed": bool, "trace": [...], "stopped_at": int|None,
       "denied_rule": str|None, "denied_reason": str|None,
       "results": [...]}
    """
    ex = executor or stub_executor
    trace, results = [], []

    for i, step in enumerate(steps):
        verdict = validate_call(step, policy=policy)
        entry = {"step": i, "tool": step.get("tool") if isinstance(step, dict) else None,
                 "allowed": verdict["allowed"], "rule": verdict["rule"],
                 "executed": False}
        if not verdict["allowed"]:
            entry["executed"] = False
            trace.append(entry)
            return {"completed": False, "trace": trace, "stopped_at": i,
                    "denied_rule": verdict["rule"],
                    "denied_reason": verdict["reason"], "results": results}
        # 通过校验才执行
        out = ex(step)
        entry["executed"] = True
        trace.append(entry)
        results.append(out)

    return {"completed": True, "trace": trace, "stopped_at": None,
            "denied_rule": None, "denied_reason": None, "results": results}
