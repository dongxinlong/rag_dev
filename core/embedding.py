"""
Embedding服务
"""

from openai import AsyncOpenAI

from config.settings import settings


class EmbeddingService:

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
        )
        self.model = settings.EMBEDDING_MODEL

    async def get_embedding(self, input_text: str):
        """
        将输入文本转换为嵌入向量
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=input_text
        )
        return response.data[0].embedding
    