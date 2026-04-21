"""
安全检查器测试用例
覆盖正常场景和异常场景
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.safety_checker import SafetyChecker, SafetyResult, OperationRiskLevel


class TestSafetyChecker:
    """安全检查器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.checker = SafetyChecker(require_approval_for_high=True)

    def test_low_risk_action(self):
        """测试：低风险操作（正常场景）"""
        action = {
            "tool": "enable_icic",
            "params": {},
        }

        result = self.checker.check_before_execute(action)

        assert result.approved, f"预期通过，实际: {result.reason}"
        assert result.risk_level == OperationRiskLevel.LOW
        print("[PASS] test_low_risk_action 通过")

    def test_medium_risk_action(self):
        """测试：中风险操作（正常场景）"""
        action = {
            "tool": "adjust_handover_offset",
            "params": {"offset_db": 2},
        }
        current_params = {"handover_offset": 0}

        result = self.checker.check_before_execute(action, current_params)

        assert result.approved
        assert result.risk_level == OperationRiskLevel.MEDIUM
        print("[PASS] test_medium_risk_action 通过")

    def test_high_risk_requires_approval(self):
        """测试：高风险操作需要审批（异常场景）"""
        action = {
            "tool": "optimize_pci",
            "params": {"new_pci": 100},
        }

        result = self.checker.check_before_execute(action)

        assert not result.approved
        assert result.risk_level == OperationRiskLevel.HIGH
        assert result.require_approval
        print("[PASS] test_high_risk_requires_approval 通过")

    def test_critical_risk_rejected(self):
        """测试：critical 操作被拒绝（异常场景）"""
        action = {
            "tool": "reset_baseband",
            "params": {},
        }

        result = self.checker.check_before_execute(action)

        assert not result.approved
        assert result.risk_level == OperationRiskLevel.CRITICAL
        assert "人工审批" in result.reason
        print("[PASS] test_critical_risk_rejected 通过")

    def test_param_out_of_safe_range(self):
        """测试：参数超出安全范围（异常场景）"""
        action = {
            "tool": "increase_tx_power",
            "params": {"power_dbm": 50},  # 超过最大 46dBm
        }

        result = self.checker.check_before_execute(action)

        assert not result.approved
        assert "超出安全范围" in result.reason
        print("[PASS] test_param_out_of_safe_range 通过")

    def test_param_delta_exceeds_limit(self):
        """测试：变更幅度超过限制（异常场景）"""
        action = {
            "tool": "increase_tx_power",
            "params": {"power_dbm": 40},
        }
        current_params = {"tx_power": 35}  # 变更 5dBm，超过限制 3dBm

        result = self.checker.check_before_execute(action, current_params)

        assert not result.approved
        assert "变更幅度" in result.reason
        print("[PASS] test_param_delta_exceeds_limit 通过")

    def test_maintenance_window_rejection(self):
        """测试：非维护窗口拒绝执行（异常场景）"""
        checker = SafetyChecker(
            maintenance_windows=[
                {"start_hour": 2, "end_hour": 6, "weekdays": [0, 1, 2, 3, 4, 5, 6]}
            ]
        )

        action = {
            "tool": "enable_icic",
            "params": {},
        }

        result = checker.check_before_execute(action)

        # 如果当前时间不在 2-6 点，应该被拒绝
        from datetime import datetime
        current_hour = datetime.now().hour
        if not (2 <= current_hour < 6):
            assert not result.approved
            assert "维护窗口" in result.reason
        else:
            assert result.approved
        print("[PASS] test_maintenance_window_rejection 通过")

    def test_add_maintenance_window(self):
        """测试：添加维护窗口（正常场景）"""
        checker = SafetyChecker()
        checker.add_maintenance_window(start_hour=0, end_hour=24, weekdays=[0, 1, 2, 3, 4])
        assert len(checker.maintenance_windows) == 1
        print("[PASS] test_add_maintenance_window 通过")

    def test_batch_actions_all_pass(self):
        """测试：批量操作全部通过（正常场景）"""
        actions = [
            {"tool": "enable_icic", "params": {}},
            {"tool": "adjust_resource_allocation", "params": {"prb_ratio": 0.5}},
        ]

        results = self.checker.check_batch_actions(actions)

        assert all(r.approved for r in results)
        assert len(results) == 2
        print("[PASS] test_batch_actions_all_pass 通过")

    def test_batch_actions_partial_fail(self):
        """测试：批量操作部分失败（异常场景）"""
        actions = [
            {"tool": "enable_icic", "params": {}},
            {"tool": "reset_baseband", "params": {}},  # critical 操作
        ]

        results = self.checker.check_batch_actions(actions)

        assert len(results) == 2
        assert results[0].approved
        assert not results[1].approved
        print("[PASS] test_batch_actions_partial_fail 通过")

    def test_double_check_power_limit(self):
        """测试：二次验证功率上限（异常场景）"""
        checker = SafetyChecker(require_approval_for_high=False)
        action = {
            "tool": "optimize_pci",
            "params": {"power_dbm": 50},
        }

        result = checker.check_before_execute(action)

        assert not result.approved
        assert "二次验证" in result.reason
        print("[PASS] test_double_check_power_limit 通过")

    def test_safety_stats(self):
        """测试：安全检查统计信息（正常场景）"""
        action = {"tool": "enable_icic", "params": {}}
        self.checker.check_before_execute(action)
        self.checker.check_before_execute(action)

        stats = self.checker.get_safety_stats()
        assert stats["total_checks"] == 2
        assert stats["pass_count"] == 2
        assert stats["pass_rate"] == 1.0
        print("[PASS] test_safety_stats 通过")


if __name__ == "__main__":
    test = TestSafetyChecker()
    test.setup_method()

    print("=" * 60)
    print("安全检查器测试")
    print("=" * 60)

    test.test_low_risk_action()
    test.setup_method()
    test.test_medium_risk_action()
    test.setup_method()
    test.test_high_risk_requires_approval()
    test.setup_method()
    test.test_critical_risk_rejected()
    test.setup_method()
    test.test_param_out_of_safe_range()
    test.setup_method()
    test.test_param_delta_exceeds_limit()
    test.setup_method()
    test.test_maintenance_window_rejection()
    test.setup_method()
    test.test_add_maintenance_window()
    test.setup_method()
    test.test_batch_actions_all_pass()
    test.setup_method()
    test.test_batch_actions_partial_fail()
    test.setup_method()
    test.test_double_check_power_limit()
    test.setup_method()
    test.test_safety_stats()

    print("=" * 60)
    print("所有安全检查器测试通过 [PASS]")
    print("=" * 60)
