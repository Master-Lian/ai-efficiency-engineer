from config import INPUT_DIR, OUTPUT_DIR
from utils.file_util import read_text_files, save_result
from utils.log_util import logger
from utils.ai_client import ai_call, validate_api_key

def load_prompt():
    with open("prompt.txt", "r", encoding="utf-8") as f:
        return f.read()

def main():
    logger.info("AI 文本处理程序启动")
    # 🔥 第一步：先校验 API Key，无效直接退出
    if not validate_api_key():
        logger.error("程序终止：API Key 未通过校验")
        return

    prompt = load_prompt()
    files = read_text_files(INPUT_DIR)

    if not files:
        logger.warning("input目录中没有找到文本文件")
        return
    
    for file_name, content in files:
        logger.info(f"正在处理文件: {file_name}")
        result = ai_call(prompt, content)
        save_result(OUTPUT_DIR, file_name, result)

if __name__ == "__main__":
    main()