"""
全局配置文件
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

BASE_DIR = Path(__file__).parent.parent

@dataclass
class ModelConfig:
    """模型配置"""
    model_name: str = "qwen-7b-lora"
    temperature: float = 0.2
    max_tokens: int = 2048
    top_p: float = 0.9
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))

    def __post_init__(self):
        """验证配置参数"""
        if not 0 <= self.temperature <= 1:
            raise ValueError(f"temperature 必须在 [0, 1] 范围内，当前值: {self.temperature}")
        if not 0 <= self.top_p <= 1:
            raise ValueError(f"top_p 必须在 [0, 1] 范围内，当前值: {self.top_p}")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens 必须大于 0，当前值: {self.max_tokens}")
        if not self.api_key:
            import warnings
            warnings.warn("DEEPSEEK_API_KEY 环境变量未设置，LLM 功能将使用占位实现")

@dataclass
class ThresholdConfig:
    """故障阈值配置"""
    rsrp_weak: float = -100.0
    rsrp_poor: float = -110.0
    sinr_low: float = 5.0
    sinr_poor: float = 0.0
    throughput_min: float = 50.0
    packet_loss_rate: float = 0.05
    consecutive_loss_threshold: int = 5

    def __post_init__(self):
        """验证阈值配置"""
        if self.rsrp_weak <= self.rsrp_poor:
            raise ValueError("rsrp_weak 必须大于 rsrp_poor")
        if self.sinr_low <= self.sinr_poor:
            raise ValueError("sinr_low 必须大于 sinr_poor")
        if self.throughput_min <= 0:
            raise ValueError("throughput_min 必须大于 0")
        if not 0 <= self.packet_loss_rate <= 1:
            raise ValueError("packet_loss_rate 必须在 [0, 1] 范围内")
        if self.consecutive_loss_threshold <= 0:
            raise ValueError("consecutive_loss_threshold 必须大于 0")

@dataclass
class PerformanceConfig:
    """性能配置"""
    ring_buffer_size: int = 1000
    memory_pool_size: int = 500
    faiss_top_k: int = 5
    bm25_top_k: int = 5
    max_rewrite_count: int = 2
    similarity_threshold: float = 0.5

    def __post_init__(self):
        """验证性能配置"""
        if self.ring_buffer_size <= 0:
            raise ValueError("ring_buffer_size 必须大于 0")
        if self.memory_pool_size <= 0:
            raise ValueError("memory_pool_size 必须大于 0")
        if self.faiss_top_k <= 0:
            raise ValueError("faiss_top_k 必须大于 0")
        if self.bm25_top_k <= 0:
            raise ValueError("bm25_top_k 必须大于 0")
        if self.max_rewrite_count <= 0:
            raise ValueError("max_rewrite_count 必须大于 0")
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("similarity_threshold 必须在 [0, 1] 范围内")

MODEL_CONFIG = ModelConfig()
THRESHOLD_CONFIG = ThresholdConfig()
PERFORMANCE_CONFIG = PerformanceConfig()

KNOWLEDGE_BASE_PATH = BASE_DIR / "data" / "5g_knowledge.md"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
