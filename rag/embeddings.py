"""RAG 系统 —— Embedding 生成"""

import os
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("rag-embeddings")

# 尝试导入 OpenAI SDK
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK 未安装，Embedding 将返回模拟数据")


class EmbeddingService:
    """Embedding 向量生成服务"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # 修正 base_url 用于 embeddings 端点
        if "/chat/completions" in self.base_url:
            self.embed_url = self.base_url.replace("/chat/completions", "/embeddings")
        elif self.base_url.endswith("/v1") or self.base_url.endswith("/v3"):
            self.embed_url = self.base_url.rstrip("/") + "/embeddings"
        else:
            self.embed_url = self.base_url.rstrip("/") + "/embeddings"

        self.available = bool(self.api_key) and OPENAI_AVAILABLE

        if self.available:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"Embedding 服务已配置 (model={self.model})")
        else:
            logger.warning("Embedding 服务未配置，使用稀疏向量模拟")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本 Embedding 向量

        Args:
            texts: 文本列表

        Returns:
            向量列表，每个 1536 维（text-embedding-3-small）
        """
        if not self.available:
            return self._mock_embed(texts)

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [d.embedding for d in response.data]

        except Exception as e:
            logger.error(f"Embedding 生成失败: {e}")
            return self._mock_embed(texts)

    def embed_query(self, query: str) -> List[float]:
        """单条查询 Embedding"""
        results = self.embed([query])
        return results[0] if results else []

    def _mock_embed(self, texts: List[str]) -> List[List[float]]:
        """模拟 Embedding（使用简单 hash，仅用于开发）"""
        import hashlib
        results = []
        for text in texts:
            # 使用 MD5 生成 128 维模拟向量
            h = hashlib.md5(text.encode()).digest()
            vec = [float(b) / 255.0 for b in h] * 12  # 扩展为 ~1536 维
            results.append(vec[:1536])
        return results


# 全局实例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取 Embedding 服务单例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
