from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union

from database.session import db_session
from schemas.chat import ChatCreate, ChatResponse
from schemas.response import SuccessResponse, PageSuccessResponse, ErrorResponse
from services.chat import ChatService

chat_router = APIRouter()


@chat_router.post("/chats", response_model=SuccessResponse[ChatResponse])
async def create_chat(chat: ChatCreate, session: AsyncSession = Depends(db_session.get_session)):
    service = ChatService(session)
    result = await service.createChat(title=chat.title)
    return SuccessResponse(data=result)

@chat_router.get("/chats", response_model=PageSuccessResponse[ChatResponse])
async def get_chats(title: Union[str, None] = None, page: int = 1, size: int = 20, session: AsyncSession = Depends(db_session.get_session)):
    service = ChatService(session)
    result = await service.chats(title=title, page=page, size=size)
    return PageSuccessResponse(
        page=result.page,
        size=result.size,
        total=result.total,
        items=result.items
    )

@chat_router.delete("/chats/{chat_id}", response_model=SuccessResponse[bool])
async def delete_chat(chat_id: str, session: AsyncSession = Depends(db_session.get_session)):
    service = ChatService(session)
    result = await service.deleteChat(chat_id=chat_id)
    return SuccessResponse(data=result)

@chat_router.put("/chats/{chat_id}", response_model=SuccessResponse[bool])
async def update_chat(chat_id: str, title: str, session: AsyncSession = Depends(db_session.get_session)):
    service = ChatService(session)
    result = await service.updateChat(chat_id=chat_id, title=title)
    return SuccessResponse(data=result)