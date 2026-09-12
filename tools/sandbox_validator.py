#!/usr/bin/env python3
"""C 线安执沙箱验证器（TaskWeaver「安全执行」迁移；基础设施，stdlib only）。

作用：对「即将执行的工具调用」做策略校验，输出 allow / deny + 命中规则 + 理由。
本文件**不含任何 bench 语义、不产生任何评测数字**——它是安全基础设施，
与 check_gates.py 同类（assertions only），因此不计入 bench 实现代码。

策略（默认最严；可显式放宽）：
  R-TOOL     工具必须在白名单内
  R-READONLY 写类工具默认拒绝（只读沙箱）
  R-NETWORK  外联默认拒绝（allowlist 为空）
  R-EVAL     代码求值 / 动态执行默认拒绝
  R-ABSPATH  绝对路径拒绝（含 Windows 盘符与 POSIX 根）
  R-ESCAPE   相对路径越界（..）拒绝
  R-METACHAR shell 元字符拒绝（防注入）
  R-SENSITIVE 系统敏感路径拒绝

设计要点（fail-closed）：未知情况一律 deny；deny 时给出首个命中的规则名，
便于反证用例断言「被拦的是哪一条」。
"""

import json
import os
import re

# ---- 危险工具类别（按工具名/动作归类）----
WRITE_TOOLS = {"write_file", "delete_file", "move_file", "chmod", "mkdir"}
SHELL_TOOLS = {"shell", "bash", "sh", "cmd", "powershell", "subprocess", "exec"}
EVAL_TOOLS = {"eval", "exec_code", "python_exec", "pickle_load", "yaml_load"}
NET_TOOLS = {"http_get", "http_post", "fetch", "requests", "curl", "wget", "socket"}

SAFE_TOOLS = {"read_file", "list_dir", "search", "grep", "stat", "hash_file"}

METACHARS = ("&&", "||", ";", "|", "`", "$(", ">", "<", "&")
SENSITIVE = ("/etc/", "/proc/", "/sys/", "/dev/", "c:\\windows", "c:\\users\\",
             "/root/", "/home/")
ABS_WIN = re.compile(r"^[A-Za-z]:[\\/]")
ABS_POSIX = re.compile(r"^/")
ESCAPE = re.compile(r"(^|[\\/])\.\.([\\/]|$)")


def default_policy():
    """默认策略：只读、无网、无求值、路径限沙箱。"""
    return {
        "allowed_tools": sorted(SAFE_TOOLS),
        "allow_write": False,
        "allow_network": False,
        "allow_eval": False,
        "sandbox_root": "sandbox",
        "allow_metachars": False,
    }


def _first_path(call):
    for key in ("path", "file", "target", "src", "dst"):
        v = call.get("args", {}).get(key) if isinstance(call.get("args"), dict) else None
        if isinstance(v, str):
            return v
    return None


def validate_call(call, policy=None):
    """校验一次工具调用。

    返回 {"allowed": bool, "rule": str|None, "reason": str}
    fail-closed：任何未识别/畸形输入 → deny。
    """
    pol = dict(default_policy())
    if policy:
        pol.update(policy)

    if not isinstance(call, dict):
        return {"allowed": False, "rule": "R-MALFORMED",
                "reason": "call 不是对象"}
    name = call.get("tool")
    if not isinstance(name, str) or not name:
        return {"allowed": False, "rule": "R-MALFORMED",
                "reason": "缺少 tool 名称"}
    name_l = name.lower()

    # R-TOOL：白名单
    if name_l not in pol["allowed_tools"]:
        # 归类给出更精确的规则
        if name_l in SHELL_TOOLS and not pol["allow_metachars"]:
            return {"allowed": False, "rule": "R-METACHAR",
                    "reason": f"shell 类工具被拒: {name}"}
        if name_l in EVAL_TOOLS and not pol["allow_eval"]:
            return {"allowed": False, "rule": "R-EVAL",
                    "reason": f"动态求值被拒: {name}"}
        if name_l in NET_TOOLS and not pol["allow_network"]:
            return {"allowed": False, "rule": "R-NETWORK",
                    "reason": f"外联被拒: {name}"}
        if name_l in WRITE_TOOLS and not pol["allow_write"]:
            return {"allowed": False, "rule": "R-READONLY",
                    "reason": f"写类操作被拒（只读沙箱）: {name}"}
        return {"allowed": False, "rule": "R-TOOL",
                "reason": f"工具不在白名单: {name}"}

    # 路径类规则
    p = _first_path(call)
    if isinstance(p, str) and p:
        low = p.replace("\\", "/").lower()
        if ABS_WIN.match(p) or ABS_POSIX.match(p):
            return {"allowed": False, "rule": "R-ABSPATH",
                    "reason": f"绝对路径被拒: {p}"}
        if ESCAPE.search(p):
            return {"allowed": False, "rule": "R-ESCAPE",
                    "reason": f"路径越界被拒: {p}"}
        for s in SENSITIVE:
            if s.replace("\\", "/").lower() in low:
                return {"allowed": False, "rule": "R-SENSITIVE",
                        "reason": f"敏感路径被拒: {p}"}
        root = pol["sandbox_root"].replace("\\", "/").lower()
        if root and not low.startswith(root):
            return {"allowed": False, "rule": "R-OUTSIDE",
                    "reason": f"越出沙箱根({pol['sandbox_root']}): {p}"}

    # shell 元字符（即使工具在白名单）
    if not pol["allow_metachars"]:
        blob = json.dumps(call.get("args", {}), ensure_ascii=False)
        for m in METACHARS:
            if m in blob:
                return {"allowed": False, "rule": "R-METACHAR",
                        "reason": f"参数含 shell 元字符: {m}"}

    return {"allowed": True, "rule": None, "reason": "ok"}


def load_golden(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    golden = load_golden(os.path.join(here, "golden_attacks.json"))

    denied = 0
    for atk in golden["attacks"]:
        r = validate_call(atk["call"])
        ok = (not r["allowed"]) and r["rule"] == atk["expect_rule"]
        denied += ok
        if not ok:
            print(f"LEAK  {atk['name']}: {r}")
    print(f"[拦截] {denied}/{len(golden['attacks'])} 危险调用被拦"
          f"（且命中期望规则）")

    allowed = 0
    for safe in golden["safe"]:
        r = validate_call(safe["call"])
        allowed += r["allowed"]
        if not r["allowed"]:
            print(f"FALSE-POSITIVE  {safe['name']}: {r}")
    print(f"[误拦] {len(golden['safe']) - allowed} 例合法调用被误拦")

    ok = (denied == len(golden["attacks"])
          and allowed == len(golden["safe"]))
    print("\nSANDBOX VALIDATOR " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
