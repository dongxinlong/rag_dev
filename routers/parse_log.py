"""
文件解析日志接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import db_session
from services.parse_log import ParseLogService
from schemas.parse_log import ParseLogResponse
from schemas.response import PageSuccessResponse
from core.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/parse-logs", tags=["文件解析日志"])


@router.get("", response_model=PageSuccessResponse)
async def get_parse_logs(
    kb_id: str = Query(..., description="知识库 ID（必填）"),
    file_id: str = Query(None, description="文件 ID（可选）"),
    status: str = Query(None, description="任务状态（可选）：success/failed/pending"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取解析日志列表

    Args:
        kb_id: 知识库 ID（必填）
        file_id: 文件 ID（可选）
        status: 任务状态（可选）：success/failed/pending
    """
    service = ParseLogService(session)
    result = await service.list_by_kb_id(kb_id=kb_id, file_id=file_id, status=status, page=page, size=size)

    # 批量获取文件信息
    file_ids = [item.file_id for item in result.items if item.file_id]
    file_info = await service.get_file_info(file_ids)

    # 构造响应
    items = []
    for log in result.items:
        response = ParseLogResponse.model_validate(log)
        info = file_info.get(log.file_id, {})
        response.file_name = info.get("file_name")
        response.kb_name = info.get("kb_name")
        items.append(response)

    return PageSuccessResponse(
        items=items,
        total=result.total,
        page=result.page,
        size=result.size
    )
