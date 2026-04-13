from utils.model_opt import MiniLLM, model_quantization, inference_perf_test
import torch

# ===================== MCP 技能注册表 =====================
SKILLS = {
    "create_model": MiniLLM,
    "quant_model": model_quantization,
    "test_perf": inference_perf_test
}

# ===================== Agent 核心调度 =====================
def agent_task(task: str, **kwargs):
    """
    Agent大脑：根据任务类型自动调用AI效率技能
    :param task: 任务名称
    :return: 执行结果
    """
    print(f"🤖 AI效率Agent执行任务：{task}")

    # 1. 创建模型
    if task == "create_model":
        return MiniLLM(**kwargs)

    # 2. 模型量化优化
    elif task == "quant_model":
        return model_quantization(kwargs.get("model"))

    # 3. 性能测试
    elif task == "test_perf":
        return inference_perf_test(
            model=kwargs.get("model"),
            input_tensor=kwargs.get("input")
        )

    else:
        return "❌ 未知任务"