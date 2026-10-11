# P3 PHASE_LOG — C线 mini-agent-runtime-bench（世界先进封顶，保持空仓哲学）

- 结果 vs 验收 G3：`tools/check_gates.py` A1/A2/A3 全 PASS；零耦合（evolve/gsm8k/rag_demo 零命中）；csv 仅表头零编造。G3 通过。
- 产出物：`tools/check_gates.py`；`docs/gates-A1-A3.md` 追加 1 行（门禁脚本说明）。
- 失败+纠正：门禁脚本落盘使文件数 9→10 → EXPECTED 加白自身并同步文档（1次纠正）。
- 未动：无实现代码（by design）；数字全 TBD + trace_id 空。

## P3-HARDEN（质量加固到可评审，仍空仓）

- 结果 vs 验收：`python3 tools/check_gates.py` 输出 A1/A2/A2-readme/A2-pillars/A3/A3-header/A3-honesty 全 PASS；`git status` 仅预期文件变更（6 改 + 1 新增），工作树除本段外无杂散文件。门禁通过。
- 产出物：重写 `README.md`（愿景一句话 + 三支柱 + 非目标 + 空仓契约 + 门禁 + 路线图 + 仓库地图，仍声明零实现是特性）；扩展 `docs/W1-environment.md`、`docs/W2-runtime.md`、`docs/W3-experience.md` 到可独立评审（schema 字段表 + 反作弊各 4 条 + 验收标准，数字一律 TBD）；新增 `results/README.md`（空表语义 + 列定义 + 落数 trace_id 链）；加固 `tools/check_gates.py`（README 门面断言、三支柱可评审断言、csv 表头逐字校验、耦合扫描对禁止性表述豁免、诚实性数字检查）；同步 `docs/gates-A1-A3.md` 语义说明（文件数不再写死）。
- 失败+纠正：`python` 命令在host缺失（exit 127）→ 改用 `python3` 验证通过（1次纠正）；旧门禁耦合扫描误伤禁止性表述（如 W2 原文 "Does NOT depend on A-line evolve"）→ 加固版引入禁止性表述豁免 + 白名单注释机制（1次纠正）。
- 未动：零实现代码（by design）；零编造数字（新增诚实性检查强制）；`results/flip_rate_empty.csv` 仍仅表头；绝不 push（本机提交为止）。

## P3-CLOSE（最终验收，空仓封存）

- 结果 vs 验收：GATES A1-A3 全绿，empty-bin 完好。`git status --short` 为空（工作树干净）；`git log --oneline -3` 顶部基线 `bcae518` 与控制器基线全哈希一致；`python3 tools/check_gates.py` 以 `GATES A1-A3 PASS` 结尾；`results/flip_rate_empty.csv` 恰为 1 行表头（`wc -l` = 1），与契约逐字一致。验收通过，封存为空仓状态。
- 实际命令输出（verbatim）：
  - `git -C mini-agent-runtime-bench status --short` →（无输出，空）
  - `git -C mini-agent-runtime-bench log --oneline -3` →
    `bcae518 P3-HARDEN: reviewable spec + empty-csv contract + hardened gates`
    `ed09813 C-line: runtime-bench skeleton (gates-A1-A3 doc + check_gates + empty-csv placeholders) + MIT LICENSE`
  - `git rev-parse HEAD` → `bcae5183c9d2bbfbce82fc530918d0b3b001ba12`（与控制器基线一致）
  - `python3 tools/check_gates.py`（cwd=mini-agent-runtime-bench）→
    `PASS [A1] structure: 12 files present, no drift`
    `PASS [A2] docs: W1/W2/W3 + placeholder spec + results contract complete`
    `PASS [A2-readme] README is reviewable (vision/pillars/non-goals/contract/gates/roadmap)`
    `PASS [A2-pillars] W1/W2/W3 independently reviewable (schema + anti-gaming>=3 + acceptance)`
    `PASS [A3] zero coupling, no abs paths, header-only csv`
    `PASS [A3-header] flip_rate_empty.csv header matches contract`
    `PASS [A3-honesty] no invented numbers in README/docs/results`
    （空行）
    `GATES A1-A3 PASS: pre-W1 empty repo honest`
  - `wc -l results/flip_rate_empty.csv` → `1 results/flip_rate_empty.csv`；首行 `trace_id,task_id,condition,run_id,flip_occurred,flip_type,evidence_path,notes`；`od -c` 尾为 `s \n`（单行表头 + 换行）。
  - `ls FINAL_ACCEPTANCE.md` → `无法访问 'FINAL_ACCEPTANCE.md': 没有那个文件或目录`（按控制器裁决未创建）。
