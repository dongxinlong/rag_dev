"""
用户相关接口
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import db_session
from services.user import UserService
from core.auth import get_current_user, get_current_admin_user
from core.minio import MinioClient
from models.user import User
from config.settings import settings
from schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    LoginRequest, RegisterRequest, TokenResponse,
    ChangePasswordRequest
)
from schemas.response import SuccessResponse, PageSuccessResponse, ErrorResponse

router = APIRouter(prefix="/user", tags=["用户相关接口"])

# MinIO 客户端
minio_client = MinioClient()

async def get_avatar_url(avatar_path: str) -> str:
    """获取头像的 presigned URL（带签名，可直接访问）"""
    if not avatar_path:
        return None
    await minio_client.init()
    return await minio_client.presigned_download_url(
        settings.MINIO_BUCKET,
        avatar_path
    )

@router.post("/register", response_model=SuccessResponse[UserResponse])
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(db_session.get_session)
):
    """用户注册"""
    service = UserService(session)
    result = await service.register(
        username=data.username,
        email=data.email,
        password=data.password,
        nickname=data.nickname
    )

    if not result["success"]:
        return ErrorResponse(message=result["message"])

    user = result["user"]
    avatar_url = await get_avatar_url(user.avatar)
    return SuccessResponse(
        message="注册成功",
        data=UserResponse.from_model(user, avatar_url)
    )


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(db_session.get_session)
):
    """用户登录"""
    service = UserService(session)
    result = await service.login(
        username=data.username,
        password=data.password
    )

    if not result["success"]:
        return ErrorResponse(message=result["message"])

    user = result["user"]
    avatar_url = await get_avatar_url(user.avatar)
    return SuccessResponse(
        message="登录成功",
        data=TokenResponse(
            access_token=result["token"],
            user=UserResponse.from_model(user, avatar_url)
        )
    )


@router.get("/info", response_model=SuccessResponse[UserResponse])
async def get_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    avatar_url = await get_avatar_url(current_user.avatar)
    return SuccessResponse(data=UserResponse.from_model(current_user, avatar_url))


@router.put("/info", response_model=SuccessResponse[UserResponse])
async def update_user_info(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_session.get_session)
):
    """更新当前用户信息"""
    service = UserService(session)
    user = await service.update(
        current_user.id,
        nickname=data.nickname,
        avatar=data.avatar,
        email=data.email
    )

    if not user:
        return ErrorResponse(code=404, message="用户不存在")

    avatar_url = await get_avatar_url(user.avatar)
    return SuccessResponse(data=UserResponse.from_model(user, avatar_url))


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_session.get_session)
):
    """修改密码"""
    service = UserService(session)
    result = await service.change_password(
        current_user.id,
        data.old_password,
        data.new_password
    )

    if not result["success"]:
        return ErrorResponse(message=result["message"])

    return SuccessResponse(message=result["message"])


@router.post("/avatar", response_model=SuccessResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_session.get_session)
):
    """上传头像"""
    # 读取文件内容
    content = await file.read()

    service = UserService(session)
    result = await service.upload_avatar(
        current_user.id,
        content,
        file.filename
    )

    if not result["success"]:
        return ErrorResponse(message=result["message"])

    avatar_url = await get_avatar_url(result["avatar"])
    return SuccessResponse(
        message="头像上传成功",
        data={"avatar": avatar_url}
    )


# ========== 管理员接口 ==========

@router.get("/list", response_model=PageSuccessResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query(None, description="搜索关键词（用户名/邮箱/昵称）"),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(db_session.get_session)
):
    """获取用户列表（管理员，支持模糊搜索）"""
    service = UserService(session)
    result = await service.get_list(page, size, keyword)
    items = []
    for user in result["items"]:
        avatar_url = await get_avatar_url(user.avatar)
        items.append(UserResponse.from_model(user, avatar_url))
    return PageSuccessResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"]
    )


@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(db_session.get_session)
):
    """删除用户（管理员）"""
    service = UserService(session)
    result = await service.delete(user_id)

    if not result["success"]:
        return ErrorResponse(message=result["message"])

    return SuccessResponse(message=result["message"])


@router.post("/{user_id}/toggle-active", response_model=SuccessResponse[UserResponse])
async def toggle_user_active(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(db_session.get_session)
):
    """切换用户状态（管理员）"""
    service = UserService(session)
    user = await service.toggle_active(user_id)

    if not user:
        return ErrorResponse(code=404, message="用户不存在")

    avatar_url = await get_avatar_url(user.avatar)
    return SuccessResponse(data=UserResponse.from_model(user, avatar_url))
