# tools.py – 检索工具定义
import os
from langchain_core.tools import tool
from vector_store import get_retriever

retriever = None

def get_retriever_instance():
    global retriever
    if retriever is None:
        retriever = get_retriever()
    return retriever

@tool
def retrieve_local_docs(query: str):
    """
    从本地知识库中检索与查询相关的文档。
    """
    docs = get_retriever_instance().invoke(query)
    if not docs:
        return "未找到相关文档"
    formatted = []
    book_stats = {}
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        filename = os.path.basename(source)
        content = doc.page_content.strip()
        if len(content) > 500:
            content = content[:500] + " ..."
        formatted.append(f"[来源:{filename}]\n {content}\n")
        if filename not in book_stats:
            book_stats[filename] = 0
        book_stats[filename] += 1
    result = "\n---\n".join(formatted)
    top_books = sorted(book_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    book_list = ", ".join([f"《{book}》" for book, _ in top_books])
    result += f"\n\n【检索到相关内容的书籍】: {book_list}"
    return result

@tool
def retrieve_books_for_recommendation(query: str):
    """
    检索更多文档用于分析并推荐相似书籍。
    返回更多检索结果以便统计哪些书籍出现频率最高。
    """
    from vector_store import load_vector_store
    vectorstore = load_vector_store()
    if vectorstore is None:
        return {}
    retriever_large = vectorstore.as_retriever(search_kwargs={"k": 20})
    docs = retriever_large.invoke(query)
    if not docs:
        return {}
    book_stats = {}
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        filename = os.path.basename(source)
        if filename not in book_stats:
            book_stats[filename] = 0
        book_stats[filename] += 1
    return book_stats

tools = [retrieve_local_docs, retrieve_books_for_recommendation]