# LLM 知识抽取 + 混合 RAG 检索实现说明

## 📋 概述

该文件实现了一个基于 LLM 的知识图谱抽取与混合 RAG（Retrieval-Augmented Generation）检索系统。系统结合了**结构化数据**（知识图谱）和**非结构化数据**（向量检索），提供更精准的问答能力。

**核心特点**：
- ✅ 使用 DeepSeek 大模型进行知识图谱抽取
- ✅ 结合 FAISS 向量库进行语义检索
- ✅ 混合检索策略：结构化关系 + 非结构化文本
- ✅ 无需 Neo4j 图数据库，纯内存运行

---

## 🏗️ 系统架构

```
原始文本
    │
    ├─→ 知识图谱抽取（LLMGraphTransformer）
    │       └─→ 结构化数据（实体关系）
    │
    └─→ 文本分块 + 向量化（FAISS）
            └─→ 非结构化数据（向量索引）
                    │
                    ▼
              混合检索器
              （结构化 + 非结构化）
                    │
                    ▼
              RAG 问答生成
```

---

## 🔧 技术栈

| 组件 | 技术选型 | 作用 |
|------|---------|------|
| **LLM** | DeepSeek Chat | 知识图谱抽取、答案生成 |
| **图谱转换** | LLMGraphTransformer | 从文本中抽取实体关系 |
| **向量库** | FAISS | 非结构化文本的向量检索 |
| **Embedding** | HuggingFace (all-MiniLM-L6-v2) | 文本向量化 |
| **文本分块** | RecursiveCharacterTextSplitter | 长文本切分 |

---

## 📝 核心实现步骤

### 步骤 1：初始化模型

```python
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

llm_transformer = LLMGraphTransformer(llm=llm)
```

**说明**：
- 使用 DeepSeek 作为底层大模型
- `LLMGraphTransformer` 是 LangChain 提供的图谱转换工具，能自动从文本中识别实体和关系

---

### 步骤 2：抽取知识图谱（结构化数据）

```python
documents = [Document(page_content=text)]
graph_documents = llm_transformer.convert_to_graph_documents(documents)
graph_data = graph_documents[0]
```

**功能**：
- 将原始文本转换为图结构数据
- 提取实体（如"乔布斯"、"苹果公司"）和关系（如"创始人"、"发布"）
- 结果存储在 `graph_data.relationships` 中

**示例输出**：
```
- 乔布斯 → 创始人 → 苹果公司
- 苹果公司 → 发布 → iPhone
- iPhone → 设计于 → 美国加州
```

---

### 步骤 3：构建向量库（非结构化数据）

```python
text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
splits = text_splitter.split_text(text)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_index = FAISS.from_texts(splits, embeddings)
```

**功能**：
- 将文本按 300 字符分块，重叠 50 字符
- 使用 HuggingFace Embedding 模型向量化
- 构建 FAISS 向量索引用于相似度检索

---

### 步骤 4：结构化检索器

```python
def structured_retriever(question: str) -> str:
    result = ""
    for rel in graph_data.relationships:
        if rel.source.id in question or rel.target.id in question:
            result += f"- {rel.source.id} → {rel.type} → {rel.target.id}\n"
    return result if result else "没有相关关系"
```

**优化点**：
- 只返回与问题相关的实体关系
- 通过检查关系中的源实体或目标实体是否出现在问题中来过滤
- 避免返回无关的关系数据

---

### 步骤 5：混合检索器

```python
def retriever(question: str) -> str:
    structured_data = structured_retriever(question)
    unstructured_data = [el.page_content for el in vector_index.similarity_search(question)]
    final_data = f"""
结构化数据：
{structured_data}
非结构化数据：
{"#Document ".join(unstructured_data)}
    """
    return final_data
```

**混合策略**：
1. **结构化检索**：从知识图谱中获取精确的实体关系
2. **非结构化检索**：从向量库中获取语义相似的文本片段
3. **合并输出**：将两种数据格式化为统一的上下文

---

### 步骤 6：RAG 问答

```python
user_question = "乔布斯是谁？苹果公司发布了什么产品？"
context = retriever(user_question)

prompt = f"""根据以下信息回答问题：
{context}
问题：{user_question}
"""

answer = llm.invoke(prompt)
```

