# 智能体可用工具：文本总结 + RAG知识库查询
import os
from openai import OpenAI
from utils.log_util import logger
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 工具1：文本总结
def tool_summarize(text: str) -> str:
    try:
        res = client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=[{"role":"user","content":f"总结这段文字：{text}"}]
        )
        return res.choices[0].message.content.strip()
    except:
        return "总结失败"

# 工具2：RAG知识库查询
def tool_rag_query(question: str) -> str:
    try:
        knowledge = ""
        if os.path.exists("docs/knowledge.txt"):
            with open("docs/knowledge.txt","r",encoding="utf-8") as f:
                knowledge = f.read()

        prompt = f"知识库：{knowledge}\n问题：{question}\n只回答知识库内容"
        res = client.chat.completions.create(model=os.getenv("MODEL"),messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content.strip()
    except:
        return "未找到信息"