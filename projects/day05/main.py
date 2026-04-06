from utils.agent_core import validate_api_key, agent_run
from utils.log_util import logger

def main():
    logger.info("=== Day05 AI 智能体启动 ===")
    
    # 密钥校验
    if not validate_api_key():
        return
    
    # 交互模式
    logger.info("=== 智能体已就绪，输入任务开始（exit退出）===")
    while True:
        task = input("\n请输入任务：")
        if task.lower() == "exit":
            logger.info("智能体退出")
            break
        
        result = agent_run(task)
        print(f"\n✅ 执行结果：\n{result}")

if __name__ == "__main__":
    main()