- 产出物：仅追加本 `## P3-CLOSE` 段到 `PHASE_LOG.md`（EXPECTED 集内文件，无新增文件，无文件集漂移）。
- 失败+纠正：0 次纠正。门禁一次跑通；`python` 裸命令未用（按要求只用 `python3`）；`tools/check_gates.py` EXPECTED 未改。
- 未动/约束遵守：零实现代码（by design，空仓即特性）；未编造数字（诚实性门禁通过）；未创建 `FINAL_ACCEPTANCE.md`（控制器裁决：新文件会触发 A1 漂移）；未运行 `git push`、未创建 remotes；未触碰 `gsm8k-self-evolve`、`rag_min_demo`；未修改 `tools/check_gates.py`；本地提交为止。

## P3-HARDEN-C1：C 线运行时安全门（2026-09-12，本地 commit，绝不 push）

- 授权：用户全权授权（P3 加固）；沿用 C 线「空仓诚实 + 零杜撰数字」纪律。
- 新增（基础设施，均零 bench 语义）：
  - `tools/sandbox_validator.py`：安执策略校验器（TaskWeaver 安执迁移）。
  - `tools/golden_attacks.json`：安执 golden 集（危险 + 合法调用，纯数据）。
  - `tools/call_guard.py`：函数调用解析守卫（Gorilla 迁移 + 上游未防护边补强）。
  - `tools/agent_scoring.py`：API-Bank 三分 + DyLAN 选人 + MemGPT 记忆块（确定性纯函数）。
  - `tools/check_runtime_gates.py`：R1-R5 fail-closed 门（含非空性反证）。
  - `docs/p3-runtime-gates.md`：门说明（无杜撰数字，A3-honesty 通过）。
- 实测（cwd=mini-agent-runtime-bench，`python3`）：
  - `python3 tools/check_runtime_gates.py` → exit 0：
    R1 拦截 22/22 危险调用（命中期望规则）；R2 放行 6/6 合法调用（零误拦）；
    R3 畸形语料 27 条零崩溃、零结构异常；R4 三分/选人/记忆块断言全过；
    R5 非空性反证通过（弱化策略后泄漏数 1 与 4，均 > 0 → 门非恒真）。
  - `python3 tools/check_gates.py` → exit 0：A1 18 文件无漂移；A2 四段齐；
    A3 零耦合/无绝对路径/csv 仅表头；A3-header 契约符合；A3-honesty 无杜撰数字。
- 本轮 1 处缺陷发现与修正（门自己抓到的）：
  - `select_agents` 原先把「调用次数不足」的智能体按 0 分参与排序 → 仍可能入选。
    修正为**证据不足不入选**（不是 0 分混入）。R4 断言先 FAIL 后修复转 PASS，
    证明该门具备真实鉴别力（非恒真）。
- 迁移边界：未建远端；未运行 `git push`；未触碰 `gsm8k-self-evolve`、`rag_min_demo`；
  `results/flip_rate_empty.csv` 仍仅表头（空仓契约不变）。
