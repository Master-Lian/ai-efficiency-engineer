# config.py – 配置参数
import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请在.env中设置DEEPSEEK_API_KEY环境变量")

KNOWLEDGE_BASE = os.getenv("KNOWLEDGE_BASE")
if not KNOWLEDGE_BASE:
    raise ValueError("请在.env中设置KNOWLEDGE_BASE环境变量")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(SCRIPT_DIR, "chroma")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

RETRIEVAL_K = 3

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100