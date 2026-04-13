from utils.model_opt import MiniLLM, model_quantization, inference_perf_test
import torch

# 1. 初始化模型
model = MiniLLM()
quant_model = model_quantization(model)

# 2. 构造输入
test_input = torch.randn(1, 16, 128)  # batch=1, 序列长度=16

# 3. 测试性能
quant_time, quant_throughput = inference_perf_test(quant_model, test_input)
raw_time, raw_throughput = inference_perf_test(model, test_input)

# 4. 打印结果
print("="*50)
print("AI模型效率测试报告")
print("="*50)
print(f"原始模型 | 平均耗时: {raw_time}ms | 吞吐量: {raw_throughput} req/s")
print(f"量化模型 | 平均耗时: {quant_time}ms | 吞吐量: {quant_throughput} req/s")
print(f"✅ 优化效果：耗时降低 {round((raw_time-quant_time)/raw_time*100)}%")