- 未迁移（诚实边界）：Docker/多卡执行沙箱未实现（本机无该条件）；
  TaskWeaver 的插件执行链未接入（仅策略验证层）；安执是必要不充分，
  不据此声称任何能力或完成率。

---

## P3-HARDEN-C2：真实容器沙箱 + 插件执行链（补首轮「未迁移」项，2026-09-12）

- **重要更正**：首轮把「Docker/多卡沙箱」记为「本机无条件」是**错误的假设**。
  新增 `tools/capability_probe.py` 实测后推翻：Docker 可用（容器实测起停成功）、
  `nvidia-smi` 列出 1 卡、容器级隔离可用。教训：能力边界必须探测，不能凭印象。
- 新增（基础设施，零 bench 语义）：
  - `tools/capability_probe.py`：Docker/GPU/沙箱能力探测（命令缺失/超时/报错一律 unavailable）。
  - `tools/docker_sandbox.py`：真实容器执行器（加固参数 + 超时 fail-closed）。
  - `tools/plugin_chain.py`：插件执行链（每步先过安执校验；被拒即中止且不执行该步）。
- 实测（cwd=mini-agent-runtime-bench，`python3`）：
  - `python3 tools/check_runtime_gates.py` → exit 0，R1-R7 全过：
    R6 容器隔离五项（加固参数齐备 / 非 root uid!=0 / 只读挂载拒写 / 默认断网 / 超时即杀）；
    R7 插件链三项（被拒即中止且该步未执行 / 放行步骤在真实容器内执行成功 / 非空性）。
  - `python3 tools/check_gates.py` → exit 0（A1 期望集含 21 文件，无漂移；A3-honesty 通过）。
  - 能力探测实测：`docker=可用`、`gpu=可用`、`sandbox=可用`。
- 本轮发现并固化的两个非显然坑：
  1. 工作目录必须落在策略 `sandbox` 根内，否则在校验层即被拒（表现为「容器没启动」）；
  2. 挂载目录必须可被沙箱用户遍历（`mkdtemp` 默认 0700），否则容器内读取静默
     `Permission denied`。两者均已写入门禁断言。
- 诚实边界（未变）：真实 LLM 调用仍未接入（RankGPT 排序增益未复现）；
  容器沙箱为单容器隔离，非多租户强隔离，不声称生产级安全。

---

## M2-RUNTIME-LOOP：W2 契约可执行雏形（2026-10-11）

- 动机：M2 原本的目标是"补第一个真 bench"。逐条读 `docs/W2-runtime.md` 后
  发现契约的验收标准本身可以**先被满足一半**——三接口、四必填字段、
  AG-W2-2 有界、AG-W2-4 确定性重放都是可判定的，且不需要任何 bench 数字。
  于是先把"契约可执行"做出来，bench 部分按契约前提是否冻结来决定动不动。
- 新增（基础设施，零 bench 语义）：
  - `tools/runtime_loop.py`（约 `allow-number`：200 行，stdlib only）：
    `RuntimeLoop.reset/step/done` 三接口 + 八字段轨迹 + `replay()` 重放入口
    + `--selftest` 四项非空性反证（确定性 / 完备性 / 有界性 / reset 一次性）。
  - `docs/m2-runtime-loop.md`：M2 说明，含"抵达了契约哪一条 / 没到哪一条"。
- 实测（cwd=mini-agent-runtime-bench，`python3`）：
  - `python3 tools/runtime_loop.py` → 正常产出轨迹，
    `allow-number`：verdict=OK steps=2 digest=2c04b4c5428d。
  - `python3 tools/runtime_loop.py --selftest` → 四项全 PASS
    （缺字段时错误信息点名 `['latency_log']`；`max_steps=1` 时第 2 步中止）。
  - `python3 tools/check_gates.py` → exit 0，A1-A3 八项全 PASS
    （A1 EXPECTED 由 23 文件增至 25 文件，新增两项已入白名单）。
  - `python3 tools/check_runtime_gates.py` → exit 0，R1-R7 全过。
