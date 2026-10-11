# M3：按「真正加分」筛选的下一步（先看环境实测再说做什么）

> 判定标准：**一个陌生面试官 clone 下来，能不能不联网、不买 key 就复现出数字**。
> 所以我先实测了本机到底有什么弹药，再决定做哪几件事。

## 本机弹药实测（不是我 remembered 的，是 `python3 -c import` + `ls` 的输出）

| 资源 | 状态 | 能支撑什么 |
|---|---|---|
| `sentence_transformers` 6.1.0 + `transformers` 5.17.0 | ✅ 在盘 | **本地真语义向量**，无需 API key |
| 已缓存模型 `models--sentence-transformers--all-MiniLM-L6-v2` | ✅ 93MB 级，**离线可用** | 英文 dense retrieval / 语义相似度 |
| 已缓存模型 `models--BAAI--bge-small-zh-v1.5` | ✅ 93M，**离线可用** | 中文 dense retrieval |
| `docker` | ✅ `ps` 通 | agent runtime 的执行隔离（R6 已证明容器可用） |
| `datasets` | ❌ MISSING | 不能直接 `load_dataset` |
| OpenAI / DeepSeek / Anthropic / SiliconFlow / DashScope key | ❌ **全部 unset** | **不能做任何需要 LLM API 的事** |
| `numpy 2.5.2 / scipy 1.18.1 / sklearn 1.9.1 / torch 2.14.1+cu130` | ✅ | 统计检验 / 聚类 / bootstrapping |

## 因此我选这三件（全部可离线复现）

### 候选 A：heap 真信号 --------------------------------------------------
**做什么**：`enterprise-rag/hybrid/` 现在的 dense 索引是 char-bigram TF-IDF 伪装的正规 dense。
换上 `all-MiniLM-L6-v2` 真语义向量 + `bge-small-zh-v1.5`（中文），重跑同一题集。

**为什么加分**：
- 这是 M1 里"缺语义级重排"的**正面回应**，不是补一句 TODO。
- 同一题集上前后的对比数字有了；如果真语义向量在 537-docs / 11994-chunks 规模上
  **打不过** char-bigram TF-IDF（小语料完全可能），那这个阴性结果本身就是可讲的发现：
  说明"企业知识库 embedding 升级"不是无条件有效的，跟库的规模/噪声有关。
- **离线可复现**：模型已缓存，`python3 hybrid/dense_rag.py` 就能跑。

**风险（先认）**：10 题题集下任何差异都可能是噪声。所以我会同时报
bootstrap CI，且不宣称"显著提升"。

### 候选 B：A-to-B 变异测试（最有含金量） --------------------------------
**做什么**：写一个 metamorphic 测试工具，产出「查询被等价改写后，检索结果翻没翻」的
差分报告。同一查询改写三次，输出三条结果路径。

**为什么加分（说实话 logistics 检查完可能有变）**：查了 MiniLM 与 bge 的度量函数，
是**余弦不变量 + 幅度重标定**，所以这个类型可在降维空间上跑，不用重缩放。
这条比"我做了 embedding 增强"更硬：它检验 embedding 本身是否值得信任。

> **执行情况（事后回填，2026-10-11）**：候选 B 最终做在 `enterprise-rag/hybrid/metamorphic_test.py`，
> 结果见 `enterprise-rag/hybrid/RESULTS_M3_METAMORPHIC.md`：
> 归一化前 IN-VARIANT 命中 6/30，之后 allow-number（降到零）；DESIRABLE 由 11/30 降到 8/30，
> 残余 8 例均可解释（char-bigram 不保序、无中文停用词表）。
> 本仓不重复实现，目录里不再出现 `tools/metamorphic.py`。
面试问"你怎么知道你的检索器是稳的"，这个工具就是答案。

### 候选 C：跑通 8 个真 agent 任务（让 bench 有数字） ----------------------
**做什么**：用 runtime_loop + docker_sandbox + call_guard，跑 8 个手工构造的任务
（文件检索/多步计算/工具组合），输出 `results/w2_runs.jsonl`（**不只表头**）。

**为什么加分**：这是把 M2 的"契约可执行"变成"契约跑过数据"。
**为什么有限**：没有 LLM API key，**没有任何 LLM 被调用**，这 8 个任务是我手写动作序列，
测的是 runtime 的行为，不是 agent 的智能。所以叫 `runtime_contract_runs`，
**不能叫 agent benchmark**——名字会骗人，结果不会。

## 我做不了的事（写下来，免得后面被当成可以做）

1. **任何需要 LLM API 的实验**——key 全 unset。做不了 SWE-bench 式 agent 评测，
   做不了 LLM-as-judge。谁在这台机器上宣称跑过，就是编的。
2. **`datasets` 库加载 HF datasets**——MISSING。ARC 的两个数据集在缓存里但拿不到。
3. **中文 bench**没有真 LLM 可调，只能做"运行时契约"层。

## 输出与验收（每个都要过 A3-honesty）

- `hybrid/dense_rag.py` + 增量章节写进 RESULTS_M1.md（不删旧结论，标注 M2 追加）
- `tools/metamorphic.py` + `results/metamorphic.json`
- `tools/w2_runs.py` + `results/w2_runs.jsonl`
- 每次改完重跑 `check_gates.py` / `check_runtime_gates.py`，A1 白名单同步新增文件
- `PHASE_LOG.md` 追加 M3 段
