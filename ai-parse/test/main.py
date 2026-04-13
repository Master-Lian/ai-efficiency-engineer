import torch
import torch.nn as nn
# 模拟简易Transformer层（对标大模型核心结构）
class MiniTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=128, num_heads=2)
        self.linear = nn.Linear(128, 128)
    def forward(self, x):
        x, _ = self.attn(x, x, x)
        x = self.linear(x)
        return x

# 测试推理性能
model = MiniTransformer()
x = torch.randn(10, 32, 128)  # 模拟输入

# 性能 profiling
with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU]) as p:
    for _ in range(10):
        model(x)
print(p.key_averages().table(sort_by="cpu_time_total", row_limit=5))