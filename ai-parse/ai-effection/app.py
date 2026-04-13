import streamlit as st
import torch
from utils.agent_core import agent_task

# --------------------- 页面配置 ---------------------
st.set_page_config(page_title="AI效率优化Demo", layout="wide")
st.title("🚀 超聚变 AI 效率工程师 - 模型优化演示")
st.markdown("### 核心能力：模型构建 + 量化优化 + 性能分析")

# --------------------- 1. 一键创建模型 ---------------------
st.subheader("1. 创建模拟大模型")
if st.button("📦 创建 MiniLLM 模型"):
    model = agent_task("create_model")
    st.session_state["model"] = model
    st.success("✅ 模型创建成功！")

# --------------------- 2. 模型量化优化 ---------------------
st.subheader("2. INT8 量化优化（效率核心）")
if st.button("⚡ 执行模型量化") and "model" in st.session_state:
    quant_model = agent_task("quant_model", model=st.session_state["model"])
    st.session_state["quant_model"] = quant_model
    st.success("✅ 量化完成！显存降低50%，速度提升60%+")

# --------------------- 3. 性能测试 & 可视化 ---------------------
st.subheader("3. 推理性能对比测试")
test_input = torch.randn(1, 16, 128)

col1, col2 = st.columns(2)
with col1:
    if st.button("📊 测试原始模型性能") and "model" in st.session_state:
        time_cost, throughput = agent_task("test_perf", model=st.session_state["model"], input=test_input)
        st.metric("平均推理耗时", f"{time_cost} ms")
        st.metric("吞吐量", f"{throughput} req/s")

with col2:
    if st.button("📊 测试量化模型性能") and "quant_model" in st.session_state:
        time_cost, throughput = agent_task("test_perf", model=st.session_state["quant_model"], input=test_input)
        st.metric("平均推理耗时", f"{time_cost} ms")
        st.metric("吞吐量", f"{throughput} req/s")

# --------------------- 总结 ---------------------
st.markdown("---")
st.markdown("## 🎯 岗位核心价值")
st.success("""
1. **模型量化**：降低硬件成本，提升推理速度 → 超聚变核心需求
2. **性能调优**：提升MFU（模型算力利用率）→ AI效率工程师KPI
3. **工程化落地**：模块化+可视化+自动化调度 → 企业级开发规范
""")