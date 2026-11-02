# PREREG — mini-agent-runtime-bench (规约仓)

> 预注册规格：本文件声明**本规约仓可检验的研究假设、评测方案、成功标准与
> 明确边界**。内容全部对应仓库真实实现与真实门禁输出
> （`docs/W1-environment.md`/`W2-runtime.md`/`W3-experience.md` 三支柱、
> `tools/check_gates.py` 的 A1–A3、`tools/check_runtime_gates.py` 的 R1–R7、
> `tools/runtime_loop.py` 的 `--selftest`、`results/w2_runs.jsonl` 的 8 条轨迹、
> `results/flip_rate_empty.csv` 的仅表头），不含虚构数字或未实现能力。
>
> 定位：**规约仓 + 可执行基础设施雏形**，不是排行榜。零 bench 语义是**特性**，
> 不是缺失。

## 1. 研究问题

为 mini-agent 的「环境—运行时—经验」三层提供一份**先于任何实现、可独立
评审、可机器校验**的空仓规约，让未来的每一次跑分都能被复算、被证伪、被
追溯。核心机制问题：在一个尚无数值的系统里，如何用**诚实空仓契约**把
「尚无证据」与「测得为零」区分开。

## 2. 假设（H1–H3，全部可证伪）

- **H1（W2 契约可执行）**：`reset/step/done` 三接口 + 八字段轨迹已落成
  （`tools/runtime_loop.py`）；`--selftest` 四项反证全 PASS（确定性重放一致 /
  缺 latency_log 拒产 / 超步数中止 / reset 一次性）。
- **H2（诚实空仓契约）**：每个未来指标落地前必须同时满足三项——值为 `TBD`、
  链路 `trace_id: null`、证据 `evidence: none`；`results/flip_rate_empty.csv`
  仅表头表示「尚无证据」，绝不表示「测得为零」。
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
4. `tests/`（本规格新增）：12 项离线测试全过——运行时闭环八字段、篡改检出、
   超步数中止、reset 一次性、确定性重放、call-guard 解析（合法/空/非 JSON/
   尾逗号/fence/垃圾永不外抛）。
5. **边界如实**：`flip_rate_empty.csv` 保持仅表头；任务完成率、翻转率分子分母
   仍 `TBD`（零 bench 语义是特性）。

## 5. 明确边界（不证明什么）

- **不证明任何 bench 数字**：不跑分、不产出任务完成率或模型排名；凡需测量的
  值一律写 `TBD`。`w2_runs.jsonl` 的 8 条轨迹测**运行时行为**，不构成 agent
  benchmark。
- **不证明任务完成率/检索质量/agent 智能**：无裁判、无任务集，`OK` 只是
  「快照未被改动」的自洽判定，**不是任务成功**；无任何 LLM 被调用。
- **不证明容器隔离当前可通过**：R6/R7 需本机已有
  `nvidia/cuda:12.6.0-base-ubuntu24.04` 镜像；本机 2026-11-01 实测
  `docker pull` 超时、该镜像未拉取，故 R6/R7 **如实 FAIL**（fail-closed，
  不伪装 PASS）——这是**环境缺镜像**，不是代码缺陷。
- **不证明免于耦合**：A3 强制零耦合（禁 IMPORT A 线模块、无跨仓绝对路径），
  但它是机器检查，不是人类评审。

## 6. 数据与复现

- 复现：
  ```bash
  python tools/check_gates.py            # A1-A3 八项，应全 PASS
  python tools/check_runtime_gates.py    # R1-R7（R6/R7 需本机已有 DEFAULT_IMAGE 镜像）
  python tools/runtime_loop.py --selftest  # 四项反证
  python tools/w2_runs.py                # 8 条轨迹 → results/w2_runs.jsonl
  python -m pytest tests/ -q             # 12 项离线测试
  ```
