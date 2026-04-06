from utils.skills import (
    ai_efficiency_calculate,
    model_quantization_optimize,
    chat_answer
)

# 技能注册表
SKILL_REGISTRY = {
    "ai_efficiency": ai_efficiency_calculate,
    "quant_optimize": model_quantization_optimize,
    "chat": chat_answer
}

def mcp_invoke(skill_name: str, **kwargs):
    if skill_name not in SKILL_REGISTRY:
        return f"❌ 未找到技能：{skill_name}"
    
    func = SKILL_REGISTRY[skill_name]
    return func(**kwargs)