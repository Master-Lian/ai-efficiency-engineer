"""
RAG混合检索技能
结合 FAISS 向量检索和 BM25 关键词检索
支持工业级 RRF（Reciprocal Rank Fusion）排名融合算法
"""
from typing import Any, Dict, List, Optional, Tuple
import logging
import math
from collections import Counter
from core.base_skill import BaseSkill
from core.config import KNOWLEDGE_FILE, PERFORMANCE_CONFIG

logger = logging.getLogger(__name__)


class RRFConfig:
    """RRF 配置参数"""
    def __init__(
        self,
        k: float = 60.0,
        faiss_weight: float = 0.6,
        bm25_weight: float = 0.4,
        min_score_threshold: float = 0.01,
    ):
        self.k = k
        self.faiss_weight = faiss_weight
        self.bm25_weight = bm25_weight
        self.min_score_threshold = min_score_threshold


class BM25Retriever:
    """BM25 关键词检索器"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_freq = Counter()
        self.avg_doc_len = 0
        self._idf_cache = {}

    def add_documents(self, documents: List[str]):
        """添加文档到索引"""
        self.documents = documents
        self._build_index()

    def _build_index(self):
        """构建 BM25 索引"""
        if not self.documents:
            return

        total_docs = len(self.documents)
        doc_lengths = []

        for doc in self.documents:
            words = self._tokenize(doc)
            doc_lengths.append(len(words))
            unique_words = set(words)
            for word in unique_words:
                self.doc_freq[word] += 1

        self.avg_doc_len = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        return text.lower().split()

    def _idf(self, term: str) -> float:
        """计算 IDF 值"""
        if term in self._idf_cache:
            return self._idf_cache[term]

        n = self.doc_freq.get(term, 0)
        if n == 0:
            return 0.0

        idf = math.log((len(self.documents) - n + 0.5) / (n + 0.5) + 1.0)
        self._idf_cache[term] = idf
        return idf

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """执行 BM25 检索"""
        if not self.documents:
            return []

        query_terms = self._tokenize(query)
        scores = []

        for i, doc in enumerate(self.documents):
            doc_words = self._tokenize(doc)
            doc_len = len(doc_words)
            doc_word_count = Counter(doc_words)

            score = 0.0
            for term in query_terms:
                tf = doc_word_count.get(term, 0)
                idf = self._idf(term)

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                score += idf * (numerator / denominator) if denominator > 0 else 0

            if score > 0:
                scores.append({
                    "index": i,
                    "score": score,
                    "content": doc,
                    "source": "bm25",
                })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]


class RRFFusion:
    """工业级 RRF（Reciprocal Rank Fusion）排名融合算法"""

    def __init__(self, config: Optional[RRFConfig] = None):
        self.config = config or RRFConfig()

    def fuse(
        self,
        faiss_results: List[Dict],
        bm25_results: List[Dict],
        top_k: int = 5,
    ) -> List[Dict]:
        """
        执行 RRF 融合
        
        RRF 公式: score(d) = Σ 1 / (k + rank(d))
        其中 k 是常数（通常 60），rank(d) 是文档在某检索器中的排名
        """
        doc_scores = {}
        doc_info = {}

        for rank, result in enumerate(faiss_results, 1):
            idx = result["index"]
            rrf_score = self.config.faiss_weight / (self.config.k + rank)
            doc_scores[idx] = doc_scores.get(idx, 0) + rrf_score
            doc_info[idx] = result

        for rank, result in enumerate(bm25_results, 1):
            idx = result["index"]
            rrf_score = self.config.bm25_weight / (self.config.k + rank)
            doc_scores[idx] = doc_scores.get(idx, 0) + rrf_score
            if idx not in doc_info:
                doc_info[idx] = result

        fused_results = []
        for idx, score in doc_scores.items():
            if score >= self.config.min_score_threshold:
                result = doc_info[idx].copy()
                result["rrf_score"] = score
                result["score"] = score
                fused_results.append(result)

        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_results[:top_k]

    def get_fusion_stats(
        self,
        faiss_results: List[Dict],
        bm25_results: List[Dict],
        fused_results: List[Dict],
    ) -> Dict[str, Any]:
        """获取融合统计信息"""
        faiss_indices = {r["index"] for r in faiss_results}
        bm25_indices = {r["index"] for r in bm25_results}
        fused_indices = {r["index"] for r in fused_results}

        return {
            "faiss_count": len(faiss_results),
            "bm25_count": len(bm25_results),
            "fused_count": len(fused_results),
            "overlap_count": len(faiss_indices & bm25_indices),
            "faiss_only": len(faiss_indices - bm25_indices),
            "bm25_only": len(bm25_indices - faiss_indices),
        }


class RAGRetrieveSkill(BaseSkill):
    """RAG混合检索技能 - FAISS + BM25 + RRF 融合"""

    def __init__(self):
        super().__init__()
        self._bm25_retriever = BM25Retriever()
        self._rrf_fusion = RRFFusion()
        self._knowledge_chunks = []
        self._initialized = False

    @property
    def name(self) -> str:
        return "rag_retrieve"

    @property
    def description(self) -> str:
        return "结合FAISS向量检索和BM25关键词检索，使用RRF算法进行排名融合"

    def _ensure_initialized(self):
        """延迟初始化检索索引"""
        if self._initialized:
            return

        try:
            self._load_knowledge_base()
            self._initialized = True
            self._log_execute("检索索引初始化完成")
        except Exception as e:
            self._log_execute(f"检索索引初始化失败: {e}", level="error")

    def _load_knowledge_base(self):
        """加载知识库并构建索引"""
        if not KNOWLEDGE_FILE.exists():
            self._log_execute(f"知识库文件不存在: {KNOWLEDGE_FILE}", level="warning")
            return

        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        self._knowledge_chunks = self._chunk_text(content)
        self._bm25_retriever.add_documents(self._knowledge_chunks)
        self._log_execute(f"加载知识库: {len(self._knowledge_chunks)} 个文档块")

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """文本分块"""
        chunks = []
        words = text.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行检索"""
        start_time = self._track_execution_start()
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", PERFORMANCE_CONFIG.faiss_top_k)

        self._log_execute(f"开始检索: {query[:50]}...")

        try:
            self._ensure_initialized()

            bm25_results = self._bm25_retriever.search(query, top_k * 2)
            faiss_results = self._faiss_search(query, top_k * 2)

            fused_results = self._rrf_fusion.fuse(faiss_results, bm25_results, top_k)
            context = self._build_context(fused_results)

            fusion_stats = self._rrf_fusion.get_fusion_stats(faiss_results, bm25_results, fused_results)

            elapsed = self._track_execution(start_time)
            self._log_execute(f"RRF融合检索完成: 返回 {len(fused_results)} 条结果")

            return self._build_result(
                status="retrieved",
                query=query,
                context=context,
                sources=["faiss_vector_store", "bm25_keyword_index"],
                result_count=len(fused_results),
                faiss_count=len(faiss_results),
                bm25_count=len(bm25_results),
                fusion_stats=fusion_stats,
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = self._track_execution(start_time)
            self._log_execute(f"检索失败: {str(e)}", level="error")
            return self._build_error_result(str(e), elapsed)

    def _track_execution_start(self) -> float:
        import time
        return time.time()

    def _faiss_search(self, query: str, top_k: int) -> List[Dict]:
        """FAISS 向量检索（占位实现）"""
        if not self._knowledge_chunks:
            return []

        results = []
        for i, chunk in enumerate(self._knowledge_chunks[:top_k]):
            results.append({
                "source": "faiss",
                "content": chunk,
                "score": 0.8,
                "index": i,
            })
        return results

    def _build_context(self, results: List[Dict]) -> str:
        """构建检索上下文字符串"""
        if not results:
            return "未检索到相关知识"

        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(f"[{i+1}] (RRF: {r.get('rrf_score', 0):.4f}) {r['content']}")

        return "\n\n".join(context_parts)

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """获取检索统计信息"""
        return {
            "knowledge_chunks": len(self._knowledge_chunks),
            "initialized": self._initialized,
            "algorithm": "RRF (Reciprocal Rank Fusion)",
        }
