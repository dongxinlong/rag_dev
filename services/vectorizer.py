"""
向量化入库服务

将分块后的文档向量化并存入 pgvector
"""
from typing import List
from core.embedding import EmbeddingService
from models.rag import Document
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class Vectorizer:
    """向量化入库服务"""

    def __init__(self, db):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def vectorize_and_store(self, chunks: list, file_id: str, file_name: str = None) -> int:
        """
        批量向量化并存入数据库

        Args:
            chunks: Chunk 列表
            file_id: 知识库文件 ID
            file_name: 文件名

        Returns:
            存入的 chunk 数量
        """
        if not chunks:
            logger.warning("没有需要向量化的 chunk")
            return 0

        logger.info(f"开始向量化: {len(chunks)} 个 chunk")

        # 批量获取 embedding
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_service.get_embeddings(texts, batch_size=settings.EMBEDDING_BATCH_SIZE)

        # 批量插入数据库
        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = Document(
                file_id=file_id,
                file_name=file_name or chunk.metadata.get("document_name", ""),
                file_type=self._get_file_type(file_name),
                content=chunk.content,
                embedding=embedding,
                chunk_index=chunk.index,
                heading=chunk.heading,
                heading_level=chunk.heading_level,
                heading_path=chunk.metadata.get("heading_path", []),
                token_count=chunk.token_count,
                char_count=chunk.char_count,
                chunk_strategy=chunk.metadata.get("chunk_strategy", ""),
                is_atomic=chunk.metadata.get("is_atomic", False)
            )
            documents.append(doc)

        # 批量插入
        self.db.add_all(documents)
        await self.db.commit()

        logger.info(f"向量化完成: {len(documents)} 个 chunk 已存入数据库")
        return len(documents)

    async def delete_by_file_id(self, file_id: str) -> int:
        """
        根据文件 ID 删除所有 chunk（用于重新处理）

        Args:
            file_id: 知识库文件 ID

        Returns:
            删除的 chunk 数量
        """
        from sqlalchemy import delete

        stmt = delete(Document).where(Document.file_id == file_id)
        result = await self.db.execute(stmt)
        await self.db.commit()

        deleted_count = result.rowcount
        logger.info(f"已删除 {deleted_count} 个 chunk: file_id={file_id}")
        return deleted_count

    def _get_file_type(self, file_name: str) -> str:
        """从文件名获取类型"""
        if not file_name:
            return "unknown"
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        return ext


# 全局实例（需要在使用时初始化 db）
def get_vectorizer(db):
    """获取向量化服务实例"""
    return Vectorizer(db)
