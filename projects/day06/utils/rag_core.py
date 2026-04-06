from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_knowledge():
    try:
        with open("docs/knowledge.txt","r",encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def rag_ask(question):
    knowledge = load_knowledge()
    prompt = f"知识库：{knowledge}\n问题：{question}\n只根据知识库回答"
    try:
        res = client.chat.completions.create(model=os.getenv("MODEL"),messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except:
        return "API 密钥无效或网络错误"