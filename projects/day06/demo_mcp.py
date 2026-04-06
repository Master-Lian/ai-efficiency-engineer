# app.py
import streamlit as st
from utils.agent_core import agent_mcp_task

st.title("🤖 AI效率Agent - MCP+Skills 调用演示")
st.subheader("超聚变AI效率工程师实战")

# 选择技能
task_option = st.selectbox("选择Agent执行任务", [
    "ai_efficiency",  # AI效率计算
    "quant_optimize", # 模型量化优化
    "chat"            # 问答
])

# 输入参数
if task_option == "ai_efficiency":
    model_name = st.text_input("模型名称", value="Llama-7B")
    batch_size = st.number_input("Batch Size", value=8)
    params = {"model_name": model_name, "batch_size": batch_size}

elif task_option == "quant_optimize":
    model_name = st.text_input("模型名称", value="Qwen-14B")
    params = {"model_name": model_name}

else:
    question = st.text_input("输入问题", value="什么是AI效率优化？")
    params = {"question": question}

# 点击执行：Agent调用MCP→Skills
if st.button("🚀 执行Agent任务"):
    with st.spinner("Agent执行中..."):
        # 最终调用：一行代码完成全链路
        result = agent_mcp_task(task_type=task_option, **params)
        st.success(result)