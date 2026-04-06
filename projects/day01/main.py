import os
import dotenv
from openai import OpenAI

# 加载环境变量
dotenv.load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    timeout=120
)

def read_text(file_path):
    # 自动找文件，绝对不会找不到
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "input/sample.txt")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def summarize_and_struct(text):
    prompt = f"""
请对下面的文本做处理，输出严格的Markdown格式：

1. 简短总结（100字内）
2. 核心关键词（5-8个）
3. 主要内容分点概述

文本：
{text}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def save_result(content):
    # 自动保存到正确目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(current_dir, "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "result.md")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path

if __name__ == "__main__":
    print("正在读取文本...")
    text = read_text("input/sample.txt")
    
    print("正在调用AI总结...")
    result = summarize_and_struct(text)
    
    print("\n===== 生成完成 =====\n")
    print(result)
    
    save_result(result)
    print("\n✅ 已保存到 output/result.md")