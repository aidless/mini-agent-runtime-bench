# PREREG — mini-agent-runtime-bench (规约仓)

> 预注册规格：本文件声明**本规约仓可检验的研究假设、评测方案、成功标准与
> 明确边界**。内容全部对应仓库真实实现与真实门禁输出
> （`docs/W1-environment.md`/`W2-runtime.md`/`W3-experience.md` 三支柱、
> `tools/check_gates.py` 的 A1–A3、`tools/check_runtime_gates.py` 的 R1–R7、
> `tools/runtime_loop.py` 的 `--selftest`、`results/w2_runs.jsonl` 的 8 条轨迹、
> `results/flip_rate_empty.csv` 的仅表头，以及 `results/flip_rate.csv` 的
> 脚本策略计数），不含虚构数字或未实现能力。
>
> 定位：**可复算的脚本策略翻转率管道 + 运行时门禁**，不是排行榜，也不是
> LLM 智能体基准。空表哨兵仍然表示「尚无那张表的证据」，不是测得为零。

## 1. 研究问题

为 mini-agent 的「环境—运行时—经验」三层提供一份**先于任何实现、可独立
评审、可机器校验**的空仓规约，让未来的每一次跑分都能被复算、被证伪、被
追溯。核心机制问题：在一个尚无数值的系统里，如何用**诚实空仓契约**把
「尚无证据」与「测得为零」区分开。

## 2. 假设（H1–H3，全部可证伪）

- **H1（W2 契约可执行）**：`reset/step/done` 三接口 + 八字段轨迹已落成
  （`tools/runtime_loop.py`）；`--selftest` 四项反证全 PASS（确定性重放一致 /
  缺 latency_log 拒产 / 超步数中止 / reset 一次性）。
- **H2（诚实契约）**：没有 trace 的指标保持 `TBD`、`trace_id: null`、
  `evidence: none`。`results/flip_rate_empty.csv` 仅表头，表示「尚无这张表的
  证据」，绝不表示「测得为零」。`results/flip_rate.csv` 允许有行，但每行必须
  有能回链的 trace id 和存在的证据文件，并且 README 的 measured 块与重算一致。
- **H3（门禁 fail-closed）**：A1–A3（结构漂移/空仓诚实/耦合零容忍）与 R1–R7
  （危险调用拦截/合法放行/畸形语料零崩溃/确定性/非空性/真实容器隔离/插件链
  被拒即中止）全部通过才算门禁有效；任何一项 FAIL 即整体 FAIL，不伪装 PASS。

## 3. 评测方案

- **门禁**：`tools/check_gates.py`（A1–A3 八项）与 `tools/check_runtime_gates.py`
  （R1–R7）做 fail-closed 的存在性与诚实性断言；`tools/runtime_loop.py
  --selftest` 四项反证。
- **轨迹**：`tools/w2_runs.py` 产出 `results/w2_runs.jsonl` 8 条真实轨迹
  （动作解析/策略拒绝/契约中止/digest 不变性），无 LLM 被调用。
- **诚实性**：`A3-honesty` 机器扫描 README/docs/results 的**无出处数值声明**，
  违规即 FAIL；扫描前剥离版本号（版本不是结果）。

## 4. 成功标准

1. `tools/check_gates.py`：A1–A3 八项全 PASS（本仓已实测）。
2. `tools/runtime_loop.py --selftest`：四项反证全 PASS（本仓已实测）。
3. `tools/w2_runs.py`：8 条轨迹落盘，含 3 条被拒绝/中止路径。
4. `tools/run_offline_tests.py` 退出码为零。条数以该命令打印的 PASS 行为准，
   不在本文写死。覆盖运行时闭环、篡改检出、超步数中止、reset 一次性、确定性重放、
   call-guard 畸形输入，以及脚本策略翻转率（确定性策略翻转数为零、按序号交替的
   策略翻转数非零、缺 trace id 的计数行被拒绝）。
5. **边界如实**：`flip_rate_empty.csv` 保持仅表头。脚本策略翻转率的分子分母
   只来自重算，并且页面写明它不是 LLM 能力。三轴里的阶段切换与独立裁判仍是
   `TBD`。

## 5. 明确边界（不证明什么）

- **不证明 LLM 能力或模型排名**。`w2_runs.jsonl` 的轨迹测运行时行为。
  `flip_rate.csv` 测的是脚本函数在「再跑一次」下稳不稳，不构成 agent
  benchmark。
- **不证明任务完成率来自阅读题面**：脚本策略执行 `spec`，不解析 `task_text`。
  `w2_runs.jsonl` 里的 `OK` 只是「快照未被改动」。无任何 LLM 被调用。
- **不证明容器隔离当前可通过**：R6 与 R7 的容器步骤需要本机已经有
  `DEFAULT_IMAGE`（`nvidia/cuda:12.6.0-base-ubuntu24.04` <!-- allow-number -->）。
  镜像不在本地时门禁打印 `SKIP` 和原因，不拉取、不伪装 `PASS`。
  `REQUIRE_DOCKER=1` 才把跳过当成失败。
- **不证明免于耦合**：A3 强制零耦合（禁 IMPORT A 线模块、无跨仓绝对路径），
  但它是机器检查，不是人类评审。

## 6. 数据与复现

- 复现：
  ```bash
  make check                                 # 重算翻转率；容器门可 SKIP
  python tools/check_gates.py            # A1-A3，含证据链
  python tools/check_runtime_gates.py    # R1-R5 必跑；R6/R7 容器步骤可 SKIP
  python tools/runtime_loop.py --selftest
  python tools/compute_flip_rate.py --check
  python tools/run_offline_tests.py
  ```