- **没有做的事（重要，防止误读）**：
  1. **没有落任何 `trace_id` 数据行**。AG-W3-2 要求覆盖扰动矩阵全部格点，
     而格点清单仍是 `TBD`；AG-W3-3 裁判独立性标准仍是 `TBD`。
     在两项前提冻结前落数 = 自己违反反作弊条款。
     故 `results/flip_rate_empty.csv` 保持仅表头，本仓仍是 pre-W1 空仓。
  2. **没有声称任何 bench 数字**。loop 的 verdict 是"被检快照是否被改动"的
     自洽性判定，与任务完成率、检索质量无关。
  3. **执行未托管给容器**。R6 已证明真实容器隔离可用，但 loop 只做只读观测；
     把 loop 接到 `docker_sandbox.py` 是下一步。
- 教训：把"补 bench"拆成"契约可执行"与"bench 落数"两步后，第二步自己喊停——
  因为停下来比继续更需要理由，而这个理由（反作弊前提未冻结）是契约写明的。

## M3-RUNTIME-RUNS：8 个手写动作序列的真实轨迹（2026-10-11）

- 动机：用户要求「多做一些真正加分的项目」，判定标准 = **陌生人 clone 后能否
  不联网、不买 key 复现出数字**。本机 LLM API key 全 unset（`docs/m3-plan.md`
  弹药表），所以任何需要别处推理的"agent 行为"都做不了；能做的是
  **把运行时契约跑成真实轨迹**，并如实说明它不是 bench。
- 新增：`tools/w2_runs.py`、`results/w2_runs.jsonl`、`docs/m3-runtime-runs.md`、
  `docs/m3-plan.md`。另修 `tools/check_gates.py` 两处（见下）。
- 实测（`python3 tools/w2_runs.py`）：
  - 8 runs → verdict OK 5 / CONTRACT_ABORT 3，violations 4（T04/T05/T07 策略拒绝，
    T08 `max_steps=1` 契约中止）。8 个 run 的快照 digest 均为 `469e5e59f80e`。
  - `python3 tools/check_gates.py` → exit 0，A1-A3 八项全 PASS（A1 由 25 增至 29 文件）。
  - `python3 tools/check_runtime_gates.py` → exit 0，R1-R7 全过。
- **口径纠错（本轮最重要的一条）**：第一版把策略层拒绝（DANGEROUS_TOOL / NOT_JSON）
  写进了 runtime 的 `tool_calls`，看起来 T04 也有完整的"被拒轨迹"。错在
  **轨迹契约 = "实际发生的事"**：runtime 没执行的动作塞进它的 `tool_calls`，
  会把"试图调用过 rm -rf"变成"调用过 rm -rf 且被记录"——审计含义完全不同。
  修正后策略拒绝只进 `rec["violations"]`，`disclosure.log_semantics` 写死该语义。
- **修 `check_gates.py` 的 A3-honesty 误报**：`HONESTY_RES` 的 `\b\d+\.\d+\b`
  把 `sentence_transformers 6.1.0` 这类版本号当成"带小数点的编造结果"。
  加 `VERSION_RE = \b\d+\.\d+(?:\.\d+)+\b` 在扫描前剥离（要求至少两个小数段，
  单段小数仍会命中），并把 `docs/m3-plan.md` 里两处裸小数改成文字 + `allow-number`。
  这是修门禁而非放水：真正的"0.633 / 5/10"仍然会被拦。
- **没有做的事**：①无任务定义，`OK` 不代表任务成功；②无裁判，
  `results/flip_rate_empty.csv` 仍仅表头；③8 个 run 的执行未托管给容器
  （R6 容器隔离单独证明）。
- 教训：**"拒绝"有三层来源**（序列层策略 / 契约层中止 / 日志不完备拒产），
  混在一张表里报告就是误导。这一层的账必须在写代码前分清，不是写完再解释。
