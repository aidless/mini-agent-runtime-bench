"""C 线 judge 判分金标门（P4-NOISE-FLOOR）——空壳前的接线点。

为什么这个门现在是 SKIP 而不是 PASS：见 docs/p4-noise-floor-gate.md 的「空仓契约」。
本仓目前没有任何 bench 结果，所以也**没有任何 judge 判分**可供审计。
在没有 judge 判分之前谈 judge 复现率是无意义的（分母为零），
所以本门在缺少 audit 报告时返回 SKIP，并把该臂标为 unscored。

本文件是纯接线基础设施（stdlib only），不含 bench 语义、不产生也不声称任何 bench 数字。
"""
from __future__ import annotations

import json
import os
import sys

# 与 tools/bench-noise-floor/README.md §6.1 的阈值保持一致。
# 复现率阈值取自该 README 实测的留一法下限量级（两口径约 85%~89%），不是随手取的整数。
MIN_REPRODUCTION = 85.0
MIN_ITEMS = 200
MARGINAL_MARGIN = 2.0

VERDICTS = ("READABLE", "MARGINAL", "UNREADABLE")

REQUIRED_KEYS = ("gold_method", "n_items", "ceiling_loo_macro", "verdict",
                 "leaderboard")

# audit 报告默认放在本仓的 results/ 下；未生成时即为「未接入证据」。
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPORT = os.path.join(REPO, "results", "judge_gold_audit.json")


def classify(ceiling, top):
    """与 tools/bench-noise-floor/audit.py 的三档判决保持同构。

    本仓不允许 import 那个脚本：它依赖 pandas/numpy，而本仓所有门都是
    stdlib only 的独立实现。这里重复实现是为了让两处判决不会因为
    一方被改坏而静默分歧；变异测试请分别在两侧做。
    """
    if ceiling > top + 1e-9:
        return "UNREADABLE"
    if top - ceiling < MARGINAL_MARGIN:
        return "MARGINAL"
    return "READABLE"


def gate(report):
    """返回 (verdict, why, todo)。verdict ∈ {"PASS", "FAIL"}。"""
    if not isinstance(report, dict):
        return "FAIL", "报告不是 JSON 对象", ["重跑 audit.py --json"]
    missing = [k for k in REQUIRED_KEYS if k not in report]
    if missing:
        return "FAIL", f"缺必需字段 {missing}", ["报告不是 audit.py --json 的产物"]
    n = report["n_items"]
    if not isinstance(n, int) or isinstance(n, bool) or n < MIN_ITEMS:
        return "FAIL", f"题量 {n!r} 不足 {MIN_ITEMS}", ["补题量；样本太小的门禁没有意义"]
    ceiling = report["ceiling_loo_macro"]
    if not isinstance(ceiling, (int, float)) or not 0 <= ceiling <= 100:
        return "FAIL", f"留一法下限 {ceiling!r} 非法", ["报告缺少可用的复现率"]
    lb = report["leaderboard"]
    if not isinstance(lb, list) or not lb or "macro" not in lb[0]:
        return "FAIL", "leaderboard 为空或缺 macro", ["重跑 audit.py"]
    top = lb[0]["macro"]
    declared = report["verdict"]
    if declared not in VERDICTS:
        return "FAIL", f"verdict={declared!r} 非法", ["重跑 audit.py"]
    recomputed = classify(float(ceiling), float(top))
    if recomputed != declared:
        return "FAIL", (f"报告自相矛盾：声明 {declared}，本门重算 {recomputed}"
                        "（报告被改过或两侧判决漂移）"), ["重跑 audit.py；勿手改报告"]
    if declared == "UNREADABLE":
        return "FAIL", (f"榜首 {top:.2f}% vs 留一法下限 {ceiling:.2f}% "
                        "-> UNREADABLE：名次首先反映与 judge 的对齐程度而非能力"), \
                       ["该臂标 unscored，不参与任何均值与排名"]
    if float(ceiling) < MIN_REPRODUCTION:
        return "FAIL", (f"复现率 {ceiling:.2f}% < 阈值 {MIN_REPRODUCTION}%"), \
               ["换 judge / 补人工标注 / 只报原始引用并附本报告"]
    if declared == "MARGINAL":
        return "PASS", (f"判决 MARGINAL，余量仅 {top - float(ceiling):.2f} 点"), \
               ["可收，但名次表必须并列两种金标口径（--gold both）且必须报 CI"]
    return "PASS", f"判决 READABLE（榜首 {top:.2f}% vs 下限 {ceiling:.2f}%）", []


