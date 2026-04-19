"""
代理型 RAG 智能体（Agentic RAG）工作流：代码解析与实现
整体架构总览：
1. 智能决策：由agent节点决定是否需要调用检索工具获取外部知识
2. 动态检索：根据决策调用retrieve节点，从向量库获取相关文档
3. 相关性校验：grade_documents条件边判断检索结果是否匹配问题
4. 迭代优化：不匹配则调用rewrite节点重写查询，重新进入流程；匹配则调用generate节点生成回答
5. 闭环控制：重写后的问题会回到agent节点重新决策，直到生成有效回答
"""
import os
# 消除请求警告
os.environ["USER_AGENT"] = "my-rag-app"
# 加载本地.env环境变量
from dotenv import load_dotenv
load_dotenv()

from typing import Annotated, Literal, Sequence, TypedDict
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
# 内置伪造嵌入，零网络、零下载、零依赖
from langchain_core.embeddings import FakeEmbeddings
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

# ====================== 读取本地.env的DeepSeek密钥 ======================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请在项目根目录的.env文件中配置 DEEPSEEK_API_KEY")

# 关闭调试追踪
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# ====================== 本地模拟文档（无网络请求） ======================
local_documents = [
    Document(
        page_content="""The key components of an LLM agent include:
        1. Planning: Breaking down complex tasks into subgoals, task decomposition
        2. Memory: Short-term memory (in-context learning) and Long-term memory (external vector storage)
        3. Tool Use: Calling external APIs, retrievers, calculators, and other tools
        4. Reflection: Self-critique, learning from mistakes, and improving decisions""",
        metadata={"source": "LLM Agent Blog"}
    ),
    Document(
        page_content="""Prompt engineering techniques:
        1. Zero-shot prompting: No examples provided
        2. Few-shot prompting: Provide a few examples
        3. Chain-of-Thought (CoT): Reason step by step
        4. Self-Consistency: Sample multiple reasoning paths
        5. Instruction Tuning: Fine-tune models with natural language instructions""",
        metadata={"source": "Prompt Engineering Blog"}
    ),
    Document(
        page_content="""Adversarial attacks on LLMs:
        1. Jailbreaking: Bypassing safety guardrails
        2. Prompt Injection: Malicious inputs overriding instructions
        3. Data Poisoning: Corrupting training data
        4. Evasion Attacks: Slight input modifications to fool models
        Defense methods: Input filtering, fine-tuning, robust prompt design""",
        metadata={"source": "Adversarial Attacks Blog"}
    )
]

# 文本分块
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=1000,
    chunk_overlap=100
)
doc_splits = text_splitter.split_documents(local_documents)

# 🔥 零网络嵌入模型
embeddings = FakeEmbeddings(size=1024)

# 构建本地向量库
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="rag-chroma",
    embedding=embeddings,
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# ====================== ✅ 修复：标准工具定义（彻底解决Callback报错） ======================
@tool
def retrieve_blog_posts(query: str):
    """Search and return information about LLM agents, prompt engineering, and adversarial attacks on LLMs."""
    return retriever.invoke(query)

tools = [retrieve_blog_posts]

# ====================== 定义代理状态 ======================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], ...]

# ====================== 文档相关性校验（DeepSeek兼容） ======================
def grade_documents(state: AgentState) -> Literal["generate", "rewrite"]:
    print("---CHECK RELEVANCE---")
    messages = state["messages"]
    question = messages[0].content
    docs = messages[-1].content

    prompt = PromptTemplate(
        template="""You are a grader assessing relevance of a retrieved document to a user question.
        Here is the retrieved document: \n\n {context} \n\n
        Here is the user question: {question} \n
        Only answer 'yes' or 'no'.""",
        input_variables=["context", "question"],
    )

    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
        streaming=True
    )

    chain = prompt | model | StrOutputParser()
    score = chain.invoke({"question": question, "context": docs}).strip().lower()

    if score == "yes":
        print("DECISION: DOCS RELEVANT")
        return "generate"
    else:
        print("DECISION: DOCS NOT RELEVANT")
        return "rewrite"

# ====================== 工作流节点（全修复） ======================
def agent(state: AgentState):
    print("---CALL AGENT---")
    messages = state["messages"]
    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
        streaming=True
    )
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    return {"messages": [response]}

def rewrite(state: AgentState):
    print("---TRANSFORM QUERY---")
    messages = state["messages"]
    question = messages[0].content

    msg = [HumanMessage(content=f"Optimize this question: {question}")]
    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
        streaming=True
    )
    response = model.invoke(msg)
    return {"messages": [response]}

def generate(state: AgentState):
    print("---GENERATE---")
    messages = state["messages"]
    question = messages[0].content
    last_message = messages[-1]
    docs = last_message.content

    prompt = PromptTemplate(
        template="""Use the context to answer the question. If you don't know, say so.
        Context: {context}
        Question: {question}
        Answer:""",
        input_variables=["context", "question"]
    )

    llm = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
        streaming=True
    )

    rag_chain = prompt | llm | StrOutputParser()
    response = rag_chain.invoke({"context": docs, "question": question})
    return {"messages": [response]}

# ====================== 构建工作流（连接无错误） ======================
workflow = StateGraph(AgentState)
# 添加节点
workflow.add_node("agent", agent)
workflow.add_node("retrieve", ToolNode(tools))
workflow.add_node("rewrite", rewrite)
workflow.add_node("generate", generate)

# 入口
workflow.set_entry_point("agent")

# 条件边
workflow.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "retrieve", END: END}
)
workflow.add_conditional_edges("retrieve", grade_documents)

# 普通边
workflow.add_edge("generate", END)
workflow.add_edge("rewrite", "agent")

# 编译
graph = workflow.compile()

# ====================== 运行 ======================
if __name__ == "__main__":
    inputs = {"messages": [("user", "What are the key components of LLM agents?")]}
    for output in graph.stream(inputs):
        for key, value in output.items():
            print(f"\n--- [{key}] 输出 ---")
            print(value["messages"][-1].content)