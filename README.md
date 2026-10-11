# mini-agent-runtime-bench

> 愿景（一句话）：为 mini-agent 的“环境—运行时—经验”三层提供一份**先于任何实现、可独立评审、可机器校验**的空仓规约，让未来的每一次跑分都能被复算、被证伪、被追溯。

状态（2026-10-11）：**规约仓 + 可执行基础设施雏形**。三支柱规约与 `A1–A3` / `R1–R7` 门禁已经落成并通过；**W2 契约已可执行、已能产出真实自洽轨迹**（M2/M3）。但这里的"轨迹"是运行时行为的自洽性判定，**不是 bench 数字**：`results/flip_rate_empty.csv` 保持仅表头，任务完成率、翻转率分子分母仍然 `TBD`。零 bench 语义依然是特性，不是缺失。

## 30 秒看清进度

| 支柱 | 状态 | 说明 |
|---|---|---|
| W1 环境 | 规约 | 快照只读格式已冻结，`tools/runtime_loop.py` 的 `snapshot_id`/`digest` 已实现其中"不可变"这一条 |
| W2 运行时 | **可执行** | `reset/step/done` 三接口 + 八字段轨迹 + 有界 + 确定性重放（`tools/runtime_loop.py`，`--selftest` 四项反证全 PASS） |
| W3 经验 | 空 | 无裁判、无任务集，`results/flip_rate_empty.csv` 仍仅表头 |
| 门禁 A1–A3 | ✅ 全绿 | 结构漂移 / 空仓诚实性 / 耦合零容忍；`A3-honesty` 会在扫描前剥离版本号 |
| 门禁 R1–R7 | ✅ 全绿 | 危险调用拦截、合法放行、畸形语料零崩溃、确定性、非空性、**真实容器隔离**、插件链被拒即中止 |
| M3 轨迹 | ✅ 落盘 | `results/w2_runs.jsonl` 8 条真实轨迹，含 3 条被拒绝/中止的路径 |

## 三支柱

- **W1 环境（`docs/W1-environment.md`）**：定义任务快照的只读格式——任务文本与参考答案以 COPY 方式冻结落盘，落盘后不可变。W1 不做任何实时取数，不依赖任何外部 A 线实现；它的全部职责是让“测的是同一道题”这件事可被检查。
- **W2 运行时（`docs/W2-runtime.md`）**：声明最小闭环接口契约（reset → step → done）与轨迹日志模式。契约本身仍以文档为准；**实现雏形见 `tools/runtime_loop.py` 与 `docs/m2-runtime-loop.md`**，任何未来实现都必须逐条满足其中的不变量与反作弊条款，否则门禁判定其轨迹无效。
- **W3 经验（`docs/W3-experience.md`）**：定义翻转率（flip-rate）——同一轨迹在“扰动矩阵 × 阶段切换 × 裁判重判”下重放，结论发生翻转的比例。定义先行、数据空缺：`results/flip_rate_empty.csv` 当前仅表头，这是诚实的零证据声明，而不是零结果。

## 显式非目标（Non-goals）

- 不做任何 bench 实现代码（agent、环境、裁判一律不实现）。
- **不跑分、不产出任务完成率或模型排名**；凡需测量的值一律写 `TBD`。`tools/w2_runs.py` 的 8 条轨迹测的是运行时行为（动作解析、策略拒绝、契约中止、digest 不变性），没有任何 LLM 被调用，**不构成 agent benchmark**。
- 不从 A 线复制或引用实现；快照只 COPY 文本，禁 IMPORT 任何 A 线模块（门禁 A3 强制，详见各 W 文档的反作弊条款）。
- 不做横向模型排名、不发布榜单；本仓库是规约仓，不是排行榜。

## 空仓契约（Empty-bin contract）

1. 每个未来指标在落地前必须同时满足三项：值为 `TBD`、链路为 `trace_id: null`、证据为 `evidence: none`，三者缺一即视为对空仓的破坏。
2. `results/` 下的空表（当前仅 `flip_rate_empty.csv` 的一行表头）表示“尚无证据”，绝不表示“测得为零”；在真实运行产生证据之前，禁止向其中追加任何数据行（语义与落数规范见 `results/README.md`）。
3. 任何文档不得出现无出处的数值声明（百分比、样本量、指标赋值、小数型结论一律禁止，`TBD` 与白名单注释行除外）；门禁 A3 对此做机器检查，违规即 FAIL。
4. 耦合零容忍：除“禁止性表述”（含“禁/禁止/不得”等字样的反作弊条款）与显式白名单注释行外，正文不得出现 A 线实现引用与跨仓绝对路径；门禁 A3 做机器检查。

