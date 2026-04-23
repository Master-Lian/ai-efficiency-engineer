"""
安全检查器
确保执行操作的安全性和合规性
提供风险等级评估、参数边界检查、维护窗口验证
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OperationRiskLevel(Enum):
    """操作风险等级"""
    LOW = "low"           # 低风险：调整日志级别、查询状态
    MEDIUM = "medium"     # 中风险：调整切换参数、功率微调
    HIGH = "high"         # 高风险：复位基带板、PCI 变更
    CRITICAL = "critical" #  critical：核心网配置变更、基站重启


@dataclass
class SafetyResult:
    """安全检查结果"""
    approved: bool
    reason: str = ""
    risk_level: OperationRiskLevel = OperationRiskLevel.LOW
    require_approval: bool = False
    suggestions: List[str] = field(default_factory=list)


class ChangeBoundary:
    """变更边界限制"""
    
    # 参数安全范围
    SAFE_RANGES = {
        "tx_power": {"min": 30, "max": 46, "unit": "dBm"},
        "handover_offset": {"min": -6, "max": 6, "unit": "dB"},
        "antenna_tilt": {"min": -10, "max": 10, "unit": "度"},
        "pci": {"min": 0, "max": 503, "unit": ""},
        "prb_ratio": {"min": 0.1, "max": 0.9, "unit": ""},
    }
    
    # 单次变更幅度限制（避免激进调整）
    MAX_DELTA = {
        "tx_power": 3,           # dBm
        "handover_offset": 2,    # dB
        "antenna_tilt": 3,       # 度
        "prb_ratio": 0.2,        # 比例
    }


class SafetyChecker:
    """操作安全检查器"""

    def __init__(
        self,
        maintenance_windows: Optional[List[Dict]] = None,
        require_approval_for_high: bool = True,
    ):
        self.maintenance_windows = maintenance_windows or []
        self.require_approval_for_high = require_approval_for_high
        self.change_boundary = ChangeBoundary()
        self._check_count = 0
        self._pass_count = 0
        self._reject_count = 0

    def check_before_execute(self, action: Dict, current_params: Optional[Dict] = None) -> SafetyResult:
        """
        执行前安全检查
        
        Args:
            action: 待执行的操作
            current_params: 当前参数值（用于计算变更幅度）
            
        Returns:
            SafetyResult: 安全检查结果
        """
        self._check_count += 1
        action_name = action.get("tool", action.get("action", "unknown"))
        
        logger.info(f"[SafetyChecker] 开始安全检查: {action_name} (第{self._check_count}次)")

        # 1. 评估风险等级
        risk_level = self._assess_risk(action)

        # 2. critical 操作必须人工审批
        if risk_level == OperationRiskLevel.CRITICAL:
            self._reject_count += 1
            result = SafetyResult(
                approved=False,
                reason="critical 操作需要人工审批",
                risk_level=risk_level,
                require_approval=True,
                suggestions=["提交工单申请", "等待运维主管审批"],
            )
            logger.warning(f"[SafetyChecker] 检查拒绝: {result.reason}")
            return result

        # 3. 高风险操作需要二次确认
        if risk_level == OperationRiskLevel.HIGH:
            if self.require_approval_for_high:
                self._reject_count += 1
                result = SafetyResult(
                    approved=False,
                    reason="高风险操作需要人工审批",
                    risk_level=risk_level,
                    require_approval=True,
                    suggestions=["提交工单申请", "确认操作必要性"],
                )
                logger.warning(f"[SafetyChecker] 检查拒绝: {result.reason}")
                return result

            # 二次验证（自动）
            if not self._double_check(action):
                self._reject_count += 1
                result = SafetyResult(
                    approved=False,
                    reason="二次验证未通过",
                    risk_level=risk_level,
                    suggestions=["重新评估操作参数", "人工确认"],
                )
                logger.warning(f"[SafetyChecker] 检查拒绝: {result.reason}")
                return result

        # 4. 检查参数安全范围
        param_check = self._validate_params(action, current_params)
        if not param_check["valid"]:
            self._reject_count += 1
            result = SafetyResult(
                approved=False,
                reason=param_check["reason"],
                risk_level=risk_level,
                suggestions=param_check.get("suggestions", []),
            )
            logger.warning(f"[SafetyChecker] 检查拒绝: {result.reason}")
            return result

        # 5. 检查是否在维护窗口
        if self.maintenance_windows:
            if not self._is_maintenance_window():
                self._reject_count += 1
                result = SafetyResult(
                    approved=False,
                    reason="非维护窗口禁止执行",
                    risk_level=risk_level,
                    suggestions=[f"请在维护窗口内执行: {self.maintenance_windows}"],
                )
                logger.warning(f"[SafetyChecker] 检查拒绝: {result.reason}")
                return result

        # 检查通过
        self._pass_count += 1
        result = SafetyResult(
            approved=True,
            reason="安全检查通过",
            risk_level=risk_level,
        )
        logger.info(f"[SafetyChecker] 检查通过: 风险等级={risk_level.value}")
        return result

    def check_batch_actions(self, actions: List[Dict], current_params: Optional[Dict] = None) -> List[SafetyResult]:
        """批量检查多个操作"""
        results = []
        for action in actions:
            result = self.check_before_execute(action, current_params)
            results.append(result)
            if not result.approved:
                break  # 有一个不通过就停止
        return results

    def _assess_risk(self, action: Dict) -> OperationRiskLevel:
        """评估操作风险等级"""
        action_name = action.get("tool", action.get("action", ""))
        
        risk_mapping = {
            "adjust_antenna_tilt": OperationRiskLevel.MEDIUM,
            "increase_tx_power": OperationRiskLevel.MEDIUM,
            "optimize_pci": OperationRiskLevel.HIGH,
            "enable_icic": OperationRiskLevel.LOW,
            "adjust_resource_allocation": OperationRiskLevel.LOW,
            "adjust_handover_offset": OperationRiskLevel.MEDIUM,
            "trigger_inter_freq_handover": OperationRiskLevel.HIGH,
            "increase_bandwidth": OperationRiskLevel.MEDIUM,
            "reset_baseband": OperationRiskLevel.CRITICAL,
            "restart_station": OperationRiskLevel.CRITICAL,
        }

        return risk_mapping.get(action_name, OperationRiskLevel.MEDIUM)

    def _double_check(self, action: Dict) -> bool:
        """二次验证"""
        # 检查操作参数是否合理
        params = action.get("params", {})
        
        # 功率调整不能超过安全上限
        if "power_dbm" in params:
            if params["power_dbm"] > 46:
                return False
        
        # 切换偏置不能过大
        if "offset_db" in params:
            if abs(params["offset_db"]) > 6:
                return False
        
        return True

    def _validate_params(self, action: Dict, current_params: Optional[Dict] = None) -> Dict:
        """验证参数是否在安全范围内"""
        params = action.get("params", {})
        action_name = action.get("tool", action.get("action", ""))
        
        # 参数映射
        param_mapping = {
            "increase_tx_power": {"power_dbm": "tx_power"},
            "adjust_handover_offset": {"offset_db": "handover_offset"},
            "adjust_antenna_tilt": {"tilt_angle": "antenna_tilt"},
            "optimize_pci": {"new_pci": "pci"},
            "adjust_resource_allocation": {"prb_ratio": "prb_ratio"},
        }

        mapping = param_mapping.get(action_name, {})
        
        for param_key, boundary_key in mapping.items():
            if param_key not in params:
                continue
            
            new_value = params[param_key]
            
            # 检查安全范围
            if boundary_key in self.change_boundary.SAFE_RANGES:
                safe_range = self.change_boundary.SAFE_RANGES[boundary_key]
                if not (safe_range["min"] <= new_value <= safe_range["max"]):
                    return {
                        "valid": False,
                        "reason": f"参数 {param_key}={new_value} 超出安全范围 [{safe_range['min']}, {safe_range['max']}]",
                        "suggestions": [f"调整参数到安全范围内"],
                    }
            
            # 检查变更幅度
            if current_params and boundary_key in current_params:
                current_value = current_params[boundary_key]
                if boundary_key in self.change_boundary.MAX_DELTA:
                    max_delta = self.change_boundary.MAX_DELTA[boundary_key]
                    delta = abs(new_value - current_value)
                    if delta > max_delta:
                        return {
                            "valid": False,
                            "reason": f"参数 {param_key} 变更幅度 {delta:.2f} 超过限制 {max_delta}",
                            "suggestions": [f"单次调整幅度不超过 {max_delta}"],
                        }

        return {"valid": True}

    def _is_maintenance_window(self) -> bool:
        """检查是否在维护窗口内"""
        if not self.maintenance_windows:
            return True  # 无限制时默认允许
        
        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        for window in self.maintenance_windows:
            start_hour = window.get("start_hour", 0)
            end_hour = window.get("end_hour", 24)
            allowed_weekdays = window.get("weekdays", [0, 1, 2, 3, 4, 5, 6])
            
            if current_weekday in allowed_weekdays:
                if start_hour <= current_hour < end_hour:
                    return True
        
        return False

    def add_maintenance_window(self, start_hour: int, end_hour: int, weekdays: List[int] = []):
        """添加维护窗口"""
        if weekdays is None:
            weekdays = [0, 1, 2, 3, 4, 5, 6]  # 全周
        
        self.maintenance_windows.append({
            "start_hour": start_hour,
            "end_hour": end_hour,
            "weekdays": weekdays,
        })

    def get_safety_stats(self) -> Dict[str, Any]:
        """获取安全检查统计信息"""
        return {
            "total_checks": self._check_count,
            "pass_count": self._pass_count,
            "reject_count": self._reject_count,
            "pass_rate": self._pass_count / max(self._check_count, 1),
        }
