"""
Chat 相关接口
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
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
