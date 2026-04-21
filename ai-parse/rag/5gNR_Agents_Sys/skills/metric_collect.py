"""
指标采集技能
负责从5G网络设备采集性能指标数据
采用环形缓冲区 + 内存池优化性能
"""
from typing import Any, Dict, List, Optional
from collections import deque
import time
import logging
from core.base_skill import BaseSkill
from core.config import PERFORMANCE_CONFIG

logger = logging.getLogger(__name__)


class RingBuffer:
    """环形缓冲区 - 固定大小，避免动态内存分配"""

    def __init__(self, max_size: int = 1000):
        self.buffer = deque(maxlen=max_size)
        self.max_size = max_size

    def push(self, item: Any):
        """添加数据到缓冲区"""
        if not isinstance(item, dict):
            raise ValueError("缓冲区只接受字典类型数据")
        self.buffer.append(item)

    def get_all(self) -> List[Any]:
        """获取所有数据"""
        return list(self.buffer)

    def get_recent(self, n: int) -> List[Any]:
        """获取最近n条数据"""
        items = list(self.buffer)
        return items[-n:] if len(items) >= n else items

    def get_by_time_range(self, start_time: float, end_time: float) -> List[Any]:
        """按时间范围获取数据"""
        return [
            item for item in self.buffer
            if start_time <= item.get("timestamp", 0) <= end_time
        ]

    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()

    def __len__(self) -> int:
        return len(self.buffer)

    @property
    def is_full(self) -> bool:
        return len(self.buffer) == self.max_size


class MemoryPool:
    """内存池 - 预分配对象，减少 GC 开销"""

    def __init__(self, pool_size: int = 500):
        self.pool = [{} for _ in range(pool_size)]
        self.available = list(range(pool_size))
        self.pool_size = pool_size
        self._acquire_count = 0
        self._release_count = 0

    def acquire(self) -> Dict:
        """从池中获取对象"""
        if not self.available:
            return {}
        idx = self.available.pop()
        self._acquire_count += 1
        return self.pool[idx]

    def release(self, obj: Dict):
        """释放对象回池"""
        obj.clear()
        self._release_count += 1
        self.available.append(id(obj) % self.pool_size)

    def get_stats(self) -> Dict[str, Any]:
        """获取内存池统计"""
        return {
            "pool_size": self.pool_size,
            "available": len(self.available),
            "in_use": self.pool_size - len(self.available),
            "acquire_count": self._acquire_count,
            "release_count": self._release_count,
        }


class MetricCollectSkill(BaseSkill):
    """指标采集技能 - KQI 指标实时计算"""

    def __init__(self):
        super().__init__()
        self._buffer = RingBuffer(PERFORMANCE_CONFIG.ring_buffer_size)
        self._pool = MemoryPool(PERFORMANCE_CONFIG.memory_pool_size)
        self._last_collect_time = 0.0
        self._device_metrics = {}

    @property
    def name(self) -> str:
        return "metric_collect"

    @property
    def description(self) -> str:
        return "采集5G网络设备性能指标，包括RSRP、SINR、吞吐量、丢包率等KQI指标"

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行指标采集"""
        start_time = time.time()
        device_id = kwargs.get("device_id", "unknown")
        metric_type = kwargs.get("metric_type", "all")
        raw_data = kwargs.get("raw_data", None)

        self._log_execute(f"开始采集设备 {device_id} 指标")

        try:
            if raw_data:
                self._buffer.push(raw_data)

            metrics = self._collect_metrics(device_id, metric_type)

            self._device_metrics[device_id] = metrics
            self._last_collect_time = time.time()

            elapsed = self._track_execution(start_time)
            self._log_execute(f"指标采集完成，耗时 {elapsed:.2f}ms")

            return self._build_result(
                status="collected",
                device_id=device_id,
                metric_type=metric_type,
                data=metrics,
                latency_ms=elapsed,
                buffer_size=len(self._buffer),
            )
        except Exception as e:
            elapsed = self._track_execution(start_time)
            self._log_execute(f"指标采集失败: {str(e)}", level="error")
            return self._build_error_result(str(e), elapsed)

    def _collect_metrics(self, device_id: str, metric_type: str) -> Dict[str, Any]:
        """采集指标数据"""
        metrics = {}

        if metric_type in ("all", "signal"):
            metrics.update(self._collect_signal_metrics(device_id))

        if metric_type in ("all", "throughput"):
            metrics.update(self._collect_throughput_metrics(device_id))

        if metric_type in ("all", "packet_loss"):
            metrics.update(self._collect_packet_loss_metrics(device_id))

        metrics["timestamp"] = time.time()
        return metrics

    def _collect_signal_metrics(self, device_id: str) -> Dict[str, float]:
        """采集信号质量指标"""
        return {
            "rsrp": -85.0,
            "rsrq": -10.0,
            "sinr": 12.5,
            "rssi": -70.0,
        }

    def _collect_throughput_metrics(self, device_id: str) -> Dict[str, float]:
        """采集吞吐量指标"""
        return {
            "dl_throughput_mbps": 150.0,
            "ul_throughput_mbps": 50.0,
            "latency_ms": 15.0,
            "jitter_ms": 3.0,
        }

    def _collect_packet_loss_metrics(self, device_id: str) -> Dict[str, Any]:
        """采集丢包指标"""
        recent_data = self._buffer.get_recent(100)
        seq_numbers = [d.get("seq", 0) for d in recent_data if "seq" in d]

        loss_rate = self._calculate_loss_rate(seq_numbers) if seq_numbers else 0.0
        consecutive_loss = self._detect_consecutive_loss(seq_numbers)

        return {
            "packet_loss_rate": loss_rate,
            "consecutive_loss_count": consecutive_loss,
            "total_packets": len(seq_numbers),
        }

    def _calculate_loss_rate(self, seq_numbers: List[int]) -> float:
        """计算 RTP 丢包率"""
        if len(seq_numbers) < 2:
            return 0.0

        expected = seq_numbers[0]
        lost = 0
        total = len(seq_numbers) - 1

        for seq in seq_numbers[1:]:
            gap = seq - expected
            if gap > 1:
                lost += gap - 1
            expected = seq

        return lost / (total + lost) if (total + lost) > 0 else 0.0

    def _detect_consecutive_loss(self, seq_numbers: List[int]) -> int:
        """检测连续丢包次数"""
        if len(seq_numbers) < 2:
            return 0

        consecutive = 0
        max_consecutive = 0

        for i in range(1, len(seq_numbers)):
            if seq_numbers[i] - seq_numbers[i - 1] > 1:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        return max_consecutive

    def get_device_metrics(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取指定设备的最新指标"""
        return self._device_metrics.get(device_id)

    def get_buffer_stats(self) -> Dict[str, Any]:
        """获取缓冲区统计"""
        return {
            "buffer_size": len(self._buffer),
            "is_full": self._buffer.is_full,
            "memory_pool": self._pool.get_stats(),
        }
