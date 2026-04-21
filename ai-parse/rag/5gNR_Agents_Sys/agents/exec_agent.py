"""
执行智能体
负责执行自愈操作
支持回滚和验证
"""
from typing import Any, Dict, List
import time
import logging
from skills.execute import ExecuteSkill

logger = logging.getLogger(__name__)


class ExecAgent:
    """执行智能体 - 负责自愈执行"""

    def __init__(self):
        self.execute_skill = ExecuteSkill()
        self._execution_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0

    def execute(self, root_causes: list, device_id: str = "unknown", enable_rollback: bool = True) -> Dict[str, Any]:
        """执行自愈操作"""
        start_time = time.time()
        self._execution_count += 1

        logger.info(f"[ExecAgent] 开始执行自愈 (第{self._execution_count}次)")

        try:
            result = self.execute_skill.execute(
                root_causes=root_causes, 
                device_id=device_id,
                enable_rollback=enable_rollback,
            )
            
            if result.get("status") == "error":
                raise Exception(f"执行失败: {result.get('error', '未知错误')}")

            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency

            output = {
                "agent": "exec",
                "device_id": device_id,
                "actions": result.get("actions_taken", []),
                "result": result.get("result", ""),
                "status": "completed",
                "actions_planned": result.get("actions_planned", 0),
                "actions_succeeded": result.get("actions_succeeded", 0),
                "actions_failed": result.get("actions_failed", 0),
                "execution_latency_ms": total_latency,
                "skill_latency_ms": result.get("latency_ms", 0),
            }

            logger.info(
                f"[ExecAgent] 执行完成: 成功={output['actions_succeeded']}/"
                f"{output['actions_planned']}, 耗时={total_latency:.2f}ms"
            )

            return output
        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency
            self._error_count += 1
            
            logger.error(f"[ExecAgent] 执行失败: {str(e)}")
            return {
                "agent": "exec",
                "device_id": device_id,
                "status": "error",
                "error": str(e),
                "execution_latency_ms": total_latency,
                "actions_planned": 0,
                "actions_succeeded": 0,
                "actions_failed": 0,
            }

    def rollback(self, device_id: str) -> Dict[str, Any]:
        """回滚最后一次执行"""
        return self.execute_skill.rollback_last_execution(device_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "total_executions": self._execution_count,
            "error_count": self._error_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": self._total_latency_ms / max(self._execution_count, 1),
            "agent_name": "ExecAgent",
            "skill_stats": self.execute_skill.get_execution_stats(),
        }
