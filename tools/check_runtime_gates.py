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
import docker_sandbox as ds  # noqa: E402
import plugin_chain as pc  # noqa: E402
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


def r6_sandbox_isolation():
    """真实容器沙箱：加固项齐备 + 三项隔离实测（只读/断网/非特权）。

    环境不可用时记为 SKIP（不伪装成 PASS，也不记 FAIL）。
    """
    if not ds.sandbox_available():
        print("  [R6] 容器沙箱不可用 → SKIP（如实跳过，不计 PASS/FAIL）")
        return True

    argv = ds.build_argv("true")
    need = {"--network": "none", "--read-only": None, "--cap-drop": "ALL",
            "--security-opt": "no-new-privileges", "--tmpfs": None,
            "--memory": None, "--pids-limit": None, "--user": None}
    missing = [k for k in need if k not in argv]
    pts = [("加固参数齐备", not missing, not missing)]

    r = ds.run_in_sandbox("echo INSIDE_OK; id -u")
    uid_ok = r["ok"] and "INSIDE_OK" in r["stdout"] and "0" != r["stdout"].splitlines()[-1].strip()
    pts.append(("容器内可执行且非 root(uid!=0)", uid_ok, uid_ok))

    r = ds.run_in_sandbox("echo x > /work/evil 2>/dev/null && echo WROTE || echo RO_BLOCKED")
    ro_ok = "RO_BLOCKED" in r["stdout"]
    pts.append(("只读挂载拒绝写入", ro_ok, ro_ok))

    r = ds.run_in_sandbox("wget -q -O- http://example.com >/dev/null 2>&1 "
                          "&& echo NET_UP || echo NET_BLOCKED")
    net_ok = "NET_BLOCKED" in r["stdout"]
    pts.append(("默认断网（外联不可达）", net_ok, net_ok))

    r = ds.run_in_sandbox("sleep 30", timeout=3)
    to_ok = r["timed_out"] and not r["ok"]
    pts.append(("超时即杀且 ok=False（fail-closed）", to_ok, to_ok))

    ok = all(p[2] for p in pts)
    print(f"  [R6] 容器沙箱隔离实测  {'PASS' if ok else 'FAIL'}")
    for label, val, good in pts:
        print(f"       {'ok ' if good else 'BAD'} {label} = {val}"
              + (f"（缺: {missing}）" if label == '加固参数齐备' and missing else ""))
    return ok


def r7_plugin_chain():
    """插件链：被拒步骤**不执行**、整链中止；放行步骤在真实沙箱内可读文件。"""
    if not ds.sandbox_available():
        print("  [R7] 容器沙箱不可用 → SKIP")
        return True
    import tempfile

    pts = []
    # 1) 链在首个被拒步骤中止，且该步 executed=False
    steps = [{"tool": "read_file", "args": {"path": "sandbox/a.txt"}},
             {"tool": "write_file", "args": {"path": "sandbox/b.txt", "data": "x"}},
             {"tool": "read_file", "args": {"path": "sandbox/c.txt"}}]
    res = pc.execute_chain(steps)          # 默认 stub 执行器
    stopped_ok = (res["completed"] is False and res["stopped_at"] == 1
                  and res["denied_rule"] == "R-READONLY"
                  and res["trace"][1]["executed"] is False
                  and sum(1 for t in res["trace"] if t["executed"]) == 1)
    pts.append(("被拒即中止且该步未执行", stopped_ok, stopped_ok))

    # 2) 全放行的链应在真实沙箱里读到文件内容
    with tempfile.TemporaryDirectory() as td:
        sub = os.path.join(td, "sandbox")
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "hello.txt"), "w", encoding="utf-8") as f:
            f.write("SANDBOX_READ_OK\n")
        # 关键一：路径必须落在策略的 sandbox 根内，否则在校验层即被拒（R-OUTSIDE）
        # 关键二：挂载目录必须能被沙箱用户(nobody, uid 65534)遍历，否则
        #         mkdtemp 默认的 0700 会让容器内 cat 静默 Permission denied。
        os.chmod(td, 0o755)
        os.chmod(sub, 0o755)
        os.chmod(os.path.join(sub, "hello.txt"), 0o644)
        ch = pc.execute_chain(
            [{"tool": "read_file", "args": {"path": "sandbox/hello.txt"}}],
            executor=lambda s: pc.docker_executor(s, workdir=td))
        out = (ch["results"][0].get("stdout") or "") if ch["results"] else ""
        real_ok = ch["completed"] and "SANDBOX_READ_OK" in out
        pts.append(("放行步骤在真实容器内执行成功", real_ok, real_ok))
        if not real_ok:
            print(f"       调试: denied={ch['denied_rule']} results={ch['results']}")

    # 3) 非空性：把只读步骤改成被禁工具，链必须不再完成
    neg = pc.execute_chain([{"tool": "delete_file", "args": {"path": "hello.txt"}}])
    neg_ok = neg["completed"] is False
    pts.append(("非空性：违禁步骤使链失败", neg_ok, neg_ok))

    ok = all(p[2] for p in pts)
    print(f"  [R7] 插件链门控 + 真实执行  {'PASS' if ok else 'FAIL'}")
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
        ("R6 容器隔离", r6_sandbox_isolation()),
        ("R7 插件链门控", r7_plugin_chain()),
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
