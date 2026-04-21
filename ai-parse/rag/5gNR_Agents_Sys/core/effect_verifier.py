"""
效果验证器
验证修复操作是否达到预期效果
提供修复前后指标对比、改善程度计算、达标判断
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """验证状态"""
    SUCCESS = "success"           # 修复成功
    FAILED = "failed"             # 修复失败
    PARTIAL = "partial"           # 部分改善
    TIMEOUT = "timeout"           # 验证超时
    WORSE = "worse"               # 指标恶化


@dataclass
class Improvement:
    """改善程度"""
    rsrp_delta: float = 0.0           # dBm
    sinr_delta: float = 0.0           # dB
    packet_loss_delta: float = 0.0    # %
    mos_delta: float = 0.0            # MOS 分
    throughput_delta: float = 0.0     # Mbps
    handover_success_delta: float = 0.0  # %

    def meets_target(self, targets: Optional[Dict] = None) -> bool:
        """判断是否达到改善目标"""
        if targets is None:
            targets = {
                "rsrp_delta": 3,           # 至少改善 3dBm
                "sinr_delta": 2,           # 至少改善 2dB
                "packet_loss_delta": 1,    # 至少降低 1%
                "mos_delta": 0.5,          # 至少提升 0.5 分
            }

        # 检查关键指标
        if self.rsrp_delta < targets.get("rsrp_delta", 0):
            return False
        if self.sinr_delta < targets.get("sinr_delta", 0):
            return False
        if self.packet_loss_delta < targets.get("packet_loss_delta", 0):
            return False
        if self.mos_delta < targets.get("mos_delta", 0):
            return False

        return True

    def is_worse(self) -> bool:
        """判断指标是否恶化"""
        return (
            self.rsrp_delta < -3 or
            self.sinr_delta < -2 or
            self.packet_loss_delta < -2 or
            self.mos_delta < -0.5
        )


@dataclass
class VerificationResult:
    """验证结果"""
    status: VerificationStatus
    improvement: Optional[Improvement] = None
    action: str = ""  # close_ticket / rollback / retry / escalate
    message: str = ""
    pre_metrics: Dict = None
    post_metrics: Dict = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.pre_metrics is None:
            self.pre_metrics = {}
        if self.post_metrics is None:
            self.post_metrics = {}
        if self.suggestions is None:
            self.suggestions = []

    @property
    def is_success(self) -> bool:
        return self.status == VerificationStatus.SUCCESS


class EffectVerifier:
    """修复效果验证器"""

    def __init__(
        self,
        wait_seconds: int = 60,
        verification_targets: Optional[Dict] = None,
        max_retries: int = 2,
    ):
        self.wait_seconds = wait_seconds
        self.verification_targets = verification_targets or {
            "rsrp_delta": 3,
            "sinr_delta": 2,
            "packet_loss_delta": 1,
            "mos_delta": 0.5,
        }
        self.max_retries = max_retries
        self._verification_count = 0
        self._success_count = 0
        self._fail_count = 0

    def verify(
        self,
        device_id: str,
        action: Dict,
        pre_metrics: Dict,
        collect_metrics_func=None,
        wait_seconds: Optional[int] = None,
    ) -> VerificationResult:
        """
        验证修复效果
        
        Args:
            device_id: 设备 ID
            action: 执行的操作
            pre_metrics: 修复前指标
            collect_metrics_func: 采集指标的函数
            wait_seconds: 等待时间（秒）
            
        Returns:
            VerificationResult: 验证结果
        """
        self._verification_count += 1
        wait = wait_seconds or self.wait_seconds
        
        logger.info(
            f"[EffectVerifier] 开始验证修复效果 (设备: {device_id}, "
            f"等待: {wait}s, 第{self._verification_count}次)"
        )

        # 1. 等待指标稳定
        logger.info(f"[EffectVerifier] 等待 {wait} 秒让指标稳定...")
        time.sleep(wait)

        # 2. 采集修复后指标
        if collect_metrics_func:
            post_metrics = collect_metrics_func(device_id)
        else:
            # 模拟采集（实际项目中应调用感知智能体）
            post_metrics = self._simulate_collect(device_id, pre_metrics, action)

        # 3. 计算改善程度
        improvement = self._calculate_improvement(pre_metrics, post_metrics)

        # 4. 判断是否达标
        if improvement.meets_target(self.verification_targets):
            self._success_count += 1
            result = VerificationResult(
                status=VerificationStatus.SUCCESS,
                improvement=improvement,
                action="close_ticket",
                message="修复效果验证通过，指标改善达标",
                pre_metrics=pre_metrics,
                post_metrics=post_metrics,
                suggestions=["关闭工单", "更新知识库"],
            )
            logger.info(f"[EffectVerifier] 验证成功: {result.message}")
            return result

        # 5. 检查是否恶化
        if improvement.is_worse():
            self._fail_count += 1
            result = VerificationResult(
                status=VerificationStatus.WORSE,
                improvement=improvement,
                action="rollback",
                message="修复后指标恶化，需要回滚",
                pre_metrics=pre_metrics,
                post_metrics=post_metrics,
                suggestions=["立即回滚", "人工介入"],
            )
            logger.error(f"[EffectVerifier] 验证失败: {result.message}")
            return result

        # 6. 部分改善
        self._fail_count += 1
        result = VerificationResult(
            status=VerificationStatus.PARTIAL,
            improvement=improvement,
            action="retry",
            message="修复后部分改善，未完全达标",
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            suggestions=["尝试其他修复策略", "人工评估"],
        )
        logger.warning(f"[EffectVerifier] 验证部分成功: {result.message}")
        return result

    def _calculate_improvement(self, pre: Dict, post: Dict) -> Improvement:
        """计算修复前后指标改善程度"""
        return Improvement(
            rsrp_delta=post.get("rsrp", 0) - pre.get("rsrp", 0),
            sinr_delta=post.get("sinr", 0) - pre.get("sinr", 0),
            packet_loss_delta=pre.get("rtp_packet_loss", 0) - post.get("rtp_packet_loss", 0),
            mos_delta=post.get("video_mos", 0) - pre.get("video_mos", 0),
            throughput_delta=post.get("throughput_dl", 0) - pre.get("throughput_dl", 0),
            handover_success_delta=post.get("handover_success_rate", 0) - pre.get("handover_success_rate", 0),
        )

    def _simulate_collect(self, device_id: str, pre_metrics: Dict, action: Dict) -> Dict:
        """
        模拟采集修复后指标（用于演示和测试）
        实际项目中应调用感知智能体的指标采集功能
        """
        # 根据操作类型模拟指标改善
        action_name = action.get("tool", action.get("action", ""))
        
        post_metrics = pre_metrics.copy()
        
        if "tx_power" in action_name:
            post_metrics["rsrp"] = pre_metrics.get("rsrp", -110) + 5
            post_metrics["sinr"] = pre_metrics.get("sinr", -3) + 3
            post_metrics["rtp_packet_loss"] = max(0, pre_metrics.get("rtp_packet_loss", 5) - 2)
            post_metrics["video_mos"] = min(5, pre_metrics.get("video_mos", 2.5) + 0.8)
        elif "handover" in action_name:
            post_metrics["rtp_packet_loss"] = max(0, pre_metrics.get("rtp_packet_loss", 5) - 3)
            post_metrics["video_mos"] = min(5, pre_metrics.get("video_mos", 2.5) + 1)
            post_metrics["rsrp"] = pre_metrics.get("rsrp", -110) + 3
            post_metrics["sinr"] = pre_metrics.get("sinr", -3) + 2
        elif "icic" in action_name:
            post_metrics["sinr"] = pre_metrics.get("sinr", -3) + 4
            post_metrics["rsrp"] = pre_metrics.get("rsrp", -110) + 3
            post_metrics["rtp_packet_loss"] = max(0, pre_metrics.get("rtp_packet_loss", 5) - 1.5)
            post_metrics["video_mos"] = min(5, pre_metrics.get("video_mos", 2.5) + 0.6)
        elif "antenna" in action_name:
            post_metrics["rsrp"] = pre_metrics.get("rsrp", -110) + 4
            post_metrics["sinr"] = pre_metrics.get("sinr", -3) + 2
            post_metrics["rtp_packet_loss"] = max(0, pre_metrics.get("rtp_packet_loss", 5) - 1.5)
            post_metrics["video_mos"] = min(5, pre_metrics.get("video_mos", 2.5) + 0.6)

        return post_metrics

    def get_verification_stats(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return {
            "total_verifications": self._verification_count,
            "success_count": self._success_count,
            "fail_count": self._fail_count,
            "success_rate": self._success_count / max(self._verification_count, 1),
        }
