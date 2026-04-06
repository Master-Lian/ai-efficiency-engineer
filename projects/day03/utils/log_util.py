import logging

def get_logger():
    # 修复：必须用 logging 调用，不是 logger！
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("AI_Batch_Tool")

logger = get_logger()