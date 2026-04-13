import torch
import torch.nn as nn
import time

# --------------------- 1. 构建模拟大模型（Transformer核心结构） ---------------------
class MiniLLM(nn.Module):
    """模拟轻量级大模型，用于效率测试"""
    def __init__(self, embed_dim=128, num_heads=2):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.linear1 = nn.Linear(embed_dim, embed_dim * 2)
        self.linear2 = nn.Linear(embed_dim * 2, embed_dim)
        self.relu = nn.ReLU()

    def forward(self, x):
        x, _ = self.attn(x, x, x)
        x = self.relu(self.linear1(x))
        x = self.linear2(x)
        return x

# --------------------- 2. 模型量化优化（核心效率能力） ---------------------
def model_quantization(model: nn.Module) -> nn.Module:
    """
    动态量化：降低显存占用 + 提升推理速度
    返回：量化后的模型
    """
    model.eval()
    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {nn.Linear},  # 只量化线性层
        dtype=torch.qint8
    )
    return quantized_model

# --------------------- 3. 推理性能测试 ---------------------
def inference_perf_test(model: nn.Module, input_tensor, test_times=10):
    """
    测试模型推理性能
    返回：平均耗时(ms)、吞吐量
    """
    with torch.no_grad():
        # 预热
        model(input_tensor)
        
        # 正式测试
        start = time.time()
        for _ in range(test_times):
            model(input_tensor)
        total_time = time.time() - start

    avg_time = (total_time / test_times) * 1000  # 转毫秒
    throughput = test_times / total_time         # 吞吐量
    return round(avg_time, 2), round(throughput, 2)