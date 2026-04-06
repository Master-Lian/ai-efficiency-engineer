import os
import dotenv
from openai import OpenAI

dotenv.load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    timeout=60
)

def summarize_text(text: str) -> str:
    if not text.strip():
        return "输入文本不能为空，请提供有效的文本内容。"

    prompt = f"""
请对下面的文本做处理，输出严格的Markdown格式：
1. 简短总结（100字内）
2. 核心关键词（5-8个）
3. 主要内容分点概述

文本：
{text}
""".format(text)
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content