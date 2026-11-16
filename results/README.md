# results：空表哨兵与脚本策略落数

> 两份文件，两种语义，不要混读。

## 空表哨兵

- `flip_rate_empty.csv` 有且仅有一行表头。门禁检查行数与表头逐字一致。
- 文件名里的 `empty` 是语义的一部分：只要还叫 `_empty.csv`，就禁止数据行。
- 仅表头 = 尚无这张表所代表的证据。它不是翻转率为零，也不是重放已经做完。

表头（顺序与拼写不可变）：

`trace_id, task_id, condition, run_id, flip_occurred, flip_type, evidence_path, notes`

| 列 | 语义 | 空表时 | 若将来往这张空表落数 |
| --- | --- | --- | --- |
| `trace_id` | 本次重放的追踪标识 | 无行 | 非空，且能回到轨迹 |
| `task_id` | 任务编号 | 无行 | 与快照一致 |
| `condition` | 扰动格点 | 无行 | 必须是已冻结格点 |
| `run_id` | 被重放的原轨迹 | 无行 | 必须存在于轨迹文件 |
| `flip_occurred` | 结论是否变化 | 无行 | 取值表在该格点冻结时写明 |
| `flip_type` | 翻转类型 | 无行 | 必须是已定义类型 |
| `evidence_path` | 证据位置 | 无行 | 文件必须存在 |
| `notes` | 备注 | 无行 | 异常要写原因 |

这张空表目前不承载脚本策略那一格点。不要把数据行追加进来。

## 脚本策略计数表

`flip_rate.csv` 每个策略一行。列是 `policy, flips, replays, stable_verdict, trace_ids, evidence_path, notes`。

- `flips` 是分子：重放结论与基线结论不同的任务数。
- `replays` 是分母：该策略的重放条数，必须等于 `trace_ids` 里的 id 个数，也必须盖住全部冻结任务。
- `trace_ids` 里的每个 id 必须出现在 `evidence_path` 指向的轨迹文件中，且角色是重放；对应基线 id 也必须在同一文件里。
- `evidence_path` 不得是 `none` 或空。当前证据文件是 `scripted_traces.jsonl`。
- `stable_verdict` 为 `PASS` 或 `FAIL` 表示两次结论相同；`mixed` 表示两次结论不同。零翻转可以是稳定的失败。
- 这些行由 `tools/compute_flip_rate.py` 从冻结任务和脚本策略重算。`make check` 比对字节，手改分子会失败。

轨迹文件里的每条记录带 `trace_id`、`run_id`、`verdict`、`llm_called=false`、`policy_kind=scripted`。没有调用 LLM。

## 不在本计数里的文件

`w2_runs.jsonl` 是更早的运行时动作序列，含墙钟延迟。它不是 `flip_rate.csv` 的证据，`make check` 不重写它。

## 违规即失败

- 空表出现数据行，或表头被改。
- `flip_rate.csv` 的 trace id 缺失、重复、对不上轨迹，或证据文件不存在。
- README 在 measured 块之外写出结果形状的数字，或 measured 块与重算不一致。
- 把空表或零翻转说成智能体稳健。
