"""
代理型 RAG 智能体 - 本地 PDF/DOCX 知识库检索
修改：支持大量 PDF 文件，自动提取文本，构建向量库，回答时附带出处
"""

import os
os.environ["USER_AGENT"] = "my-rag-app"

from dotenv import load_dotenv
load_dotenv()

from typing import Annotated, Literal, Sequence, TypedDict
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, Docx2txtLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

# ====================== DeepSeek 配置 ======================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请在 .env 文件中配置 DEEPSEEK_API_KEY")

os.environ["LANGCHAIN_TRACING_V2"] = "false"

# ====================== 本地知识库路径 ======================
KNOWLEDGE_BASE_PATH = r"E:\廉令武研究生文件夹\学习资料\C_CPP_Materials"

# ====================== 加载文档（PDF + DOCX） ======================
print(f"正在扫描文件夹: {KNOWLEDGE_BASE_PATH}")

def load_documents(base_path):
    """加载所有 PDF 和 DOCX 文件，返回 Document 列表"""
    docs = []
    # 加载 PDF
    if os.path.exists(base_path):
        pdf_loader = DirectoryLoader(
            base_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True,
            use_multithreading=True,
            recursive=True
        )
        try:
            pdf_docs = pdf_loader.load()
            print(f"✅ 成功加载 {len(pdf_docs)} 个 PDF 文档（按页分割）")
            docs.extend(pdf_docs)
        except Exception as e:
            print(f"❌ 加载 PDF 失败: {e}")

        # 加载 DOCX（可选）
        docx_loader = DirectoryLoader(
            base_path,
            glob="**/*.docx",
            loader_cls=Docx2txtLoader,
            show_progress=True,
            use_multithreading=True,
            recursive=True
        )
        try:
            docx_docs = docx_loader.load()
            print(f"✅ 成功加载 {len(docx_docs)} 个 DOCX 文档")
            docs.extend(docx_docs)
        except Exception as e:
            print(f"⚠️ 加载 DOCX 失败（可能没有 docx 文件）: {e}")
    else:
        raise ValueError(f"路径不存在: {base_path}")

    if not docs:
        raise ValueError("未找到任何 PDF 或 DOCX 文档，请检查路径并确认文件格式。")
    
    print(f"📄 共加载原始文档页/段数量: {len(docs)}")
    return docs

raw_docs = load_documents(KNOWLEDGE_BASE_PATH)

# 文本分块（每个块约 1000 字符）
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=1000,
    chunk_overlap=100
)
doc_splits = text_splitter.split_documents(raw_docs)
print(f"✂️ 文档切分为 {len(doc_splits)} 个文本块")

# ====================== 本地嵌入模型（首次会下载） ======================
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 构建向量库（持久化到本地 ./chroma_db 文件夹）
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="cpp_knowledge",
    embedding=embeddings,
    persist_directory="./chroma_db"   # 下次运行直接加载，不用重新嵌入
)
retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})

# ====================== 检索工具（带出处） ======================
@tool
def retrieve_local_docs(query: str):
    """从本地 C/C++ 学习资料库中检索相关文档片段，返回带文件来源的内容。"""
    docs = retriever.invoke(query)
    if not docs:
        return "未找到相关文档。"
    formatted = []
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        filename = os.path.basename(source)
        content = doc.page_content.strip()
        # 限制每个片段长度，避免上下文过长
        if len(content) > 500:
            content = content[:500] + "..."
        formatted.append(f"[来源: {filename}]\n{content}\n")
    return "\n---\n".join(formatted)

tools = [retrieve_local_docs]

# ====================== 状态定义 ======================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], ...]

# ====================== 相关性判断 ======================
def grade_documents(state: AgentState) -> Literal["generate", "rewrite"]:
    print("---检查检索结果相关性---")
    messages = state["messages"]
    question = messages[0].content
    docs = messages[-1].content

    prompt = PromptTemplate(
        template="""你是相关性评估专家。根据用户问题判断以下文档内容是否有助于回答问题。
        只回答 'yes'（相关）或 'no'（不相关）。

        用户问题: {question}

        文档内容:
        {context}

        决策（yes/no）:""",
        input_variables=["context", "question"],
    )

    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
    )
    chain = prompt | model | StrOutputParser()
    score = chain.invoke({"question": question, "context": docs}).strip().lower()

    if score == "yes":
        print("✅ 文档相关 -> 进入生成")
        return "generate"
    else:
        print("❌ 文档不相关 -> 重写查询")
        return "rewrite"

# ====================== 节点定义 ======================
def agent(state: AgentState):
    print("---Agent 决策---")
    messages = state["messages"]
    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
    ).bind_tools(tools)
    response = model.invoke(messages)
    return {"messages": [response]}

def rewrite(state: AgentState):
    print("---重写查询---")
    messages = state["messages"]
    question = messages[0].content
    prompt = PromptTemplate(
        template="""请将以下用户问题改写成更清晰、更适合检索的形式，保持原意不变。
        原始问题: {question}
        改写后的问题:""",
        input_variables=["question"]
    )
    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
    )
    chain = prompt | model | StrOutputParser()
    new_question = chain.invoke({"question": question})
    return {"messages": [HumanMessage(content=new_question)]}

def generate(state: AgentState):
    print("---生成最终答案---")
    messages = state["messages"]
    question = messages[0].content
    docs = messages[-1].content

    prompt = PromptTemplate(
        template="""你是 C/C++ 技术专家。请基于以下检索到的文档片段回答问题。
        每个文档前有 [来源: 文件名]，请在答案中明确引用出处。
        如果信息不足，请诚实说明。

        检索内容：
        {context}

        问题：
        {question}

        答案（必须包含引用的书名/文件名）：""",
        input_variables=["context", "question"]
    )

    llm = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
    )
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": docs, "question": question})
    return {"messages": [answer]}

# ====================== 构建图 ======================
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("retrieve", ToolNode(tools))
workflow.add_node("rewrite", rewrite)
workflow.add_node("generate", generate)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", tools_condition, {"tools": "retrieve", END: END})
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("generate", END)
workflow.add_edge("rewrite", "agent")

graph = workflow.compile()

# ====================== 运行 ======================
if __name__ == "__main__":
    # 测试问题（你可以修改）
    user_question = "C++ 中虚函数表是如何工作的？"
    inputs = {"messages": [("user", user_question)]}
    
    print(f"\n📌 用户问题: {user_question}\n")
    for output in graph.stream(inputs):
        for key, value in output.items():
            print(f"\n--- [{key}] 输出 ---")
            res = value["messages"][-1]
            content = res if isinstance(res, str) else res.content
            print(content)