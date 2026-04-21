# 5G NR 多智能体协同保障系统 - 面试问答手册

## 目录

- [项目描述拷问](#项目描述拷问)
- [技术栈拷问](#技术栈拷问)
- [核心职责 1：架构设计](#核心职责-1架构设计)
- [核心职责 2：感知智能体](#核心职责-2感知智能体)
- [核心职责 3：RAG 混合检索](#核心职责-3rag-混合检索)
- [核心职责 4：四层防护机制](#核心职责-4四层防护机制)
- [核心职责 5：K8s 部署](#核心职责-5k8s-部署)

---

## 项目描述拷问

### Q1：你说"感知滞后"，具体滞后到什么程度？

**答**：传统网管系统的采集粒度是分钟级的，即每 1-5 分钟采集一次指标。对于 VoNR 视频通话这种实时业务，用户感知到卡顿后，网管系统可能要 3-5 分钟后才能采集到异常数据，再加上人工分析的时间，从用户投诉到问题定位平均需要数小时。

我们的系统将感知粒度提升到秒级，KQI 指标（如 RTP 丢包率、视频 MOS 分）每秒计算一次，感知时延 < 1 秒。

### Q2：你说"决策割裂"，具体表现在哪些方面？

**答**：在 5G 网络运维中，不同问题需要不同团队处理：
- 无线参数优化 → 无线优化团队
- 传输链路故障 → 传输团队
- 核心网配置问题 → 核心网团队

以 VoNR 视频卡顿为例，需要同时分析 RTP 丢包（用户面）、切换参数（无线面）、SCTP 链路（控制面），涉及多个团队协同，沟通成本高，决策效率低。

我们的系统通过多智能体协同，将感知、诊断、决策、执行整合到一个闭环中，自动完成跨域分析。

### Q3：你说"执行依赖人工"，能举个具体例子吗？

**答**：以热门景区保障为例，节假日期间用户密度激增，需要动态调整基站参数：
- 调整发射功率
- 修改切换偏置
- 增加资源预留

传统模式下，这些操作需要专家人工制定方案、逐条执行，响应速度慢。我们的系统可以自动感知用户密度变化，自动决策调整策略，自动执行参数变更，实现动态保障。

### Q4：你说"可直接适配运营商 5G 基站运维场景"，依据是什么？

**答**：
1. 指标体系基于 3GPP 标准定义（RSRP、SINR、吞吐量等）
2. 故障检测规则参考中兴 VoNR 优化实践经验
3. 知识库内容覆盖 5G 运维常见场景（弱覆盖、干扰、切换失败等）
4. 执行操作对应实际基站可配置参数（功率、切换偏置、PCI 等）

---

## 技术栈拷问

### Q5：为什么选择 Python 3.10 而不是更新的版本？

**答**：
1. **生态兼容性**：PyTorch、LangChain 等核心依赖在 3.10 上最稳定
2. **生产环境**：运营商生产环境通常使用 LTS 版本，3.10 是当前主流
3. **类型提示**：3.10 引入了 `match-case` 和更完善的类型提示，适合大型项目

### Q6：为什么同时使用 C/C++ 和 Python？

**答**：
- **C/C++**：用于性能敏感模块，如协议栈埋点、环形缓冲区、内存池、实时指标计算
- **Python**：用于 AI 模块，如 RAG 检索、LLM 推理、智能体协同

这种混合架构兼顾了性能和开发效率。

### Q7：LangChain 和 LangGraph 有什么区别？为什么都要用？

**答**：
- **LangChain**：提供 LLM 应用的基础组件（Chain、Prompt、Retriever 等）
- **LangGraph**：在 LangChain 基础上提供有向图状态机，支持循环和条件分支

我们用 LangChain 构建 RAG 检索链，用 LangGraph 定义智能体间的状态流转（感知→决策→执行→反馈）。

### Q8：rank_bm25 是什么？和 Elasticsearch 的 BM25 有什么区别？

**答**：
- **rank_bm25**：Python 库，纯 Python 实现的 BM25 算法，轻量级，适合中小规模数据
- **Elasticsearch BM25**：Java 实现，分布式，适合大规模生产环境

我们选择 rank_bm25 是因为：
1. 知识库规模不大（5G 运维文档约几十 MB）
2. 无需额外部署 ES 集群
3. 与 Python 生态无缝集成

如果数据量增长到 GB 级别，可以平滑迁移到 Elasticsearch。

### Q9：RRF 排名融合是什么？为什么叫"工业级"？

**答**：RRF（Reciprocal Rank Fusion）是一种多检索器结果融合算法，公式为：

```
score(d) = Σ 1 / (k + rank(d))
```

其中 k 是常数（通常取 60），rank(d) 是文档在某检索器中的排名。

称为"工业级"的原因：
1. **排名无关性**：不依赖各检索器的原始分数（FAISS 输出余弦相似度 0~1，BM25 输出 TF-IDF 分数可能几十到几百，无法直接加权）
2. **参数少**：只需调整 k 值，不需要调权重
3. **效果稳定**：在 TREC 等权威评测中表现优异
4. **被广泛采用**：Elasticsearch、Vespa 等工业级搜索引擎内置支持

### Q10：LoRA 微调是什么？为什么不用全量微调？

**答**：
- **全量微调**：更新模型所有参数（Qwen-7B 约 70 亿参数），需要大量 GPU 显存和训练数据
- **LoRA（Low-Rank Adaptation）**：只训练低秩矩阵，参数量减少 90%+，显存占用大幅降低

选择 LoRA 的原因：
1. 运维领域数据有限，全量微调容易过拟合
2. 训练成本低，单卡即可训练
3. 效果好，在特定领域任务上接近全量微调

### Q11：DeepSpeed 是什么？解决了什么问题？

**答**：DeepSpeed 是微软开源的分布式训练框架，核心功能：
1. **ZeRO 优化**：将优化器状态、梯度、参数分片到多张 GPU，突破单卡显存限制
2. **混合精度训练**：FP16/BF16 加速训练
3. **梯度累积**：模拟大 batch size

我们用 DeepSpeed 的 ZeRO-2 策略，在 4 张 A100 上训练 Qwen-7B，显存占用从 80GB 降到 20GB/卡。

### Q12：RLHF 是什么？在你的项目中怎么用？

**答**：RLHF（Reinforcement Learning from Human Feedback）是通过人类反馈强化学习来优化模型输出。

在我们的项目中：
1. 运维专家对模型诊断结果打分（准确/部分准确/错误）
2. 构建奖励模型（Reward Model）
3. 用 PPO 算法微调模型，使输出更符合专家期望

这比单纯的 SFT（有监督微调）效果更好，因为运维诊断没有标准答案，需要专家经验指导。

### Q13：模型蒸馏是什么？蒸馏后效果会下降吗？

**答**：模型蒸馏是将大模型（Teacher）的知识迁移到小模型（Student）的过程。

我们用 Qwen-7B 蒸馏出一个 1.5B 的小模型，用于边缘部署（基站本地）。

效果对比：
| 指标 | Qwen-7B | 蒸馏 1.5B |
|------|---------|-----------|
| 诊断准确率 | 92% | 88% |
| 推理延迟 | 2.5s | 0.8s |
| 显存占用 | 14GB | 3GB |

在可接受的精度损失下，推理速度提升 3 倍，适合边缘部署。

### Q14：vLLM 是什么？为什么不用 HuggingFace Transformers？

**答**：vLLM 是高性能 LLM 推理引擎，核心优势：
1. **PagedAttention**：类似操作系统的虚拟内存管理，显存利用率提升 2-4 倍
2. **连续批处理**：动态合并请求，吞吐量提升 10-24 倍
3. **支持多种模型**：Llama、Qwen、Mistral 等

对比 HuggingFace：
| 指标 | HuggingFace | vLLM |
|------|-------------|------|
| 吞吐量 | 10 req/s | 100+ req/s |
| 显存利用 | 40% | 90%+ |
| 首字延迟 | 500ms | 200ms |

### Q15：Redis 在项目中起什么作用？

**答**：
1. **智能体间通信**：感知智能体将指标写入 Redis，决策智能体订阅消费
2. **缓存**：缓存 RAG 检索结果，减少重复计算
3. **状态存储**：存储智能体运行状态，支持故障恢复

### Q16：Docker 和 Kubernetes 分别解决什么问题？

**答**：
- **Docker**：解决环境一致性问题，确保开发、测试、生产环境一致
- **Kubernetes**：解决大规模部署问题，提供自动扩缩容、负载均衡、故障恢复

---

## 核心职责 1：架构设计

### Q17：三智能体协同架构具体是怎么设计的？

**答**：

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  感知智能体   │───▶│  决策智能体   │───▶│  执行智能体   │
│ PerceptAgent │    │DecisionAgent │    │  ExecAgent   │
└──────────────┘    └──────────────┘    └──────────────┘
```

- **感知智能体**：负责采集 5G 网络指标，检测故障
- **决策智能体**：负责故障诊断，生成修复策略
- **执行智能体**：负责执行修复操作，验证效果

状态流转由 LangGraph 定义：
```python
workflow = StateGraph(AgentState)
workflow.add_node("percept", percept_agent)
workflow.add_node("decision", decision_agent)
workflow.add_node("execute", exec_agent)
workflow.add_edge("percept", "decision")
workflow.add_edge("decision", "execute")
workflow.add_edge("execute", "percept")  # 循环反馈
```

### Q18：MCP 调度中心是什么？

**答**：MCP（Multi-agent Coordination Platform）是我们设计的调度中心，负责：
1. **任务分发**：将用户请求路由到合适的智能体
2. **状态同步**：维护全局状态，确保智能体间信息一致
3. **异常处理**：当某个智能体失败时，触发降级策略
4. **日志记录**：记录完整执行链路，便于追溯

### Q19：LangGraph 的状态流转具体怎么实现的？

**答**：

```python
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    metrics: Dict           # 网络指标
    faults: List[Dict]      # 检测到的故障
    diagnosis: Dict         # 诊断结果
    actions: List[Dict]     # 执行动作
    result: Dict            # 执行结果

def build_workflow():
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("percept", percept_node)
    workflow.add_node("decision", decision_node)
    workflow.add_node("execute", execute_node)
    
    # 定义边
    workflow.add_conditional_edges(
        "percept",
        lambda state: "decision" if state["faults"] else END
    )
    workflow.add_edge("decision", "execute")
    workflow.add_conditional_edges(
        "execute",
        lambda state: "percept" if state["result"]["need_retry"] else END
    )
    
    return workflow.compile()
```

### Q20：智能体间怎么通信？

**答**：
1. **同步通信**：通过 LangGraph 的状态传递（State）
2. **异步通信**：通过 Redis 消息队列（用于跨进程/跨机器）

消息格式采用 JSON：
```json
{
    "type": "fault_detected",
    "device_id": "cell_001",
    "faults": [{"type": "weak_signal", "severity": "high"}],
    "metrics": {"rsrp": -115, "sinr": -5},
    "timestamp": "2025-04-21T10:30:00Z"
}
```

---

## 核心职责 2：感知智能体

### Q21：KQI 指标是什么？和 KPI 有什么区别？

**答**：
- **KPI（Key Performance Indicator）**：网络性能指标，如 RSRP、SINR、吞吐量
- **KQI（Key Quality Indicator）**：用户体验指标，如视频 MOS 分、语音 E-Model 分

KPI 是网络侧的，KQI 是用户侧的。我们的系统同时采集两者，实现从"网络正常但用户体验差"的精准感知。

### Q22：RTP 丢包率怎么统计的？

**答**：

```python
class RTPPacketLossCalculator:
    def __init__(self, window_size=1000):
        self.buffer = RingBuffer(window_size)
    
    def calculate(self, packets: List[RTCPacket]) -> float:
        """计算 RTP 丢包率"""
        expected = packets[-1].seq_num - packets[0].seq_num + 1
        received = len(packets)
        lost = expected - received
        return lost / expected if expected > 0 else 0
```

关键点：
1. 使用环形缓冲区存储最近 N 个包，避免内存泄漏
2. 通过序列号差值计算期望包数
3. 滑动窗口计算，实时反映当前网络状态

### Q23：连续丢包检测算法是什么？

**答**：

```python
class ConsecutiveLossDetector:
    def __init__(self, threshold=5):
        self.threshold = threshold
        self.consecutive_count = 0
    
    def detect(self, packet: RTCPacket) -> bool:
        if packet.lost:
            self.consecutive_count += 1
        else:
            self.consecutive_count = 0
        
        return self.consecutive_count >= self.threshold
```

连续丢包比平均丢包率更能反映用户体验。例如：
- 平均丢包率 5%，但连续丢 10 个包 → 用户感知明显卡顿
- 平均丢包率 5%，但均匀分布 → 用户可能无感知

### Q24：环形缓冲区怎么实现的？

**答**：

```python
class RingBuffer:
    def __init__(self, size: int):
        self.buffer = [None] * size
        self.size = size
        self.head = 0
        self.count = 0
    
    def append(self, item):
        self.buffer[self.head] = item
        self.head = (self.head + 1) % self.size
        self.count = min(self.count + 1, self.size)
    
    def get_all(self):
        if self.count < self.size:
            return self.buffer[:self.count]
        return self.buffer[self.head:] + self.buffer[:self.head]
```

优势：
1. **固定内存**：预分配数组，不会动态扩容
2. **O(1) 写入**：直接覆盖最旧数据
3. **无 GC 压力**：不需要频繁创建/销毁对象

### Q25：内存池怎么优化性能的？

**答**：

```python
class MemoryPool:
    def __init__(self, block_size: int, pool_size: int):
        self.pool = [bytearray(block_size) for _ in range(pool_size)]
        self.free_list = list(range(pool_size))
    
    def allocate(self) -> bytearray:
        if self.free_list:
            return self.pool[self.free_list.pop()]
        return bytearray(self.pool[0].__sizeof__())
    
    def release(self, block: bytearray):
        idx = self.pool.index(block)
        self.free_list.append(idx)
```

优势：
1. **避免频繁分配**：预分配内存块，减少系统调用
2. **减少碎片**：固定大小块，无内存碎片
3. **提升缓存命中率**：连续内存布局

性能对比：
| 操作 | 无内存池 | 有内存池 |
|------|---------|---------|
| 分配 10000 次 | 50ms | 5ms |
| GC 次数 | 100+ | 0 |

### Q26：感知时延 < 1 秒是怎么保证的？

**答**：
1. **C++ 协议栈埋点**：在基站用户面协议栈（PDCP/SDAP/RTP）直接采集，避免传输时延
2. **环形缓冲区**：O(1) 写入，无锁设计
3. **内存池**：避免动态分配开销
4. **本地计算**：KQI 指标在基站本地计算，不上报云端

端到端时延分解：
| 环节 | 时延 |
|------|------|
| 协议栈采集 | < 0.1ms |
| 环形缓冲写入 | < 0.01ms |
| KQI 计算 | < 0.5ms |
| 智能体处理 | < 100ms |
| **总计** | **< 1 秒** |

---

## 核心职责 3：RAG 混合检索

### Q27：BM25 算法的原理是什么？

**答**：BM25 是基于 TF-IDF 的改进算法，公式为：

```
score(q, d) = Σ IDF(qi) * (tf(qi, d) * (k1 + 1)) / (tf(qi, d) + k1 * (1 - b + b * |d| / avgdl))
```

参数说明：
- **k1**：控制词频饱和点（默认 1.5）
- **b**：控制文档长度归一化（默认 0.75）
- **IDF**：逆文档频率，稀有词权重更高
- **tf**：词频，但会饱和（不会无限增长）

相比 TF-IDF 的优势：
1. **词频饱和**：避免高频词主导分数
2. **长度归一化**：长文档不会天然得分更高

### Q28：RRF 融合的具体实现？

**答**：

```python
class RRFFusion:
    def __init__(self, k=60.0, faiss_weight=0.6, bm25_weight=0.4):
        self.k = k
        self.faiss_weight = faiss_weight
        self.bm25_weight = bm25_weight
    
    def fuse(self, faiss_results, bm25_results, top_k=5):
        doc_scores = {}
        
        # 累加 FAISS 结果的 RRF 分数
        for rank, result in enumerate(faiss_results, 1):
            idx = result["index"]
            rrf_score = self.faiss_weight / (self.k + rank)
            doc_scores[idx] = doc_scores.get(idx, 0) + rrf_score
        
        # 累加 BM25 结果的 RRF 分数
        for rank, result in enumerate(bm25_results, 1):
            idx = result["index"]
            rrf_score = self.bm25_weight / (self.k + rank)
            doc_scores[idx] = doc_scores.get(idx, 0) + rrf_score
        
        # 按 RRF 分数排序
        fused = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return fused[:top_k]
```

### Q29：为什么 k 取 60？

**答**：k=60 是 RRF 论文推荐的默认值，原因：
1. **排名权重衰减合理**：rank=1 时分数约 0.016，rank=10 时约 0.014，rank=60 时约 0.008
2. **对排名不敏感**：k 在 40-100 范围内效果差异不大
3. **工业实践验证**：Elasticsearch、Vespa 等默认使用 60

### Q30：FAISS 和 BM25 的权重为什么是 0.6 和 0.4？

**答**：这是通过实验调优得到的：
- FAISS 权重高（0.6）：语义检索能捕捉同义词、相关概念
- BM25 权重低（0.4）：关键词检索确保精确匹配

调参方法：
1. 构建测试集（100 个查询 + 标准答案）
2. 遍历权重组合（0.1~0.9）
3. 选择 NDCG@5 最高的组合

### Q31：运维知识库怎么构建的？

**答**：
1. **数据来源**：
   - 3GPP 技术规范
   - 中兴内部运维手册
   - 故障案例库
   - 专家经验文档

2. **处理流程**：
   ```
   原始文档 → 文本清洗 → 分块（500 词/块，50 词重叠） → BM25 索引
   ```

3. **知识覆盖**：
   - 弱覆盖/覆盖空洞
   - 干扰检测与消除
   - 切换参数优化
   - VoNR 质量保障
   - 容量规划

### Q32：诊断准确率 > 90% 是怎么验证的？

**答**：
1. **测试集构建**：从历史工单中抽取 500 个真实故障案例
2. **标注标准**：由 3 位运维专家独立标注，取多数意见
3. **评估指标**：
   - 准确率：诊断结果与专家标注一致的比例
   - Top-3 准确率：正确结果在前 3 个候选中的比例

结果：
| 指标 | 数值 |
|------|------|
| 准确率 | 92% |
| Top-3 准确率 | 97% |
| 平均诊断时间 | 25 秒 |

---

## 核心职责 4：四层防护机制

### Q33：四层防护机制分别是什么？

**答**：

| 防护层 | 组件 | 职责 | 触发条件 |
|--------|------|------|---------|
| 第一层 | DiagnosisValidator | 诊断验证 | 置信度 < 70% 或证据不足 |
| 第二层 | SafetyChecker | 安全检查 | 高风险操作或参数超限 |
| 第三层 | RollbackManager | 回滚管理 | 效果验证失败 |
| 第四层 | EffectVerifier | 效果验证 | 指标未改善或恶化 |

### Q34：诊断验证器怎么工作的？

**答**：

```python
class DiagnosisValidator:
    def validate(self, diagnosis, metrics):
        # 1. 置信度检查
        if diagnosis["confidence"] < 0.7:
            return ValidationResult(status="LOW_CONFIDENCE", action="require_human_review")
        
        # 2. 证据数量检查
        if len(diagnosis["root_causes"]) < 2:
            return ValidationResult(status="INSUFFICIENT_EVIDENCE", action="collect_more_data")
        
        # 3. 冲突检查
        if self._has_conflicts(diagnosis["root_causes"]):
            return ValidationResult(status="CONFLICTING", action="flag_for_review")
        
        # 4. 历史一致性检查
        if not self._matches_history(diagnosis):
            return ValidationResult(status="NEW_PATTERN", action="flag_as_new")
        
        return ValidationResult(status="VALIDATED", action="proceed")
```

### Q35：安全检查器怎么分级？

**答**：

| 风险等级 | 操作示例 | 审批要求 |
|---------|---------|---------|
| LOW | 调整日志级别、查询状态 | 自动执行 |
| MEDIUM | 调整切换参数、功率微调（±3dBm） | 自动执行 |
| HIGH | 复位基带板、PCI 变更 | 人工审批 |
| CRITICAL | 核心网配置变更、基站重启 | 人工审批 |

参数边界检查：
```python
SAFE_RANGES = {
    "tx_power": (30, 46),      # dBm
    "handover_offset": (-6, 6), # dB
    "antenna_tilt": (0, 15),    # 度
}
```

### Q36：回滚管理器怎么保证安全回滚？

**答**：

```python
class RollbackManager:
    def snapshot_before_action(self, device_id, params):
        """执行前保存参数快照"""
        self._snapshots[device_id] = params.copy()
    
    def record_action(self, device_id, action):
        """记录操作历史"""
        self._action_history[device_id].append(action)
    
    def rollback(self, device_id):
        """逆序回滚所有操作"""
        actions = self._action_history[device_id]
        for action in reversed(actions):
            self._restore_param(device_id, action["rollback_params"])
        self._snapshots.pop(device_id, None)
```

关键点：
1. **执行前快照**：保存所有相关参数
2. **操作记录**：记录每次执行的详细信息
3. **逆序回滚**：后执行的先回滚，确保一致性

### Q37：效果验证器怎么判断修复是否有效？

**答**：

```python
class EffectVerifier:
    VERIFICATION_TARGETS = {
        "rsrp_delta": 3,        # RSRP 至少改善 3dBm
        "sinr_delta": 2,        # SINR 至少改善 2dB
        "packet_loss_delta": 1, # 丢包率至少降低 1%
        "mos_delta": 0.5,       # MOS 分至少提升 0.5
    }
    
    def verify(self, pre_metrics, post_metrics):
        improvement = self._calculate_improvement(pre_metrics, post_metrics)
        
        if improvement.is_worse():
            return VerificationResult(status="WORSE", action="rollback")
        
        if improvement.meets_target(self.VERIFICATION_TARGETS):
            return VerificationResult(status="SUCCESS", action="complete")
        
        return VerificationResult(status="PARTIAL", action="retry")
```

验证流程：
```
执行修复 → 等待指标稳定（60s） → 采集修复后指标 → 对比修复前后 → 判断是否达标
```

### Q38：如果四层防护都失败了怎么办？

**答**：
1. **自动降级**：转人工处理，发送告警通知
2. **工单生成**：自动生成故障工单，包含完整执行链路
3. **知识库更新**：将新型故障案例加入知识库，持续学习

---

## 核心职责 5：K8s 部署

### Q39：为什么选择 Kubernetes 而不是 Docker Swarm？

**答**：

| 特性 | Kubernetes | Docker Swarm |
|------|-----------|--------------|
| 自动扩缩容 | HPA/VPA | 手动 |
| 服务发现 | 内置 | 内置 |
| 滚动更新 | 支持 | 支持 |
| 生态 | 丰富 | 有限 |
| 学习曲线 | 陡峭 | 平缓 |
| 生产采用率 | 高 | 低 |

选择 K8s 的原因：
1. **HPA 自动扩缩容**：根据 CPU/内存自动调整副本数
2. **生态成熟**：Prometheus 监控、ELK 日志、Istio 服务网格
3. **行业标准**：运营商生产环境普遍采用

### Q40：HPA 自动扩缩容策略怎么设计的？

**答**：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2    # 最小 2 个副本（保证高可用）
  maxReplicas: 10   # 最大 10 个副本（控制成本）
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70   # CPU 超过 70% 扩容
  - type: Resource
    resource:
      name: memory
      target:
        averageUtilization: 80   # 内存超过 80% 扩容
```

扩容逻辑：
- CPU > 70% 或内存 > 80% → 增加副本
- CPU < 50% 且内存 < 60% → 减少副本
- 稳定窗口：3 分钟（避免频繁扩缩容）

### Q41：健康检查怎么配置的？

**答**：

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 60   # 启动后 60 秒开始检查
  periodSeconds: 30         # 每 30 秒检查一次
  timeoutSeconds: 10        # 超时时间 10 秒
  failureThreshold: 3       # 连续 3 次失败则重启

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30   # 启动后 30 秒开始检查
  periodSeconds: 10         # 每 10 秒检查一次
  timeoutSeconds: 5         # 超时时间 5 秒
  failureThreshold: 3       # 连续 3 次失败则摘除流量
```

区别：
- **Liveness**：检测容器是否存活，失败则重启
- **Readiness**：检测容器是否就绪，失败则停止接收流量

### Q42：滚动更新怎么保证不中断服务？

**答**：

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1         # 最多新增 1 个 Pod
    maxUnavailable: 0   # 不允许有 Pod 不可用
```

更新流程：
1. 创建 1 个新版本 Pod
2. 等待新 Pod 通过 Readiness 检查
3. 摘除 1 个旧版本 Pod
4. 重复直到所有 Pod 更新完成

这样保证始终有 3 个 Pod 在提供服务，用户无感知。

### Q43：资源限制怎么设置的？依据是什么？

**答**：

```yaml
resources:
  requests:
    memory: "2Gi"    # 请求 2GB 内存
    cpu: "1000m"     # 请求 1 核 CPU
  limits:
    memory: "4Gi"    # 限制 4GB 内存
    cpu: "2000m"     # 限制 2 核 CPU
```

依据：
1. **压测数据**：单实例处理 100 QPS 时，内存占用约 1.5GB，CPU 约 0.8 核
2. **安全余量**：requests 留 30% 余量，limits 留 100% 余量
3. **OOM 保护**：limits 防止单个 Pod 占用过多资源影响其他 Pod

### Q44：数据持久化怎么做的？

**答**：

```yaml
volumes:
- name: data-volume
  persistentVolumeClaim:
    claimName: 5g-nr-data-pvc
- name: model-cache
  emptyDir: {}
```

- **PVC（PersistentVolumeClaim）**：持久化存储知识库和向量数据库，Pod 重启后数据不丢失
- **emptyDir**：临时存储模型缓存，Pod 重启后重新下载

PVC 配置：
```yaml
spec:
  accessModes:
  - ReadWriteOnce    # 单节点读写
  resources:
    requests:
      storage: 10Gi  # 10GB 存储空间
```

### Q45：如果 K8s 集群故障怎么办？

**答**：
1. **多可用区部署**：Pod 分散在不同可用区，单区故障不影响服务
2. **Pod 反亲和性**：同一应用的 Pod 不调度到同一节点
3. **自动恢复**：K8s 自动重启失败的 Pod
4. **数据备份**：定期备份 PVC 数据到对象存储

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - 5g-nr-agent
        topologyKey: kubernetes.io/hostname
```

---

## 综合拷问

### Q46：整个系统从感知到执行完成，总时延是多少？

**答**：

| 环节 | 时延 |
|------|------|
| 感知（指标采集 + 故障检测） | < 1 秒 |
| 决策（RAG 检索 + LLM 推理） | 5-10 秒 |
| 四层防护验证 | < 1 秒 |
| 执行（参数变更） | < 2 秒 |
| 效果验证（等待指标稳定） | 60 秒 |
| **总计** | **约 70 秒** |

相比传统人工处理（数小时），效率提升 100 倍以上。

### Q47：系统能处理多少并发请求？

**答**：
- **单实例**：100 QPS（基于压测）
- **3 副本**：300 QPS
- **10 副本（HPA 最大）**：1000 QPS

瓶颈主要在 LLM 推理，可以通过以下方式优化：
1. 使用 vLLM 提升吞吐量
2. 增加 GPU 资源
3. 缓存常见查询结果

### Q48：如果 LLM 服务不可用怎么办？

**答**：
1. **降级策略**：使用规则引擎进行诊断（基于知识库中的规则）
2. **缓存结果**：Redis 缓存历史诊断结果，相似故障直接返回
3. **告警通知**：发送告警，通知运维人员介入

```python
try:
    diagnosis = llm_diagnose(metrics)
except LLMServiceError:
    diagnosis = rule_based_diagnose(metrics)  # 降级到规则引擎
    send_alert("LLM 服务不可用，已切换到规则引擎")
```

### Q49：这个项目最大的技术难点是什么？

**答**：
1. **多智能体协同**：确保三个智能体之间的状态一致性和故障恢复
2. **四层防护机制**：在不影响性能的前提下，确保操作安全性
3. **RRF 排名融合**：调优权重参数，平衡语义检索和关键词检索
4. **实时性能优化**：在秒级时延要求下，完成指标采集、计算、传输

### Q50：如果让你重新设计这个系统，会做什么改进？

**答**：
1. **引入流式处理**：用 Kafka 替代 Redis，支持更高吞吐量
2. **向量检索升级**：用 Milvus 替代 FAISS，支持分布式和增量更新
3. **可观测性增强**：集成 OpenTelemetry，实现全链路追踪
4. **A/B 测试框架**：支持策略灰度发布和效果对比
5. **联邦学习**：多个基站协同训练，保护数据隐私
