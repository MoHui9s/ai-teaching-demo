"""RAG 系统 —— 检索器"""

import logging
from typing import List, Dict, Any, Optional

from rag.embeddings import get_embedding_service
from rag.vector_store import get_vector_store

logger = logging.getLogger("rag-retriever")


class KnowledgeRetriever:
    """英语知识检索器"""

    COLLECTION_GRAMMAR = "grammar"
    COLLECTION_VOCABULARY = "vocabulary"
    COLLECTION_PRONUNCIATION = "pronunciation"

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()

    def search(self, query: str, topic: str = "grammar", k: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关知识

        Args:
            query: 查询文本
            topic: 主题 (grammar / vocabulary / pronunciation)
            k: 返回条数

        Returns:
            检索结果列表
        """
        collection_map = {
            "grammar": self.COLLECTION_GRAMMAR,
            "vocabulary": self.COLLECTION_VOCABULARY,
            "pronunciation": self.COLLECTION_PRONUNCIATION,
        }
        collection = collection_map.get(topic, self.COLLECTION_GRAMMAR)

        query_embedding = self.embedding_service.embed_query(query)
        if not query_embedding:
            return []

        results = self.vector_store.similarity_search(
            collection_name=collection,
            query_embedding=query_embedding,
            k=k,
        )

        logger.debug(f"检索 '{topic}': query='{query[:30]}...', results={len(results)}")
        return results

    def search_grammar(self, query: str) -> List[Dict]:
        """检索语法规则"""
        return self.search(query, "grammar")

    def search_vocabulary(self, word: str) -> List[Dict]:
        """检索词汇"""
        return self.search(word, "vocabulary")

    def search_pronunciation_tips(self, query: str) -> List[Dict]:
        """检索发音技巧"""
        return self.search(query, "pronunciation")

    def format_for_prompt(self, results: List[Dict], topic: str = "") -> str:
        """将检索结果格式化为 Agent 提示"""
        if not results:
            return ""

        lines = []
        if topic:
            lines.append(f"## 相关知识库检索结果（{topic}）")
        else:
            lines.append("## 相关知识库检索结果")

        for i, r in enumerate(results[:3], 1):
            doc = r.get("document", "")
            meta = r.get("metadata", {})
            lines.append(f"{i}. {doc}")
            if meta:
                lines.append(f"   来源: {meta.get('source', '')} | 分类: {meta.get('category', '')}")

        return "\n".join(lines)


# 全局实例
_retriever: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    """获取检索器单例"""
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever()
    return _retriever
