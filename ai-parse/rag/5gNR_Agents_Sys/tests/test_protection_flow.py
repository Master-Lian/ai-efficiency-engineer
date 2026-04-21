"""
集成测试 - 四层防护完整流程
覆盖正常和异常场景
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.diagnosis_validator import DiagnosisValidator, ValidationStatus
from core.safety_checker import SafetyChecker, OperationRiskLevel
from core.effect_verifier import EffectVerifier, VerificationStatus
from core.rollback_manager import RollbackManager, RollbackStatus


class TestProtectionFlow:
    """四层防护集成测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.diagnosis_validator = DiagnosisValidator(
            min_confidence=0.7,
            min_evidence_count=2,
            historical_fault_db={
                "weak_signal": {"count": 10},
                "interference": {"count": 5},
                "vonr_quality_degradation": {"count": 8},
            },
        )
        self.safety_checker = SafetyChecker(require_approval_for_high=True)
        self.effect_verifier = EffectVerifier(wait_seconds=0)
        self.rollback_manager = RollbackManager()

    def test_full_protection_flow_success(self):
        """测试：完整防护流程成功（正常场景）"""
        device_id = "test_device_001"
        scenario = "weak_signal"

        print("\n[场景 1] VoNR 视频卡顿自动处理（含四层防护）")

        # ===== 第一阶段：模拟感知 =====
        percept_result = {
            "has_fault": True,
            "faults": [{"type": "weak_signal", "severity": "high"}],
            "metrics": {
                "rsrp": -115,
                "sinr": -5,
                "rtp_packet_loss": 5.0,
                "video_mos": 2.5,
            },
        }
        print(f"  感知完成: 发现故障={percept_result['has_fault']}")

        # ===== 第二阶段：模拟决策 =====
        decision_result = {
            "confidence": 0.85,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": True,
                    "rule_triggered": True,
                    "historical_similarity": 0.9,
                }
            ],
            "actions": [
                {
                    "tool": "increase_tx_power",
                    "params": {"power_dbm": 38},
                    "rollback_params": {"tx_power": 35},
                }
            ],
        }
        print(f"  诊断完成: 置信度={decision_result['confidence']}")

        # ===== 防护层 1：诊断验证 =====
        print("  [防护层 1] 诊断验证...")
        validation_result = self.diagnosis_validator.validate(
            diagnosis=decision_result,
            metrics=percept_result["metrics"],
        )
        assert validation_result.is_validated, f"诊断验证失败: {validation_result.message}"
        print(f"  [防护层 1] 验证通过: 置信度={validation_result.confidence}")

        # ===== 防护层 2：安全检查 =====
        print("  [防护层 2] 安全检查...")
        action = decision_result["actions"][0]
        safety_result = self.safety_checker.check_before_execute(
            action=action,
            current_params=percept_result["metrics"],
        )
        assert safety_result.approved, f"安全检查失败: {safety_result.reason}"
        print(f"  [防护层 2] 安全检查通过: 风险等级={safety_result.risk_level.value}")

        # ===== 防护层 3：执行前快照 =====
        print("  [防护层 3] 保存执行前快照...")
        self.rollback_manager.snapshot_before_action(
            device_id=device_id,
            params=percept_result["metrics"],
        )
        self.rollback_manager.record_action(device_id, action)
        print("  [防护层 3] 快照保存完成")

        # ===== 第三阶段：模拟执行 =====
        print("  执行修复操作...")
        exec_result = {"status": "success", "result": "发射功率已调整"}
        print(f"  执行完成: {exec_result['result']}")

        # ===== 防护层 4：效果验证 =====
        print("  [防护层 4] 效果验证...")
        pre_metrics = percept_result["metrics"]

        def mock_collect(did):
            return {
                "rsrp": -108,
                "sinr": 2,
                "rtp_packet_loss": 1.5,
                "video_mos": 4.0,
            }

        verification_result = self.effect_verifier.verify(
            device_id=device_id,
            action=action,
            pre_metrics=pre_metrics,
            collect_metrics_func=mock_collect,
            wait_seconds=0,
        )
        assert verification_result.is_success, f"效果验证失败: {verification_result.message}"
        print(f"  [防护层 4] 效果验证通过: 指标改善达标")

        # 清理快照
        self.rollback_manager.clear_snapshot(device_id)

        print("  [PASS] 完整防护流程成功")
        print("[PASS] test_full_protection_flow_success 通过")

    def test_diagnosis_validation_failure(self):
        """测试：诊断验证失败（异常场景）"""
        device_id = "test_device_002"

        print("\n[场景 2] 诊断验证失败处理")

        # 模拟低置信度诊断
        decision_result = {
            "confidence": 0.5,
            "root_causes": [
                {
                    "fault_type": "unknown_fault",
                    "rag_support": False,
                    "rule_triggered": False,
                }
            ],
        }
        percept_result = {"metrics": {"rsrp": -110}}

        # 防护层 1：诊断验证
        print("  [防护层 1] 诊断验证...")
        validation_result = self.diagnosis_validator.validate(
            diagnosis=decision_result,
            metrics=percept_result["metrics"],
        )

        assert not validation_result.is_validated
        assert validation_result.status == ValidationStatus.LOW_CONFIDENCE
        assert validation_result.action == "require_human_review"
        print(f"  [防护层 1] 验证失败: {validation_result.message}")
        print(f"  [防护层 1] 建议: {validation_result.suggestions}")
        print("  [PASS] 诊断验证失败处理正确")
        print("[PASS] test_diagnosis_validation_failure 通过")

    def test_safety_check_failure(self):
        """测试：安全检查失败（异常场景）"""
        device_id = "test_device_003"

        print("\n[场景 3] 安全检查失败处理")

        # 模拟 critical 操作
        action = {
            "tool": "reset_baseband",
            "params": {},
        }

        # 防护层 2：安全检查
        print("  [防护层 2] 安全检查...")
        safety_result = self.safety_checker.check_before_execute(action)

        assert not safety_result.approved
        assert safety_result.risk_level == OperationRiskLevel.CRITICAL
        assert "人工审批" in safety_result.reason
        print(f"  [防护层 2] 安全检查拒绝: {safety_result.reason}")
        print(f"  [防护层 2] 建议: {safety_result.suggestions}")
        print("  [PASS] 安全检查失败处理正确")
        print("[PASS] test_safety_check_failure 通过")

    def test_effect_verification_worse_and_rollback(self):
        """测试：效果验证恶化并自动回滚（异常场景）"""
        device_id = "test_device_004"

        print("\n[场景 4] 效果验证失败自动回滚")

        # 模拟感知
        percept_result = {
            "metrics": {
                "rsrp": -110,
                "sinr": 0,
                "rtp_packet_loss": 2.0,
                "video_mos": 3.5,
            },
        }

        # 模拟决策（通过验证）
        decision_result = {
            "confidence": 0.85,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": True,
                    "rule_triggered": True,
                    "historical_similarity": 0.9,
                }
            ],
            "actions": [
                {
                    "tool": "increase_tx_power",
                    "params": {"power_dbm": 38},
                    "rollback_params": {"tx_power": 35},
                }
            ],
        }

        # 防护层 1：诊断验证
        print("  [防护层 1] 诊断验证...")
        validation_result = self.diagnosis_validator.validate(
            diagnosis=decision_result,
            metrics=percept_result["metrics"],
        )
        assert validation_result.is_validated
        print("  [防护层 1] 验证通过")

        # 防护层 2：安全检查
        print("  [防护层 2] 安全检查...")
        action = decision_result["actions"][0]
        safety_result = self.safety_checker.check_before_execute(action)
        assert safety_result.approved
        print("  [防护层 2] 安全检查通过")

        # 防护层 3：快照
        print("  [防护层 3] 保存快照...")
        self.rollback_manager.snapshot_before_action(device_id, percept_result["metrics"])
        self.rollback_manager.record_action(device_id, action)
        print("  [防护层 3] 快照保存完成")

        # 模拟执行
        print("  执行修复操作...")

        # 防护层 4：效果验证（模拟恶化）
        print("  [防护层 4] 效果验证...")

        def mock_collect_worse(did):
            return {
                "rsrp": -120,  # 恶化
                "sinr": -5,    # 恶化
                "rtp_packet_loss": 8.0,  # 恶化
                "video_mos": 2.0,  # 恶化
            }

        verification_result = self.effect_verifier.verify(
            device_id=device_id,
            action=action,
            pre_metrics=percept_result["metrics"],
            collect_metrics_func=mock_collect_worse,
            wait_seconds=0,
        )

        assert verification_result.status == VerificationStatus.WORSE
        assert verification_result.action == "rollback"
        print(f"  [防护层 4] 指标恶化: {verification_result.message}")

        # 自动回滚
        print("  触发自动回滚...")
        rollback_result = self.rollback_manager.rollback(device_id)
        assert rollback_result.is_success
        print(f"  回滚成功: {rollback_result.message}")
        print("  [PASS] 效果验证恶化自动回滚正确")
        print("[PASS] test_effect_verification_worse_and_rollback 通过")

    def test_partial_improvement_warning(self):
        """测试：部分改善记录警告（异常场景）"""
        device_id = "test_device_005"

        print("\n[场景 5] 部分改善处理")

        percept_result = {
            "metrics": {
                "rsrp": -115,
                "sinr": -5,
                "rtp_packet_loss": 5.0,
                "video_mos": 2.5,
            },
        }

        decision_result = {
            "confidence": 0.85,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": True,
                    "rule_triggered": True,
                    "historical_similarity": 0.9,
                }
            ],
            "actions": [
                {
                    "tool": "increase_tx_power",
                    "params": {"power_dbm": 38},
                }
            ],
        }

        # 防护层 1-2 通过
        validation_result = self.diagnosis_validator.validate(decision_result, percept_result["metrics"])
        assert validation_result.is_validated

        safety_result = self.safety_checker.check_before_execute(decision_result["actions"][0])
        assert safety_result.approved

        # 模拟部分改善
        def mock_collect_partial(did):
            return {
                "rsrp": -113,  # 改善 2dBm（未达标 3dBm）
                "sinr": -3,    # 改善 2dB（达标）
                "rtp_packet_loss": 4.5,  # 降低 0.5%（未达标 1%）
                "video_mos": 2.8,  # 提升 0.3（未达标 0.5）
            }

        verification_result = self.effect_verifier.verify(
            device_id=device_id,
            action=decision_result["actions"][0],
            pre_metrics=percept_result["metrics"],
            collect_metrics_func=mock_collect_partial,
            wait_seconds=0,
        )

        assert verification_result.status == VerificationStatus.PARTIAL
        assert verification_result.action == "retry"
        print(f"  [防护层 4] 部分改善: {verification_result.message}")
        print(f"  [防护层 4] 建议: {verification_result.suggestions}")
        print("  [PASS] 部分改善处理正确")
        print("[PASS] test_partial_improvement_warning 通过")

    def test_protection_stats_summary(self):
        """测试：防护层统计汇总（正常场景）"""
        print("\n[场景 6] 防护层统计汇总")

        # 执行多次验证
        for i in range(3):
            diagnosis = {
                "confidence": 0.85,
                "root_causes": [
                    {
                        "fault_type": "weak_signal",
                        "rag_support": True,
                        "rule_triggered": True,
                    }
                ],
            }
            self.diagnosis_validator.validate(diagnosis, {"rsrp": -115})

        # 执行多次安全检查
        for i in range(3):
            self.safety_checker.check_before_execute({"tool": "enable_icic", "params": {}})

        # 打印统计
        diag_stats = self.diagnosis_validator.get_validation_stats()
        safety_stats = self.safety_checker.get_safety_stats()
        effect_stats = self.effect_verifier.get_verification_stats()
        rollback_stats = self.rollback_manager.get_rollback_stats()

        print(f"  诊断验证: {diag_stats}")
        print(f"  安全检查: {safety_stats}")
        print(f"  效果验证: {effect_stats}")
        print(f"  回滚管理: {rollback_stats}")

        assert diag_stats["total_validations"] == 3
        assert safety_stats["total_checks"] == 3
        print("  [PASS] 防护层统计汇总正确")
        print("[PASS] test_protection_stats_summary 通过")


if __name__ == "__main__":
    test = TestProtectionFlow()

    print("=" * 60)
    print("四层防护集成测试")
    print("=" * 60)

    test.setup_method()
    test.test_full_protection_flow_success()

    test.setup_method()
    test.test_diagnosis_validation_failure()

    test.setup_method()
    test.test_safety_check_failure()

    test.setup_method()
    test.test_effect_verification_worse_and_rollback()

    test.setup_method()
    test.test_partial_improvement_warning()

    test.setup_method()
    test.test_protection_stats_summary()

    print("=" * 60)
    print("所有四层防护集成测试通过 [PASS]")
    print("=" * 60)
