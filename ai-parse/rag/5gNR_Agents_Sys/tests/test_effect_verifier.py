"""
效果验证器测试用例
覆盖正常场景和异常场景
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.effect_verifier import EffectVerifier, VerificationResult, VerificationStatus, Improvement


class TestEffectVerifier:
    """效果验证器测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.verifier = EffectVerifier(
            wait_seconds=0,  # 测试时不等待
            verification_targets={
                "rsrp_delta": 3,
                "sinr_delta": 2,
                "packet_loss_delta": 1,
                "mos_delta": 0.5,
            },
        )

    def test_verification_success(self):
        """测试：修复效果验证通过（正常场景）"""
        pre_metrics = {
            "rsrp": -115,
            "sinr": -5,
            "rtp_packet_loss": 5.0,
            "video_mos": 2.5,
        }
        post_metrics = {
            "rsrp": -110,  # 改善 5dBm
            "sinr": -1,    # 改善 4dB
            "rtp_packet_loss": 2.0,  # 降低 3%
            "video_mos": 3.5,  # 提升 1.0
        }

        improvement = self.verifier._calculate_improvement(pre_metrics, post_metrics)

        assert improvement.rsrp_delta == 5
        assert improvement.sinr_delta == 4
        assert improvement.packet_loss_delta == 3
        assert improvement.mos_delta == 1.0
        assert improvement.meets_target(self.verifier.verification_targets)
        print("[PASS] test_verification_success 通过")

    def test_verification_worse(self):
        """测试：指标恶化（异常场景）"""
        pre_metrics = {
            "rsrp": -110,
            "sinr": 0,
            "rtp_packet_loss": 2.0,
            "video_mos": 3.5,
        }
        post_metrics = {
            "rsrp": -120,  # 恶化 10dBm
            "sinr": -5,    # 恶化 5dB
            "rtp_packet_loss": 8.0,  # 恶化 6%
            "video_mos": 2.0,  # 恶化 1.5
        }

        improvement = self.verifier._calculate_improvement(pre_metrics, post_metrics)

        assert improvement.rsrp_delta == -10
        assert improvement.is_worse()
        print("[PASS] test_verification_worse 通过")

    def test_verification_partial(self):
        """测试：部分改善（异常场景）"""
        pre_metrics = {
            "rsrp": -115,
            "sinr": -5,
            "rtp_packet_loss": 5.0,
            "video_mos": 2.5,
        }
        post_metrics = {
            "rsrp": -113,  # 改善 2dBm（未达标 3dBm）
            "sinr": -3,    # 改善 2dB（达标）
            "rtp_packet_loss": 4.5,  # 降低 0.5%（未达标 1%）
            "video_mos": 2.8,  # 提升 0.3（未达标 0.5）
        }

        improvement = self.verifier._calculate_improvement(pre_metrics, post_metrics)

        assert not improvement.meets_target(self.verifier.verification_targets)
        assert not improvement.is_worse()
        print("[PASS] test_verification_partial 通过")

    def test_improvement_meets_target(self):
        """测试：改善达标判断（正常场景）"""
        improvement = Improvement(
            rsrp_delta=4,
            sinr_delta=3,
            packet_loss_delta=2,
            mos_delta=1.0,
        )

        assert improvement.meets_target()
        print("[PASS] test_improvement_meets_target 通过")

    def test_improvement_not_meets_target(self):
        """测试：改善未达标判断（异常场景）"""
        improvement = Improvement(
            rsrp_delta=1,  # 未达标
            sinr_delta=3,
            packet_loss_delta=2,
            mos_delta=1.0,
        )

        assert not improvement.meets_target()
        print("[PASS] test_improvement_not_meets_target 通过")

    def test_improvement_is_worse(self):
        """测试：指标恶化判断（异常场景）"""
        improvement = Improvement(
            rsrp_delta=-5,  # 恶化
            sinr_delta=-3,  # 恶化
            packet_loss_delta=-4,  # 恶化
            mos_delta=-1.0,  # 恶化
        )

        assert improvement.is_worse()
        print("[PASS] test_improvement_is_worse 通过")

    def test_verify_with_custom_collect_func(self):
        """测试：自定义采集函数（正常场景）"""
        def mock_collect(device_id):
            return {
                "rsrp": -108,
                "sinr": 2,
                "rtp_packet_loss": 1.5,
                "video_mos": 4.0,
            }

        pre_metrics = {
            "rsrp": -115,
            "sinr": -5,
            "rtp_packet_loss": 5.0,
            "video_mos": 2.5,
        }
        action = {"tool": "increase_tx_power", "params": {"power_dbm": 40}}

        result = self.verifier.verify(
            device_id="test_device_001",
            action=action,
            pre_metrics=pre_metrics,
            collect_metrics_func=mock_collect,
            wait_seconds=0,
        )

        assert result.is_success
        assert result.status == VerificationStatus.SUCCESS
        assert result.action == "close_ticket"
        print("[PASS] test_verify_with_custom_collect_func 通过")

    def test_verify_simulation(self):
        """测试：模拟采集（正常场景）"""
        pre_metrics = {
            "rsrp": -115,
            "sinr": -5,
            "rtp_packet_loss": 5.0,
            "video_mos": 2.5,
        }
        action = {"tool": "increase_tx_power", "params": {"power_dbm": 40}}

        result = self.verifier.verify(
            device_id="test_device_001",
            action=action,
            pre_metrics=pre_metrics,
            wait_seconds=0,
        )

        # 模拟采集应该改善指标
        assert result.post_metrics["rsrp"] > pre_metrics["rsrp"]
        assert result.post_metrics["sinr"] > pre_metrics["sinr"]
        print("[PASS] test_verify_simulation 通过")

    def test_verify_handover_action(self):
        """测试：切换操作效果验证（正常场景）"""
        pre_metrics = {
            "rsrp": -110,
            "sinr": 0,
            "rtp_packet_loss": 8.0,
            "video_mos": 2.0,
        }
        action = {"tool": "adjust_handover_offset", "params": {"offset_db": 2}}

        result = self.verifier.verify(
            device_id="test_device_002",
            action=action,
            pre_metrics=pre_metrics,
            wait_seconds=0,
        )

        # 切换操作应该降低丢包率
        assert result.post_metrics["rtp_packet_loss"] < pre_metrics["rtp_packet_loss"]
        assert result.post_metrics["video_mos"] > pre_metrics["video_mos"]
        print("[PASS] test_verify_handover_action 通过")

    def test_verify_icic_action(self):
        """测试：ICIC 操作效果验证（正常场景）"""
        pre_metrics = {
            "rsrp": -110,
            "sinr": -5,
            "rtp_packet_loss": 5.0,
            "video_mos": 2.5,
        }
        action = {"tool": "enable_icic", "params": {}}

        result = self.verifier.verify(
            device_id="test_device_003",
            action=action,
            pre_metrics=pre_metrics,
            wait_seconds=0,
        )

        # ICIC 应该改善 SINR
        assert result.post_metrics["sinr"] > pre_metrics["sinr"]
        print("[PASS] test_verify_icic_action 通过")

    def test_verification_stats(self):
        """测试：验证统计信息（正常场景）"""
        pre_metrics = {
            "rsrp": -115,
            "sinr": -5,
            "rtp_packet_loss": 5.0,
            "video_mos": 2.5,
        }
        action = {"tool": "increase_tx_power", "params": {"power_dbm": 40}}

        self.verifier.verify(
            device_id="test_device_001",
            action=action,
            pre_metrics=pre_metrics,
            wait_seconds=0,
        )
        self.verifier.verify(
            device_id="test_device_001",
            action=action,
            pre_metrics=pre_metrics,
            wait_seconds=0,
        )

        stats = self.verifier.get_verification_stats()
        assert stats["total_verifications"] == 2
        assert stats["success_count"] == 2
        assert stats["success_rate"] == 1.0
        print("[PASS] test_verification_stats 通过")


if __name__ == "__main__":
    test = TestEffectVerifier()
    test.setup_method()

    print("=" * 60)
    print("效果验证器测试")
    print("=" * 60)

    test.test_verification_success()
    test.setup_method()
    test.test_verification_worse()
    test.setup_method()
    test.test_verification_partial()
    test.setup_method()
    test.test_improvement_meets_target()
    test.setup_method()
    test.test_improvement_not_meets_target()
    test.setup_method()
    test.test_improvement_is_worse()
    test.setup_method()
    test.test_verify_with_custom_collect_func()
    test.setup_method()
    test.test_verify_simulation()
    test.setup_method()
    test.test_verify_handover_action()
    test.setup_method()
    test.test_verify_icic_action()
    test.setup_method()
    test.test_verification_stats()

    print("=" * 60)
    print("所有效果验证器测试通过 [PASS]")
    print("=" * 60)
