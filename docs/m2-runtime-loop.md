# M2 · W2 运行时最小闭环：契约的可执行雏形

> 本文记录 2026-10-11 做的 M2：把 `docs/W2-runtime.md` 的"只声明、不实现"
> 契约做成了**可执行的最小闭环**，并如实说明它抵达了契约的哪一条、没到哪一条。
> **本页所有数字都带 `allow-number` 标记**（它们来自本机检出，不是 bench 结果）。

## 做了什么

`tools/runtime_loop.py`（约 `allow-number`：170 行，stdlib only）：

| 契约条款 | 实现 | 状态 |
|---|---|---|
| `reset` / `step` / `done` 三接口 | `RuntimeLoop.reset(snapshot_id)` / `.step()` / `.done()` | **已实现** |
| AG-W2-3 日志完备（四个必填字段随运行同步产生） | 每次 `step()` 追加一条 `prompt_log` / `tool_calls` / `latency_log`，`done()` 时校验八字段齐全，缺失即拒产轨迹 | **已实现** |
| AG-W2-2 单步有界 | `step_timeout` + `max_steps` 双上界，超步数/超时即中止 | **已实现** |
| AG-W2-4 确定性重放 | 同 `snapshot_id` + 同扰动条件重放，比对 `verdict` 是否一致 | **已实现** |
| W2 消费 W1（只读冻结快照） | 快照以只读目录形式提供，运行时不得写入 | **部分**：读侧独立，写侧仍靠约定 |
| AG-W2-1 禁依赖 A 线实现 | 全程 stdlib，不 import 任何 A 线模块 | **已实现**（A3 code coupling 门继续兜底） |

## 实测输出（`allow-number`）

```text
[loop] reset SNAP-M2-001
[loop] step 1 → tool=fs.read ok=True 0.1ms
[loop] step 2 → tool=fs.stat ok=True 0.1ms
[loop] done  verdict=OK steps=2 evidence=snapshot_digest=2c04b4c5428d steps=2
```

- **确定性验证**（`--selftest` 第 1 项）：同快照重放 `allow-number`：3 次，
  `verdict` 集合为 `allow-number`：`{OK}`（单一元素）。AG-W2-4 可判定。
- **完备性验证**（第 2 项）：手动清空 `_latency_log` 后 `done()` 抛
  `AG-W2-3 日志不完备，缺字段: ['latency_log']` —— 缺哪个字段会被点名，不是笼统拒绝。
- **有界性验证**（第 3 项）：`max_steps=1` 时第 2 步抛
  `超出步数上界 max_steps=1（AG-W2-2）`。
- **接口一次性**（第 4 项）：二次 `reset()` 被拒（契约"中途不得换题"）。

四项全 PASS。注意它们全是**契约自洽性**判定，与检索质量/任务完成率无关。

## 它**不能**声称什么（诚实边界）

1. **这 不是 bench**。loop 里没有任何任务定义、没有评分、没有翻转率分子分母。
   它只是"一条符合契约的轨迹"的生产器。
2. **翻转率仍是 `TBD`**。`results/flip_rate_empty.csv` 依旧只有表头 —— AG-W3-2
   要求"覆盖扰动矩阵全部格点"，而格点清单还没冻结（`TBD`），
   所以在格点冻结前**一行都不该落**。
3. **判定仍是自洽性判定**。loop 的 `verdict` 来自被检快照是否被改动，
   来自任何 LLM 或裁判 —— AG-W3-3（裁判独立性）尚未满足。
4. **沙箱是约定级，不是容器级**。V6 真实容器能力已由 R6 证明，
   但 loop 目前没把执行托管给 `docker_sandbox.py`；loop 只做"读快照"这一类
   非危险动作。把 loop 接到容器执行器是下一步，不是已完成。

## 为什么这样收手

再往下做（真任务、真评分、真扰动矩阵）就要动 `results/` 契约：
按 `results/README.md` 的落数规范，首个 `trace_id` 落盘之日，本仓离开 pre-W1 空仓状态，
落数者必须**在同一变更中更新 `results/README.md` 的"当前状态"小节并跑通门禁**。
在扰动矩阵格点清单（`TBD`）和裁判独立性标准（`TBD`）两个前提未冻结前落数，
等于自己违反 AG-W3-2 / AG-W3-3。

所以 M2 停在"契约可执行、契约可判定、空表仍诚实"这一行。

## 复现

```bash
cd mini-agent-runtime-bench
python3 tools/runtime_loop.py          # 跑一个最小闭环
python3 tools/runtime_loop.py --selftest   # 确定性 / 完备性 / 有界性 / 一次性四项反证
python3 tools/check_gates.py           # A1-A3 仍全 PASS（新增两文件已入 A1 白名单）
python3 tools/check_runtime_gates.py   # R1-R7 仍全 PASS
```
