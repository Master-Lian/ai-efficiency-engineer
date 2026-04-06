import os
import re
from utils.log_util import logger
from openai import OpenAI, AuthenticationError

from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL = os.getenv("MODEL")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=60
)

# 1. 读取本地知识库
def load_knowledge(docs_dir="docs"):
    knowledge = ""
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        logger.warning("docs 文件夹已创建，请放入知识库文本文件")
        return ""

    for file in os.listdir(docs_dir):
        if file.endswith((".txt", ".md")):
            path = os.path.join(docs_dir, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    knowledge = f.read() + "\n"
                logger.info(f"加载知识库文件: {file}，内容长度: {len(knowledge)}")
            except Exception as e:
                logger.error(f"加载知识库文件时出错: {file}，错误: {e}")
    return knowledge


# API Key 校验
def validate_api_key():
    if not API_KEY or len(API_KEY) < 10:
        logger.error("❌ API Key 为空或格式错误！")
        return False

    try:
        client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "测试API Key有效性"}],
        )
        logger.info("✅ API Key 验证成功！")
        return True

    except AuthenticationError:
        logger.error("❌ API Key 无效！（错误码：401）")
        logger.error("👉 解决办法：检查 .env 中的密钥是否正确，重新生成新的 API Key")
        return False

    except Exception as e:
        logger.error(f"❌ API Key 验证失败: {e}")
        return False
    
# 3. RAG 问答核心
def rag_ask(question: str, knowledge: str) -> str:
    if not knowledge:
        return "知识库内容为空，无法回答问题。"

    prompt = f"""
        你是基于知识库的智能问答助手，必须**只使用下方提供的知识**回答问题。
    如果知识中没有答案，回答：“在知识库中未找到相关信息”。
    
    知识库内容:
    {knowledge}

    问题: {question}
    """

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"RAG 问答失败: {e}")
        return f"RAG 问答失败: {e}"