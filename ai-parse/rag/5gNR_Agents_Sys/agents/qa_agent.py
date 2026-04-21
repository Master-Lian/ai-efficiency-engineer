"""
问答智能体
负责回答用户关于5G网络的问题
"""
from typing import Any, Dict
import time
import logging
from skills.rag_retrieve import RAGRetrieveSkill
from skills.qa_rag import QARAGSkill

logger = logging.getLogger(__name__)


class QAAgent:
    """问答智能体 - 负责RAG问答"""

    def __init__(self):
        self.rag_skill = RAGRetrieveSkill()
        self.qa_skill = QARAGSkill()
        self._qa_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0

    def answer(self, question: str) -> Dict[str, Any]:
        """执行问答流程"""
        start_time = time.time()
        self._qa_count += 1

        logger.info(f"[QAAgent] 开始回答问题 (第{self._qa_count}次): {question[:50]}...")

        try:
            context_result = self.rag_skill.execute(query=question)
            
            if context_result.get("status") == "error":
                raise Exception(f"检索失败: {context_result.get('error', '未知错误')}")
            
            context = context_result.get("context", "")

            qa_result = self.qa_skill.execute(question=question, context=context)
            
            if qa_result.get("status") == "error":
                raise Exception(f"问答失败: {qa_result.get('error', '未知错误')}")

            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency

            result = {
                "agent": "qa",
                "question": question,
                "answer": qa_result.get("answer", ""),
                "sources": qa_result.get("sources", []),
                "status": qa_result.get("status", "unknown"),
                "qa_latency_ms": total_latency,
                "rag_latency_ms": context_result.get("latency_ms", 0),
            }

            logger.info(f"[QAAgent] 问答完成: 耗时={total_latency:.2f}ms")

            return result
        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            self._total_latency_ms += total_latency
            self._error_count += 1
            
            logger.error(f"[QAAgent] 问答失败: {str(e)}")
            return {
                "agent": "qa",
                "question": question,
                "status": "error",
                "error": str(e),
                "answer": "抱歉，系统处理您的问题时遇到错误，请稍后重试。",
                "qa_latency_ms": total_latency,
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取问答统计信息"""
        return {
            "total_qa": self._qa_count,
            "error_count": self._error_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": self._total_latency_ms / max(self._qa_count, 1),
            "agent_name": "QAAgent",
            "rag_skill_stats": self.rag_skill.get_retrieval_stats(),
        }