**流程**：
1. 用户输入问题
2. 调用混合检索器获取上下文
3. 构造提示词（包含上下文和问题）
4. 调用 LLM 生成答案
5. 输出检索上下文和最终回答

---

## 🔄 完整执行流程示例

**用户问题**：`"乔布斯是谁？苹果公司发布了什么产品？"`

### 1. 结构化检索结果
```
- 乔布斯 → 创始人 → 苹果公司
- 苹果公司 → 发布 → iPhone
- 苹果公司 → 发布 → Mac 电脑
- 苹果公司 → 发布 → iPad
```

### 2. 非结构化检索结果
```
#Document 乔布斯是苹果公司的创始人，苹果公司发布了 iPhone 系列手机。
#Document iPhone 是一款智能手机，由苹果公司在美国加州设计。
#Document 苹果公司还发布了 Mac 电脑、iPad 平板，总部位于美国库比蒂诺。
```

### 3. 合并上下文
```
结构化数据：
- 乔布斯 → 创始人 → 苹果公司
- 苹果公司 → 发布 → iPhone
...

非结构化数据：
#Document 乔布斯是苹果公司的创始人...
...
```

### 4. LLM 生成答案
```
🤖 最终回答：
乔布斯是苹果公司的创始人。苹果公司发布了 iPhone 系列手机、Mac 电脑和 iPad 平板等产品。
```

---

## 💡 核心优势

### 1. 混合检索提升准确性
- **结构化数据**：提供精确的实体关系，避免语义模糊
- **非结构化数据**：提供丰富的上下文信息，补充细节

### 2. 无需图数据库
- 使用内存存储图谱数据，降低部署复杂度
- 适合小规模知识图谱场景

### 3. 智能关系过滤
- `structured_retriever` 只返回与问题相关的关系
- 减少无关信息干扰 LLM 判断

### 4. 灵活可扩展
- 可替换 Embedding 模型
- 可调整分块策略
- 可集成其他向量数据库

---

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件：

```bash
# DeepSeek API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com

# 模型配置
MODEL=deepseek-chat
TEMPERATURE=0.2
```

### 可调参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 300 | 文本分块大小 |
| `chunk_overlap` | 50 | 分块重叠大小 |
| `temperature` | 0.2 | LLM 生成随机性（越低越稳定） |
| `embedding_model` | all-MiniLM-L6-v2 | 向量化模型 |

---

## 🚀 使用方法

### 运行示例

```bash
cd e:\learning\aiLLM\ai-engineer\ai-parse\rag\graph
python LLMGraphTransformer.py
```

### 自定义问题

修改代码中的 `user_question` 变量：

```python
user_question = "你的问题"
```

---

## 📊 适用场景

### ✅ 适合的场景
- 小规模知识图谱构建
- 需要精确实体关系的问答
- 文档信息抽取与检索
- 快速原型开发

### ❌ 不适合的场景
- 大规模图谱（内存限制）
- 需要持久化存储图谱
- 复杂图查询（如多跳推理）
- 实时图谱更新

---

## 🔮 扩展建议

### 1. 集成 Neo4j
如需持久化和复杂查询，可替换为：
```python
from langchain_community.graphs import Neo4jGraph
graph = Neo4jGraph(url, username, password)
```

### 2. 优化检索策略
- 添加 BM25 关键词检索
- 使用混合检索器（向量 + 关键词）
- 引入重排序模型（Reranker）

### 3. 提升图谱质量
- 添加实体消歧逻辑
- 使用更专业的图谱抽取模型
- 人工校验关键关系

---

## 📝 总结

该文件实现了一个简洁高效的混合 RAG 系统，结合了知识图谱的结构化优势和向量检索的语义理解能力。通过 LLM 自动抽取实体关系，无需手动构建图谱，大大降低了知识图谱应用的门槛。

**核心价值**：
- 🎯 精准：结构化关系提供精确答案
- 🔍 全面：非结构化文本补充详细信息
- ⚡ 高效：内存运行，无需额外数据库
- 🛠️ 灵活：易于扩展和定制
