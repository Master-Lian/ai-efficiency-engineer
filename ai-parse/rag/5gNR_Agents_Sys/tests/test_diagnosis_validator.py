"""
诊断验证器测试用例
覆盖正常场景和异常场景
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.diagnosis_validator import DiagnosisValidator, ValidationResult, ValidationStatus


class TestDiagnosisValidator:
    """诊断验证器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.validator = DiagnosisValidator(
            min_confidence=0.7,
            min_evidence_count=2,
            historical_fault_db={
                "weak_signal": {"count": 10, "avg_confidence": 0.85},
                "interference": {"count": 5, "avg_confidence": 0.80},
                "vonr_quality_degradation": {"count": 8, "avg_confidence": 0.90},
            },
        )

    def test_validate_success(self):
        """测试：诊断验证通过（正常场景）"""
        diagnosis = {
            "confidence": 0.85,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": True,
                    "rule_triggered": True,
                    "historical_similarity": 0.9,
                }
            ],
        }
        metrics = {
            "rsrp": -115,
            "sinr": -5,
        }

        result = self.validator.validate(diagnosis, metrics)

        assert result.is_validated, f"预期验证通过，实际: {result.message}"
        assert result.status == ValidationStatus.VALIDATED
        assert result.confidence == 0.85
        print("[PASS] test_validate_success 通过")

    def test_low_confidence(self):
        """测试：置信度低于阈值（异常场景）"""
        diagnosis = {
            "confidence": 0.5,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": True,
                    "rule_triggered": True,
                }
            ],
        }
        metrics = {"rsrp": -115}

        result = self.validator.validate(diagnosis, metrics)

        assert not result.is_validated
        assert result.status == ValidationStatus.LOW_CONFIDENCE
        assert result.action == "require_human_review"
        print("[PASS] test_low_confidence 通过")

    def test_insufficient_evidence(self):
        """测试：证据不足（异常场景）"""
        diagnosis = {
            "confidence": 0.8,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": False,
                    "rule_triggered": False,
                    "historical_similarity": 0.5,
                }
            ],
        }
        metrics = {"rsrp": -100}  # 指标正常，无异常证据

        result = self.validator.validate(diagnosis, metrics)

        assert not result.is_validated
        assert result.status == ValidationStatus.INSUFFICIENT_EVIDENCE
        assert result.action == "collect_more_data"
        print("[PASS] test_insufficient_evidence 通过")

    def test_conflicting_evidence(self):
        """测试：证据冲突（异常场景）"""
        diagnosis = {
            "confidence": 0.85,
            "root_causes": [
                {
                    "fault_type": "weak_signal",
                    "rag_support": True,
                    "rule_triggered": True,
                },
                {
                    "fault_type": "interference",
                    "rag_support": True,
                    "rule_triggered": True,
                },
            ],
        }
        metrics = {"rsrp": -115, "sinr": -5}

        result = self.validator.validate(diagnosis, metrics)

        assert not result.is_validated
        assert result.status == ValidationStatus.CONFLICTING_EVIDENCE
        assert result.action == "flag_for_review"
        print("[PASS] test_conflicting_evidence 通过")

    def test_historical_mismatch(self):
        """测试：历史不一致（异常场景）"""
        diagnosis = {
            "confidence": 0.85,
            "root_causes": [
                {
                    "fault_type": "unknown_fault_type",
                    "rag_support": True,
                    "rule_triggered": True,
                    "historical_similarity": 0.9,
                }
            ],
        }
        metrics = {"rsrp": -115}

        result = self.validator.validate(diagnosis, metrics)

        assert not result.is_validated
        assert result.status == ValidationStatus.HISTORICAL_MISMATCH
        assert result.action == "flag_for_review"
        print("[PASS] test_historical_mismatch 通过")

    def test_vonr_scenario_success(self):
        """测试：VoNR 场景验证通过（正常场景）"""
        diagnosis = {
            "confidence": 0.90,
            "root_causes": [
                {
                    "fault_type": "vonr_quality_degradation",
                    "rag_support": True,
                    "rule_triggered": True,
                    "historical_similarity": 0.95,
                }
            ],
        }
        metrics = {
            "rtp_packet_loss": 5.0,
            "video_mos": 2.8,
        }

        result = self.validator.validate(diagnosis, metrics)

        assert result.is_validated
        assert result.status == ValidationStatus.VALIDATED
        print("[PASS] test_vonr_scenario_success 通过")

    def test_add_historical_fault(self):
        """测试：添加历史故障数据（正常场景）"""
        self.validator.add_historical_fault("new_fault", {"count": 1})
        assert "new_fault" in self.validator.historical_fault_db
        print("[PASS] test_add_historical_fault 通过")

    def test_validation_stats(self):
        """测试：验证统计信息（正常场景）"""
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
        metrics = {"rsrp": -115}

        self.validator.validate(diagnosis, metrics)
        self.validator.validate(diagnosis, metrics)

        stats = self.validator.get_validation_stats()
        assert stats["total_validations"] == 2
        assert stats["pass_count"] == 2
        assert stats["pass_rate"] == 1.0
        print("[PASS] test_validation_stats 通过")

    def test_empty_diagnosis(self):
        """测试：空诊断（异常场景）"""
        diagnosis = {}
        metrics = {}

        result = self.validator.validate(diagnosis, metrics)

        assert not result.is_validated
        assert result.status == ValidationStatus.LOW_CONFIDENCE
        print("[PASS] test_empty_diagnosis 通过")


if __name__ == "__main__":
    test = TestDiagnosisValidator()
    test.setup_method()

    print("=" * 60)
    print("诊断验证器测试")
    print("=" * 60)

    test.test_validate_success()
    test.setup_method()
    test.test_low_confidence()
    test.setup_method()
    test.test_insufficient_evidence()
    test.setup_method()
    test.test_conflicting_evidence()
    test.setup_method()
    test.test_historical_mismatch()
    test.setup_method()
    test.test_vonr_scenario_success()
    test.setup_method()
    test.test_add_historical_fault()
    test.setup_method()
    test.test_validation_stats()
    test.setup_method()
    test.test_empty_diagnosis()

    print("=" * 60)
    print("所有诊断验证器测试通过 [PASS]")
    print("=" * 60)
