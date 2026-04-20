# Library Search System Architecture

## 📋 Table of Contents
- [System Overview](#system-overview)
- [Core Architecture](#core-architecture)
- [Module Details](#module-details)
- [Workflow](#workflow)
- [Usage](#usage)
- [Configuration](#configuration)

---

## System Overview

**Library Search System** is an intelligent book Q&A system built on LangGraph, optimized for C/C++ programming knowledge base. The system uses RAG (Retrieval-Augmented Generation) technology, combining vector retrieval and LLM generation capabilities to provide users with precise technical Q&A and book recommendation services.

### Core Features
- ✅ **Intelligent Topic Filtering**: Automatically identifies and rejects non-C/C++ related questions via LLM tool-calling mechanism
- ✅ **Semantic Retrieval**: Vector similarity-based knowledge retrieval
- ✅ **Query Rewriting**: Automatically optimizes vague queries to improve retrieval quality
- ✅ **Book Recommendation**: Intelligently recommends related books based on retrieval results
- ✅ **Relevance Assessment**: Multi-level relevance judgment mechanism

---

## Core Architecture

### System Architecture Diagram

```
User Input
    │
    ▼
┌─────────────────┐
│   Agent Node     │ ← LLM decides whether to call tools
│  (Decision/      │   (No tool_calls → reject unrelated questions)
│   Routing)       │
└────────┬────────┘
         │
         │ Call Tools
         ▼
┌─────────────────┐
│  Retrieve Node  │ ← Vector Retrieval (Chroma DB)
│  (Knowledge     │
│   Retrieval)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ grade_documents │ ← Semantic Similarity + LLM Judgment
│  (Relevance     │
│   Assessment)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│Generate│ │Rewrite│
│ Node   │ │ Node  │
└──────┘  └──────┘
    │         │
    │         └─────→ Retrieve Node
    ▼
┌─────────────────┐
│   Final Answer  │
│  (Answer +      │
│   Books)        │
└─────────────────┘
```

### Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Framework** | LangGraph | Workflow orchestration |
| **LLM** | DeepSeek Chat | Decision, generation, rewriting |
| **Vector Database** | Chroma | Knowledge storage and retrieval |
| **Embedding** | sentence-transformers/all-MiniLM-L6-v2 | Text vectorization |
| **Document Loader** | LangChain Community | PDF/DOCX parsing |

---

## Module Details

### 1. **config.py** - Configuration Center

**Role**: System configuration management center

**Core Configuration Items**:
```python
DEEPSEEK_API_KEY        # LLM API key
KNOWLEDGE_BASE          # Knowledge base file path
PERSIST_DIR            # Vector database persistence directory
EMBEDDING_MODEL        # Embedding model name
RETRIEVAL_K            # Number of retrieved documents (default: 3)
CHUNK_SIZE             # Document chunk size (default: 1000)
CHUNK_OVERLAP          # Chunk overlap size (default: 100)
SIMILARITY_THRESHOLD   # Semantic similarity threshold (default: 0.5)
```

**Usage**:
```python
from config import DEEPSEEK_API_KEY, KNOWLEDGE_BASE
```

---

### 2. **vector_store.py** - Vector Database Management

**Role**: Responsible for vector database construction, loading, and retrieval

**Core Functions**:

#### `get_embeddings()`
- **Purpose**: Get Embedding model instance
- **Feature**: Prioritizes using local cached model to avoid network downloads

#### `load_documents(base_path)`
- **Purpose**: Load PDF/DOCX documents from specified path
- **Returns**: List of Document objects (containing content and metadata)

#### `build_vector_store()`
- **Purpose**: Build a new vector database
- **Process**: Load documents → Chunk → Vectorize → Store

#### `load_vector_store()`
- **Purpose**: Load existing vector database
- **Returns**: Chroma vector store instance or None

#### `get_retriever()`
- **Purpose**: Get retriever instance (called by tools)
- **Feature**: Automatic fallback handling (rebuild on load failure)

**Usage Example**:
```python
from vector_store import get_retriever

retriever = get_retriever()
docs = retriever.invoke("C++ pointer")
```

---

### 3. **tools.py** - Tool Definitions

**Role**: Define retrieval tools available for LLM to call

**Tool List**:

#### `retrieve_local_docs(query: str)`
- **Purpose**: Retrieve documents related to query
- **Returns**: Formatted document content + related book statistics
- **Retrieval Count**: k=3 (controlled by RETRIEVAL_K)

#### `retrieve_books_for_recommendation(query: str)`
- **Purpose**: Retrieve more documents for book recommendation analysis
- **Returns**: Book occurrence frequency dictionary
- **Retrieval Count**: k=20

**Usage**:
```python
# Automatically called by LLM (via tool_calls)
# Manual call
from tools import retrieve_local_docs
result = retrieve_local_docs.invoke("function overloading")
```

---

### 4. **nodes.py** - Workflow Nodes

**Role**: Implement core business logic of workflow

#### **Helper Functions**

##### `_extract_question(messages)`
- **Purpose**: Extract user question from message list
- **Feature**: Compatible with both tuple and BaseMessage formats

##### `_compute_similarity(question, docs_content)`
- **Purpose**: Calculate cosine similarity between question and document
- **Application**: Fast judgment in grade_documents node

#### **Node Functions**

##### `agent(state)` - Decision Node
- **Role**: Workflow entry point, responsible for topic filtering and tool call decision
- **Process**:
  1. Extract user question
  2. Add system prompt (reinforce LLM boundaries)
  3. Call LLM for tool selection
  4. If no tool_calls, return rejection message (LLM judges question as unrelated)

**Key Code**:
```python
def agent(state: AgentState):
    messages = state["messages"]
    
    # Add system prompt to guide LLM
    system_prompt = """You are a programming assistant. Your knowledge base 
    contains C/C++ programming books and materials. If user asks unrelated 
    questions (e.g., agriculture, medicine, history), answer that you don't 
    know and don't call retrieve_local_docs tool."""
    
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=system_prompt)] + list(messages)
    
    # Call LLM to decide
    response = model.invoke(messages)
    
    # If no tool_calls, LLM thinks question is unrelated
    if not response.tool_calls:
        return {"messages": [rejection_message]}
    
    return {"messages": [response]}
```

##### `grade_documents(state)` - Relevance Assessment Node
- **Role**: Judge whether retrieval results are relevant to question
- **Decision Logic**:
  1. Question too vague → Direct generate
  2. Reached max rewrite count → Direct generate
  3. Retrieval empty/too short → Rewrite query
  4. Semantic similarity >= threshold → Direct generate
  5. Similarity < 0.3 → Rewrite query
  6. Similarity in fuzzy range (0.3-0.5) → LLM final judgment

**Returns**: `"generate"` or `"rewrite"`

##### `rewrite(state)` - Query Rewriting Node
- **Role**: Optimize vague queries to improve retrieval quality
- **Strategy**: Let LLM generate more focused keyword queries (3-5 keywords)

**Returns**: New query message + rewrite count +1

##### `generate(state)` - Answer Generation Node
- **Role**: Generate final answer (answer + book recommendations)
- **Process**:
  1. Extract original question
  2. Check if retrieval results are valid
  3. Book recommendation query → Recommend books + explanations
  4. Regular technical question → Direct answer

**Output Format**:
```
[Question Answer]

---
**【Related Book Recommendations】** (sorted by relevance)

1. 《C++ Primer》
2. 《Effective C++》
...
```

---

### 5. **graph.py** - Workflow Orchestration

**Role**: Define and compile workflow graph

**Node Definitions**:
```python
workflow.add_node("agent", agent)          # Decision
workflow.add_node("retrieve", ToolNode(tools))  # Retrieval
workflow.add_node("rewrite", rewrite)      # Rewriting
workflow.add_node("generate", generate)    # Generation
```

**Edge Connections**:
```python
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", tools_condition, 
    {"tools": "retrieve", END: END})
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("rewrite", "retrieve")   # Rewrite then re-retrieve
workflow.add_edge("generate", END)
```

**Usage**:
```python
from graph import graph

inputs = {"messages": [("user", "C++ pointer")], "rewrite_count": 0}
for output in graph.stream(inputs):
    for key, value in output.items():
        print(f"{key}: {value}")
```

---

### 6. **main.py** - Main Program Entry

**Role**: Interactive command-line interface

**Usage**:
```bash
python main.py
```

**Run Process**:
1. Display welcome message
2. Loop to read user input
3. Build input state
4. Stream execute workflow
5. Output generation node's answer

**Input Format**:
```python
inputs = {
    "messages": [("user", user_question)],
    "rewrite_count": 0
}
```

---

## Workflow

### Complete Execution Flow

```
User Input → Agent Node
                │
                ├─→ No tool_calls → Return rejection (unrelated question)
                │
                └─→ Call tools → Retrieve Node
                                    │
                                    ▼
                             grade_documents Node
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                    Similarity >= 0.5      Similarity < 0.3
                         │                     │
                         ▼                     ▼
                    Generate Node          Rewrite Node
                         │                     │
                         │                     └─→ Retrieve Node
                         ▼
                    Final Answer
```

### Typical Scenario Examples

#### Scenario 1: C++ Technical Question
```
Input: "How do virtual functions work in C++?"
Flow: agent → retrieve → grade_documents(yes) → generate
Output: Detailed explanation + related book recommendations
```

#### Scenario 2: Unrelated Question
```
Input: "Postpartum care for sows"
Flow: agent → LLM no tool_calls → Direct rejection
Output: "Sorry, my knowledge base only contains C/C++ programming..."
```

#### Scenario 3: Vague Query
```
Input: "pointer"
Flow: agent → retrieve → grade_documents(no, low similarity) → rewrite → retrieve → generate
Output: Pointer explanation + book recommendations
```

#### Scenario 4: Book Recommendation
```
Input: "Recommend some C++ beginner books"
Flow: agent → retrieve → grade_documents(yes) → generate
Output: Book recommendation list + brief descriptions
```

---

## Usage

### 1. Command-Line Interactive Mode

```bash
cd e:\learning\aiLLM\ai-engineer\ai-parse\rag\rag_agent_pro
python main.py
```

### 2. Python Script Call

```python
from graph import graph

# Single query
inputs = {
    "messages": [("user", "How to use C++ smart pointers?")],
    "rewrite_count": 0
}

for output in graph.stream(inputs):
    for key, value in output.items():
        if key == "generate":
            answer = value["messages"][-1]
            print(answer.content if hasattr(answer, 'content') else answer)
```

### 3. Batch Testing

```python
test_queries = [
    "C++ pointer",
    "function overloading",
    "Recommend C++ books",
    "Postpartum care for sows"  # Should be rejected
]

for query in test_queries:
    inputs = {"messages": [("user", query)], "rewrite_count": 0}
    result = list(graph.stream(inputs))
    print(f"Query: {query}")
    print(f"Result: {result[-1]}\n")
```

---

## Configuration

### Environment Variable Configuration

Create `.env` file in project root:

```bash
# DeepSeek API Key
DEEPSEEK_API_KEY=your_api_key_here

# Knowledge Base Path (containing PDF/DOCX files)
KNOWLEDGE_BASE=E:\path\to\your\knowledge\base
```

### Vector Database Configuration

Modify parameters in `config.py`:

```python
RETRIEVAL_K = 3           # Number of retrieved documents
CHUNK_SIZE = 1000         # Chunk size
CHUNK_OVERLAP = 100       # Overlap size
SIMILARITY_THRESHOLD = 0.5  # Similarity threshold
```

### Rebuild Vector Database

```python
from vector_store import build_vector_store

# Delete old vector database (optional)
import shutil
shutil.rmtree("chroma")

# Rebuild
build_vector_store()
```

---

## Performance Optimization Suggestions

1. **Embedding Model Localization**
   - Use cached local model to avoid downloads on each startup

2. **Vector Database Persistence**
   - Persist after first build, load directly subsequently

3. **Retrieval Count Optimization**
   - Adjust `RETRIEVAL_K` based on actual needs
   - Balance retrieval speed and accuracy

4. **Query Rewrite Count Limit**
   - Default max 2 rewrites to avoid infinite loops

---

## FAQ

### Q1: Why are some questions directly rejected?
A: The system uses LLM's tool-calling mechanism for topic filtering. If LLM doesn't call tools (judges question as unrelated), it returns a rejection message.

### Q2: What if retrieval results are inaccurate?
A: 
1. Adjust `SIMILARITY_THRESHOLD` threshold
2. Optimize query rewriting logic
3. Improve knowledge base document quality

### Q3: How to extend to other domains?
A:
1. Update system prompt in `agent` node to describe new domain
2. Replace knowledge base documents
3. Adjust embedding model if needed

---

## Changelog

### v2.0 (2024-04-20)
- ✅ Optimized topic filtering mechanism (using LLM tool-calling)
- ✅ Improved agent node rejection logic
- ✅ Enhanced vector database load failure handling
- ✅ Optimized book recommendation logic
- ✅ Added semantic similarity pre-assessment

### v1.0 (Initial Version)
- ✅ Basic RAG workflow
- ✅ Vector retrieval functionality
- ✅ Query rewriting mechanism
- ✅ Book recommendation functionality

---

## Contact

For questions or suggestions, please contact project maintainers.
