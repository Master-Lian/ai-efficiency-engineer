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

def find_docs_dir(start_path=None):
    if start_path is None:
        start_path = os.getcwd()
    current = os.path.abspath(start_path)
    while True:
        candidate = os.path.join(current, "docs")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:  # 已经到达根目录
            break
        current = parent
    return None

def load_knowledge(docs_dir="docs"):
    if docs_dir is None:
        docs_path = find_docs_dir()
        if docs_path is None:
            logger.error("未找到 docs 文件夹，请确保在项目目录或父目录中存在一个名为 docs 的文件夹")
            return ""
        else:
            docs_dir = docs_path

    logger.info(f"当前工作目录: {os.getcwd()}")
    logger.info(f"期望的知识库目录: {docs_dir}")

    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        logger.warning(f"❌ 目录不存在，已自动创建：{docs_path}")
        logger.warning("👉 请在该目录下放入 .txt 或 .md 文件，然后重新运行程序")
        return ""

    files = [f for f in os.listdir(docs_dir) if f.endswith((".txt", ".md"))]
    if not files:
        logger.warning(f"⚠️ 目录 {docs_dir} 中没有找到 .txt 或 .md 文件")
        return ""

    knowledge = ""
    loaded_count = 0
    for file in files:
        path = os.path.join(docs_dir, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                knowledge += content + "\n"
                loaded_count += 1
                logger.info(f"✅ 加载知识库文件: {file}，内容长度: {len(content)} 字符")
        except Exception as e:
            logger.error(f"❌ 加载知识库文件时出错: {file}，错误: {e}")
    logger.info(f"总共加载了 {loaded_count} 个知识库文件，累计内容长度: {len(knowledge)} 字符")
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