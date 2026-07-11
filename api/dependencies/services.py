"""
依赖注入
"""

from core.llm import LLMAPIService
from core.embedding import EmbeddingService
from database.session import DatabaseSession
from database.session import db_session


def get_db_session() -> DatabaseSession:
    return db_session

def get_llm_api_service() -> LLMAPIService:
    return LLMAPIService()

def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()   
