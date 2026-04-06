from openai import OpenAI
import os
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

def ai_summarize(text):
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":f"请总结这段文字：{text}"}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"错误：{str(e)}"