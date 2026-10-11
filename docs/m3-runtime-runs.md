# M3-C：8 个手写动作序列跑成了真实轨迹，但它不是 agent benchmark

**结论先说**：`tools/w2_runs.py` 把 W2 运行时契约跑成了 8 条落盘轨迹
（`results/w2_runs.jsonl`）：**verdict OK 5 / CONTRACT_ABORT 3，共 4 次策略拒绝或契约中止**。
这不是 benchmark 输出。本机 LLM API key 全部 unset（`docs/m3-plan.md` 弹药表），
**没有任何 LLM 被调用**，8 个动作序列是我手写的。名字必须诚实：
它测的是**运行时基础设施的行为**，不是 agent 的智能。

```bash
cd mini-agent-runtime-bench
python3 tools/w2_runs.py     # 零网络零依赖，重写 results/w2_runs.jsonl
```

## 8 个 run 各自在测什么

| id | 序列 | verdict | 测到的行为 |
|---|---|---|---|
| T01 | `fs.read` 目录 | OK | 基线：一次只读观测，digest 不变 |
| T02 | `fs.read` + `fs.stat` | OK | 两步连走，八字段轨迹完整 |
| T03 | 围栏 ```json 包裹的调用 | OK | `call_guard` 剥围栏后解析成功（R 线守卫生效） |
| T04 | `shell.exec rm -rf /tmp/x` | CONTRACT_ABORT | **序列层黑名单拒绝执行** |
| T05 | `fs.write /etc/passwd` | CONTRACT_ABORT | **同上：DANGEROUS_TOOL 拒绝** |
| T06 | 前后夹带自然语言的调用 | OK | `_balanced_slice` 从夹台词文本里切出平衡 JSON |
| T07 | 纯自然语言无动作 | CONTRACT_ABORT | `NOT_JSON`——没有动作可执行时不出轨迹 |
| T08 | `max_steps=1` 时走第 2 步 | OK | **契约层**中止：`超出步数上界 max_steps=1（AG-W2-2）`，已有 1 步进入轨迹 |

## 三层拒绝必须分清，混在一起报告就是误导

这一轮我遇到的最大口径问题不是性能，是**"拒绝"有三种来源**：

1. **序列层策略拒绝**（T04/T05/T07）：`call_guard.parse_call` 或 DANGEROUS 黑名单
   判定不该执行 → 动作**从未进入 `loop.step()`**。所以它**不在** runtime 的
   `tool_calls` 里，只出现在 `violations`。
2. **契约层中止**（T08）：动作合法，但 `max_steps` 上界触发 → 已发生的步骤
   留在轨迹里，后续步骤不执行。
3. **日志不完备拒产**（T04/T05/T07 的最终 verdict）：被拒后 runtime 的
   `tool_calls` 是空的，八字段校验 `AG-W2-3` 判定字段缺失，
   `done()` 抛 `AG-W2-3 日志不完备，缺字段: ['tool_calls', 'latency_log']`。

第一版我把前两种拒绝**写进了 runtime 的 `tool_calls`**，看起来 T04 也有完整的
"被拒绝轨迹"。这是错的：**轨迹的契约是"实际发生的事"**。runtime 没执行的动作
塞进它的 `tool_calls`，会让"这个 agent 试图调用过 rm -rf"变成"这个 agent 调用了
rm -rf 且被记录"——审计时这两件事的法律含义完全不同。修正后把策略拒绝全部移到
`violations`，`disclosure.log_semantics` 里写死这个语义。

## 非空性反证：这个工具必须能失败

`w2_runs.py` 自带一条断言：**若 8 个 run 全部 verdict=OK 且 violations=0，
直接 `SystemExit`**。理由和 R5 一样——一个只会说"一切正常"的拒绝路径观测器
没有任何证据价值。现在 8 个 run 里有 4 个拒绝/中止，反证通过。

## 这仍然没做到的三件事

1. **没有任务定义，没有完成率**。T01–T08 的 verdict 是"快照 digest 是否被改动"的
   自洽判定，`OK` 不代表任何任务成功，`CONTRACT_ABORT` 也不代表任何任务失败。
2. **没有裁判、没有翻转率分子分母**。`results/flip_rate_empty.csv` 仍是仅表头——
   这是 M2 定下的纪律，M3 没有打破它。
3. **沙箱仍是约定级**。T01–T03/T06/T08 的快照只读由 `_digest` 校验；
   `docker_sandbox.py` 的容器隔离能力在 `check_runtime_gates.py` R6 已被单独证明，
   但这 8 个 run 的执行**没有托管给容器**。

## 由此得出的下一步

- **把 `normalize_query` 等价物接到 bench 的输入侧**：T07 说明"无动作"是被判
  `NOT_JSON` 的，但真实 agent 的"我想先看看目录"这类输出是否该归一成一个
  `noop` 动作、还是判失败，这是策略选择，需要写进契约而不是留在工具里。
- 真要出 bench 数字，缺的从来不是 runtime，是**任务集 + 裁判 + LLM API key**。
  前两者我可以写，第三项这台机器上没有——继续往下做之前应先确认可用的推理端点。
