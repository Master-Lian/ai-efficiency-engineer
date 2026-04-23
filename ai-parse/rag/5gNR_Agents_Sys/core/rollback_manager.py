"""
回滚管理器
确保执行失败后能够安全回滚到执行前状态
提供参数快照、逆序回滚、回滚验证
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class RollbackStatus(Enum):
    """回滚状态"""
    SUCCESS = "success"              # 回滚成功
    FAILED = "failed"                # 回滚失败
    NO_SNAPSHOT = "no_snapshot"      # 无快照
    PARTIAL = "partial"              # 部分回滚


@dataclass
class RollbackResult:
    """回滚结果"""
    status: RollbackStatus
    device_id: str = ""
    restored_params: Dict = field(default_factory=dict)
    failed_params: List[str] = field(default_factory=list)
    message: str = ""
    rollback_time_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status == RollbackStatus.SUCCESS


class RollbackManager:
    """回滚管理器"""

    def __init__(self):
        self._snapshots: Dict[str, Dict] = {}  # device_id -> 参数快照
        self._action_history: Dict[str, List[Dict]] = {}  # device_id -> 操作历史
        self._rollback_count = 0
        self._success_count = 0
        self._fail_count = 0

    def snapshot_before_action(self, device_id: str, params: Dict):
        """
        执行前保存参数快照
        
        Args:
            device_id: 设备 ID
            params: 当前参数值
        """
        if device_id not in self._snapshots:
            self._snapshots[device_id] = {}
        
        # 保存当前参数（覆盖式保存，保留最新快照）
        self._snapshots[device_id].update(params)
        logger.info(f"[RollbackManager] 保存设备 {device_id} 参数快照: {list(params.keys())}")

    def record_action(self, device_id: str, action: Dict):
        """
        记录执行的操作
        
        Args:
            device_id: 设备 ID
            action: 执行的操作
        """
        if device_id not in self._action_history:
            self._action_history[device_id] = []
        
        self._action_history[device_id].append(action)
        logger.info(f"[RollbackManager] 记录设备 {device_id} 操作: {action.get('tool', 'unknown')}")

    def rollback(self, device_id: str, restore_func=None) -> RollbackResult:
        """
        回滚到执行前状态
        
        Args:
            device_id: 设备 ID
            restore_func: 恢复参数的函数
            
        Returns:
            RollbackResult: 回滚结果
        """
        self._rollback_count += 1
        start_time = time.time()
        
        logger.info(f"[RollbackManager] 开始回滚设备 {device_id} (第{self._rollback_count}次)")

        # 1. 检查是否有快照
        if device_id not in self._snapshots:
            self._fail_count += 1
            result = RollbackResult(
                status=RollbackStatus.NO_SNAPSHOT,
                device_id=device_id,
                message=f"设备 {device_id} 无参数快照，无法回滚",
            )
            logger.error(f"[RollbackManager] 回滚失败: {result.message}")
            return result

        snapshot = self._snapshots[device_id]

        # 2. 获取操作历史（逆序）
        actions = self._action_history.get(device_id, [])
        if not actions:
            self._fail_count += 1
            result = RollbackResult(
                status=RollbackStatus.NO_SNAPSHOT,
                device_id=device_id,
                message=f"设备 {device_id} 无操作历史，无需回滚",
            )
            logger.info(f"[RollbackManager] 无需回滚: {result.message}")
            return result

        # 3. 按逆序回滚（后执行的先回滚）
        restored_params = {}
        failed_params = []

        for action in reversed(actions):
            action_name = action.get("tool", action.get("action", ""))
            rollback_params = action.get("rollback_params", {})
            
            if rollback_params:
                # 使用回滚参数
                if restore_func:
                    success = restore_func(device_id, action_name, rollback_params)
                else:
                    success = self._simulate_restore(device_id, action_name, rollback_params)
                
                if success:
                    restored_params.update(rollback_params)
                else:
                    failed_params.append(action_name)
            else:
                # 使用快照恢复
                param_name = self._get_param_name(action_name)
                if param_name and param_name in snapshot:
                    original_value = snapshot[param_name]
                    if restore_func:
                        success = restore_func(device_id, action_name, {param_name: original_value})
                    else:
                        success = self._simulate_restore(device_id, action_name, {param_name: original_value})
                    
                    if success:
                        restored_params[param_name] = original_value
                    else:
                        failed_params.append(param_name)

        # 4. 清理快照和操作历史
        if device_id in self._snapshots:
            del self._snapshots[device_id]
        if device_id in self._action_history:
            del self._action_history[device_id]

        rollback_time = (time.time() - start_time) * 1000

        # 5. 判断回滚结果
        if not failed_params:
            self._success_count += 1
            result = RollbackResult(
                status=RollbackStatus.SUCCESS,
                device_id=device_id,
                restored_params=restored_params,
                message="回滚成功，所有参数已恢复",
                rollback_time_ms=rollback_time,
            )
            logger.info(f"[RollbackManager] 回滚成功: 耗时 {rollback_time:.2f}ms")
        else:
            self._fail_count += 1
            result = RollbackResult(
                status=RollbackStatus.PARTIAL,
                device_id=device_id,
                restored_params=restored_params,
                failed_params=failed_params,
                message=f"部分回滚成功，失败参数: {failed_params}",
                rollback_time_ms=rollback_time,
            )
            logger.warning(f"[RollbackManager] 回滚部分成功: {result.message}")

        return result

    def clear_snapshot(self, device_id: str):
        """清理指定设备的快照"""
        if device_id in self._snapshots:
            del self._snapshots[device_id]
        if device_id in self._action_history:
            del self._action_history[device_id]
        logger.info(f"[RollbackManager] 清理设备 {device_id} 快照")

    def get_snapshot(self, device_id: str) -> Optional[Dict]:
        """获取指定设备的快照"""
        return self._snapshots.get(device_id)

    def _get_param_name(self, action_name: str) -> Optional[str]:
        """根据操作名称获取参数名称"""
        param_mapping = {
            "adjust_antenna_tilt": "antenna_tilt",
            "increase_tx_power": "tx_power",
            "optimize_pci": "pci",
            "adjust_handover_offset": "handover_offset",
            "adjust_resource_allocation": "prb_ratio",
        }
        return param_mapping.get(action_name)

    def _simulate_restore(self, device_id: str, action_name: str, params: Dict) -> bool:
        """模拟参数恢复（用于演示和测试）"""
        logger.info(f"[RollbackManager] 模拟恢复设备 {device_id} 参数: {params}")
        return True  # 模拟总是成功

    def get_rollback_stats(self) -> Dict[str, Any]:
        """获取回滚统计信息"""
        return {
            "total_rollbacks": self._rollback_count,
            "success_count": self._success_count,
            "fail_count": self._fail_count,
            "success_rate": self._success_count / max(self._rollback_count, 1),
            "active_snapshots": len(self._snapshots),
        }
