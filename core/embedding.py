"""
Embedding服务
"""

from typing import List
from openai import AsyncOpenAI

from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:

    def __init__(self):
        self.model = settings.EMBEDDING_MODEL

    def _get_client(self):
        """获取新的客户端实例"""
        return AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
        )

    async def get_embedding(self, input_text: str):
        """
        将输入文本转换为嵌入向量
        """
        async with self._get_client() as client:
            response = await client.embeddings.create(
                model=self.model,
                input=input_text
            )
            return response.data[0].embedding

    async def get_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        批量获取嵌入向量

        Args:
            texts: 文本列表
            batch_size: 每批处理数量

        Returns:
            嵌入向量列表
        """
        all_embeddings = []

        async with self._get_client() as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                try:
                    response = await client.embeddings.create(
                        model=self.model,
                        input=batch
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    logger.debug(f"批量 Embedding 完成: {len(batch)} 条")
                except Exception as e:
                    logger.error(f"批量 Embedding 失败: {e}")
                    # 失败时用零向量填充
                    dim = 2560  # 默认维度
                    all_embeddings.extend([[0.0] * dim for _ in batch])

        return all_embeddings
    