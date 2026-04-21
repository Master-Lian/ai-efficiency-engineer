#!/usr/bin/env python
"""
5G NR Agents System - 系统入口
一键启动5G智能运维系统
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.scheduler import MCPScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("5G_NR_System")


def print_banner():
    """打印系统横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       5G NR 无线网络多智能体协同保障系统                    ║
║       中兴通讯 | 核心开发 | 2025.04~2025.10               ║
║                                                           ║
║  秒级感知 → 自动诊断 → 智能决策 → 快速执行                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_menu():
    """打印菜单"""
    print("\n请选择操作模式:")
    print("  1. 故障自愈 (输入设备ID)")
    print("  2. 智能问答 (输入问题)")
    print("  3. 查看系统统计")
    print("  4. 回滚最后一次执行")
    print("  5. 退出系统")


def display_system_stats(stats: dict):
    """显示系统统计信息"""
    print("\n" + "=" * 60)
    print("  系统统计信息")
    print("=" * 60)
    print(f"总任务数: {stats['total_tasks']}")
    print(f"成功任务: {stats['success_count']}")
    print(f"失败任务: {stats['failure_count']}")
    print(f"成功率: {stats['success_rate']*100:.1f}%")
    print("\n--- 感知智能体 ---")
    print(f"  感知次数: {stats['percept_stats']['total_perceptions']}")
    print(f"  错误次数: {stats['percept_stats']['error_count']}")
    print(f"  平均耗时: {stats['percept_stats']['avg_latency_ms']:.2f}ms")
    print("\n--- 决策智能体 ---")
    print(f"  决策次数: {stats['decision_stats']['total_decisions']}")
    print(f"  错误次数: {stats['decision_stats']['error_count']}")
    print(f"  平均耗时: {stats['decision_stats']['avg_latency_ms']:.2f}ms")
    print("\n--- 执行智能体 ---")
    print(f"  执行次数: {stats['exec_stats']['total_executions']}")
    print(f"  错误次数: {stats['exec_stats']['error_count']}")
    print(f"  平均耗时: {stats['exec_stats']['avg_latency_ms']:.2f}ms")
    print("\n--- 问答智能体 ---")
    print(f"  问答次数: {stats['qa_stats']['total_qa']}")
    print(f"  错误次数: {stats['qa_stats']['error_count']}")
    print(f"  平均耗时: {stats['qa_stats']['avg_latency_ms']:.2f}ms")
    print("=" * 60)


def main():
    """主函数"""
    print_banner()
    logger.info("5G NR 智能运维系统启动")

    scheduler = MCPScheduler()

    while True:
        print_menu()
        choice = input("\n请输入选项 (1/2/3/4/5): ").strip()

        if choice == "1":
            device_id = input("请输入设备ID: ").strip()
            if device_id:
                result = scheduler.run_fault_healing(device_id)
                print(f"\n处理结果: {result['status']}")
            else:
                print("设备ID不能为空")

        elif choice == "2":
            question = input("请输入问题: ").strip()
            if question:
                result = scheduler.run_qa(question)
            else:
                print("问题不能为空")

        elif choice == "3":
            stats = scheduler.get_system_stats()
            display_system_stats(stats)

        elif choice == "4":
            device_id = input("请输入要回滚的设备ID: ").strip()
            if device_id:
                result = scheduler.rollback_last_execution(device_id)
                print(f"\n回滚结果: {result['status']}")
                print(f"回滚消息: {result.get('message', '无')}")
            else:
                print("设备ID不能为空")

        elif choice == "5":
            print("\n感谢使用，再见！")
            logger.info("系统退出")
            break

        else:
            print("无效选项，请重新输入")


if __name__ == "__main__":
    main()