def main(argv):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    path = DEFAULT_REPORT
    for i, a in enumerate(argv):
        if a == "--report" and i + 1 < len(argv):
            path = argv[i + 1]
    if not os.path.exists(path):
        print(f"SKIP：找不到 audit 报告 {path}")
        print("      → 本门**未接入证据**，不计 PASS 也不计 FAIL。")
        print("      → 在量出 judge 对人工金标的复现率之前，任何由 judge "
              "判分推出的名次/计数都不得被引用为「可读」。")
        print("      → 该臂标 unscored，不参与任何均值与排名（0 会伪装成"
              "「测过且全错」）。")
        return 0
    with open(path, encoding="utf-8") as fh:
        report = json.load(fh)
    verdict, why, todo = gate(report)
    print(f"判分金标门禁 · {os.path.basename(path)}")
    print(f"  · 金标口径 gold={report.get('gold_method')!r}，"
          f"题量 n={report.get('n_items')}")
    print(f"  · {why}")
    for t in todo:
        print(f"  → {t}")
    print(f"  阈值：复现率>={MIN_REPRODUCTION}%、题量>={MIN_ITEMS}、"
          "UNREADABLE 一律拒收")
    print(f"VERDICT = {verdict}")
    return 0 if verdict == "PASS" else 1


def selftest():
    """非空性反证：证明这个门能够失败。门若恒真，本项 FAIL。"""
    def rep(ceiling=85.0, top=90.0, n=200, verdict=None,
            gold="majority", lb=True):
        # verdict=None 时按本门自己的 classify() 推出，让夹具内部自洽。
        # 早先默认写死 "MARGINAL"（与 top=90/ceiling=85 的实际 READABLE 矛盾），
        # 于是两条本意不同的负例都被「报告自相矛盾」先拦下 —— 门看起来在拦，
        # 其实拦的是别的东西：这是假门的又一种形态。
        if verdict is None:
            verdict = classify(float(ceiling), float(top))
        return {"gold_method": gold, "n_items": n,
                "ceiling_loo_macro": ceiling, "verdict": verdict,
                "leaderboard": ([{"system": "s", "macro": top}] if lb else [])}

    def expect_fail(label, report, must_contain):
        v, why, _ = gate(report)
        hit = v == "FAIL" and must_contain in why
        print(f"  {'ok ' if hit else 'BAD'} {label} -> {v}（{why[:56]}）")
        if not hit:
            print(f"       期望 FAIL 且原因含「{must_contain}」，"
                  f"实得 {v} / {why[:56]}")
        return hit

    def expect_pass(label, report):
        v, why, _ = gate(report)
        ok = v == "PASS"
        print(f"  {'ok ' if ok else 'BAD'} {label} -> {v}（{why[:56]}）")
        return ok

    print("judge 判分金标门 · 非空性反证")
    pts = [
        expect_pass("正常 READABLE", rep(top=95.0)),
        expect_pass("正常 MARGINAL（擦线 1.08 点）", rep(top=86.08)),
        expect_fail("UNREADABLE", rep(top=85.96, ceiling=89.21),
                    "UNREADABLE"),
        expect_fail("复现率 84.99% 低于阈值", rep(ceiling=84.99), "复现率"),
        expect_fail("题量 199 不足", rep(n=199), "不足"),
        expect_fail("缺复现率字段", {"gold_method": "majority", "n_items": 200,
                                     "verdict": "READABLE", "leaderboard": []},
                    "缺必需字段"),
        expect_fail("手改报告只改 verdict", rep(top=95.0, verdict="MARGINAL"),
                    "自相矛盾"),
        expect_fail("verdict 非法值", rep(verdict="MAYBE"), "非法"),
        expect_fail("复现率超出 100%", rep(ceiling=101.0), "非法"),
        expect_fail("leaderboard 为空", rep(lb=False), "leaderboard"),
    ]
    ok = all(p for p in pts)
    print(f"  [{'PASS' if ok else 'FAIL'}] 非空性反证 "
          f"{sum(1 for p in pts if p)}/{len(pts)}")
    if not ok:
        print("RUNTIME: judge 金标门恒真，门失效")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(None))