## 门禁（Gates）

```sh
python tools/check_gates.py
```

预期输出（全部 PASS 才算通过）：

```text
PASS [A1] structure: file set matches, no drift
PASS [A2] docs: W1/W2/W3 + placeholder spec complete
PASS [A2-readme] README is reviewable (vision/pillars/non-goals/contract/gates/roadmap)
PASS [A2-pillars] W1/W2/W3 independently reviewable (schema + anti-gaming + acceptance)
PASS [A3] zero coupling, no abs paths, header-only csv
PASS [A3-header] flip_rate_empty.csv header matches contract
PASS [A3-honesty] no invented numbers in README/docs/results
```

门禁脚本 `tools/check_gates.py` 本身是基础设施（标准库 only），不是 bench 实现代码，不计入“零实现”承诺的例外——它不实现任何 bench 语义，只做 fail-closed 的存在性与诚实性断言。门禁语义详见 `docs/gates-A1-A3.md`。

## 路线图（Roadmap）

- **W1 → 落盘任务快照模式**：先冻结“测什么”，字段表与反作弊见 `docs/W1-environment.md`；快照未冻结前，不讨论运行时。
- **W2 → 声明运行时契约**：契约已声明，2026-10-11 起有可执行雏形（`tools/runtime_loop.py`）+ 真实轨迹（`results/w2_runs.jsonl`）。注意 `OK` 只是"快照未被改动"的自洽判定，**不是任务成功**。
- **W3 → 落数经验指标**：仍然只定义、不落数。翻转率定义与重放规范见 `docs/W3-experience.md`，落数规范见 `results/README.md`；首个真实 `trace_id` 落盘之前，所有指标保持 `TBD`。
- **下一步的真实缺口**：任务集（含负例）、裁判独立性标准（AG-W3-3 仍 `TBD`）、可用的推理端点。三者齐备之前不落任何 bench 数字——这是 M2 定下、M3 沿用的纪律。

## 怎么复现

```sh
python tools/check_gates.py            # A1-A3 八项，应全 PASS
python tools/check_runtime_gates.py    # R1-R7，含真实容器隔离
python tools/runtime_loop.py --selftest  # 四项反证（确定性/完备性/有界/reset 一次性）
python tools/w2_runs.py                # 8 条轨迹 → results/w2_runs.jsonl
```

全部为标准库 + 本机 `docker`，无网络、无 API key。

## 仓库地图

| 路径 | 性质 | 说明 |
| --- | --- | --- |
| `docs/W1-environment.md` | 规约 | W1 快照模式：字段表、不变量/反作弊、验收标准 |
| `docs/W2-runtime.md` | 规约 | W2 运行时契约：接口、轨迹日志、不变量/反作弊、验收标准 |
| `docs/W3-experience.md` | 规约 | W3 翻转率定义：扰动矩阵、重放表模式、反作弊、验收标准 |
| `docs/gates-A1-A3.md` | 规约 | 门禁语义说明 |
| `docs/resume-placeholder-spec.md` | 规约 | 占位符恢复语义：`TBD` + 空 `trace_id` 链 |
| `results/flip_rate_empty.csv` | 空证据 | 仅表头；零数据行 = 零证据诚实声明 |
| `results/w2_runs.jsonl` | 真实轨迹 | 8 条运行时行为轨迹（M3）。**非 bench 结果**：无 LLM 被调用，无任务完成率 |
| `results/README.md` | 规约 | 空表语义、列定义、将来落数规范（`trace_id` 链） |
| `tools/check_gates.py` | 门禁 | fail-closed 校验 A1–A3（标准库 only，非 bench 实现） |
| `tools/check_runtime_gates.py` | 门禁 | fail-closed 校验 R1–R7 运行安全，含非空性反证 |
| `tools/runtime_loop.py` | 雏形 | W2 `reset/step/done` + 八字段轨迹 + `replay()` 重放（M2，stdlib only） |
| `tools/call_guard.py` `docker_sandbox.py` `plugin_chain.py` | 基础设施 | 解析守卫 / 真实容器沙箱 / 插件执行链（P3-HARDEN） |
| `tools/w2_runs.py` | 基础设施 | 8 个手写动作序列 → 落盘轨迹（M3） |
| `docs/m2-runtime-loop.md` `docs/m3-runtime-runs.md` `docs/m3-plan.md` | 过程文档 | 各阶段"做了什么/没做什么/口径怎么定的" |
| `PHASE_LOG.md` | 过程记录 | 阶段门禁日志（过程记录，非 bench 实现） |

许可：MIT（见 `LICENSE`）。
