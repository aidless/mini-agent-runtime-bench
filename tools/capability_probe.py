#!/usr/bin/env python3
"""C 线能力探测（Docker / GPU）——把「做不到」如实变成可审计的事实。

首轮 P3 把「Docker/多卡沙箱」记为未迁移（本机无条件）。本轮补上**探测**：
不假装具备能力，而是把环境事实落成结构化结果，供门禁与报告引用。

探测项：
  - docker  : 是否存在 docker 可执行文件并可用（`docker info` 成功）
  - gpu     : 是否存在 NVIDIA 设备（`nvidia-smi -L` 有输出）
  - sandbox : 本机是否具备容器级隔离（= docker 可用）

诚实边界：探测**只报告事实**；`sandbox` 不可用时明确返回 unavailable，
不得据此声称「已具备执行沙箱」。探测命令缺失/超时/报错一律记为 unavailable。
零依赖：标准库 only（用 subprocess 调用外部命令，命令缺失即 unavailable）。
"""

import os
import shutil
import subprocess

__all__ = ["probe", "PROBES"]

TIMEOUT = 8


def _run(cmd, args):
    exe = shutil.which(cmd)
    if not exe:
        return None, f"{cmd} 不可用（未找到可执行文件）"
    try:
        p = subprocess.run([exe] + args, capture_output=True, text=True,
                           timeout=TIMEOUT)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, f"{cmd} 调用失败: {type(e).__name__}"
    if p.returncode != 0:
        return None, f"{cmd} 返回码 {p.returncode}"
    return (p.stdout or "").strip(), None


def _probe_docker():
    out, err = _run("docker", ["info", "--format", "{{.ServerVersion}}"])
    if err:
        return {"available": False, "detail": err}
    return {"available": bool(out), "detail": f"docker server {out}"}


def _probe_gpu():
    out, err = _run("nvidia-smi", ["-L"])
    if err:
        return {"available": False, "detail": err}
    n = len([ln for ln in out.splitlines() if ln.strip()])
    return {"available": n > 0, "detail": f"nvidia-smi 列出 {n} 个设备"}


def _probe_sandbox():
    d = _probe_docker()
    return {"available": bool(d["available"]),
            "detail": "容器级隔离可用" if d["available"] else "无容器级隔离"}


PROBES = {"docker": _probe_docker, "gpu": _probe_gpu, "sandbox": _probe_sandbox}


def probe(names=None):
    """返回 {name: {"available": bool, "detail": str}}。"""
    names = names or list(PROBES)
    return {n: PROBES[n]() for n in names if n in PROBES}


if __name__ == "__main__":
    import json
    res = probe()
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("\n结论：", "；".join(f"{k}={'可用' if v['available'] else '不可用'}"
                               for k, v in res.items()))
