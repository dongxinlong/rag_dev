from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag import RAGService
from schemas.rag import RAGQueryRequest, RAGQueryResponse
from schemas.response import SuccessResponse
from database.session import db_session
from api.dependencies.services import get_llm_api_service, get_db_session, get_embedding_service
from core.llm import LLMAPIService
from core.embedding import EmbeddingService
from database.session import DatabaseSession
from core.auth import get_current_user
from models.user import User


rag_router = APIRouter(prefix="/rag", tags=["RAG相关接口"])


@rag_router.get("/query", response_model=SuccessResponse[RAGQueryResponse])
async def rag_query(
    request: Request,
    chat_id: str,
    question: str,
    top_k: int = 5,
    session: AsyncSession = Depends(db_session.get_session),
    llm: LLMAPIService = Depends(get_llm_api_service),
    embedding: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(get_current_user)
):
    rag_service = RAGService(llm, session, embedding, request)
    result = await rag_service.rag_query(
        chat_id=chat_id,
        question=question,
        top_k=top_k
    )
    result["cost"] = float(result["cost"])
    return SuccessResponse(data=result)

@rag_router.get("/query/stream")
async def rag_query_stream(
    request: Request,
    chat_id: str,
    question: str,
    top_k: int = 5,
    llm: LLMAPIService = Depends(get_llm_api_service),
    embedding: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(get_current_user)
):
    async def stream_generator():
        # 流式请求需要在生成器内部创建独立的 session
        async with db_session.session_factory() as session:
            try:
                rag_service = RAGService(llm, session, embedding, request)
                async for chunk in rag_service.rag_query_stream(
                    chat_id=chat_id,
                    question=question,
                    top_k=top_k
                ):
                    yield chunk
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'value': str(e)})}\n\n"
            finally:
                await session.close()

    import json
    return StreamingResponse(stream_generator(), media_type="text/event-stream")