"""
故障检测技能
负责分析指标数据，检测异常和故障
基于阈值规则和连续丢包检测算法
支持故障关联分析和趋势预测
"""
from typing import Any, Dict, List, Optional
import logging
from core.base_skill import BaseSkill
from core.config import THRESHOLD_CONFIG

logger = logging.getLogger(__name__)


class FaultDetectSkill(BaseSkill):
    """故障检测技能 - 多维度故障检测"""

    def __init__(self):
        super().__init__()
        self._fault_history = []
        self._device_fault_count = {}

    @property
    def name(self) -> str:
        return "fault_detect"

    @property
    def description(self) -> str:
        return "分析性能指标数据，检测5G网络异常和潜在故障（弱信号、干扰、丢包等）"

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行故障检测"""
        start_time = self._track_execution_start()
        metrics = kwargs.get("metrics", {})
        device_id = kwargs.get("device_id", "unknown")

        self._log_execute(f"开始分析设备 {device_id} 指标")

        try:
            faults = []
            faults.extend(self._check_signal_quality(metrics))
            faults.extend(self._check_throughput(metrics))
            faults.extend(self._check_packet_loss(metrics))

            faults = self._correlate_faults(faults, metrics)
            faults = self._analyze_trends(faults, device_id)

            has_fault = len(faults) > 0
            severity = self._calculate_severity(faults) if has_fault else "none"

            if has_fault:
                self._device_fault_count[device_id] = self._device_fault_count.get(device_id, 0) + 1
                self._fault_history.extend(faults)

            self._log_execute(
                f"检测完成: 发现 {len(faults)} 个故障，严重等级 {severity}",
                level="warning" if has_fault else "info",
            )

            elapsed = self._track_execution(start_time)
            return self._build_result(
                status="analyzed",
                device_id=device_id,
                faults_detected=has_fault,
                fault_count=len(faults),
                severity=severity,
                faults=faults,
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = self._track_execution(start_time)
            self._log_execute(f"故障检测失败: {str(e)}", level="error")
            return self._build_error_result(str(e), elapsed)

    def _track_execution_start(self) -> float:
        import time
        return time.time()

    def _check_signal_quality(self, metrics: Dict) -> List[Dict]:
        """检查信号质量故障"""
        faults = []
        rsrp = metrics.get("rsrp", 0)
        sinr = metrics.get("sinr", 0)

        if rsrp < THRESHOLD_CONFIG.rsrp_poor:
            faults.append({
                "type": "weak_signal",
                "severity": "critical",
                "metric": "RSRP",
                "value": rsrp,
                "threshold": THRESHOLD_CONFIG.rsrp_poor,
                "description": f"RSRP过低 ({rsrp} dBm < {THRESHOLD_CONFIG.rsrp_poor} dBm)",
                "suggestion": "调整天线倾角或增加发射功率",
            })
        elif rsrp < THRESHOLD_CONFIG.rsrp_weak:
            faults.append({
                "type": "weak_signal",
                "severity": "high",
                "metric": "RSRP",
                "value": rsrp,
                "threshold": THRESHOLD_CONFIG.rsrp_weak,
                "description": f"RSRP偏低 ({rsrp} dBm < {THRESHOLD_CONFIG.rsrp_weak} dBm)",
                "suggestion": "优化站点位置或调整天线参数",
            })

        if sinr < THRESHOLD_CONFIG.sinr_poor:
            faults.append({
                "type": "interference",
                "severity": "critical",
                "metric": "SINR",
                "value": sinr,
                "threshold": THRESHOLD_CONFIG.sinr_poor,
                "description": f"SINR极低 ({sinr} dB < {THRESHOLD_CONFIG.sinr_poor} dB)",
                "suggestion": "启用ICIC干扰协调，优化PCI规划",
            })
        elif sinr < THRESHOLD_CONFIG.sinr_low:
            faults.append({
                "type": "interference",
                "severity": "medium",
                "metric": "SINR",
                "value": sinr,
                "threshold": THRESHOLD_CONFIG.sinr_low,
                "description": f"SINR偏低 ({sinr} dB < {THRESHOLD_CONFIG.sinr_low} dB)",
                "suggestion": "优化频率复用，检查邻区干扰",
            })

        return faults

    def _check_throughput(self, metrics: Dict) -> List[Dict]:
        """检查吞吐量故障"""
        faults = []
        throughput = metrics.get("dl_throughput_mbps", 0)

        if throughput < THRESHOLD_CONFIG.throughput_min:
            faults.append({
                "type": "low_throughput",
                "severity": "high",
                "metric": "DL_Throughput",
                "value": throughput,
                "threshold": THRESHOLD_CONFIG.throughput_min,
                "description": f"下行吞吐量过低 ({throughput} Mbps < {THRESHOLD_CONFIG.throughput_min} Mbps)",
                "suggestion": "检查资源调度配置，优化信道质量",
            })

        return faults

    def _check_packet_loss(self, metrics: Dict) -> List[Dict]:
        """检查丢包故障"""
        faults = []
        loss_rate = metrics.get("packet_loss_rate", 0)
        consecutive_loss = metrics.get("consecutive_loss_count", 0)

        if loss_rate > THRESHOLD_CONFIG.packet_loss_rate:
            faults.append({
                "type": "packet_loss",
                "severity": "high",
                "metric": "PacketLossRate",
                "value": loss_rate,
                "threshold": THRESHOLD_CONFIG.packet_loss_rate,
                "description": f"丢包率过高 ({loss_rate*100:.2f}% > {THRESHOLD_CONFIG.packet_loss_rate*100:.2f}%)",
                "suggestion": "检查传输链路质量，优化RTP参数",
            })

        if consecutive_loss >= THRESHOLD_CONFIG.consecutive_loss_threshold:
            faults.append({
                "type": "consecutive_packet_loss",
                "severity": "critical",
                "metric": "ConsecutiveLoss",
                "value": consecutive_loss,
                "threshold": THRESHOLD_CONFIG.consecutive_loss_threshold,
                "description": f"连续丢包次数过多 ({consecutive_loss} >= {THRESHOLD_CONFIG.consecutive_loss_threshold})",
                "suggestion": "立即检查传输链路，可能存在链路中断",
            })

        return faults

    def _correlate_faults(self, faults: List[Dict], metrics: Dict) -> List[Dict]:
        """故障关联分析 - 识别共同根因的故障"""
        if len(faults) < 2:
            return faults

        correlated_faults = []
        for fault in faults:
            fault_type = fault.get("type", "")
            related_faults = []

            if fault_type == "weak_signal":
                related_faults = [f for f in faults if f.get("type") in ["low_throughput", "interference"]]
            elif fault_type == "interference":
                related_faults = [f for f in faults if f.get("type") in ["low_throughput", "packet_loss"]]
            elif fault_type in ["low_throughput", "packet_loss"]:
                related_faults = [f for f in faults if f.get("type") in ["weak_signal", "interference"]]

            if related_faults:
                fault["correlated_with"] = [f["type"] for f in related_faults]
                fault["is_root_cause"] = fault_type in ["weak_signal", "interference"]
            else:
                fault["correlated_with"] = []
                fault["is_root_cause"] = True

            correlated_faults.append(fault)

        return correlated_faults

    def _analyze_trends(self, faults: List[Dict], device_id: str) -> List[Dict]:
        """趋势分析 - 基于历史故障数据"""
        if not faults:
            return faults

        device_count = self._device_fault_count.get(device_id, 0)
        for fault in faults:
            fault["device_fault_count"] = device_count
            if device_count > 3:
                fault["is_recurring"] = True
                fault["suggestion"] += " (频繁发生，建议彻底排查)"
            else:
                fault["is_recurring"] = False

        return faults

    def _calculate_severity(self, faults: List[Dict]) -> str:
        """计算整体严重等级"""
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        max_severity = "none"

        for fault in faults:
            fault_severity = fault.get("severity", "low")
            if severity_order.get(fault_severity, 0) > severity_order.get(max_severity, 0):
                max_severity = fault_severity

        return max_severity

    def get_fault_stats(self) -> Dict[str, Any]:
        """获取故障统计信息"""
        return {
            "total_faults_detected": len(self._fault_history),
            "devices_with_faults": len(self._device_fault_count),
            "device_fault_counts": self._device_fault_count.copy(),
        }
