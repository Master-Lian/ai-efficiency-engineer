"""
Skill 基类 - 最小抽象单元
所有原子技能必须继承此类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def skill_execution_logger(func):
    """技能执行日志装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            elapsed = time.time() - start_time
            self._log_execute(f"执行成功，耗时 {elapsed*1000:.2f}ms")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            self._log_execute(f"执行失败: {str(e)}，耗时 {elapsed*1000:.2f}ms", level="error")
            return self._build_error_result(str(e), elapsed * 1000)
    return wrapper


class BaseSkill(ABC):
    """技能基类"""

    def __init__(self):
        self._execution_count = 0
        self._total_latency_ms = 0.0
        self._error_count = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """技能描述"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行技能逻辑"""
        pass

    def __repr__(self) -> str:
        return f"<Skill: {self.name}>"

    def _log_execute(self, msg: str, level: str = "info"):
        """记录执行日志"""
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.name}] {msg}")

    def _build_result(self, status: str, **kwargs) -> Dict[str, Any]:
        """构建标准结果字典"""
        result = {
            "skill": self.name,
            "status": status,
            "execution_count": self._execution_count,
        }
        result.update(kwargs)
        return result

    def _build_error_result(self, error_msg: str, latency_ms: float = 0.0) -> Dict[str, Any]:
        """构建错误结果字典"""
        self._error_count += 1
        return {
            "skill": self.name,
            "status": "error",
            "error": error_msg,
            "latency_ms": latency_ms,
            "execution_count": self._execution_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取技能统计信息"""
        return {
            "skill_name": self.name,
            "total_executions": self._execution_count,
            "error_count": self._error_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": self._total_latency_ms / max(self._execution_count, 1),
        }

    def _track_execution(self, start_time: float):
        """跟踪执行统计"""
        self._execution_count += 1
        elapsed = (time.time() - start_time) * 1000
        self._total_latency_ms += elapsed
        return elapsed
