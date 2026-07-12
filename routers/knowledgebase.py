"""
知识库相关接口
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import db_session
from services.knowledgebase import KnowledgeBaseService, KnowledgeCategoryService
from schemas.knowledgebase import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    KnowledgeBaseUpdate, KnowledgeBaseResponse
)
from schemas.response import SuccessResponse, PageSuccessResponse, ErrorResponse
from core.auth import get_current_user
from models.user import User
from config.settings import settings

router = APIRouter(prefix="/knowledge", tags=["知识库相关接口"])


# ========== 分类接口 ==========

@router.post("/category", response_model=SuccessResponse[CategoryResponse])
async def create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """创建分类"""
    service = KnowledgeCategoryService(session)
    category = await service.create(
        name=data.name,
        description=data.description,
        icon=data.icon,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
        creator_id=str(current_user.id)
    )
    return SuccessResponse(data=CategoryResponse.model_validate(category))


@router.get("/category/list", response_model=PageSuccessResponse[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query(None, description="搜索关键词"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取分类列表（支持模糊搜索）"""
    service = KnowledgeCategoryService(session)
    result = await service.get_list(page, size, keyword)
    items = [CategoryResponse.model_validate(item) for item in result["items"]]
    return PageSuccessResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"]
    )


@router.put("/category/{category_id}", response_model=SuccessResponse[CategoryResponse])
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """更新分类"""
    service = KnowledgeCategoryService(session)
    result = await service.update(
        category_id,
        user_id=str(current_user.id),
        name=data.name,
        description=data.description,
        icon=data.icon,
        parent_id=data.parent_id,
        sort_order=data.sort_order
    )
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(data=CategoryResponse.model_validate(result["data"]))


