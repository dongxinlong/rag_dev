from typing import List, Generic, TypeVar
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select


T = TypeVar('T')


class PageData(BaseModel, Generic[T]):
    page: int
    size: int
    total: int
    items: List[T]

async def paginate(
    session: AsyncSession,
    stmt,
    page: int = 1,
    size: int = 20
) -> PageData:
    """
    通用分页器函数
    """
    # 1. 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar()

    # 2. 分页查询
    stmt = stmt.offset((page - 1) * size).limit(size) 
    result = (await session.execute(stmt)).scalars().all()

    return PageData(
        items=result,
        total=total,
        page=page,
        size=size
    )