#!/usr/bin/env python
"""
主程序：图书查询系统。
使用方法：
    python main.py
"""
from graph import graph

if __name__ == "__main__":
    print(">>> 欢迎使用图书查询系统，输入 'exit' 退出 <<<\n")
    while True:
        user_question = input("请输入你要查询的内容：").strip()
        if user_question.lower() == "exit":
            print("\n感谢使用，再见！")
            break
        if not user_question:
            print("查询内容不能为空，请重新输入\n")
            continue
        inputs = {"messages": [("user", user_question)], "rewrite_count": 0}
        print(f"\n>>> 查询内容: {user_question}\n")
        print("=" * 60)
        for output in graph.stream(inputs):
            for key, value in output.items():
                if key == "generate":
                    print(f"\n--- [{key}] 输出 ---")
                    res = value["messages"][-1]
                    content = res if isinstance(res, str) else res.content
                    print(content)
        print("=" * 60)