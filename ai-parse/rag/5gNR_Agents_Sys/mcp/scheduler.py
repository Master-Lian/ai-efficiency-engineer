"""
MCP 调度器
负责协调多个智能体完成复杂任务
基于 LangGraph 实现状态流转
支持异常恢复和任务重试
支持场景化工作流（VoNR/景区/高铁等）
集成四层防护机制：诊断验证→安全检查→效果验证→回滚保障
"""
from typing import Any, Dict, List
import time
import logging
from agents.percept_agent import PerceptAgent
from agents.decision_agent import DecisionAgent
from agents.exec_agent import ExecAgent
from agents.qa_agent import QAAgent
from core.diagnosis_validator import DiagnosisValidator
from core.safety_checker import SafetyChecker
from core.effect_verifier import EffectVerifier
from core.rollback_manager import RollbackManager

logger = logging.getLogger(__name__)


class WorkflowState:
    """工作流状态枚举"""
    INIT = "init"
    PERCEPT = "percept"
    DECISION = "decision"
    EXECUTE = "execute"
    COMPLETED = "completed"
    FAILED = "failed"


class MCPScheduler:
    """MCP 调度中心 - 协调多智能体工作流"""

    def __init__(self):
        self.percept = PerceptAgent()
        self.decision = DecisionAgent()
        self.exec = ExecAgent()
        self.qa = QAAgent()
        
        # 四层防护机制
        self.diagnosis_validator = DiagnosisValidator()
        self.safety_checker = SafetyChecker()
        self.effect_verifier = EffectVerifier()
        self.rollback_manager = RollbackManager()
        
        self._task_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._current_state = WorkflowState.INIT

    def run_fault_healing(
        self, 
        device_id: str, 
        max_retries: int = 2,
        scenario: str = "general",
        metric_type: str = "all"
    ) -> Dict[str, Any]:
        """
        运行故障自愈流程，支持重试和场景化配置
        
        Args:
            device_id: 设备 ID
            max_retries: 最大重试次数
            scenario: 场景类型 (general/scenic_area/stadium/high_speed_rail/vonr)
            metric_type: 指标类型 (all/signal/throughput/vonr/handover)
        """
        self._task_count += 1
        start_time = time.time()
        self._current_state = WorkflowState.INIT

        logger.info(
            f"[MCP] 开始故障自愈任务 #{self._task_count}: "
            f"设备 {device_id}, 场景 {scenario}"
        )
        print(f"\n{'='*60}")
        print(f"  故障自愈任务 #{self._task_count}: 设备 {device_id}")
        print(f"  场景: {scenario}, 指标类型: {metric_type}")
        print(f"{'='*60}")

        try:
            for attempt in range(1, max_retries + 1):
                logger.info(f"[MCP] 尝试 #{attempt}/{max_retries}")
                print(f"\n[MCP] 尝试 #{attempt}/{max_retries}")

                result = self._execute_fault_healing(device_id, scenario, metric_type)
                
                if result.get("status") != "error":
                    self._success_count += 1
                    total_latency = (time.time() - start_time) * 1000
                    result["task_id"] = self._task_count
                    result["total_latency_ms"] = total_latency
                    result["attempts"] = attempt
                    self._current_state = WorkflowState.COMPLETED

                    logger.info(f"[MCP] 故障自愈任务完成: 总耗时={total_latency:.2f}ms")
                    print(f"\n{'='*60}")
                    print(f"  任务完成: 总耗时 {total_latency:.2f}ms, 尝试次数: {attempt}")
                    print(f"{'='*60}")

                    return result

                if attempt < max_retries:
                    logger.warning(f"[MCP] 尝试 #{attempt} 失败，准备重试...")
                    print(f"\n[MCP] 尝试 #{attempt} 失败，准备重试...")
                    time.sleep(1)

            self._failure_count += 1
            total_latency = (time.time() - start_time) * 1000
            self._current_state = WorkflowState.FAILED
            
            logger.error(f"[MCP] 故障自愈任务失败: 已重试 {max_retries} 次")
            print(f"\n{'='*60}")
            print(f"  任务失败: 已重试 {max_retries} 次，总耗时 {total_latency:.2f}ms")
            print(f"{'='*60}")

            return {
                "status": "failed",
                "message": f"故障自愈失败，已重试 {max_retries} 次",
                "task_id": self._task_count,
                "total_latency_ms": total_latency,
                "attempts": max_retries,
            }
        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            self._failure_count += 1
            self._current_state = WorkflowState.FAILED
            
            logger.error(f"[MCP] 故障自愈任务异常: {str(e)}")
            return {
                "status": "error",
                "message": f"故障自愈异常: {str(e)}",
                "task_id": self._task_count,
                "total_latency_ms": total_latency,
            }

    def _execute_fault_healing(
        self, 
        device_id: str, 
        scenario: str,
        metric_type: str
    ) -> Dict[str, Any]:
        """执行故障自愈流程（集成四层防护机制）"""
        self._current_state = WorkflowState.PERCEPT
        
        # ===== 第一阶段：感知 =====
        percept_result = self.percept.perceive(
            device_id=device_id,
            metric_type=metric_type,
            scenario=scenario,
        )
        
        if percept_result.get("status") == "error":
            raise Exception(f"感知失败: {percept_result.get('error', '未知错误')}")
        
        print(f"[MCP] 感知完成: 发现故障={percept_result['has_fault']}, "
              f"耗时={percept_result['perception_latency_ms']:.2f}ms")

        if not percept_result["has_fault"]:
            logger.info("[MCP] 设备运行正常，无需处理")
            print(f"[MCP] 设备运行正常，无需处理")
            return {
                "status": "no_fault",
                "message": "设备运行正常",
                "percept": percept_result,
            }

        # ===== 第二阶段：决策 =====
        self._current_state = WorkflowState.DECISION
        
        decision_result = self.decision.decide(
            faults=percept_result["faults"],
            device_id=device_id,
            query="5G网络故障诊断",
            metrics=percept_result.get("metrics", {}),
            scenario=scenario,
        )
        
        if decision_result.get("status") == "error":
            raise Exception(f"决策失败: {decision_result.get('error', '未知错误')}")
        
        print(f"[MCP] 诊断完成: 根因={len(decision_result['root_causes'])}个, "
              f"规则触发={len(decision_result.get('rule_recommendations', []))}个, "
              f"耗时={decision_result['decision_latency_ms']:.2f}ms")
        print(f"\n{decision_result['report']}")

        # ===== 防护层 1：诊断验证 =====
        print("\n[防护层 1] 诊断验证...")
        validation_result = self.diagnosis_validator.validate(
            diagnosis=decision_result,
            metrics=percept_result.get("metrics", {}),
        )
        
        if not validation_result.is_validated:
            print(f"[防护层 1] 验证失败: {validation_result.message}")
            print(f"[防护层 1] 建议: {validation_result.suggestions}")
            return {
                "status": "validation_failed",
                "message": f"诊断验证未通过: {validation_result.message}",
                "validation": {
                    "status": validation_result.status.value,
                    "action": validation_result.action,
                    "confidence": validation_result.confidence,
                    "evidence_count": validation_result.evidence_count,
                    "suggestions": validation_result.suggestions,
                },
                "percept": percept_result,
                "decision": decision_result,
            }
        
        print(f"[防护层 1] 验证通过: 置信度={validation_result.confidence:.2f}, "
              f"证据数={validation_result.evidence_count}")

        # ===== 防护层 2：安全检查 =====
        print("\n[防护层 2] 安全检查...")
        actions = self._plan_actions_from_decision(decision_result, device_id)
        
        safety_results = self.safety_checker.check_batch_actions(
            actions=actions,
            current_params=percept_result.get("metrics", {}),
        )
        
        for i, safety_result in enumerate(safety_results):
            if not safety_result.approved:
                print(f"[防护层 2] 安全检查拒绝: {safety_result.reason}")
                print(f"[防护层 2] 建议: {safety_result.suggestions}")
                return {
                    "status": "safety_check_failed",
                    "message": f"安全检查未通过: {safety_result.reason}",
                    "safety_check": {
                        "approved": False,
                        "reason": safety_result.reason,
                        "risk_level": safety_result.risk_level.value,
                        "require_approval": safety_result.require_approval,
                        "suggestions": safety_result.suggestions,
                    },
                    "percept": percept_result,
                    "decision": decision_result,
                }
        
        print(f"[防护层 2] 安全检查通过: 所有操作风险等级合规")

        # ===== 防护层 3：执行前快照 =====
        print("\n[防护层 3] 保存执行前快照...")
        self.rollback_manager.snapshot_before_action(
            device_id=device_id,
            params=percept_result.get("metrics", {}),
        )
        print(f"[防护层 3] 快照保存完成")

        # ===== 第三阶段：执行 =====
        self._current_state = WorkflowState.EXECUTE
        
        exec_result = self.exec.execute(
            root_causes=decision_result["root_causes"],
            device_id=device_id,
            rule_recommendations=decision_result.get("rule_recommendations", []), # pyright: ignore[reportCallIssue]
        )
        
        if exec_result.get("status") == "error":
            # 执行失败，自动回滚
            print(f"\n[MCP] 执行失败，触发自动回滚...")
            rollback_result = self.rollback_manager.rollback(device_id)
            
            return {
                "status": "exec_failed_and_rolled_back",
                "message": f"执行失败: {exec_result.get('error', '未知错误')}",
                "exec": exec_result,
                "rollback": {
                    "status": rollback_result.status.value,
                    "message": rollback_result.message,
                    "restored_params": rollback_result.restored_params,
                },
                "percept": percept_result,
                "decision": decision_result,
            }
        
        print(f"\n[MCP] 执行完成: {exec_result['result']}, "
              f"耗时={exec_result['execution_latency_ms']:.2f}ms")

        # ===== 防护层 4：效果验证 =====
        print("\n[防护层 4] 效果验证...")
        pre_metrics = percept_result.get("metrics", {})
        
        verification_result = self.effect_verifier.verify(
            device_id=device_id,
            action=exec_result.get("actions_taken", [{}])[0] if exec_result.get("actions_taken") else {},
            pre_metrics=pre_metrics,
            collect_metrics_func=lambda did: self.percept.perceive(
                device_id=did, 
                metric_type=metric_type, 
                scenario=scenario
            ).get("metrics", {}),
        )
        
        if verification_result.status.value == "worse":
            # 指标恶化，自动回滚
            print(f"[防护层 4] 指标恶化，触发自动回滚...")
            rollback_result = self.rollback_manager.rollback(device_id)
            
            return {
                "status": "verification_failed_and_rolled_back",
                "message": f"效果验证失败: {verification_result.message}",
                "verification": {
                    "status": verification_result.status.value,
                    "pre_metrics": verification_result.pre_metrics,
                    "post_metrics": verification_result.post_metrics,
                    "improvement": self._improvement_to_dict(verification_result.improvement),
                },
                "rollback": {
                    "status": rollback_result.status.value,
                    "message": rollback_result.message,
                    "restored_params": rollback_result.restored_params,
                },
                "exec": exec_result,
                "percept": percept_result,
                "decision": decision_result,
            }
        
        if verification_result.status.value == "partial":
            # 部分改善，记录警告
            print(f"[防护层 4] 部分改善: {verification_result.message}")
            print(f"[防护层 4] 建议: {verification_result.suggestions}")
        
        if verification_result.is_success:
            print(f"[防护层 4] 效果验证通过: 指标改善达标")
            # 清理快照
            self.rollback_manager.clear_snapshot(device_id)

        return {
            "status": "healed",
            "percept": percept_result,
            "decision": decision_result,
            "exec": exec_result,
            "verification": {
                "status": verification_result.status.value,
                "pre_metrics": verification_result.pre_metrics,
                "post_metrics": verification_result.post_metrics,
                "improvement": self._improvement_to_dict(verification_result.improvement),
            },
            "protection_layers": {
                "diagnosis_validation": "passed",
                "safety_check": "passed",
                "snapshot": "saved",
                "effect_verification": verification_result.status.value,
            },
        }

    def _plan_actions_from_decision(self, decision_result: Dict, device_id: str) -> List[Dict]:
        """从决策结果中提取待执行操作"""
        actions = []
        
        # 从规则推荐中提取
        for rec in decision_result.get("rule_recommendations", []):
            actions.append({
                "tool": rec.get("action", ""),
                "target": device_id,
                "params": rec.get("params", {}),
            })
        
        # 从根因建议中提取
        for cause in decision_result.get("root_causes", []):
            suggestion = cause.get("suggestion", "")
            if "天线" in suggestion or "倾角" in suggestion:
                actions.append({
                    "tool": "adjust_antenna_tilt",
                    "target": device_id,
                    "params": {"tilt_angle": -3.0},
                })
            elif "功率" in suggestion or "发射" in suggestion:
                actions.append({
                    "tool": "increase_tx_power",
                    "target": device_id,
                    "params": {"power_dbm": 43.0},
                })
        
        return actions

    def _improvement_to_dict(self, improvement) -> Dict:
        """将 Improvement 对象转换为字典"""
        if improvement is None:
            return {}
        return {
            "rsrp_delta": improvement.rsrp_delta,
            "sinr_delta": improvement.sinr_delta,
            "packet_loss_delta": improvement.packet_loss_delta,
            "mos_delta": improvement.mos_delta,
            "throughput_delta": improvement.throughput_delta,
            "handover_success_delta": improvement.handover_success_delta,
        }

    def run_qa(self, question: str) -> Dict[str, Any]:
        """运行问答流程"""
        self._task_count += 1
        start_time = time.time()

        logger.info(f"[MCP] 开始问答任务 #{self._task_count}")
        print(f"\n{'='*60}")
        print(f"  问答任务 #{self._task_count}")
        print(f"{'='*60}")

        try:
            result = self.qa.answer(question)
            
            if result.get("status") == "error":
                raise Exception(f"问答失败: {result.get('error', '未知错误')}")

            total_latency = (time.time() - start_time) * 1000
            self._success_count += 1

            print(f"\n回答: {result.get('answer', '无回答')}")
            print(f"\n来源: {', '.join(result.get('sources', []))}")
            print(f"耗时: {result.get('qa_latency_ms', 0):.2f}ms")
            print(f"{'='*60}")

            result["task_id"] = self._task_count
            result["total_latency_ms"] = total_latency

            return result
        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            self._failure_count += 1
            
            logger.error(f"[MCP] 问答任务异常: {str(e)}")
            print(f"\n{'='*60}")
            print(f"  问答失败: {str(e)}")
            print(f"{'='*60}")

            return {
                "status": "error",
                "message": f"问答异常: {str(e)}",
                "task_id": self._task_count,
                "total_latency_ms": total_latency,
            }

    def rollback_last_execution(self, device_id: str) -> Dict[str, Any]:
        """回滚最后一次执行"""
        return self.exec.rollback(device_id)

    def get_current_state(self) -> str:
        """获取当前工作流状态"""
        return self._current_state

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            "total_tasks": self._task_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self._success_count / max(self._task_count, 1),
            "current_state": self._current_state,
            "percept_stats": self.percept.get_stats(),
            "decision_stats": self.decision.get_stats(),
            "exec_stats": self.exec.get_stats(),
            "qa_stats": self.qa.get_stats(),
            "protection_stats": {
                "diagnosis_validation": self.diagnosis_validator.get_validation_stats(),
                "safety_check": self.safety_checker.get_safety_stats(),
                "effect_verification": self.effect_verifier.get_verification_stats(),
                "rollback": self.rollback_manager.get_rollback_stats(),
            },
        }
