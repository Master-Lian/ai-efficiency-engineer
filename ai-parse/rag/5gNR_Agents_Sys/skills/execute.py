"""
自愈执行技能
根据诊断结果执行自动修复操作
提供完整的运维工具集，支持执行回滚和验证
"""
from typing import Any, Dict, List, Optional
import time
import logging
from core.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class SelfHealingTools:
    """自愈执行工具集"""

    @staticmethod
    def adjust_antenna_tilt(device_id: str, tilt_angle: float, old_tilt: float = 0.0) -> Dict[str, Any]:
        """调整天线倾角"""
        return {
            "action": "adjust_antenna_tilt",
            "target": device_id,
            "params": {"tilt_angle": tilt_angle},
            "status": "success",
            "message": f"天线倾角已调整为 {tilt_angle} 度",
            "rollback_params": {"tilt_angle": old_tilt},
        }

    @staticmethod
    def increase_tx_power(device_id: str, power_dbm: float, old_power: float = 40.0) -> Dict[str, Any]:
        """增加发射功率"""
        return {
            "action": "increase_tx_power",
            "target": device_id,
            "params": {"power_dbm": power_dbm},
            "status": "success",
            "message": f"发射功率已调整为 {power_dbm} dBm",
            "rollback_params": {"power_dbm": old_power},
        }

    @staticmethod
    def optimize_pci(device_id: str, new_pci: int, old_pci: int = 0) -> Dict[str, Any]:
        """优化 PCI 配置"""
        return {
            "action": "optimize_pci",
            "target": device_id,
            "params": {"new_pci": new_pci, "old_pci": old_pci},
            "status": "success",
            "message": f"PCI 已更新为 {new_pci}",
            "rollback_params": {"new_pci": old_pci, "old_pci": new_pci},
        }

    @staticmethod
    def enable_icic(device_id: str) -> Dict[str, Any]:
        """启用 ICIC 干扰协调"""
        return {
            "action": "enable_icic",
            "target": device_id,
            "params": {},
            "status": "success",
            "message": "ICIC 干扰协调功能已启用",
            "rollback_params": {"action": "disable_icic"},
        }

    @staticmethod
    def adjust_resource_allocation(device_id: str, prb_ratio: float, old_ratio: float = 0.5) -> Dict[str, Any]:
        """调整资源分配"""
        return {
            "action": "adjust_resource_allocation",
            "target": device_id,
            "params": {"prb_ratio": prb_ratio, "old_ratio": old_ratio},
            "status": "success",
            "message": f"PRB 分配比例已调整为 {prb_ratio}",
            "rollback_params": {"prb_ratio": old_ratio, "old_ratio": prb_ratio},
        }

    @staticmethod
    def adjust_handover_offset(device_id: str, offset_db: float, old_offset_db: float = 0.0) -> Dict[str, Any]:
        """调整切换偏置"""
        return {
            "action": "adjust_handover_offset",
            "target": device_id,
            "params": {"offset_db": offset_db},
            "status": "success",
            "message": f"切换偏置已调整为 {offset_db} dB",
            "rollback_params": {"offset_db": old_offset_db},
        }

    @staticmethod
    def trigger_inter_freq_handover(device_id: str, target_freq: str, old_freq: str = "n78") -> Dict[str, Any]:
        """触发异频切换"""
        return {
            "action": "trigger_inter_freq_handover",
            "target": device_id,
            "params": {"target_freq": target_freq, "old_freq": old_freq},
            "status": "success",
            "message": f"已触发异频切换到 {target_freq}",
            "rollback_params": {"target_freq": old_freq, "old_freq": target_freq},
        }

    @staticmethod
    def increase_bandwidth(device_id: str, bandwidth_mhz: int, old_bw_mhz: int = 20) -> Dict[str, Any]:
        """增加带宽"""
        return {
            "action": "increase_bandwidth",
            "target": device_id,
            "params": {"bandwidth_mhz": bandwidth_mhz},
            "status": "success",
            "message": f"带宽已调整为 {bandwidth_mhz} MHz",
            "rollback_params": {"bandwidth_mhz": old_bw_mhz},
        }


