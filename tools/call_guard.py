#!/usr/bin/env python3
"""C 线函数调用解析守卫（Gorilla「函数调用」迁移 + 上游未防护边补强）。

上游 Gorilla 暴露的调用解析常见未防护边（本文件逐条加守卫）：
  1. 模型输出夹带 markdown 围栏 / 前后台词 → 需剥离
  2. JSON 里嵌套引号 / 尾随逗号 / 单引号 → 需容错或明确拒绝
  3. 顶层不是对象（数组/字符串/数字）→ 需拒绝而非崩
  4. 参数不是对象 / 工具名不是字符串 → 需拒绝
  5. 深度炸弹 / 超长输入 → 需限深限长（防 DoS）
  6. 二进制垃圾 / 空串 → 需拒绝

契约（fail-closed）：任何输入都返回结构化结果，**永不抛异常**——
  {"ok": bool, "tool": str|None, "args": dict|None,
   "error_kind": str|None, "error": str|None}

基础设施，stdlib only，不含 bench 语义、不产生评测数字。
"""

import json
import re

MAX_LEN = 100000      # 输入长度上限
MAX_DEPTH = 32        # 嵌套深度上限
MAX_ARGS = 256        # 参数个数上限

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _depth(obj, cur=0):
    """近似深度（超限即早返回，避免对深度炸弹做完整遍历）。"""
    if cur > MAX_DEPTH:
        return cur
    if isinstance(obj, dict):
        return max([cur] + [_depth(v, cur + 1) for v in obj.values()])
    if isinstance(obj, list):
        return max([cur] + [_depth(v, cur + 1) for v in obj])
    return cur


def _err(kind, msg):
    return {"ok": False, "tool": None, "args": None,
            "error_kind": kind, "error": msg}


def _strip_fence(text):
    m = _FENCE.search(text)
    return m.group(1) if m else text


def _balanced_slice(text):
    """取第一个平衡的 {...} 片段（忽略字符串内的括号）。"""
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def parse_call(text):
    """解析一次函数调用；永不抛异常（fail-closed）。"""
    try:
        if text is None:
            return _err("EMPTY", "输入为 None")
        if not isinstance(text, str):
            return _err("NOT_STR", f"输入非字符串: {type(text).__name__}")
        if not text.strip():
            return _err("EMPTY", "输入为空")
        if len(text) > MAX_LEN:
            return _err("TOO_LONG", f"输入超长 {len(text)} > {MAX_LEN}")

        body = _strip_fence(text).strip()

        obj = None
        for cand in (body, _balanced_slice(body)):
            if cand is None:
                continue
            try:
                obj = json.loads(cand)
                break
            except (json.JSONDecodeError, ValueError):
                fixed = TRAILING_COMMA.sub(r"\1", cand)
                try:
                    obj = json.loads(fixed)
                    break
                except (json.JSONDecodeError, ValueError):
                    continue

        if obj is None:
            return _err("NOT_JSON", "无法解析为 JSON 对象")

        if not isinstance(obj, dict):
            return _err("NOT_OBJ", f"顶层非对象: {type(obj).__name__}")

        if _depth(obj) > MAX_DEPTH:
            return _err("TOO_DEEP", f"嵌套超深 > {MAX_DEPTH}")

        tool = obj.get("tool")
        if tool is None:
            tool = obj.get("name")
        if not isinstance(tool, str) or not tool.strip():
            return _err("BAD_TOOL", f"工具名缺失或非字符串: {tool!r}")

        args = obj.get("args", obj.get("arguments", {}))
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return _err("BAD_ARGS", f"参数非对象: {type(args).__name__}")
        if len(args) > MAX_ARGS:
            return _err("TOO_MANY_ARGS", f"参数过多 {len(args)} > {MAX_ARGS}")

        for k in args:
            if not isinstance(k, str):
                return _err("BAD_KEY", f"参数键非字符串: {k!r}")

        return {"ok": True, "tool": tool.strip(), "args": args,
                "error_kind": None, "error": None}

    except Exception as e:  # 兜底：任何未预期异常都转结构化错误，绝不外抛
        return _err("INTERNAL", f"未预期异常: {type(e).__name__}: {e}")
