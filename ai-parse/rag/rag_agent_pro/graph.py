# graph.py – 构建工作流图
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from nodes import AgentState, agent, grade_documents, rewrite, generate
from tools import tools

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent)
    workflow.add_node("retrieve", ToolNode(tools))
    workflow.add_node("rewrite", rewrite)
    workflow.add_node("generate", generate)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", tools_condition, {"tools": "retrieve", END: END})
    workflow.add_conditional_edges("retrieve", grade_documents)
    workflow.add_edge("generate", END)
    workflow.add_edge("rewrite", "agent")

    return workflow.compile()

# 预编译图，供 main 使用
graph = build_graph()
