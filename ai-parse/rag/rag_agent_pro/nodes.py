# nodes.py – 工作流节点函数（优化版）
from typing import Literal, Annotated, Sequence, TypedDict
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from config import DEEPSEEK_API_KEY, SIMILARITY_THRESHOLD
from tools import tools, retrieve_books_for_recommendation
import re
import numpy as np
from vector_store import get_embeddings

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], ...]
    rewrite_count: Annotated[int, ...]

# ---------- 辅助函数 ----------
def _extract_question(messages) -> str:
    """从messages中提取用户问题，处理tuple或BaseMessage格式"""
    first = messages[0]
    if isinstance(first, tuple):
        return first[1]
    return first.content

def _compute_similarity(question: str, docs_content: str) -> float:
    """计算问题与文档内容的余弦相似度（使用文档块的平均向量）"""
    try:
        embedder = get_embeddings()
        # 简单切分文档（按段落或句子）
        doc_chunks = [chunk for chunk in docs_content.split('\n') if len(chunk) > 30]
        if not doc_chunks:
            doc_chunks = [docs_content[:500]]
        # 限制块数，避免过慢
        doc_chunks = doc_chunks[:5]
        question_vec = embedder.embed_query(question)
        doc_vecs = [embedder.embed_query(chunk) for chunk in doc_chunks]
        if not doc_vecs:
            return 0.0
        doc_vec = np.mean(doc_vecs, axis=0)
        similarity = np.dot(question_vec, doc_vec) / (np.linalg.norm(question_vec) * np.linalg.norm(doc_vec))
        return float(similarity)
    except Exception:
        return 0.0  # 出错时返回0，降级到LLM判断

# ---------- 节点函数 ----------
def agent(state: AgentState):
    print("---Agent 决策---")
    messages = state["messages"]
    system_prompt = """你是一个编程技术助手。你的知识库主要包含 C/C++ 编程相关的书籍和技术资料。
如果用户询问的问题与编程完全无关（例如：农业、医学、历史、生活常识等），请直接回答你不了解该领域，不要调用 retrieve_local_docs 工具。
如果问题与编程相关（包括但不限于 C/C++、算法、数据结构、软件开发、学习路线、书籍推荐等），请调用 retrieve_local_docs 工具检索知识库。"""
    
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=system_prompt)] + list(messages)
    
    model = ChatOpenAI(
        temperature=0,
        model="deepseek-chat",
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com",
    ).bind_tools(tools)
    response = model.invoke(messages)
    
    # 如果没有 tool_calls，说明模型判断问题与编程无关
    if not response.tool_calls:
        print(">>> 模型判断问题与编程无关，输出拒绝提示")
        refusal_message = (
            "抱歉，您的问题与系统知识库（C/C++ 编程）无关。\n\n"
            "我的知识库仅包含 C/C++ 编程相关的书籍和技术资料。\n"
            "请提出与 C/C++ 编程相关的技术问题，例如：\n"
            "  - C++ 中虚函数的工作原理？\n"
            "  - 如何学习 C++ 指针？\n"
            "  - 推荐几本 C++ 经典书籍？"
        )
        return {"messages": [HumanMessage(content=refusal_message)]}
    
    return {"messages": [response]}

