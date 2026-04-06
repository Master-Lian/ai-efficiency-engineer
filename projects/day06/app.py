import streamlit as st
import os
from utils.ai_tools import ai_summarize
from utils.rag_core import rag_ask
from utils.agent_core import agent_task

# 页面配置
st.set_page_config(page_title="AI 效率工作台", page_icon="🤖", layout="wide")
st.title("🤖 AI 效率工程师 - 全功能可视化平台")

# 侧边栏菜单
menu = st.sidebar.selectbox(
    "选择功能",
    ["📝 AI 文本总结", "❓ RAG 知识库问答", "🧠 AI 智能体"]
)

# --------------------------
# 功能 1：AI 批量总结
# --------------------------
if menu == "📝 AI 文本总结":
    st.header("📝 文本文件一键总结")
    uploaded = st.file_uploader("上传 TXT 文件", type="txt")
    
    if uploaded:
        content = uploaded.read().decode("utf-8")
        st.text_area("文件内容", content, height=200)
        
        if st.button("开始总结"):
            with st.spinner("AI 处理中..."):
                result = ai_summarize(content)
            st.success("总结完成！")
            st.markdown(result)

# --------------------------
# 功能 2：RAG 知识库问答
# --------------------------
elif menu == "❓ RAG 知识库问答":
    st.header("❓ 本地知识库智能问答")
    question = st.text_input("输入你的问题")
    
    if st.button("查询答案"):
        with st.spinner("检索中..."):
            ans = rag_ask(question)
        st.info(ans)

# --------------------------
# 功能 3：AI 智能体
# --------------------------
elif menu == "🧠 AI 智能体":
    st.header("🧠 AI 智能体 - 自主完成任务")
    task = st.text_input("输入任务（如：总结AI学习知识点、写一段工作计划）")
    
    if st.button("执行任务"):
        with st.spinner("智能体执行中..."):
            res = agent_task(task)
        st.success("任务完成！")
        st.markdown(res)

st.sidebar.markdown("---")
st.sidebar.success("✅ 所有功能安全运行")

# 程序运行：streamlit run app.py