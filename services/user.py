"""
用户相关服务
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from core.security import hash_password, verify_password, create_access_token
from core.minio import MinioClient
from config.settings import settings


class UserService:
    """用户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.minio_client = MinioClient()

    async def register(self, username: str, email: str, password: str, nickname: str = None) -> dict:
        """用户注册"""
        # 用户名不能包含 @ 符号
        if "@" in username:
            return {"success": False, "message": "用户名不能包含@符号"}

        # 检查用户名是否已存在（包括已注销的）
        from sqlalchemy import or_
        stmt = select(User).where(
            or_(User.username == username, User.email == email),
            User.is_deleted == False
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.username == username:
                return {"success": False, "message": "用户名已存在"}
            else:
                return {"success": False, "message": "邮箱已存在"}

        # 创建用户
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            nickname=nickname or username
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return {"success": True, "user": user}

    async def login(self, username: str, password: str) -> dict:
        """用户登录（支持用户名或邮箱）"""
        # 判断是用户名还是邮箱
        if "@" in username:
            user = await self.get_by_email(username)
        else:
            user = await self.get_by_username(username)

        if not user:
            return {"success": False, "message": "用户不存在"}

        # 检查是否已删除
        if user.is_deleted:
            return {"success": False, "message": "账号已注销"}

        # 验证密码
        if not verify_password(password, user.password_hash):
            return {"success": False, "message": "密码错误"}

        # 检查是否激活
        if not user.is_active:
            return {"success": False, "message": "账号未激活"}

        # 更新登录信息
        user.last_login_at = datetime.now().isoformat()
        user.login_count += 1
        await self.db.commit()

        # 生成 Token
        token = create_access_token({"sub": str(user.id), "username": user.username})

        return {"success": True, "token": token, "user": user}

    async def get_by_id(self, user_id) -> Optional[User]:
        """根据 ID 获取用户"""
        return await self.db.get(User, user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户（过滤已删除）"""
        stmt = select(User).where(User.username == username, User.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户（过滤已删除）"""
        stmt = select(User).where(User.email == email, User.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, user_id, **kwargs) -> Optional[User]:
        """更新用户"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id, old_password: str, new_password: str) -> dict:
        """修改密码"""
        user = await self.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        if not verify_password(old_password, user.password_hash):
            return {"success": False, "message": "原密码错误"}

        user.password_hash = hash_password(new_password)
        await self.db.commit()

        return {"success": True, "message": "密码修改成功"}

    async def upload_avatar(self, user_id, file_content: bytes, file_name: str) -> dict:
        """上传头像"""
        user = await self.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        # 初始化 MinIO
        await self.minio_client.init()

        # 删除旧头像
        if user.avatar:
            try:
                await self.minio_client.remove_object(settings.MINIO_BUCKET, user.avatar)
            except Exception:
                pass

        # 上传新头像
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "jpg"
        avatar_key = f"avatars/{user_id}/avatar.{ext}"
        await self.minio_client.upload_data(
            bucket_name=settings.MINIO_BUCKET,
            object_name=avatar_key,
            data=file_content,
            content_type=f"image/{ext}"
        )

        # 更新用户头像路径（不带域名前缀）
        user.avatar = avatar_key
        await self.db.commit()
        await self.db.refresh(user)

        return {"success": True, "avatar": avatar_key}

    async def get_list(self, page: int = 1, size: int = 20, keyword: str = None) -> dict:
        """获取用户列表（过滤已删除，支持模糊搜索）"""
        from sqlalchemy import func, or_

        count_stmt = select(func.count()).select_from(User).where(User.is_deleted == False)
        stmt = select(User).where(User.is_deleted == False)

        # 模糊搜索：用户名、邮箱、昵称
        if keyword:
            like_pattern = f"%{keyword}%"
            search_condition = or_(
                User.username.ilike(like_pattern),
                User.email.ilike(like_pattern),
                User.nickname.ilike(like_pattern)
            )
            count_stmt = count_stmt.where(search_condition)
            stmt = stmt.where(search_condition)

        total = (await self.db.execute(count_stmt)).scalar()
        stmt = stmt.order_by(User.id.desc()).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return {
            "items": users,
            "total": total,
            "page": page,
            "size": size
        }

    async def delete(self, user_id) -> dict:
        """删除用户（逻辑删除）"""
        user = await self.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}

        user.is_deleted = True
        await self.db.commit()

        return {"success": True, "message": "删除成功"}

    async def toggle_active(self, user_id) -> Optional[User]:
        """切换用户状态"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # 已删除用户不能切换状态
        if user.is_deleted:
            return None

        user.is_active = not user.is_active
        await self.db.commit()
        await self.db.refresh(user)
        return user
