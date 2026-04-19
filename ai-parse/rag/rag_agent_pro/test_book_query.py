#!/usr/bin/env python
"""快速测试脚本"""
from graph import graph

inputs = {"messages": [("user", "QT中如何创建窗口")], "rewrite_count": 0}
print(">>> 查询内容: QT中如何创建窗口\n")
print("=" * 60)
for output in graph.stream(inputs):
    for key, value in output.items():
        if key == "generate":
            print(f"\n--- [{key}] 输出 ---")
            res = value["messages"][-1]
            content = res if isinstance(res, str) else res.content
            print(content)
print("=" * 60)