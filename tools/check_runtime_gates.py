#!/usr/bin/env python3
"""C 线运行时门（P3-HARDEN）——安执 / 解析守卫 / 智能体评分的 fail-closed 验收。

门清单：
  R1 安执拦截：golden 攻击集全部被拦且命中期望规则（拦截率必须为全量）
  R2 零误拦：golden 合法集全部放行
  R3 零崩溃：解析守卫对畸形输入语料永不抛异常，且始终返回结构化结果
  R4 评分正确：API-Bank 三分 / DyLAN 选人 / MemGPT 记忆块的确定性断言
  R5 非空性（反证）：证明以上门**能够失败**——弱化策略必须让攻击泄漏，
     注入畸形用例必须让断言失守。门若恒真，本项 FAIL。

基础设施，stdlib only，不含 bench 语义、不产生评测数字。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from agent_scoring import (  # noqa: E402
    MemoryBlock, rate, score_three_dim, select_agents,
)
from call_guard import parse_call  # noqa: E402
from sandbox_validator import (  # noqa: E402
    default_policy, load_golden, validate_call,
)

GOLDEN = os.path.join(HERE, "golden_attacks.json")

FUZZ = [
    None, "", "   ", "null", "[]", "{}", "{", "}", '"just a string"', "123",
    "true", "not json", "{'tool':'x'}", '{"tool":"x",}',
    '{"tool":123,"args":{}}', '{"tool":[],"args":{}}',
    '{"tool":"x","args":[]}', '{"tool":"x","args":null}',
    '{"tool":"x","args":{"a":1}} trailing',
    '```json\n{"tool":"x","args":{}}\n```',
    '```\n{"tool":"y","args":{"p":"sandbox/a"}}\n```',
    '{"name":"z","arguments":{"p":"sandbox/b"}}',
    "{" * 200 + "}" * 200,          # 深/长括号
    '{"tool":"' + "a" * 50000 + '","args":{}}',
    '\x00\x01\x02', "🙂" * 100, "{\"tool\":\"x\"}",
]


def r1_attacks(golden):
    leaks = []
    for atk in golden["attacks"]:
        r = validate_call(atk["call"])
        if r["allowed"] or r["rule"] != atk["expect_rule"]:
            leaks.append((atk["name"], r))
    n = len(golden["attacks"])
    ok = not leaks
    print(f"  [R1] 拦截 {n - len(leaks)}/{n} 危险调用"
          f"（命中期望规则）  {'PASS' if ok else 'FAIL'}")
    for name, r in leaks:
        print(f"       LEAK {name}: {r}")
    return ok


def r2_safe(golden):
    fp = []
    for s in golden["safe"]:
        r = validate_call(s["call"])
        if not r["allowed"]:
            fp.append((s["name"], r))
    n = len(golden["safe"])
    ok = not fp
    print(f"  [R2] 放行 {n - len(fp)}/{n} 合法调用（零误拦）"
          f"  {'PASS' if ok else 'FAIL'}")
    for name, r in fp:
        print(f"       FALSE-POSITIVE {name}: {r}")
    return ok


def r3_fuzz():
    crashed, malformed = [], []
    for i, text in enumerate(FUZZ):
        try:
            res = parse_call(text)
        except Exception as e:  # 门要抓的就是这个
            crashed.append((i, type(e).__name__, str(e)[:60]))
            continue
        if not (isinstance(res, dict) and set(res) ==
                {"ok", "tool", "args", "error_kind", "error"}):
            malformed.append((i, res))
    ok = not crashed and not malformed
    print(f"  [R3] 畸形语料 {len(FUZZ)} 条：崩溃 {len(crashed)}，"
          f"结构异常 {len(malformed)}  {'PASS' if ok else 'FAIL'}")
    for c in crashed:
        print(f"       CRASH #{c[0]} {c[1]}: {c[2]}")
    return ok


def r4_scoring():
    bad = []

    s = score_three_dim([{"dim": "plan", "ok": True},
                         {"dim": "plan", "ok": False},
                         {"dim": "retrieve", "ok": True},
                         {"dim": "call", "ok": True}])
    if s["plan"] != [1, 2] or s["retrieve"] != [1, 1] or s["call"] != [1, 1]:
        bad.append(f"three_dim {s}")
    if s["overall"] != [3, 4]:
        bad.append(f"overall {s['overall']}")
    if rate([0, 0]) is not None:
        bad.append("rate 分母 0 应返回 None")
    if abs(rate([3, 4]) - 0.75) > 1e-9:
        bad.append("rate 计算错")

    picks = select_agents([{"agent": "b", "calls": 4, "useful": 2},
                           {"agent": "a", "calls": 4, "useful": 2},
                           {"agent": "c", "calls": 1, "useful": 1},
                           {"agent": "d", "calls": 9, "useful": 0}],
                          k=2, min_calls=2)
    if picks != ["a", "b"]:
        bad.append(f"select_agents {picks}（同分应按名字典序）")
    if select_agents([{"agent": "x", "calls": 0, "useful": 0}], k=1) != []:
        bad.append("调用次数不足不应入选")

    m = MemoryBlock(2)
    if m.append("p") is not None or m.append("q") is not None:
        bad.append("容量内不应晋升")
    if m.append("r") != "p":
        bad.append("溢出应晋升最旧项")
    if not m.recall("p") or m.state()["items"] != ["q", "r", "p"]:
        bad.append("recall 未把项调回块尾")
    if m.recall("zz") is not False:
        bad.append("recall 不存在项应返回 False")

    ok = not bad
    print(f"  [R4] 三分/选人/记忆块确定性断言  {'PASS' if ok else 'FAIL'}")
    for b in bad:
        print(f"       {b}")
    return ok


def r5_nonvacuity(golden):
    """反证：门必须能失败。弱化策略后攻击应泄漏；否则 R1 恒真、形同虚设。"""
    pts = []

    weak = dict(default_policy())
    weak["allowed_tools"] = sorted(set(weak["allowed_tools"]) | {"write_file"})
    weak["allow_write"] = True
    leaked = sum(1 for a in golden["attacks"]
                 if a["expect_rule"] == "R-READONLY"
                 and validate_call(a["call"], policy=weak)["allowed"])
    pts.append(("弱化策略(allow_write)后 R-READONLY 攻击泄漏数", leaked, leaked > 0))

    weak2 = dict(default_policy())
    weak2["allow_metachars"] = True
    weak2["allowed_tools"] = sorted(set(weak2["allowed_tools"]) | {"shell"})
    leaked2 = sum(1 for a in golden["attacks"]
                  if a["expect_rule"] == "R-METACHAR"
                  and validate_call(a["call"], policy=weak2)["allowed"])
    pts.append(("弱化策略(allow_metachars+shell)后 R-METACHAR 泄漏数",
                leaked2, leaked2 > 0))

    # 解析守卫反向：注入「本应失败」的期望，断言确实为失败
    bad_expect = parse_call("{}")["ok"]
    pts.append(("parse_call('{}') 必须 ok=False", bad_expect, bad_expect is False))

    ok = all(p[2] for p in pts)
    print(f"  [R5] 非空性反证（门能失败）  {'PASS' if ok else 'FAIL'}")
    for label, val, good in pts:
        print(f"       {'ok ' if good else 'BAD'} {label} = {val}")
    return ok


def main():
    golden = load_golden(GOLDEN)
    print("C 线运行时门（P3-HARDEN）")
    results = [
        ("R1 安执拦截", r1_attacks(golden)),
        ("R2 零误拦", r2_safe(golden)),
        ("R3 零崩溃", r3_fuzz()),
        ("R4 评分正确", r4_scoring()),
        ("R5 非空性", r5_nonvacuity(golden)),
    ]
    print()
    failed = [name for name, ok in results if not ok]
    if failed:
        print(f"RUNTIME GATES FAIL: {len(failed)} 门未过 → {failed}")
        return 1
    print(f"RUNTIME GATES PASS: {len(results)} 门全过"
          f"（含非空性反证，门可失败）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
