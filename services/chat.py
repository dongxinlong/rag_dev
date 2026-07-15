"""
Chat 相关接口
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Union

from models.rag import Chat
from schemas.chat import ChatResponse
from utils.pagination import paginate


class ChatService:

    def __init__(self, session: AsyncSession):
        self.db = session


    async def createChat(self, title: str):
        """
        新增对话框
        """
        # 创建对象
        chat_instance = Chat(title=title)
        self.db.add(chat_instance)
        # 把sql发送到数据库，但是不提交事务
        await self.db.flush()
        await self.db.refresh(chat_instance)

        # 转换为 Pydantic 模型
        res = ChatResponse.model_validate(chat_instance)
        return res
    
    async def chats(self, title: Union[str, None] = None, page: int = 1, size: int = 20):
        """
        获取所有的聊天列表
        支持按标题模糊筛选
        """
        stmt = select(Chat).where(Chat.is_deleted == False)
        if title:
            stmt = stmt.where(Chat.title.contains(title))
        stmt = stmt.order_by(Chat.created_at.desc())
        return await paginate(self.db, stmt, page, size)
    
    async def deleteChat(self, chat_id: str):
        """
        删除对话框（软删除）
        """
        stmt = select(Chat).where(Chat.id == chat_id)
        result = await self.db.execute(stmt)
        chat_instance = result.scalar_one_or_none()
        if not chat_instance:
            raise ValueError("Chat not found")
        chat_instance.is_deleted = True
        await self.db.flush()
        return True
    
    async def updateChat(self, chat_id: str, title: str):
        """
        更新对话框
        """
        stmt = select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)
        result = await self.db.execute(stmt)
        chat_instance = result.scalar_one_or_none()
        if not chat_instance:
            raise ValueError("Chat not found")
        chat_instance.title = title
        await self.db.flush()
        return True
    
    async def updateSummary(self, chat_id: str, summary: str, exchange_id: int, key_points: dict = None):
        """
        更新对话摘要
        """
        stmt = select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)
        result = await self.db.execute(stmt)
        chat_instance = result.scalar_one_or_none()
        if not chat_instance:
            raise ValueError("Chat not found")
        
        chat_instance.summary = summary
        chat_instance.summary_exchange_id = exchange_id
        if key_points is not None:
            chat_instance.key_points = key_points
        
        await self.db.flush()
        return True
    
    async def getMaxexchangeId(self, chat_id: str) -> int:
        """
        获取指定对话的最大 exchange_id
        """
        from models.rag import Messages
        from sqlalchemy import func

        stmt = select(func.max(Messages.exchange_id)).where(
            Messages.chat_id == chat_id
        )
        result = await self.db.execute(stmt)
        max_exchange_id = result.scalar()

        return max_exchange_id if max_exchange_id else 0

    async def getMaxexchangeIdAndSummary(self, chat_id: str) -> dict:
        """
        获取指定对话的摘要信息
        """
        stmt = select(
            Chat.summary_exchange_id,
            Chat.summary,
            Chat.key_points
        ).where(Chat.id == chat_id)

        result = await self.db.execute(stmt)
        row = result.fetchone()

        return {
            "max_exchange_id": row[0] if row and row[0] else 0,
            "summary": row[1] if row and row[1] else "",
            "key_points": row[2] if row and row[2] else {}
        }
