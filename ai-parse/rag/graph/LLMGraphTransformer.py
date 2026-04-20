# ======================================
# LLM知识抽取 + 混合RAG检索（DeepSeek版 无Neo4j）
# ======================================
import os
from dotenv import load_dotenv
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 国内镜像站，全量同步
# 核心导入
from langchain_deepseek import ChatDeepSeek
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# 加载环境变量
load_dotenv()

# ===================== 初始化模型 =====================
llm = ChatDeepSeek(
    model=os.getenv("MODEL", "deepseek-chat"),
    temperature=float(os.getenv("TEMPERATURE", 0.2)),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# 知识图谱转换器
llm_transformer = LLMGraphTransformer(llm=llm)

# ===================== 原始文本 =====================
text = """
乔布斯是苹果公司的创始人，苹果公司发布了iPhone系列手机。
iPhone是一款智能手机，由苹果公司在美国加州设计。
苹果公司还发布了Mac电脑、iPad平板，总部位于美国库比蒂诺。
乔布斯创造了苹果的经典产品，改变了全球智能手机行业。
"""

# ===================== 步骤1：抽取知识图谱（结构化数据）=====================
print("正在抽取知识图谱...\n")
documents = [Document(page_content=text)]
graph_documents = llm_transformer.convert_to_graph_documents(documents)
graph_data = graph_documents[0]

# ===================== 步骤2：构建向量库（非结构化数据）=====================
text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
splits = text_splitter.split_text(text)
# 修复拼写错误
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_index = FAISS.from_texts(splits, embeddings)

# ===================== 步骤3：结构化检索器（优化：按问题匹配）=====================
def structured_retriever(question: str) -> str:
    result = ""
    # 优化：只返回和问题相关的实体关系
    for rel in graph_data.relationships:
        if rel.source.id in question or rel.target.id in question:
            result += f"- {rel.source.id} → {rel.type} → {rel.target.id}\n"
    return result if result else "没有相关关系"

# ===================== 步骤4：你的混合检索器（完全保留！）=====================
def retriever(question: str) -> str:
    print(f"用户查询：{question}")
    structured_data = structured_retriever(question)
    unstructured_data = [el.page_content for el in vector_index.similarity_search(question)]
    final_data = f"""
结构化数据：
{structured_data}
非结构化数据：
{"#Document ".join(unstructured_data)}
    """
    return final_data

# ===================== 步骤5：RAG问答 =====================
if __name__ == "__main__":
    user_question = "乔布斯是谁？苹果公司发布了什么产品？"
    # 获取检索上下文
    context = retriever(user_question)
    
    # 构造提示词
    prompt = f"""根据以下信息回答问题：
{context}
问题：{user_question}
"""
    # 调用LLM生成答案
    answer = llm.invoke(prompt)
    
    # 输出结果
    print("\n" + "="*60)
    print("📝 检索到的上下文：")
    print(context)
    print("="*60)
    print("🤖 最终回答：")
    print(answer.content)