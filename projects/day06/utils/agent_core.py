from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def agent_task(task):
    prompt = f"""任务：{task}
    你是AI助手，直接给出详细结果。"""
    try:
        res = client.chat.completions.create(model=os.getenv("MODEL"),messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except:
        return "密钥无效"

from utils.mcp import mcp_invoke

def agent_mcp_task(task_type: str, **params):
    print(f"🤖 Agent执行任务：{task_type}")
    return mcp_invoke(skill_name=task_type, **params)