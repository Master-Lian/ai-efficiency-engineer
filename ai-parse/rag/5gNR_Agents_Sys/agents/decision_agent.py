"""
决策智能体
负责基于感知结果进行诊断和决策
支持规则引擎和 LLM 推理混合决策
"""
from typing import Any, Dict, List
import time
import logging
from skills.rag_retrieve import RAGRetrieveSkill
from skills.diagnose import DiagnoseSkill

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎 - 基于 5G 运维专家经验的决策规则"""
    
    @staticmethod
    def evaluate(metrics: Dict, faults: List) -> Dict[str, Any]:
        """
        评估规则并返回决策建议
        
        规则示例:
        - 对热门景区，动态调整基站功率、切换参数
        - 对高质套餐用户，自动提升 QoS 优先级
        - 视频 MOS < 3.5，触发异频切换
        """
        rules_triggered = []
        
        for fault in faults:
            fault_type = fault.get("type", "")
            
            if fault_type == "weak_signal":
                rules_triggered.append({
                    "rule": "weak_signal_optimization",
                    "action": "increase_tx_power",
                    "params": {"power_increase_dbm": 3},
                    "priority": "high",
                })
                rules_triggered.append({
                    "rule": "handover_optimization",
                    "action": "adjust_handover_offset",
                    "params": {"offset_increase_db": 2},
                    "priority": "medium",
                })
            
            elif fault_type == "interference":
                rules_triggered.append({
                    "rule": "interference_mitigation",
                    "action": "enable_icic",
                    "params": {},
                    "priority": "high",
                })
                rules_triggered.append({
                    "rule": "pci_optimization",
                    "action": "optimize_pci",
                    "params": {},
                    "priority": "medium",
                })
            
            elif fault_type == "low_throughput":
                rules_triggered.append({
                    "rule": "throughput_optimization",
                    "action": "increase_bandwidth",
                    "params": {"bandwidth_mhz": 20},
                    "priority": "medium",
                })
            
            elif fault_type == "vonr_quality_degradation":
                rules_triggered.append({
                    "rule": "vonr_quality_optimization",
                    "action": "trigger_inter_freq_handover",
                    "params": {"target_freq": "n78"},
                    "priority": "critical",
                })
        
        return {
            "rules_triggered": rules_triggered,
            "rule_count": len(rules_triggered),
            "has_recommendations": len(rules_triggered) > 0,
        }


class DecisionAgent:
    """决策智能体 - 负责故障诊断和决策"""

    def __init__(self):
        self.rag_skill = RAGRetrieveSkill()
        self.diagnose_skill = DiagnoseSkill()
        self.rule_engine = RuleEngine()
        self._decision_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0

    def decide(
        self, 
        faults: list, 
        device_id: str = "unknown", 
        query: str = "",
        metrics: Dict = None,
        scenario: str = "general"
    ) -> Dict[str, Any]:
        """
        执行决策流程
        
        Args:
            faults: 故障列表
            device_id: 设备 ID
            query: 查询语句
            metrics: 指标数据（用于规则引擎）
            scenario: 场景类型 (general/scenic_area/stadium/high_speed_rail)
        """
        start_time = time.time()
        self._decision_count += 1

        logger.info(
            f"[DecisionAgent] 开始决策 (场景: {scenario}, "
            f"故障数: {len(faults)}, 第{self._decision_count}次)"
        )

        try:
            context_result = self.rag_skill.execute(query=query)
            
            if context_result.get("status") == "error":
                raise Exception(f"检索失败: {context_result.get('error', '未知错误')}")
            
            context = context_result.get("context", "")

            diagnose_result = self.diagnose_skill.execute(
                faults=faults,
                context=context,
                device_id=device_id,
            )
            
            if diagnose_result.get("status") == "error":
                raise Exception(f"诊断失败: {diagnose_result.get('error', '未知错误')}")

            rule_result = self.rule_engine.evaluate(metrics or {}, faults)

            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency

            root_causes = diagnose_result.get("root_causes", [])
            
            result = {
                "agent": "decision",
                "device_id": device_id,
                "scenario": scenario,
                "root_causes": root_causes,
                "report": diagnose_result.get("report", ""),
                "rule_recommendations": rule_result.get("rules_triggered", []),
                "recommendation": self._build_recommendation(root_causes, rule_result),
                "decision_latency_ms": total_latency,
                "rag_latency_ms": context_result.get("latency_ms", 0),
                "diagnose_latency_ms": diagnose_result.get("latency_ms", 0),
                "fusion_stats": context_result.get("fusion_stats", {}),
            }

            logger.info(
                f"[DecisionAgent] 决策完成: 根因={len(result['root_causes'])}个, "
                f"规则触发={rule_result.get('rule_count', 0)}个, "
                f"耗时={total_latency:.2f}ms"
            )

            return result
        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency
            self._error_count += 1
            
            logger.error(f"[DecisionAgent] 决策失败: {str(e)}")
            return {
                "agent": "decision",
                "device_id": device_id,
                "scenario": scenario,
                "status": "error",
                "error": str(e),
                "decision_latency_ms": total_latency,
                "root_causes": [],
                "report": "诊断失败，请联系运维人员",
            }

    def _build_recommendation(self, root_causes: List, rule_result: Dict) -> str:
        """构建综合决策建议"""
        if not root_causes and not rule_result.get("rules_triggered"):
            return "无需操作"

        recommendations = []
        
        if root_causes:
            recommendations.append("建议执行自愈操作")
        
        if rule_result.get("rules_triggered"):
            rule_actions = [r["action"] for r in rule_result["rules_triggered"]]
            recommendations.append(f"规则引擎建议: {', '.join(rule_actions)}")
        
        return "; ".join(recommendations)

    def get_stats(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        return {
            "total_decisions": self._decision_count,
            "error_count": self._error_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": self._total_latency_ms / max(self._decision_count, 1),
            "agent_name": "DecisionAgent",
            "rag_skill_stats": self.rag_skill.get_retrieval_stats(),
            "diagnose_skill_stats": self.diagnose_skill.get_diagnosis_stats(),
        }