@router.delete("/category/{category_id}", response_model=SuccessResponse)
async def delete_category(
    category_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """删除分类"""
    service = KnowledgeCategoryService(session)
    result = await service.delete(category_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(message=result["message"])


# ========== 知识库接口 ==========

@router.post("/folder", response_model=SuccessResponse[KnowledgeBaseResponse])
async def create_folder(
    name: str,
    parent_id: str = Query("0"),
    category_id: str = Query(None, description="分类ID"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """创建文件夹"""
    service = KnowledgeBaseService(session)
    try:
        folder = await service.create_folder(
            name,
            creator_id=str(current_user.id),
            parent_id=parent_id,
            category_id=category_id
        )
        return SuccessResponse(data=KnowledgeBaseResponse.model_validate(folder))
    except ValueError as e:
        return ErrorResponse(message=str(e))


@router.post("/upload", response_model=SuccessResponse[KnowledgeBaseResponse])
async def upload_file(
    file: UploadFile = File(...),
    parent_id: str = Query("0"),
    category_id: str = Query(None, description="分类ID"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """上传文件"""
    service = KnowledgeBaseService(session)

    # 读取文件内容
    content = await file.read()
    # 提取纯文件名，去掉路径
    file_name = file.filename.split("/")[-1].split("\\")[-1]
    file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    # 支持解析的格式
    SUPPORTED_FORMATS = ["pdf", "docx", "pptx", "xlsx", "txt", "md", "csv"]

    try:
        kb = await service.upload_file(
            file_name=file_name,
            file_content=content,
            file_ext=file_ext,
            creator_id=str(current_user.id),
            parent_id=parent_id,
            category_id=category_id,
            content_type=file.content_type
        )

        # 只有支持的格式才触发 Celery 异步任务
        if file_ext in SUPPORTED_FORMATS:
            from tasks.document import process_document
            from config.logging import get_logger
            logger = get_logger("knowledgebase.upload")

            logger.info(f"准备提交 Celery 任务: kb_id={category_id}, file_id={kb.id}, file_path={kb.minio_key}")
            task = process_document.delay(
                kb_id=category_id,  # 知识库 ID（分类 ID）
                file_path=kb.minio_key,
                file_id=str(kb.id)  # 文件 ID
            )
            logger.info(f"Celery 任务已提交: task_id={task.id}")

            return SuccessResponse(
                data=KnowledgeBaseResponse.model_validate(kb),
                message="上传成功，文档处理任务已提交"
            )
        else:
            # 不支持的格式，只上传不解析
            return SuccessResponse(
                data=KnowledgeBaseResponse.model_validate(kb),
                message=f"上传成功（{file_ext} 格式不支持文档解析，仅存储文件）"
            )
    except ValueError as e:
        return ErrorResponse(message=str(e))


@router.get("/search", response_model=PageSuccessResponse[KnowledgeBaseResponse])
async def search_knowledge_base(
    keyword: str = Query(..., description="搜索关键词"),
    category_id: str = Query(None, description="分类ID"),
    parent_id: str = Query(None, description="父文件夹ID（指定搜索范围）"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """搜索文件/文件夹（Windows 风格，平铺返回）"""
    service = KnowledgeBaseService(session)
    result = await service.search(keyword, category_id, parent_id, page, size)
    items = [KnowledgeBaseResponse.model_validate(item) for item in result.items]
    return PageSuccessResponse(
        items=items,
        total=result.total,
        page=result.page,
        size=result.size
    )


@router.get("/list", response_model=PageSuccessResponse[KnowledgeBaseResponse])
async def list_knowledge_base(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    parent_id: str = Query("0"),
    category_id: str = Query(None, description="分类ID"),
    keyword: str = Query(None, description="搜索关键词"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取知识库列表（分页，支持模糊搜索）"""
    service = KnowledgeBaseService(session)
    result = await service.get_list(page, size, parent_id, category_id, keyword)
    items = [KnowledgeBaseResponse.model_validate(item) for item in result.items]
    return PageSuccessResponse(
        items=items,
        total=result.total,
        page=result.page,
        size=result.size
    )


# 不可预览的文件类型
NOT_PREVIEWABLE = {
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz",
    "exe", "dll", "so", "bin", "dat",
    "mp3", "mp4", "avi", "mov", "wmv", "flv",
    "psd", "ai", "sketch"
}


@router.get("/preview/{kb_id}")
async def preview_file(
    kb_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """预览文件（返回 presigned URL）"""
    from core.minio import MinioClient

    service = KnowledgeBaseService(session)
    kb = await service.get_by_id(kb_id)

    if not kb:
        return ErrorResponse(code=404, message="文件不存在")

    # 检查是否可预览（忽略大小写）
    if kb.file_ext and kb.file_ext.lower() in NOT_PREVIEWABLE:
        return ErrorResponse(code=400, message="该文件类型不支持预览")

    if not kb.minio_key:
        return ErrorResponse(code=400, message="文件无 MinIO 路径")

    # 生成 presigned URL
    minio_client = MinioClient()
    await minio_client.init()
    url = await minio_client.presigned_download_url(
        settings.MINIO_BUCKET,
        kb.minio_key
    )

    return SuccessResponse(data={"url": url, "name": kb.name, "ext": kb.file_ext})


@router.get("/navigation/{kb_id}", response_model=SuccessResponse)
async def get_navigation(
    kb_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取面包屑导航路径"""
    service = KnowledgeBaseService(session)
    navigation = await service.get_navigation(kb_id)
    return SuccessResponse(data=navigation)


@router.post("/rename", response_model=SuccessResponse[KnowledgeBaseResponse])
async def rename_knowledge_base(
    kb_id: str = Query(..., description="要重命名的文件/文件夹ID"),
    new_name: str = Query(..., description="新名称"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """重命名文件/文件夹"""
    service = KnowledgeBaseService(session)
    result = await service.rename(kb_id, new_name, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(data=KnowledgeBaseResponse.model_validate(result["data"]))


@router.get("/folder-tree", response_model=SuccessResponse)
async def get_folder_tree(
    parent_id: str = Query("0"),
    category_id: str = Query(None),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取文件夹树（用于选择目标路径）"""
    service = KnowledgeBaseService(session)
    tree = await service.get_folder_tree(parent_id, category_id)
    return SuccessResponse(data=tree)


@router.post("/move", response_model=SuccessResponse[KnowledgeBaseResponse])
async def move_knowledge_base(
    kb_id: str = Query(..., description="要移动的文件/文件夹ID"),
    target_parent_id: str = Query(..., description="目标文件夹ID"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """移动文件/文件夹"""
    service = KnowledgeBaseService(session)
    result = await service.move(kb_id, target_parent_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(data=KnowledgeBaseResponse.model_validate(result["data"]))


@router.post("/copy", response_model=SuccessResponse[KnowledgeBaseResponse])
async def copy_knowledge_base(
    kb_id: str = Query(..., description="要复制的文件/文件夹ID"),
    target_parent_id: str = Query(..., description="目标文件夹ID"),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """复制文件/文件夹"""
    service = KnowledgeBaseService(session)
    result = await service.copy(kb_id, target_parent_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(data=KnowledgeBaseResponse.model_validate(result["data"]))


@router.get("/tree", response_model=SuccessResponse)
async def get_tree(
    parent_id: int = Query(0),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取树形结构"""
    service = KnowledgeBaseService(session)
    tree = await service.get_tree(parent_id)
    return SuccessResponse(data=tree)


# ========== 回收站接口（必须在 /{kb_id} 前面）==========

@router.get("/recycle-bin", response_model=PageSuccessResponse)
async def get_recycle_bin(
    keyword: str = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取回收站列表"""
    service = KnowledgeBaseService(session)
    result = await service.get_recycle_bin(
        user_id=str(current_user.id),
        keyword=keyword,
        page=page,
        size=size
    )
    items = [KnowledgeBaseResponse.model_validate(item) for item in result.items]
    return PageSuccessResponse(items=items, total=result.total, page=result.page, size=result.size)


@router.post("/recycle-bin/{kb_id}/restore", response_model=SuccessResponse)
async def restore_from_recycle_bin(
    kb_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """从回收站恢复"""
    service = KnowledgeBaseService(session)
    result = await service.restore(kb_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(message=result["message"])


@router.delete("/recycle-bin/{kb_id}", response_model=SuccessResponse)
async def permanent_delete(
    kb_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """彻底删除（删除 MinIO 文件 + 数据库记录）"""
    service = KnowledgeBaseService(session)
    result = await service.permanent_delete(kb_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(message=result["message"])


@router.delete("/recycle-bin/clear", response_model=SuccessResponse)
async def clear_recycle_bin(
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """清空回收站"""
    service = KnowledgeBaseService(session)
    result = await service.clear_recycle_bin(str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(message=result["message"])


@router.get("/{kb_id}", response_model=SuccessResponse[KnowledgeBaseResponse])
async def get_knowledge_base(
    kb_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """获取知识库详情"""
    service = KnowledgeBaseService(session)
    kb = await service.get_by_id(kb_id)
    if not kb:
        return ErrorResponse(code=404, message="知识库不存在")
    return SuccessResponse(data=KnowledgeBaseResponse.model_validate(kb))


@router.put("/{kb_id}", response_model=SuccessResponse[KnowledgeBaseResponse])
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """更新知识库"""
    service = KnowledgeBaseService(session)
    result = await service.update(
        kb_id,
        user_id=str(current_user.id),
        name=data.name,
        parent_id=data.parent_id,
        sort_order=data.sort_order
    )
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(data=KnowledgeBaseResponse.model_validate(result["data"]))


@router.delete("/{kb_id}", response_model=SuccessResponse)
async def delete_knowledge_base(
    kb_id: str,
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """删除知识库（级联删除子项）"""
    service = KnowledgeBaseService(session)
    result = await service.delete(kb_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(message=result["message"])


@router.post("/{kb_id}/move", response_model=SuccessResponse[KnowledgeBaseResponse])
async def move_knowledge_base(
    kb_id: str,
    target_parent_id: str = "0",
    session: AsyncSession = Depends(db_session.get_session),
    current_user: User = Depends(get_current_user)
):
    """移动到目标文件夹"""
    service = KnowledgeBaseService(session)
    result = await service.move(kb_id, target_parent_id, str(current_user.id))
    if not result["success"]:
        return ErrorResponse(message=result["message"])
    return SuccessResponse(data=KnowledgeBaseResponse.model_validate(result["data"]))
