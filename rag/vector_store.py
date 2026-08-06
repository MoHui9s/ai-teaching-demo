"""RAG 系统 —— ChromaDB 向量存储"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("rag-vector-store")

# 尝试导入 ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB 未安装，使用内存模拟存储")


class ChromaVectorStore:
    """ChromaDB 向量存储封装"""

    def __init__(self, persist_dir: str = None):
        if persist_dir is None:
            persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.available = CHROMADB_AVAILABLE

        if self.available:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"ChromaDB 已连接 (persist_dir={self.persist_dir})")
        else:
            # 模拟存储
            self._mock_store: Dict[str, List[Dict]] = {}
            logger.warning("ChromaDB 未安装，使用内存模拟存储")

    def get_or_create_collection(self, name: str):
        """获取或创建集合"""
        if self.available:
            return self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        else:
            if name not in self._mock_store:
                self._mock_store[name] = []
            return name

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict] = None,
        ids: List[str] = None,
    ):
        """添加文档到向量存储"""
        if self.available:
            collection = self.get_or_create_collection(collection_name)
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in documents]
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids,
            )
            logger.debug(f"已添加 {len(documents)} 条文档到集合 '{collection_name}'")
        else:
            col = self._mock_store.setdefault(collection_name, [])
            for i, doc in enumerate(documents):
                col.append({
                    "id": ids[i] if ids else f"doc_{i}",
                    "document": doc,
                    "embedding": embeddings[i],
                    "metadata": metadatas[i] if metadatas else {},
                })

    def similarity_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        相似度检索

        Returns:
            [{"id": "...", "document": "...", "metadata": {...}, "distance": 0.1}, ...]
        """
        if self.available:
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, collection.count()),
            )
            if results and results["ids"] and results["ids"][0]:
                return [
                    {
                        "id": rid,
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                    }
                    for rid, doc, meta, dist in zip(
                        results["ids"][0],
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ]
            return []
        else:
            # 模拟：简单余弦相似度
            col = self._mock_store.get(collection_name, [])
            if not col:
                return []

            scored = []
            for item in col:
                sim = self._cosine_similarity(query_embedding, item["embedding"])
                scored.append((sim, item))
            scored.sort(key=lambda x: x[0], reverse=True)

            return [
                {
                    "id": item["id"],
                    "document": item["document"],
                    "metadata": item["metadata"],
                    "distance": 1 - sim,
                }
                for sim, item in scored[:k]
            ]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# 全局实例
_vector_store: Optional[ChromaVectorStore] = None


def get_vector_store() -> ChromaVectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore()
    return _vector_store