def grade_documents(state: AgentState) -> Literal["generate", "rewrite"]:
    """基于语义相似度预判 + LLM 兜底的相关性判断"""
    print("---检查检索结果相关性---")
    messages = state["messages"]
    rewrite_count = state.get("rewrite_count", 0)
    question = _extract_question(messages)
    docs = messages[-1].content
    # 如果问题过于宽泛（如单个词且非技术关键词），直接进入生成，不进行相似度判断
    if len(question.strip()) < 5 and not any(kw in question.lower() for kw in ["指针", "类", "函数", "模板", "内存"]):
        print(">>> 问题过于宽泛，直接生成帮助信息")
        return "generate"

    MAX_REWRITE = 2
    if rewrite_count >= MAX_REWRITE:
        print(f"已达到最大重写次数（{MAX_REWRITE}）-> 进入生成")
        return "generate"

    # 快速判断：如果文档内容为空或极短，直接重写
    if not docs or len(docs.strip()) < 50:
        print(">>> 检索结果为空或过短 -> 重写查询")
        return "rewrite"

    # 1. 计算语义相似度
    sim_score = _compute_similarity(question, docs)
    print(f">>> 语义相似度: {sim_score:.3f}")

    if sim_score >= SIMILARITY_THRESHOLD:
        print(">>> 相似度足够高 -> 进入生成")
        return "generate"
    elif sim_score < 0.3:
        print(">>> 相似度极低 -> 重写查询")
        return "rewrite"
    else:
        # 模糊区间，调用 LLM 最终判断
        print(">>> 相似度模糊，调用 LLM 确认")
        prompt = PromptTemplate(
            template="""判断以下文档是否有助于回答用户问题。只回答 'yes' 或 'no'。

问题: {question}
文档: {context}
决策:""",
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
            print(">>> LLM 判断相关 -> 进入生成")
            return "generate"
        else:
            print(">>> LLM 判断不相关 -> 重写查询")
            return "rewrite"

def rewrite(state: AgentState):
    print("---重写查询---")
    messages = state["messages"]
    rewrite_count = state.get("rewrite_count", 0)
    question = _extract_question(messages)

    # 简化重写：直接让 LLM 生成更聚焦的关键词查询
    prompt = PromptTemplate(
        template="""请将以下用户问题改写成更简洁、清晰的检索关键词（3-5个关键词或短语），只输出改写结果，不要解释。

原始问题: {question}
改写后:""",
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
    return {"messages": [HumanMessage(content=new_question)], "rewrite_count": rewrite_count + 1}

def generate(state: AgentState):
    print("---生成最终回答---")
    messages = state["messages"]
    original_question = _extract_question(messages)
    docs = messages[-1].content
    rewrite_count = state.get("rewrite_count", 0)

    # 判断是否有有效检索结果
    if not docs or len(docs.strip()) < 50:
        answer = """抱歉，当前知识库中没有找到与您查询内容相关的资料。

当前知识库主要包含 C/C++ 编程相关的书籍和技术文档（如 C++ Primer、Effective C++、深度探索C++对象模型等）。

建议您：
1. 查询 C/C++ 编程相关的技术问题（如指针、内存管理、多态、模板等）
2. 或提供更具体的关键词（例如：C++ 虚函数工作原理、Qt 信号槽机制等）"""
        return {"messages": [answer]}

    # 书籍推荐类问题（包含推荐、书籍等关键词）
    book_keywords = ["推荐", "书籍", "教材", "学习", "资料", "book", "books", "recommend"]
    is_book_query = any(keyword in original_question.lower() for keyword in book_keywords)

    if is_book_query:
        # 获取书籍统计
        try:
            book_stats = retrieve_books_for_recommendation.invoke(original_question)
            top_5_books = sorted(book_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            recommended_books = "\n".join([f"{i+1}. 《{book}》" for i, (book, count) in enumerate(top_5_books)])
        except Exception:
            top_5_books = []
            recommended_books = ""

        prompt = PromptTemplate(
            template="""你是一个专业的图书推荐助手。请根据以下文档内容，为用户推荐相关的书籍。

用户问题: {question}

文档内容:
{context}

请基于文档内容，为用户推荐几本适合的书籍，并简要说明推荐理由。""",
            input_variables=["context", "question"],
        )
        model = ChatOpenAI(
            temperature=0.7,
            model="deepseek-chat",
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
        )
        chain = prompt | model | StrOutputParser()
        answer = chain.invoke({"question": original_question, "context": docs})

        if top_5_books:
            final_answer = f"{answer}\n\n---\n**【相关书籍推荐】（根据内容相关度排序）**\n{recommended_books}\n\n提示：以上推荐基于检索结果中各书籍出现的频率，越靠前的书籍与您的查询内容越相关。"
        else:
            final_answer = answer
    else:
        # 普通技术问题
        prompt = PromptTemplate(
            template="""你是一个专业的 C/C++ 技术问答助手。请根据以下文档内容回答用户问题。

用户问题: {question}

文档内容:
{context}

请用自然、友好的语言给出详细的解释和答案。""",
            input_variables=["context", "question"],
        )
        model = ChatOpenAI(
            temperature=0.7,
            model="deepseek-chat",
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
        )
        chain = prompt | model | StrOutputParser()
        final_answer = chain.invoke({"question": original_question, "context": docs})

    return {"messages": [final_answer]}