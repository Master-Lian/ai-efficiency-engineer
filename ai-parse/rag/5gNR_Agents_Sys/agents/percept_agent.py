"""
感知智能体
负责采集网络指标和检测故障
实现秒级感知能力，支持 VoNR 视频质量监测
"""
from typing import Any, Dict, List
import time
import logging
from skills.metric_collect import MetricCollectSkill
from skills.fault_detect import FaultDetectSkill

logger = logging.getLogger(__name__)


class KQIMetrics:
    """KQI 指标定义 - 5G 网络关键质量指标"""
    
    # 信号质量指标
    RSRP = "rsrp"  # 参考信号接收功率 (dBm)
    RSRQ = "rsrq"  # 参考信号接收质量 (dB)
    SINR = "sinr"  # 信号干扰噪声比 (dB)
    
    # 吞吐量指标
    THROUGHPUT_DL = "throughput_dl"  # 下行吞吐量 (Mbps)
    THROUGHPUT_UL = "throughput_ul"  # 上行吞吐量 (Mbps)
    
    # VoNR 视频质量指标
    RTP_PACKET_LOSS = "rtp_packet_loss"  # RTP 丢包率 (%)
    RTP_CONSECUTIVE_LOSS = "rtp_consecutive_loss"  # 连续丢包数
    RTP_JITTER = "rtp_jitter"  # RTP 抖动 (ms)
    RTP_LATENCY = "rtp_latency"  # RTP 时延 (ms)
    VIDEO_MOS = "video_mos"  # 视频 MOS 分 (1-5)
    VOICE_EMI = "voice_emi"  # 语音 EMI 分 (0-100)
    
    # 切换相关指标
    HANDOVER_SUCCESS_RATE = "handover_success_rate"  # 切换成功率 (%)
    HANDOVER_COUNT = "handover_count"  # 切换次数


class PerceptAgent:
    """感知智能体 - 负责数据采集和故障检测"""

    def __init__(self):
        self.metric_skill = MetricCollectSkill()
        self.fault_skill = FaultDetectSkill()
        self._perception_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0

    def perceive(
        self, 
        device_id: str, 
        metric_type: str = "all",
        scenario: str = "general"
    ) -> Dict[str, Any]:
        """
        执行感知流程
        
        Args:
            device_id: 设备 ID
            metric_type: 指标类型 (all/signal/throughput/vonr/handover)
            scenario: 场景类型 (general/voNR/video/voice)
        """
        start_time = time.time()
        self._perception_count += 1

        logger.info(
            f"[PerceptAgent] 开始感知设备 {device_id} "
            f"(场景: {scenario}, 指标: {metric_type}, 第{self._perception_count}次)"
        )

        try:
            metrics_result = self.metric_skill.execute(
                device_id=device_id, 
                metric_type=metric_type,
                scenario=scenario,
            )
            
            if metrics_result.get("status") == "error":
                raise Exception(f"指标采集失败: {metrics_result.get('error', '未知错误')}")
            
            metrics = metrics_result.get("data", {})

            fault_result = self.fault_skill.execute(
                metrics=metrics, 
                device_id=device_id,
                scenario=scenario,
            )
            
            if fault_result.get("status") == "error":
                raise Exception(f"故障检测失败: {fault_result.get('error', '未知错误')}")

            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency

            result = {
                "agent": "percept",
                "device_id": device_id,
                "scenario": scenario,
                "metrics": metrics,
                "faults": fault_result.get("faults", []),
                "has_fault": fault_result.get("faults_detected", False),
                "fault_count": fault_result.get("fault_count", 0),
                "severity": fault_result.get("severity", "none"),
                "perception_latency_ms": total_latency,
                "metric_latency_ms": metrics_result.get("latency_ms", 0),
                "fault_latency_ms": fault_result.get("latency_ms", 0),
                "kqi_summary": self._build_kqi_summary(metrics),
            }

            logger.info(
                f"[PerceptAgent] 感知完成: 故障={result['has_fault']}, "
                f"严重等级={result['severity']}, "
                f"耗时={total_latency:.2f}ms"
            )

            return result
        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency
            self._error_count += 1
            
            logger.error(f"[PerceptAgent] 感知失败: {str(e)}")
            return {
                "agent": "percept",
                "device_id": device_id,
                "scenario": scenario,
                "status": "error",
                "error": str(e),
                "perception_latency_ms": total_latency,
                "has_fault": False,
                "faults": [],
            }

    def _build_kqi_summary(self, metrics: Dict) -> Dict[str, Any]:
        """构建 KQI 指标摘要"""
        summary = {}
        
        if "signal" in metrics:
            signal = metrics["signal"]
            summary["rsrp"] = signal.get("rsrp", "N/A")
            summary["sinr"] = signal.get("sinr", "N/A")
        
        if "vonr" in metrics:
            vonr = metrics["vonr"]
            summary["rtp_loss"] = vonr.get("packet_loss_rate", "N/A")
            summary["rtp_jitter"] = vonr.get("jitter", "N/A")
            summary["video_mos"] = vonr.get("video_mos", "N/A")
            summary["voice_emi"] = vonr.get("voice_emi", "N/A")
        
        if "throughput" in metrics:
            tp = metrics["throughput"]
            summary["throughput_dl"] = tp.get("downlink", "N/A")
            summary["throughput_ul"] = tp.get("uplink", "N/A")
        
        return summary

    def get_stats(self) -> Dict[str, Any]:
        """获取感知统计信息"""
        return {
            "total_perceptions": self._perception_count,
            "error_count": self._error_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": self._total_latency_ms / max(self._perception_count, 1),
            "agent_name": "PerceptAgent",
            "metric_skill_stats": self.metric_skill.get_stats(),
            "fault_skill_stats": self.fault_skill.get_fault_stats(),
        }
