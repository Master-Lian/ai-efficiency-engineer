from openai import OpenAI
import os
from utils.log_util import logger
from utils.agent_tools import tool_summarize, tool_rag_query
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# API 校验
def validate_api_key():
    try:
        client.chat.completions.create(model=os.getenv("MODEL"),messages=[{"role":"user","content":"test"}],max_tokens=1)
        logger.info("✅ API Key 校验通过")
        return True
    except:
        logger.error("❌ API Key 无效")
        return False

# 智能体执行任务
def agent_run(task: str):
    logger.info(f"📥 收到任务：{task}")
    
    # 1. 任务拆解
    prompt = f"""
    你是AI效率助手，分析任务并选择工具：
    工具1：summarize（文本总结）
    工具2：rag（知识库查询）
    任务：{task}
    只输出：工具名|参数
    例：summarize|需要总结的文本
    例：rag|问题
    """
    
    # 2. AI决策
    res = client.chat.completions.create(
        model=os.getenv("MODEL"),
        messages=[{"role":"user","content":prompt}]
    )
    decision = res.choices[0].message.content.strip()
    
    # 3. 执行工具
    try:
        tool_name, param = decision.split("|",1)
        logger.info(f"🤖 智能体选择工具：{tool_name}")
        
        if tool_name == "summarize":
            return tool_summarize(param)
        elif tool_name == "rag":
            return tool_rag_query(param)
        else:
            return "无法识别工具"
    except:
        return "任务执行失败"