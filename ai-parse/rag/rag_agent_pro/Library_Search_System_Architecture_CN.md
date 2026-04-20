# 书库搜索系统架构说明

## 📋 目录

- [系统概述](#系统概述)
- [核心架构](#核心架构)
- [模块详解](#模块详解)
- [工作流程](#工作流程)
- [使用方法](#使用方法)
- [配置说明](#配置说明)

***

## 系统概述

**书库搜索系统**是一个基于 LangGraph 构建的智能图书问答系统，专门针对 C/C++ 编程领域的知识库进行优化。系统采用 RAG（Retrieval-Augmented Generation）技术，结合向量检索和 LLM 生成能力，为用户提供精准的技术问答和书籍推荐服务。

### 核心特性

- ✅ **智能主题过滤**：通过 LLM 工具调用机制自动识别并拒绝非 C/C++ 相关问题
- ✅ **语义检索**：基于向量相似度的知识检索
- ✅ **查询重写**：自动优化模糊查询以提高检索质量
- ✅ **书籍推荐**：根据检索结果智能推荐相关书籍
- ✅ **相关性评估**：多层级相关性判断机制

***

## 核心架构

### 系统架构图

```
用户输入
    │
    ▼
┌─────────────────┐
│   Agent 节点     │ ← LLM 决策是否调用工具
│  (决策/路由)     │   (无 tool_calls → 拒绝无关问题)
└────────┬────────┘
         │
         │ 调用工具
         ▼
┌─────────────────┐
│  retrieve 节点   │ ← 向量检索（Chroma DB）
│  (知识检索)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ grade_documents │ ← 语义相似度 + LLM 判断
│  (相关性评估)    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│生成   │  │重写  │
│节点   │  │节点  │
└──────┘  └──────┘
    │         │
    │         └─────→ retrieve 节点
    ▼
┌─────────────────┐
│   最终回答       │
│  (答案 + 书籍)   │
└─────────────────┘
```

### 技术栈

| 组件            | 技术选型                                   | 作用          |
| ------------- | -------------------------------------- | ----------- |
| **框架**        | LangGraph                              | 工作流编排       |
| **LLM**       | DeepSeek Chat                          | 决策、生成、重写    |
| **向量数据库**     | Chroma                                 | 知识存储与检索     |
| **Embedding** | sentence-transformers/all-MiniLM-L6-v2 | 文本向量化       |
| **文档加载**      | LangChain Community                    | PDF/DOCX 解析 |

***

## 模块详解

### 1. **config.py** - 配置中心

**定位**：系统配置管理中心

**核心配置项**：

```python
DEEPSEEK_API_KEY        # LLM API 密钥
KNOWLEDGE_BASE          # 知识库文件路径
PERSIST_DIR            # 向量数据库持久化目录
EMBEDDING_MODEL        # Embedding 模型名称
RETRIEVAL_K            # 检索返回文档数量（默认 3）
CHUNK_SIZE             # 文档分块大小（默认 1000）
CHUNK_OVERLAP          # 分块重叠大小（默认 100）
SIMILARITY_THRESHOLD   # 语义相似度阈值（默认 0.5）
```

**调用方式**：

```python
from config import DEEPSEEK_API_KEY, KNOWLEDGE_BASE
```

***

### 2. **vector\_store.py** - 向量数据库管理

**定位**：负责向量数据库的构建、加载和检索

**核心函数**：

#### `get_embeddings()`

- **作用**：获取 Embedding 模型实例
- **特性**：优先使用本地缓存模型，避免网络下载

#### `load_documents(base_path)`

- **作用**：加载指定路径下的 PDF/DOCX 文档
- **返回**：Document 对象列表（包含内容和元数据）

#### `build_vector_store()`

- **作用**：构建新的向量数据库
- **流程**：加载文档 → 分块 → 向量化 → 存储

#### `load_vector_store()`

- **作用**：加载已存在的向量数据库
- **返回**：Chroma 向量库实例或 None

#### `get_retriever()`

- **作用**：获取检索器实例（供 tools 调用）
- **特性**：自动降级处理（加载失败时重建）

**调用示例**：

```python
from vector_store import get_retriever

retriever = get_retriever()
docs = retriever.invoke("C++ 指针")
```

***

### 3. **tools.py** - 工具定义

**定位**：定义可供 LLM 调用的检索工具

**工具列表**：

#### `retrieve_local_docs(query: str)`

- **作用**：检索与查询相关的文档
- **返回**：格式化的文档内容 + 相关书籍统计
- **检索数量**：k=3（由 RETRIEVAL\_K 控制）

#### `retrieve_books_for_recommendation(query: str)`

- **作用**：检索更多文档用于书籍推荐分析
- **返回**：书籍出现频率统计字典
- **检索数量**：k=20

**调用方式**：

```python
# LLM 自动调用（通过 tool_calls）
# 手动调用
from tools import retrieve_local_docs
result = retrieve_local_docs.invoke("函数重载")
```

***

### 4. **nodes.py** - 工作流节点

**定位**：实现工作流的核心业务逻辑

#### **辅助函数**

##### `_extract_question(messages)`

- **作用**：从消息列表中提取用户问题
- **特性**：兼容 tuple 和 BaseMessage 两种格式

##### `_compute_similarity(question, docs_content)`

- **作用**：计算问题与文档的余弦相似度
- **应用**：grade\_documents 节点的快速判断

#### **节点函数**

##### `agent(state)` - 决策节点

- **定位**：工作流入口，负责主题过滤和工具调用决策
- **流程**：
  1. 提取用户问题
  2. 添加系统提示（强化 LLM 边界）
  3. 调用 LLM 进行工具选择
  4. 如果无 tool\_calls，返回拒绝提示（LLM 判断问题无关）

**关键代码**：

```python
def agent(state: AgentState):
    messages = state["messages"]
    
    # 添加系统提示引导 LLM
    system_prompt = """你是一个编程技术助手。你的知识库仅包含 
    C/C++ 编程相关的书籍和资料。如果用户询问无关问题（如农业、
    医学、历史等），请直接回答不了解，不要调用 retrieve_local_docs 工具。"""
    
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=system_prompt)] + list(messages)
    
    # 调用 LLM 决策
    response = model.invoke(messages)
    
    # 如果无 tool_calls，LLM 认为问题无关
    if not response.tool_calls:
        return {"messages": [拒绝消息]}
    
    return {"messages": [response]}
```

##### `grade_documents(state)` - 相关性评估节点

- **定位**：判断检索结果是否与问题相关
- **决策逻辑**：
  1. 问题过于宽泛 → 直接生成
  2. 达到最大重写次数 → 直接生成
  3. 检索结果为空/过短 → 重写查询
  4. 语义相似度 >= 阈值 → 直接生成
  5. 相似度 < 0.3 → 重写查询
  6. 相似度在模糊区间 (0.3-0.5) → LLM 最终判断

**返回**：`"generate"` 或 `"rewrite"`

##### `rewrite(state)` - 查询重写节点

- **定位**：优化模糊查询以提高检索质量
- **策略**：让 LLM 生成更聚焦的关键词查询（3-5 个关键词）

**返回**：新的查询消息 + 重写计数 +1

##### `generate(state)` - 回答生成节点

- **定位**：生成最终回答（答案 + 书籍推荐）
- **流程**：
  1. 提取原始问题
  2. 检查检索结果是否有效
  3. 书籍推荐类查询 → 推荐书籍 + 说明
  4. 普通技术问题 → 直接回答

**输出格式**：

```
[问题回答]

---
**【相关书籍推荐】**（根据内容相关度排序）

1. 《C++ Primer》
2. 《Effective C++》
...
```

***

### 5. **graph.py** - 工作流编排

**定位**：定义和编译工作流图

**节点定义**：

```python
workflow.add_node("agent", agent)          # 决策
workflow.add_node("retrieve", ToolNode(tools))  # 检索
workflow.add_node("rewrite", rewrite)      # 重写
workflow.add_node("generate", generate)    # 生成
```

**边连接**：

```python
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", tools_condition, 
    {"tools": "retrieve", END: END})
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("rewrite", "retrieve")   # 重写后重新检索
workflow.add_edge("generate", END)
```

**调用方式**：

```python
from graph import graph

inputs = {"messages": [("user", "C++ 指针")], "rewrite_count": 0}
for output in graph.stream(inputs):
    for key, value in output.items():
        print(f"{key}: {value}")
```

***

### 6. **main.py** - 主程序入口

**定位**：交互式命令行界面

**使用方法**：

```bash
python main.py
```

**运行流程**：

1. 显示欢迎信息
2. 循环读取用户输入
3. 构建输入状态
4. 流式执行工作流
5. 输出生成节点的回答

**输入格式**：

```python
inputs = {
    "messages": [("user", user_question)],
    "rewrite_count": 0
}
```

***

## 工作流程

### 完整执行流程

```
用户输入 → Agent 节点
            │
            ├─→ 无 tool_calls → 返回拒绝（问题无关）
            │
            └─→ 调用工具 → retrieve 节点
                            │
                            ▼
                     grade_documents 节点
                            │
                 ┌──────────┴──────────┐
                 │                     │
            相似度 >= 0.5          相似度 < 0.3
                 │                     │
                 ▼                     ▼
            Generate 节点          Rewrite 节点
                 │                     │
                 │                     └─→ Retrieve 节点-->(循环评估...)
                 ▼
            最终回答
```

### 典型场景示例

#### 场景 1：C++ 技术问题

```
输入："C++ 中虚函数的工作原理"
流程：agent → retrieve → grade_documents(yes) → generate
输出：详细解释 + 相关书籍推荐
```

#### 场景 2：无关问题

```
输入："母猪的产后护理"
流程：agent → LLM 无 tool_calls → 直接拒绝
输出："抱歉，我的知识库仅包含 C/C++ 编程相关的书籍..."
```

#### 场景 3：模糊查询

```
输入："指针"
流程：agent → retrieve → grade_documents(no, 相似度低) → rewrite → retrieve → generate
输出：指针相关解释 + 书籍推荐
```

#### 场景 4：书籍推荐

```
输入："推荐几本 C++ 入门书籍"
流程：agent → retrieve → grade_documents(yes) → generate
输出：书籍推荐列表 + 简介
```

***

## 使用方法

### 1. 命令行交互模式

```bash
cd e:\learning\aiLLM\ai-engineer\ai-parse\rag\rag_agent_pro
python main.py
```

### 2. Python 脚本调用

```python
from graph import graph

# 单次查询
inputs = {
    "messages": [("user", "C++ 智能指针如何使用？")],
    "rewrite_count": 0
}

for output in graph.stream(inputs):
    for key, value in output.items():
        if key == "generate":
            answer = value["messages"][-1]
            print(answer.content if hasattr(answer, 'content') else answer)
```

### 3. 批量测试

```python
test_queries = [
    "C++ 指针",
    "函数重载",
    "推荐 C++ 书籍",
    "母猪的产后护理"  # 应被拒绝
]

for query in test_queries:
    inputs = {"messages": [("user", query)], "rewrite_count": 0}
    result = list(graph.stream(inputs))
    print(f"查询：{query}")
    print(f"结果：{result[-1]}\n")
```

***

## 配置说明

### 环境变量配置

在项目根目录创建 `.env` 文件：

```bash
# DeepSeek API 密钥
DEEPSEEK_API_KEY=your_api_key_here

# 知识库路径（包含 PDF/DOCX 文件）
KNOWLEDGE_BASE=E:\你的知识库路径
```

### 向量数据库配置

修改 `config.py` 中的参数：

```python
RETRIEVAL_K = 3           # 检索文档数量
CHUNK_SIZE = 1000         # 分块大小
CHUNK_OVERLAP = 100       # 重叠大小
SIMILARITY_THRESHOLD = 0.5  # 相似度阈值
```

### 重建向量数据库

```python
from vector_store import build_vector_store

# 删除旧的向量数据库（可选）
import shutil
shutil.rmtree("chroma")

# 重建
build_vector_store()
```

***

## 性能优化建议

1. **Embedding 模型本地化**
   - 使用缓存的本地模型，避免每次启动时下载
2. **向量数据库持久化**
   - 首次构建后持久化存储，后续直接加载
3. **检索数量优化**
   - 根据实际需求调整 `RETRIEVAL_K`
   - 平衡检索速度和准确性
4. **查询重写次数限制**
   - 默认最大重写 2 次，避免无限循环

***

## 常见问题

### Q1: 为什么有些问题被直接拒绝？

A: 系统使用 LLM 的工具调用机制进行主题过滤。如果 LLM 不调用工具（判断问题无关），会返回拒绝消息。

### Q2: 检索结果不准确怎么办？

A:

1. 调整 `SIMILARITY_THRESHOLD` 阈值
2. 优化查询重写逻辑
3. 增加知识库文档质量

### Q3: 如何扩展到其他领域？

A:

1. 更新 `agent` 节点中的系统提示以描述新领域
2. 替换知识库文档
3. 根据需要调整 Embedding 模型

***

## 更新日志

### v2.0 (2024-04-20)

- ✅ 优化主题过滤机制（使用 LLM tool-calling）
- ✅ 改进 agent 节点拒绝逻辑
- ✅ 增强向量数据库加载失败处理
- ✅ 优化书籍推荐逻辑
- ✅ 添加语义相似度预评估

### v1.0 (初始版本)

- ✅ 基础 RAG 工作流
- ✅ 向量检索功能
- ✅ 查询重写机制
- ✅ 书籍推荐功能

***

## 联系方式

如有问题或建议，请联系项目维护人员。

***

***

***

在您的代码中，**LLM 的 tool-calling 机制**主要体现在 `agent` 节点函数中，具体通过以下两个关键步骤实现：

***

## 1. 绑定工具：`model.bind_tools(tools)`

```python
model = ChatOpenAI(...).bind_tools(tools)
```

- `bind_tools()` 是 LangChain 提供的方法，它将工具（`tools` 列表中的函数）的定义和 schema 附加到 LLM 模型上。
- 当模型接收到消息后，它会根据用户问题和系统提示，**自主决定是否调用某个工具**，以及调用时应该传入什么参数。
- 这一步相当于给 LLM 安装了“工具箱”，模型可以理解每个工具的功能和参数要求。

***

## 2. 处理模型返回的工具调用请求：`response.tool_calls`

```python
response = model.invoke(messages)
if not response.tool_calls:
    # 模型没有请求调用任何工具 → 直接输出文本回答
else:
    # 模型请求调用工具 → 进入工具执行流程
```

- `model.invoke()` 返回的 `response` 对象（通常是 `AIMessage`）包含一个 `tool_calls` 属性。
- 如果 LLM 认为需要调用工具，`tool_calls` 会是一个列表，每个元素包含工具名称和参数（如 `{'name': 'retrieve_local_docs', 'args': {'query': 'C++ 虚函数'}}`）。
- 如果 LLM 认为不需要调用工具（例如问题与编程完全无关），`tool_calls` 为空列表 `[]`，此时模型会直接生成一段文本回答（存放在 `response.content` 中）。

***

## 3. 工作流中的工具执行节点：`ToolNode(tools)`

在 `graph.py` 中，我们定义了 `retrieve` 节点：

```python
workflow.add_node("retrieve", ToolNode(tools))
```

- `ToolNode` 是 LangGraph 内置的节点，它会自动检测 `AIMessage` 中的 `tool_calls`，并执行对应的工具函数。
- 工具执行的结果会包装成 `ToolMessage` 添加到消息列表中，供后续节点（如 `grade_documents`）使用。

***

## 完整流程示例

用户问：`"C++ 中虚函数表是如何工作的？"`

1. **`agent`** **节点**：
   - 模型收到消息，判断需要检索知识库 → 返回 `tool_calls=[{'name': 'retrieve_local_docs', 'args': {'query': 'C++ 虚函数表工作原理'}}]`。
2. **条件边判断**：
   - `tools_condition` 检测到 `tool_calls` 非空 → 进入 `retrieve` 节点。
3. **`retrieve`** **节点**：
   - `ToolNode` 执行 `retrieve_local_docs(query)` → 返回检索到的文档片段。
4. **后续节点**（`grade_documents` → `generate`）生成最终答案。

***

## 对比：无工具调用的情况

用户问：`"母猪的产后护理"`

1. **`agent`** **节点**：
   - 模型判断与编程无关 → 不调用任何工具 → `tool_calls` 为空 → `response.content` 中直接生成拒绝文本。
2. **条件边判断**：
   - `tools_condition` 检测到 `tool_calls` 为空 → 工作流走向 `END`（结束）。
3. **最终输出**：
   - 您修改后的 `agent` 节点中，当 `tool_calls` 为空时，会手动返回一个 `HumanMessage` 包含明确拒绝提示，从而输出给用户。

***

## 总结

**tool-calling 机制在代码中的体现位置**：

- **绑定**：`model.bind_tools(tools)`
- **决策**：`response.tool_calls` 属性
- **执行**：`ToolNode(tools)` 节点
- **路由**：`tools_condition` 条件边

LangChain 和 LangGraph 将这一机制封装得很简洁，您无需手动解析 JSON 或处理函数调用细节，只需按照上述模式即可实现智能工具调用。