class ExecuteSkill(BaseSkill):
    """自愈执行技能 - 自动化修复"""

    def __init__(self):
        super().__init__()
        self.tools = SelfHealingTools()
        self._action_history = []
        self._rollback_history = []
        self._execution_count = 0

    @property
    def name(self) -> str:
        return "execute"

    @property
    def description(self) -> str:
        return "根据诊断结果执行自动修复操作，实现网络自愈，支持回滚"

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行自愈操作"""
        start_time = self._track_execution_start()
        root_causes = kwargs.get("root_causes", [])
        device_id = kwargs.get("device_id", "unknown")
        enable_rollback = kwargs.get("enable_rollback", True)
        rule_recommendations = kwargs.get("rule_recommendations", [])

        self._log_execute(f"开始执行设备 {device_id} 自愈操作")

        try:
            actions = self._plan_actions(root_causes, device_id, rule_recommendations)
            results = self._execute_actions(actions, enable_rollback)

            success_count = sum(1 for r in results if r.get("status") == "success")
            total_count = len(results)

            self._execution_count += 1
            elapsed = self._track_execution(start_time)

            self._log_execute(
                f"自愈执行完成: {success_count}/{total_count} 个操作成功",
                level="info" if success_count == total_count else "warning",
            )

            return self._build_result(
                status="executed",
                device_id=device_id,
                actions_planned=len(actions),
                actions_executed=total_count,
                actions_succeeded=success_count,
                actions_failed=total_count - success_count,
                actions_taken=results,
                result="全部成功" if success_count == total_count else "部分成功",
                execution_time_ms=elapsed,
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = self._track_execution(start_time)
            self._log_execute(f"自愈执行失败: {str(e)}", level="error")
            return self._build_error_result(str(e), elapsed)

    def _track_execution_start(self) -> float:
        import time
        return time.time()

    def rollback_last_execution(self, device_id: str) -> Dict[str, Any]:
        """回滚最后一次执行"""
        if not self._action_history:
            return {
                "status": "no_action_to_rollback",
                "message": "没有可回滚的操作",
            }

        self._log_execute(f"开始回滚设备 {device_id} 的操作")

        rollback_results = []
        for action in reversed(self._action_history[-1]):
            rollback_params = action.get("rollback_params", {})
            if rollback_params:
                tool_name = action.get("action", "")
                target = action.get("target", "")

                tool_func = getattr(self.tools, tool_name, None)
                if tool_func:
                    result = tool_func(target, **rollback_params)
                    result["is_rollback"] = True
                    rollback_results.append(result)

        self._rollback_history.append(rollback_results)
        self._action_history.pop()

        return {
            "status": "rolled_back",
            "device_id": device_id,
            "rollback_actions": rollback_results,
        }

    def _plan_actions(
        self, 
        root_causes: List[Dict], 
        device_id: str,
        rule_recommendations: List[Dict] = None
    ) -> List[Dict]:
        """根据根因和规则推荐规划修复动作"""
        actions = []

        for cause in root_causes:
            fault_type = cause.get("fault_type", "")
            suggestion = cause.get("suggestion", "")

            if "天线" in suggestion or "倾角" in suggestion:
                actions.append({
                    "tool": "adjust_antenna_tilt",
                    "target": device_id,
                    "params": {"tilt_angle": -3.0},
                    "reason": cause.get("root_cause", ""),
                })
            elif "功率" in suggestion or "发射" in suggestion:
                actions.append({
                    "tool": "increase_tx_power",
                    "target": device_id,
                    "params": {"power_dbm": 43.0},
                    "reason": cause.get("root_cause", ""),
                })
            elif "PCI" in suggestion or "pci" in suggestion.lower():
                actions.append({
                    "tool": "optimize_pci",
                    "target": device_id,
                    "params": {"new_pci": 126, "old_pci": 0},
                    "reason": cause.get("root_cause", ""),
                })
            elif "ICIC" in suggestion or "干扰协调" in suggestion:
                actions.append({
                    "tool": "enable_icic",
                    "target": device_id,
                    "params": {},
                    "reason": cause.get("root_cause", ""),
                })
            else:
                actions.append({
                    "tool": "adjust_resource_allocation",
                    "target": device_id,
                    "params": {"prb_ratio": 0.8, "old_ratio": 0.5},
                    "reason": cause.get("root_cause", ""),
                })

        if rule_recommendations:
            for rec in rule_recommendations:
                action = rec.get("action", "")
                params = rec.get("params", {})
                if action and action not in [a["tool"] for a in actions]:
                    actions.append({
                        "tool": action,
                        "target": device_id,
                        "params": params,
                        "reason": f"规则引擎推荐: {rec.get('rule', '')}",
                    })

        return actions

    def _execute_actions(self, actions: List[Dict], enable_rollback: bool = True) -> List[Dict]:
        """执行修复动作"""
        results = []
        start_time = time.time()

        for action in actions:
            tool_name = action.get("tool", "")
            target = action.get("target", "")
            params = action.get("params", {})

            tool_func = getattr(self.tools, tool_name, None)
            if tool_func:
                result = tool_func(target, **params)
            else:
                result = {
                    "action": tool_name,
                    "target": target,
                    "status": "error",
                    "message": f"未知工具: {tool_name}",
                }

            result["reason"] = action.get("reason", "")
            result["enable_rollback"] = enable_rollback
            results.append(result)

        self._action_history.append(results)
        self._last_execution_time = (time.time() - start_time) * 1000
        return results

    def _get_execution_time(self) -> float:
        """获取执行耗时"""
        return getattr(self, "_last_execution_time", 0.0)

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "total_executions": self._execution_count,
            "total_rollbacks": len(self._rollback_history),
            "action_history_count": len(self._action_history),
        }
