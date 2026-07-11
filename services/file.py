"""
文件相关服务
"""
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.minio import MinioClient
from models.rag import File as FileModel
from config.settings import settings


class FileService:
    """文件服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.minio_client = MinioClient()

    async def upload_file(self, file_name: str, file_content: bytes, file_ext: str, content_type: str = None) -> dict:
        """
        上传文件到 MinIO 并保存元数据

        Args:
            file_name: 文件名
            file_content: 文件内容
            file_ext: 文件扩展名
            content_type: 内容类型

        Returns:
            dict: 上传结果
        """
        # 初始化 MinIO
        await self.minio_client.init()

        # 生成文件 UUID
        file_uuid = str(uuid.uuid4())

        # 上传原始文件到 MinIO
        minio_key = f"documents/{file_uuid}/original/{file_name}"
        await self.minio_client.upload_data(
            bucket_name=settings.MINIO_BUCKET,
            object_name=minio_key,
            data=file_content,
            content_type=content_type or "application/octet-stream"
        )

        # 保存元数据到数据库
        file_record = FileModel(
            file_name=file_name,
            file_ext=file_ext,
            file_type="original",
            file_size=len(file_content),
            minio_key=minio_key,
            status="uploaded"
        )
        self.db.add(file_record)
        await self.db.commit()
        await self.db.refresh(file_record)

        return {
            "file_id": file_record.id,
            "file_name": file_name,
            "file_size": len(file_content),
            "minio_key": minio_key
        }

    async def get_file_list(self, page: int = 1, size: int = 20) -> dict:
        """
        获取文件列表

        Args:
            page: 页码
            size: 每页数量

        Returns:
            dict: 文件列表
        """
        # 查询总数
        count_stmt = select(func.count()).select_from(FileModel)
        total = (await self.db.execute(count_stmt)).scalar()

        # 查询列表
        stmt = select(FileModel).order_by(FileModel.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        files = result.scalars().all()

        return {
            "items": [
                {
                    "id": f.id,
                    "file_name": f.file_name,
                    "file_ext": f.file_ext,
                    "file_size": f.file_size,
                    "status": f.status,
                    "minio_key": f.minio_key,
                    "parsed_minio_key": f.parsed_minio_key,
                    "created_at": str(f.created_at) if f.created_at else None
                }
                for f in files
            ],
            "total": total,
            "page": page,
            "size": size
        }

    async def get_file_by_id(self, file_id: int) -> FileModel:
        """
        根据 ID 获取文件

        Args:
            file_id: 文件ID

        Returns:
            FileModel: 文件记录
        """
        return await self.db.get(FileModel, file_id)
