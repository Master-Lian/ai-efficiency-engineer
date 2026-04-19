#!/usr/bin/env python
"""
独立脚本：更新本地知识库的向量索引。
运行方式：python update_vector_store.py
"""
from vector_store import build_vector_store

if __name__ == "__main__":
    print("正在更新向量库...")
    build_vector_store()
    print("向量库更新完成！")