"""
Messages 相关接口
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, not_
from typing import Union

from models.rag import Messages
from schemas.messages import MessagesCreate, MessagesResponse
from utils.pagination import paginate
from config.settings import settings


class MessagesService:

    def __init__(self, session: AsyncSession):
        self.db = session

    async def createMessages(self, **body: MessagesCreate):
        """
        消息新增
        """
        # 获取本chat之内的最新的的对话次数
        # 创建对象
        messages_instance = Messages(
            chat_id=body.get("chat_id"),
            role=body.get("role"),
            content=body.get("content"),
            tokens_prompt=body.get("tokens_prompt"),
            tokens_completion=body.get("tokens_completion"),
            cache_tokens=body.get("cache_tokens"),
            model=body.get("model"),
            cost=body.get("cost"),
            extra_data=body.get("extra_data"),
            status=body.get("status"),
            exchange_id=body.get("exchange_id")
        )
        self.db.add(messages_instance)
        # 把sql发送到数据库，并提交事务
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(messages_instance)

        # 转换为 Pydantic 模型
        res = MessagesResponse.model_validate(messages_instance)
        return res
    
    async def messages(self, chat_id: str, page: int = 1, size: int = 20):
        """
        获取所有的聊天列表
        支持按标题模糊筛选
        """
        stmt = select(Messages)
        stmt = stmt.where(Messages.chat_id == chat_id, Messages.is_deleted == False).order_by(Messages.created_at.desc())   
        return await paginate(self.db, stmt, page, size)
    
    async def messages_for_rag(self, chat_id: str):
        """
        获取用于 RAG 查询的消息列表
        """
        # 查询出所有的无效回复
        exchange_ids = select(Messages.exchange_id).where(
            Messages.content.contains("抱歉"),
            Messages.chat_id == chat_id,
            Messages.exchange_id.isnot(None)
        ).distinct()
        exchange_ids = await self.db.execute(exchange_ids)
        exchange_ids = exchange_ids.scalars().all()
        if exchange_ids:
            stmt = select(Messages).where(
                Messages.chat_id == chat_id, 
                Messages.is_deleted == False,
                ~Messages.exchange_id.in_(exchange_ids)
            ).order_by(
                Messages.created_at.desc()
            ).limit(settings.MAX_HISTORY_MESSAGES)
        else:
            stmt = select(Messages).where(
                Messages.chat_id == chat_id,
                Messages.is_deleted == False
            ).order_by(
                Messages.created_at.desc()
            ).limit(settings.MAX_HISTORY_MESSAGES)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        # 反转升序
        messages.reverse()
        return messages

    async def deleteMessages(self, id: str):
        """
        删除对话框（软删除）
        """
        stmt = select(Messages).where(Messages.id == id)
        result = await self.db.execute(stmt)
        messages_instance = result.scalar_one_or_none()
        if not messages_instance:
            raise ValueError("Messages not found")
        messages_instance.is_deleted = True
        await self.db.flush()
        await self.db.commit()
        return True

    async def updateMessagesStatus(self, id: str, **kwargs):
        """
        更新消息
        """
        stmt = select(Messages).where(Messages.id == id)
        result = await self.db.execute(stmt)
        messages_instance = result.scalar_one_or_none()
        if not messages_instance:
            raise ValueError("Messages not found")
        for key, value in kwargs.items():
            if hasattr(messages_instance, key):
                setattr(messages_instance, key, value)
        await self.db.flush()
        await self.db.commit()
        return True

    async def get_exchange_id(self, chat_id: str):
        """
        获取当前对话轮次
        """
        max_exchange_id = (
            select(func.max(Messages.exchange_id)).where(Messages.chat_id == chat_id)
        )
        result = await self.db.execute(max_exchange_id)
        return result.scalar_one_or_none()