"""
诊断验证器
确保诊断结果的正确性和可靠性
提供置信度检查、多证据交叉验证、历史一致性检查
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """验证状态"""
    VALIDATED = "validated"                    # 验证通过
    LOW_CONFIDENCE = "low_confidence"          # 置信度低
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # 证据不足
    HISTORICAL_MISMATCH = "historical_mismatch"  # 历史不一致
    CONFLICTING_EVIDENCE = "conflicting_evidence"  # 证据冲突


@dataclass
class ValidationResult:
    """验证结果"""
    status: ValidationStatus
    action: str  # proceed / require_human_review / collect_more_data / flag_for_review
    confidence: float = 0.0
    evidence_count: int = 0
    message: str = ""
    suggestions: List[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

    @property
    def is_validated(self) -> bool:
        return self.status == ValidationStatus.VALIDATED


class DiagnosisValidator:
    """诊断结果验证器"""

    def __init__(
        self,
        min_confidence: float = 0.7,
        min_evidence_count: int = 2,
        historical_fault_db: Optional[Dict] = None,
    ):
        self.min_confidence = min_confidence
        self.min_evidence_count = min_evidence_count
        self.historical_fault_db = historical_fault_db or {}
        self._validation_count = 0
        self._pass_count = 0
        self._fail_count = 0

    def validate(self, diagnosis: Dict, metrics: Dict) -> ValidationResult:
        """
        验证诊断结果
        
        Args:
            diagnosis: 诊断结果
            metrics: 当前指标数据
            
        Returns:
            ValidationResult: 验证结果
        """
        self._validation_count += 1
        logger.info(f"[DiagnosisValidator] 开始验证诊断结果 (第{self._validation_count}次)")

        # 1. 置信度检查
        confidence = diagnosis.get("confidence", 0)
        if confidence < self.min_confidence:
            self._fail_count += 1
            result = ValidationResult(
                status=ValidationStatus.LOW_CONFIDENCE,
                action="require_human_review",
                confidence=confidence,
                message=f"诊断置信度 {confidence:.2f} 低于阈值 {self.min_confidence}",
                suggestions=["建议人工审查诊断结果", "收集更多指标数据"],
            )
            logger.warning(f"[DiagnosisValidator] 验证失败: {result.message}")
            return result

        # 2. 多证据交叉验证
        root_causes = diagnosis.get("root_causes", [])
        evidence_count = self._count_supporting_evidence(root_causes, metrics)
        if evidence_count < self.min_evidence_count:
            self._fail_count += 1
            result = ValidationResult(
                status=ValidationStatus.INSUFFICIENT_EVIDENCE,
                action="collect_more_data",
                confidence=confidence,
                evidence_count=evidence_count,
                message=f"支持证据数 {evidence_count} 低于阈值 {self.min_evidence_count}",
                suggestions=["补充采集相关指标", "扩大检索范围"],
            )
            logger.warning(f"[DiagnosisValidator] 验证失败: {result.message}")
            return result

        # 3. 证据冲突检查
        if self._check_conflicting_evidence(root_causes, metrics):
            self._fail_count += 1
            result = ValidationResult(
                status=ValidationStatus.CONFLICTING_EVIDENCE,
                action="flag_for_review",
                confidence=confidence,
                evidence_count=evidence_count,
                message="检测到冲突证据，诊断结果存疑",
                suggestions=["人工介入判断", "重新执行诊断"],
            )
            logger.warning(f"[DiagnosisValidator] 验证失败: {result.message}")
            return result

        # 4. 历史一致性检查
        if not self._check_historical_consistency(diagnosis):
            self._fail_count += 1
            result = ValidationResult(
                status=ValidationStatus.HISTORICAL_MISMATCH,
                action="flag_for_review",
                confidence=confidence,
                evidence_count=evidence_count,
                message="诊断结果与历史故障模式不一致",
                suggestions=["标记为新型故障", "人工确认诊断"],
            )
            logger.warning(f"[DiagnosisValidator] 验证失败: {result.message}")
            return result

        # 验证通过
        self._pass_count += 1
        result = ValidationResult(
            status=ValidationStatus.VALIDATED,
            action="proceed",
            confidence=confidence,
            evidence_count=evidence_count,
            message="诊断验证通过",
        )
        logger.info(f"[DiagnosisValidator] 验证通过: 置信度={confidence:.2f}, 证据数={evidence_count}")
        return result

    def _count_supporting_evidence(self, root_causes: List[Dict], metrics: Dict) -> int:
        """
        计算支持诊断的独立证据数量
        
        证据来源:
        - 指标异常（RSRP/SINR/丢包率等）
        - RAG 检索到的相似故障
        - 规则引擎触发
        """
        evidence_count = 0

        for cause in root_causes:
            fault_type = cause.get("fault_type", "")
            
            # 证据 1: 指标异常
            if self._check_metric_anomaly(fault_type, metrics):
                evidence_count += 1
            
            # 证据 2: RAG 检索支持
            if cause.get("rag_support", False):
                evidence_count += 1
            
            # 证据 3: 规则引擎触发
            if cause.get("rule_triggered", False):
                evidence_count += 1
            
            # 证据 4: 历史相似故障
            if cause.get("historical_similarity", 0) > 0.8:
                evidence_count += 1

        return evidence_count

    def _check_metric_anomaly(self, fault_type: str, metrics: Dict) -> bool:
        """检查指标是否异常"""
        anomaly_thresholds = {
            "weak_signal": {"rsrp": -110, "sinr": 0},
            "interference": {"sinr": -3},
            "low_throughput": {"throughput_dl": 10},  # Mbps
            "vonr_quality_degradation": {
                "rtp_packet_loss": 2,  # %
                "video_mos": 3.5,
            },
            "handover_failure": {"handover_success_rate": 95},  # %
        }

        thresholds = anomaly_thresholds.get(fault_type, {})
        for metric_name, threshold in thresholds.items():
            if metric_name in metrics:
                value = metrics[metric_name]
                # 根据指标类型判断是否异常
                if metric_name in ["rsrp", "sinr", "throughput_dl", "handover_success_rate", "video_mos"]:
                    if value < threshold:
                        return True
                elif metric_name in ["rtp_packet_loss"]:
                    if value > threshold:
                        return True

        return False

    def _check_conflicting_evidence(self, root_causes: List[Dict], metrics: Dict) -> bool:
        """检查是否存在冲突证据"""
        if len(root_causes) < 2:
            return False

        # 检查根因之间是否矛盾
        fault_types = [cause.get("fault_type", "") for cause in root_causes]
        
        # 矛盾规则库
        conflicting_rules = [
            ("weak_signal", "interference"),  # 弱信号和干扰通常不会同时出现
        ]

        for rule in conflicting_rules:
            if rule[0] in fault_types and rule[1] in fault_types:
                logger.warning(f"[DiagnosisValidator] 检测到冲突根因: {rule}")
                return True

        return False

    def _check_historical_consistency(self, diagnosis: Dict) -> bool:
        """检查历史一致性"""
        if not self.historical_fault_db:
            return True  # 无历史数据时跳过检查

        root_causes = diagnosis.get("root_causes", [])
        for cause in root_causes:
            fault_type = cause.get("fault_type", "")
            if fault_type in self.historical_fault_db:
                # 找到历史相似故障
                return True

        # 新型故障模式
        return False

    def add_historical_fault(self, fault_type: str, fault_data: Dict):
        """添加历史故障数据"""
        self.historical_fault_db[fault_type] = fault_data

    def get_validation_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return {
            "total_validations": self._validation_count,
            "pass_count": self._pass_count,
            "fail_count": self._fail_count,
            "pass_rate": self._pass_count / max(self._validation_count, 1),
        }
