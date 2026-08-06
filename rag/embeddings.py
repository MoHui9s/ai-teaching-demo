"""RAG 系统 —— Embedding 生成（支持 OpenAI / 百炼 DashScope / 智谱 等兼容 API）"""

import os
import logging
from typing import List, Optional

logger = logging.getLogger("rag-embeddings")

# 尝试导入 OpenAI SDK
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK 未安装，Embedding 将返回模拟数据")


class EmbeddingService:
    """Embedding 向量生成服务

    通过 OpenAI 兼容接口调用 Embedding 模型。
    已测试兼容：OpenAI / 阿里云百炼 DashScope (text-embedding-v4)
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")

        self.available = bool(self.api_key) and OPENAI_AVAILABLE

        if self.available:
            # OpenAI SDK 会自动在 base_url 后追加 /embeddings
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"Embedding 服务已配置 (model={self.model}, base_url={self.base_url})")
        else:
            logger.warning("Embedding 服务未配置（缺少 API Key 或 SDK），使用稀疏向量模拟")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本 Embedding 向量

        Args:
            texts: 文本列表

        Returns:
            向量列表，维度取决于模型（text-embedding-v4 默认 1024 维）
        """
        if not self.available:
            return self._mock_embed(texts)

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [d.embedding for d in response.data]

        except Exception as e:
            logger.warning(f"Embedding API 调用失败（将使用模拟向量）: {e}")
            return self._mock_embed(texts)

    def embed_query(self, query: str) -> List[float]:
        """单条查询 Embedding"""
        results = self.embed([query])
        return results[0] if results else []

    def _mock_embed(self, texts: List[str]) -> List[List[float]]:
        """模拟 Embedding（MD5 hash，仅用于 Embedding API 不可用时的回退）

        注意：模拟向量不支持语义搜索，ChromaDB 检索将降级为关键词匹配。
        要启用真正的语义搜索，请在 .env 中配置有效的 OPENAI_API_KEY。
        """
        import hashlib
        results = []
        for text in texts:
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
