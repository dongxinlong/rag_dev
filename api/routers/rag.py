"""
RAG 相关接口
"""
import uuid
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from core.minio import MinioClient
from core.parser.mineru_parser import MinerUParser
from models.rag import File
from config.settings import settings
from schemas.response import SuccessResponse

router = APIRouter(prefix="/rag", tags=["RAG"])

# MinIO 客户端单例
minio_client = MinioClient()
mineru_parser = MinerUParser()


@router.post("/upload", response_model=SuccessResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    上传文件

    Args:
        file: 上传的文件

    Returns:
        SuccessResponse: 上传结果
    """
    # 初始化 MinIO
    await minio_client.init()

    # 生成文件 UUID
    file_uuid = str(uuid.uuid4())
    file_name = file.filename
    file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 上传原始文件到 MinIO
    minio_key = f"documents/{file_uuid}/original/{file_name}"
    await minio_client.upload_data(
        bucket_name=settings.MINIO_BUCKET,
        object_name=minio_key,
        data=content,
        content_type=file.content_type or "application/octet-stream"
    )

    # 保存元数据到数据库
    file_record = File(
        file_name=file_name,
        file_ext=file_ext,
        file_type="original",
        file_size=file_size,
        minio_key=minio_key,
        status="uploaded"
    )
    db.add(file_record)
    await db.commit()
    await db.refresh(file_record)

    return SuccessResponse(
        message="文件上传成功",
        data={
            "file_id": file_record.id,
            "file_name": file_name,
            "file_size": file_size,
            "minio_key": minio_key
        }
    )


@router.post("/parse/{file_id}", response_model=SuccessResponse)
async def parse_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    解析文件

    Args:
        file_id: 文件ID

    Returns:
        SuccessResponse: 解析结果
    """
    # 查询文件记录
    file_record = await db.get(File, file_id)
    if not file_record:
        return SuccessResponse(code=404, message="文件不存在")

    # 更新状态为解析中
    file_record.status = "parsing"
    await db.commit()

    try:
        # 从 MinIO 下载文件到临时目录
        import tempfile
        import os
        from config.settings import BASE_DIR

        temp_dir = os.path.join(BASE_DIR, "resources", "temp")
        os.makedirs(temp_dir, exist_ok=True)

        temp_file_path = os.path.join(temp_dir, file_record.file_name)
        await minio_client.download_file(
            bucket_name=settings.MINIO_BUCKET,
            object_name=file_record.minio_key,
            file_path=temp_file_path
        )

        # 调用 MinerU 解析
        result = await mineru_parser.parse(temp_file_path, file_id)

        # 更新文件记录
        file_record.status = "completed"
        file_record.parsed_minio_key = result.metadata.get("parsed_minio_key")
        file_record.extra_data = {
            "parsed_images": result.metadata.get("metadata_images", []),
            "content_length": len(result.content)
        }
        await db.commit()

        # 清理临时文件
        os.remove(temp_file_path)

        return SuccessResponse(
            message="文件解析成功",
            data={
                "file_id": file_id,
                "content_length": len(result.content),
                "parsed_minio_key": result.metadata.get("parsed_minio_key")
            }
        )

    except Exception as e:
        # 更新状态为失败
        file_record.status = "failed"
        file_record.error_message = str(e)
        await db.commit()
        return SuccessResponse(code=500, message=f"解析失败: {str(e)}")


@router.get("/files", response_model=SuccessResponse)
async def list_files(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取文件列表

    Args:
        page: 页码
        size: 每页数量

    Returns:
        SuccessResponse: 文件列表
    """
    from sqlalchemy import select, func

    # 查询总数
    count_stmt = select(func.count()).select_from(File)
    total = (await db.execute(count_stmt)).scalar()

    # 查询列表
    stmt = select(File).order_by(File.id.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    files = result.scalars().all()

    return SuccessResponse(
        data={
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
    )
