"""
文件解析日志服务

记录文档解析过程的详细信息
"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.parse_log import ParseLog
from utils.pagination import PageData, paginate


class ParseLogService:
    """解析日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, kb_id: str, file_name: str = None, file_path: str = None, **kwargs) -> ParseLog:
        """创建日志记录"""
        log = ParseLog(
            kb_id=kb_id,
            file_name=file_name,
            file_path=file_path,
            task_status="pending",
            **kwargs
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def update(self, log_id: str, **kwargs) -> None:
        """更新日志"""
        log = await self.get_by_id(log_id)
        if not log:
            return

        for key, value in kwargs.items():
            if hasattr(log, key):
                setattr(log, key, value)

        await self.db.commit()

    async def get_by_id(self, log_id: str) -> ParseLog:
        """根据 ID 获取"""
        return await self.db.get(ParseLog, log_id)

    async def get_by_file_id(self, file_id: str) -> ParseLog:
        """根据文件 ID 获取最新日志"""
        stmt = select(ParseLog).where(
            ParseLog.file_id == file_id
        ).order_by(ParseLog.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_kb_id(self, kb_id: str) -> ParseLog:
        """根据知识库 ID 获取最新日志"""
        stmt = select(ParseLog).where(
            ParseLog.kb_id == kb_id
        ).order_by(ParseLog.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_kb_id(self, kb_id: str, file_id: str = None, page: int = 1, size: int = 20) -> PageData:
        """
        根据知识库 ID 获取日志列表

        Args:
            kb_id: 知识库 ID（必填）
            file_id: 文件 ID（可选，用于筛选特定文件）
        """
        # 简单查询，不使用关联
        stmt = select(ParseLog).where(ParseLog.kb_id == kb_id)

        # 可选：按 file_id 筛选
        if file_id:
            stmt = stmt.where(ParseLog.file_id == file_id)

        stmt = stmt.order_by(ParseLog.created_at.desc())
        return await paginate(self.db, stmt, page, size)

    async def get_file_info(self, file_ids: list) -> dict:
        """
        批量获取文件信息

        Args:
            file_ids: 文件 ID 列表

        Returns:
            {file_id: {"file_name": xxx, "kb_name": xxx}}
        """
        from models.knowledgebase import KnowledgeBase, KnowledgeCategory

        if not file_ids:
            return {}

        # 查询文件信息和分类名称
        stmt = select(
            KnowledgeBase.id,
            KnowledgeBase.name,
            KnowledgeCategory.name
        ).outerjoin(
            KnowledgeCategory,
            KnowledgeBase.category_id == KnowledgeCategory.id
        ).where(KnowledgeBase.id.in_(file_ids))

        result = await self.db.execute(stmt)
        return {
            row[0]: {"file_name": row[1], "kb_name": row[2]}
            for row in result.all()
        }

    # ============ 便捷方法 ============

    async def start_task(self, log_id: str, task_id: str) -> None:
        """开始任务"""
        await self.update(
            log_id,
            task_id=task_id,
            task_status="started",
            stage="initializing",
            stage_message="任务开始"
        )

    async def update_stage(self, log_id: str, stage: str, message: str = None) -> None:
        """更新阶段"""
        await self.update(
            log_id,
            stage=stage,
            stage_message=message
        )

    async def complete_task(self, log_id: str) -> None:
        """完成任务"""
        await self.update(
            log_id,
            task_status="success",
            stage="completed",
            stage_message="处理完成"
        )

    async def fail_task(self, log_id: str, error_message: str = None, error_stage: str = None) -> None:
        """任务失败"""
        await self.update(
            log_id,
            task_status="failed",
            stage="failed",
            error_message=error_message,
            error_stage=error_stage
        )

    async def add_error(self, log_id: str, stage: str, message: str, error_type: str = None) -> None:
        """
        添加错误记录（追加到 errors JSON 数组）

        Args:
            log_id: 日志 ID
            stage: 错误阶段
            message: 错误信息
            error_type: 错误类型（如：mineru_error, image_error, timeout）
        """
        log = await self.get_by_id(log_id)
        if not log:
            return

        # 初始化 errors 列表
        errors = log.errors or []

        # 追加新错误
        errors.append({
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "message": message,
            "error_type": error_type
        })

        # 更新
        log.errors = errors
        await self.db.commit()

    async def update_mineru_info(self, log_id: str, **kwargs) -> None:
        """更新 MinerU 解析信息"""
        update_data = {}
        for key, value in kwargs.items():
            update_data[f"mineru_{key}"] = value
        await self.update(log_id, **update_data)

    async def update_image_info(self, log_id: str, **kwargs) -> None:
        """更新图片处理信息"""
        update_data = {}
        for key, value in kwargs.items():
            update_data[f"image_{key}"] = value
        await self.update(log_id, **update_data)
