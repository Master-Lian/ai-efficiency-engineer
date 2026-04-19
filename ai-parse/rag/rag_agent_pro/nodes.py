# nodes.py – 工作流节点函数
from typing import Literal, Annotated, Sequence, TypedDict
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from config import DEEPSEEK_API_KEY

from tools import tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], ...]
    rewrite_count: Annotated[int, ...]

# ---------- 节点函数 ----------
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

def grade_documents(state: AgentState) -> Literal["generate", "rewrite"]:
    print("---检查检索结果相关性---")
    messages = state["messages"]
    rewrite_count = state.get("rewrite_count", 0)
    question = messages[0].content
    docs = messages[-1].content

    MAX_REWRITE = 2

    if rewrite_count >= MAX_REWRITE:
        print(f"已达到最大重写次数（{MAX_REWRITE}）-> 进入生成")
        return "generate"

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
        print(">>> 文档相关 -> 进入生成")
        return "generate"
    else:
        print(">>> 文档不相关 -> 重写查询")
        return "rewrite"

def rewrite(state: AgentState):
    print("---重写查询---")
    messages = state["messages"]
    rewrite_count = state.get("rewrite_count", 0)
    question = messages[0].content
    prompt = PromptTemplate(
        template="""请将以下用户问题改写成更简洁、清晰的检索关键词，保留核心概念。
        只输出改写后的查询语句，不要解释。

        原始问题: {question}

        改写后（只输出查询语句）:""",
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
    question = messages[0].content
    docs = messages[-1].content

    from tools import retrieve_books_for_recommendation
    book_stats = retrieve_books_for_recommendation.invoke(question)
    top_5_books = sorted(book_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    recommended_books = "\n".join([f"{i+1}. 《{book}》" for i, (book, count) in enumerate(top_5_books)])

    prompt = PromptTemplate(
        template="""你是一个专业的图书问答助手。请根据以下文档内容回答用户问题。
        注意：请使用纯文本回答，不要使用任何emoji表情符号。

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
    answer = chain.invoke({"question": question, "context": docs})

    if top_5_books:
        final_answer = f"""{answer}

    ---
    **【相关书籍推荐】（根据内容相关度排序）**

    {recommended_books}

    提示：以上推荐基于检索结果中各书籍出现的频率，越靠前的书籍与你的查询内容越相关。"""
    else:
        final_answer = answer

    return {"messages": [final_answer]}

