from typing import Any, TypeVar, List, Generic, Optional
from pydantic import BaseModel

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None


class PageSuccessResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    page: int
    size: int
    total: int
    items: List[T]


class ErrorResponse(BaseModel):
    code: int = 400
    message: str = "Error"
    data: Any = None