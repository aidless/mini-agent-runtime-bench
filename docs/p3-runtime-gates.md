# C 线运行时门（P3-HARDEN）

本页说明 C 线在 P3 加固轮新增的**运行时安全门**。它们与 `check_gates.py` 的
A1–A3 门同属**基础设施**（只做断言，不含 bench 语义），因此不产生、也不声称
任何 bench 数字。空仓契约（`results/flip_rate_empty.csv` 只有表头）保持不变。

## 为什么有这些门

C 线的非目标是「把智能体能力吹大」，而是「在真实执行前把危险动作挡在门外」。
主张边界（与 P2 台账一致）：运行时控制 **不等于** 任务完成率；本页只描述
「能否稳定拦下危险调用 / 能否稳定解析畸形输入」这类可判定的运行时性质。

## 门清单

| 门 | 断言 | 失败含义 |
|---|---|---|
| `sandbox_validator.py`（R1） | golden 攻击集里的危险调用**全量**被拦，且命中期望规则 | 存在可绕过策略的危险调用 |
| 同上（R2） | golden 合法调用**全量**放行 | 策略过严，正常调用被误拦 |
| `call_guard.py`（R3） | 畸形输入语料下**零崩溃**，且始终返回结构化结果 | 解析路径存在未捕获异常 |
| `agent_scoring.py`（R4） | 三分 / 选人 / 记忆块的确定性断言成立 | 评分或分层语义漂移 |
| `check_runtime_gates.py`（R5） | **非空性反证**：弱化策略必须让攻击泄漏 | 门恒真、形同虚设 |
| `docker_sandbox.py`（R6） | 真实容器内：非特权用户可执行、只读挂载拒写、默认断网、超时即杀 | 隔离措施形同虚设 |
| `plugin_chain.py`（R7） | 链中任一步被拒即**不执行该步**并整链中止；放行步骤在真实容器内可执行 | 门控被绕过或步骤被跳过执行 |

## 用法

```
python3 tools/check_runtime_gates.py      # R1–R7，fail-closed
python3 tools/sandbox_validator.py        # 单独跑安执 golden 集
python3 tools/capability_probe.py         # 探测 Docker / GPU / 容器隔离是否可用
python3 tools/check_gates.py              # A1–A3（结构 / 文档 / 隔离与诚实）
```

## 真实容器沙箱（第二轮补充）

首轮曾以「本机无条件」把容器沙箱记为未迁移。`capability_probe.py` 的**探测推翻了该假设**
（Docker、GPU、容器级隔离均可用；版本号见探测输出，`allow-number`）。故第二轮补上真实执行：

- `docker_sandbox.py`：加固参数为 `--network none`、`--read-only`、
  `--tmpfs`（noexec）、`--cap-drop ALL`、`--security-opt no-new-privileges`、
  `--memory` / `--pids-limit`、`--user nobody`、工作目录只读挂载。
- 两个非显然的坑（均已由门禁固化）：
  1. 工作目录必须落在策略的 `sandbox` 根内，否则在校验层即被拒（`R-OUTSIDE`）；
  2. 挂载目录必须**可被沙箱用户遍历**，否则容器内读取会静默 `Permission denied`。
- `plugin_chain.py` 的默认执行器仍是 stub（显式标记），
  真实执行需显式注入 `docker_executor`。

## 安执策略要点（fail-closed）

- 未知一律拒绝：工具白名单之外、参数结构畸形、路径越出沙箱根，全部 `deny`。
- 危险类别分规则命名（`R-TOOL` / `R-READONLY` / `R-NETWORK` / `R-EVAL` /
  `R-ABSPATH` / `R-ESCAPE` / `R-SENSITIVE` / `R-METACHAR`），便于反证用例
  断言「被拦的是哪一条」，而不是只知道「被拦了」。
- shell 元字符在参数值上做二次扫描，避免「白名单工具 + 注入参数」的组合绕过。

## 边界（诚实）

- 本页不给出任何拦截率 / 崩溃率的数字；数字由 `check_runtime_gates.py`
  运行时产出，且仅用于门自身的 PASS/FAIL 判定。
- 安执是**必要不充分**：拦住危险调用不代表任务能完成；本线不据此声称能力。
- golden 集是**有限**攻击样本：它证明「已覆盖的攻击被拦」，不证明「没有未知攻击」。
- 容器沙箱是**单容器**隔离，**不是**多租户强隔离方案；不声称生产级沙箱安全。

