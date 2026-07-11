"""
消息相关接口
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import db_session
from services.messages import MessagesService
from schemas.messages import MessagesResponse
from schemas.response import PageSuccessResponse, SuccessResponse
from core.auth import get_current_user
from models.user import User

messages_router = APIRouter(prefix="/messages", tags=["消息相关接口"])


@messages_router.get("", response_model=PageSuccessResponse)
async def get_messages(
    chat_id: str,
    page: int = 1,
    size: int = 50,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取对话消息历史"""
    service = MessagesService(session)
    result = await service.messages(chat_id=chat_id, page=page, size=size)
    items = [MessagesResponse.model_validate(item) for item in result.items]
    return PageSuccessResponse(
        items=items,
        total=result.total,
        page=result.page,
        size=result.size
    )


@messages_router.delete("/{message_id}", response_model=SuccessResponse)
async def delete_message(
    message_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """删除消息"""
    service = MessagesService(session)
    await service.deleteMessages(id=message_id)
    return SuccessResponse(message="删除成功")
