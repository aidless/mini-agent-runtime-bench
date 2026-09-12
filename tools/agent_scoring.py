#!/usr/bin/env python3
"""C 线智能体评分 / 组队 / 记忆（API-Bank 三分 + DyLAN 选人 + MemGPT 记忆块迁移）。

迁移自 P2 台账的 C 线配方，**全部为确定性纯函数**（无随机、无外部依赖）：
  - API-Bank 三分：把一次会话的「规划 / 检索 / 调用」三个维度分别计分
  - DyLAN 选人：按「有效贡献 / 调用次数」算重要度，选出 top-k 智能体
  - MemGPT 记忆块：容量受限的块 + 溢出晋升（虚存式分层）

基础设施，stdlib only，不含 bench 语义；运行时请用 check_runtime_gates.py 验收。
"""

DIMS = ("plan", "retrieve", "call")


def score_three_dim(events):
    """API-Bank 三分。

    events: [{"dim": "plan"|"retrieve"|"call", "ok": bool}, ...]
    返回 {"plan": [hit, n], "retrieve": [...], "call": [...],
          "overall": [hit, n]}
    未出现的维度记为 [0, 0]（不臆造分母）。
    """
    out = {d: [0, 0] for d in DIMS}
    for e in events:
        d = e.get("dim")
        if d not in out:
            continue
        out[d][1] += 1
        if e.get("ok"):
            out[d][0] += 1
    hit = sum(v[0] for v in out.values())
    n = sum(v[1] for v in out.values())
    out["overall"] = [hit, n]
    return out


def rate(hit_n):
    """命中率；分母为 0 时返回 None（不臆造 0 或 1）。"""
    h, n = hit_n
    return None if n == 0 else h / n


def importance(trace, min_calls=1):
    """DyLAN 式重要度：有效贡献 / 调用次数（调用不足则不计入）。"""
    calls = int(trace.get("calls", 0))
    useful = int(trace.get("useful", 0))
    if calls < min_calls or calls <= 0:
        return 0.0
    return useful / calls


def select_agents(traces, k=2, min_calls=1):
    """按重要度选 top-k。

    调用次数不足 min_calls 的智能体**不入选**（不是得 0 分后仍参与排序）；
    同分时按 agent 名字典序（确定性，避免抖动）。
    """
    scored = []
    for t in traces:
        name = t.get("agent")
        if not isinstance(name, str) or not name:
            continue
        calls = int(t.get("calls", 0))
        if calls < min_calls or calls <= 0:
            continue          # 证据不足 → 不入选（不得以 0 分形式混入）
        scored.append((importance(t, min_calls), name))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [name for _, name in scored[:max(0, k)]]


class MemoryBlock:
    """MemGPT 式记忆块：容量受限，溢出项晋升到归档层（虚存分层）。

    只做结构搬运，不做内容改写；同输入同输出（确定性）。
    """

    def __init__(self, limit):
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit 必须为正整数")
        self.limit = limit
        self.items = []
        self.archived = []

    def append(self, item):
        """写入一项；超出容量则把最旧项晋升到归档层。返回被归档项（或 None）。"""
        self.items.append(item)
        if len(self.items) > self.limit:
            evicted = self.items.pop(0)
            self.archived.append(evicted)
            return evicted
        return None

    def recall(self, item):
        """从归档层调回（若存在）；成功则置于块尾并返回 True。"""
        if item in self.archived:
            self.archived.remove(item)
            self.items.append(item)
            return True
        return False

    def state(self):
        return {"limit": self.limit, "items": list(self.items),
                "archived": list(self.archived)}
