from utils.rag_core import load_knowledge, validate_api_key, rag_ask
from utils.log_util import logger

def main():
    logger.info("=== Day04 RAG 本地知识库启动 ===")
    
    # 1. 校验密钥
    if not validate_api_key():
        return
    
    # 2. 加载知识库
    knowledge = load_knowledge()
    
    # 3. 开始问答
    logger.info("=== 进入知识库问答模式（输入 exit 退出）===")
    while True:
        question = input("\n请输入你的问题：")
        if question.lower() in ["exit", "quit", "q"]:
            logger.info("程序退出")
            break
        
        answer = rag_ask(question, knowledge)
        print(f"\n📝 回答：\n{answer}")

if __name__ == "__main__":
    main()