#!/usr/bin/env python3
"""C 线真实容器沙箱执行器（Docker）——把「未迁移」真做掉。

背景（诚实纠正）：P3 首轮把「Docker/多卡沙箱」记为「本机无条件」。
`capability_probe.py` 的探测推翻了该假设：本机 **Docker 29.8.0 可用、
1 张 NVIDIA 卡可用、容器级隔离可用**；并已实测
`docker run --rm --network none <img> /bin/sh -c 'echo SANDBOX_OK'` → SANDBOX_OK。
故本轮补上**真实**容器执行（不再是 stub）。

加固措施（默认最严，逐条可验证）：
  --network none              默认断网（外联不可达）
  --read-only                 根文件系统只读
  --tmpfs /tmp                仅给一块小而 noexec 的临时空间
  --cap-drop ALL              丢弃全部 Linux capabilities
  --security-opt no-new-privileges
  --memory / --pids-limit     资源上限（防 DoS）
  -v <work>:/work:ro          工作目录只读挂载
  --user nobody               非特权用户

诚实边界：这是**单容器**隔离，不是多租户强隔离方案；不声称达到生产级沙箱安全。
零依赖：标准库 only（调用 docker CLI）。
"""

import os
import subprocess

__all__ = ["DEFAULT_IMAGE", "run_in_sandbox", "sandbox_available"]

DEFAULT_IMAGE = "nvidia/cuda:12.6.0-base-ubuntu24.04"
DEFAULT_TIMEOUT = 20
MEMORY = "256m"
PIDS = "128"


def sandbox_available():
    try:
        p = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                           capture_output=True, text=True, timeout=10)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def build_argv(command, workdir=None, image=DEFAULT_IMAGE, network=False,
               memory=MEMORY, pids=PIDS, user="nobody"):
    """构造加固后的 docker 运行参数（纯函数，便于门禁断言其加固项）。"""
    argv = ["docker", "run", "--rm",
            "--network", "none" if not network else "bridge",
            "--read-only",
            "--tmpfs", "/tmp:rw,size=16m,noexec",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--memory", memory, "--pids-limit", pids]
    if user:
        argv += ["--user", user]
    if workdir:
        argv += ["-v", f"{os.path.abspath(workdir)}:/work:ro", "-w", "/work"]
    argv += [image, "/bin/sh", "-c", command]
    return argv


def run_in_sandbox(command, workdir=None, image=DEFAULT_IMAGE, timeout=DEFAULT_TIMEOUT,
                   network=False, memory=MEMORY, pids=PIDS, user="nobody"):
    """在加固容器内执行命令。

    返回 {"ok", "exit_code", "stdout", "stderr", "timed_out", "argv"}
    ok 表示「容器正常起停且退出码为 0」；超时/启动失败一律 ok=False（fail-closed）。
    """
    argv = build_argv(command, workdir=workdir, image=image, network=network,
                      memory=memory, pids=pids, user=user)
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": None, "stdout": "", "stderr": "",
                "timed_out": True, "argv": argv}
    except OSError as e:
        return {"ok": False, "exit_code": None, "stdout": "", "stderr": str(e),
                "timed_out": False, "argv": argv}
    return {"ok": p.returncode == 0, "exit_code": p.returncode,
            "stdout": (p.stdout or "").strip(), "stderr": (p.stderr or "").strip(),
            "timed_out": False, "argv": argv}
