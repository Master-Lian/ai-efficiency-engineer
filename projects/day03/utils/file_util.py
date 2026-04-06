import os
from utils.log_util import logger

def read_text_files(folder):
    files = []
    for name in os.listdir(folder):
        if name.endswith(".txt"):
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                files.append((name, content))
                logger.info(f"读取文件: {name}，内容长度: {len(content)}")
            except Exception as e:
                logger.error(f"读取文件时出错: {name}，错误: {e}")
    return files

def save_result(folder, file_name, content):
    os.makedirs(folder, exist_ok=True)
    out_name = f"{os.path.splitext(file_name)[0]}_result.md"
    path = os.path.join(folder, out_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"保存结果: {out_name}，内容长度: {len(content)}")
