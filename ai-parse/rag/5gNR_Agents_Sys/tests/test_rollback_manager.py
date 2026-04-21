"""
回滚管理器测试用例
覆盖正常场景和异常场景
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.rollback_manager import RollbackManager, RollbackResult, RollbackStatus


class TestRollbackManager:
    """回滚管理器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.manager = RollbackManager()

    def test_snapshot_and_rollback_success(self):
        """测试：快照保存和回滚成功（正常场景）"""
        device_id = "test_device_001"
        params = {
            "tx_power": 35,
            "handover_offset": 0,
            "antenna_tilt": 5,
        }

        self.manager.snapshot_before_action(device_id, params)

        action = {
            "tool": "increase_tx_power",
            "params": {"power_dbm": 38},
            "rollback_params": {"tx_power": 35},
        }
        self.manager.record_action(device_id, action)

        result = self.manager.rollback(device_id)

        assert result.is_success
        assert result.status == RollbackStatus.SUCCESS
        assert "tx_power" in result.restored_params
        assert result.restored_params["tx_power"] == 35
        print("[PASS] test_snapshot_and_rollback_success 通过")

    def test_rollback_no_snapshot(self):
        """测试：无快照回滚（异常场景）"""
        result = self.manager.rollback("non_existent_device")

        assert not result.is_success
        assert result.status == RollbackStatus.NO_SNAPSHOT
        assert "无参数快照" in result.message
        print("[PASS] test_rollback_no_snapshot 通过")

    def test_rollback_no_action_history(self):
        """测试：无操作历史回滚（异常场景）"""
        device_id = "test_device_002"
        self.manager.snapshot_before_action(device_id, {"tx_power": 35})

        result = self.manager.rollback(device_id)

        assert not result.is_success
        assert result.status == RollbackStatus.NO_SNAPSHOT
        assert "无操作历史" in result.message
        print("[PASS] test_rollback_no_action_history 通过")

    def test_rollback_multiple_actions(self):
        """测试：多次操作逆序回滚（正常场景）"""
        device_id = "test_device_003"
        params = {
            "tx_power": 35,
            "handover_offset": 0,
        }
        self.manager.snapshot_before_action(device_id, params)

        actions = [
            {
                "tool": "increase_tx_power",
                "params": {"power_dbm": 38},
                "rollback_params": {"tx_power": 35},
            },
            {
                "tool": "adjust_handover_offset",
                "params": {"offset_db": 2},
                "rollback_params": {"handover_offset": 0},
            },
        ]

        for action in actions:
            self.manager.record_action(device_id, action)

        result = self.manager.rollback(device_id)

        assert result.is_success
        assert "tx_power" in result.restored_params
        assert "handover_offset" in result.restored_params
        print("[PASS] test_rollback_multiple_actions 通过")

    def test_rollback_with_custom_restore_func(self):
        """测试：自定义恢复函数（正常场景）"""
        restored = {}

        def mock_restore(device_id, action_name, params):
            restored.update(params)
            return True

        device_id = "test_device_004"
        self.manager.snapshot_before_action(device_id, {"tx_power": 35})

        action = {
            "tool": "increase_tx_power",
            "params": {"power_dbm": 38},
            "rollback_params": {"tx_power": 35},
        }
        self.manager.record_action(device_id, action)

        result = self.manager.rollback(device_id, restore_func=mock_restore)

        assert result.is_success
        assert restored.get("tx_power") == 35
        print("[PASS] test_rollback_with_custom_restore_func 通过")

    def test_clear_snapshot(self):
        """测试：清理快照（正常场景）"""
        device_id = "test_device_005"
        self.manager.snapshot_before_action(device_id, {"tx_power": 35})

        assert self.manager.get_snapshot(device_id) is not None

        self.manager.clear_snapshot(device_id)

        assert self.manager.get_snapshot(device_id) is None
        print("[PASS] test_clear_snapshot 通过")

    def test_get_snapshot(self):
        """测试：获取快照（正常场景）"""
        device_id = "test_device_006"
        params = {"tx_power": 35, "handover_offset": 0}
        self.manager.snapshot_before_action(device_id, params)

        snapshot = self.manager.get_snapshot(device_id)

        assert snapshot is not None
        assert snapshot["tx_power"] == 35
        assert snapshot["handover_offset"] == 0
        print("[PASS] test_get_snapshot 通过")

    def test_get_param_name(self):
        """测试：参数名称映射（正常场景）"""
        assert self.manager._get_param_name("adjust_antenna_tilt") == "antenna_tilt"
        assert self.manager._get_param_name("increase_tx_power") == "tx_power"
        assert self.manager._get_param_name("optimize_pci") == "pci"
        assert self.manager._get_param_name("unknown_action") is None
        print("[PASS] test_get_param_name 通过")

    def test_rollback_stats(self):
        """测试：回滚统计信息（正常场景）"""
        device_id = "test_device_007"
        self.manager.snapshot_before_action(device_id, {"tx_power": 35})
        self.manager.record_action(device_id, {"tool": "increase_tx_power", "params": {}})
        self.manager.rollback(device_id)

        stats = self.manager.get_rollback_stats()
        assert stats["total_rollbacks"] == 1
        assert stats["success_count"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["active_snapshots"] == 0  # 回滚后清理
        print("[PASS] test_rollback_stats 通过")

    def test_multiple_devices(self):
        """测试：多设备管理（正常场景）"""
        self.manager.snapshot_before_action("device_1", {"tx_power": 35})
        self.manager.snapshot_before_action("device_2", {"tx_power": 40})

        assert self.manager.get_snapshot("device_1")["tx_power"] == 35
        assert self.manager.get_snapshot("device_2")["tx_power"] == 40

        self.manager.record_action("device_1", {"tool": "increase_tx_power", "params": {}})
        self.manager.record_action("device_2", {"tool": "increase_tx_power", "params": {}})

        result1 = self.manager.rollback("device_1")
        result2 = self.manager.rollback("device_2")

        assert result1.is_success
        assert result2.is_success
        print("[PASS] test_multiple_devices 通过")


if __name__ == "__main__":
    test = TestRollbackManager()
    test.setup_method()

    print("=" * 60)
    print("回滚管理器测试")
    print("=" * 60)

    test.test_snapshot_and_rollback_success()
    test.setup_method()
    test.test_rollback_no_snapshot()
    test.setup_method()
    test.test_rollback_no_action_history()
    test.setup_method()
    test.test_rollback_multiple_actions()
    test.setup_method()
    test.test_rollback_with_custom_restore_func()
    test.setup_method()
    test.test_clear_snapshot()
    test.setup_method()
    test.test_get_snapshot()
    test.setup_method()
    test.test_get_param_name()
    test.setup_method()
    test.test_rollback_stats()
    test.setup_method()
    test.test_multiple_devices()

    print("=" * 60)
    print("所有回滚管理器测试通过 [PASS]")
    print("=" * 60)
