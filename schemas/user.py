"""
用户相关 Schema
"""
import re
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any

# 正则规则（前端可直接复用）
USERNAME_REGEX = r'^[a-zA-Z][a-zA-Z0-9_]{2,19}$'
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$'


def validate_username(v: str) -> str:
    """验证用户名：字母开头，3-20位，只能包含字母、数字、下划线"""
    if not re.match(USERNAME_REGEX, v):
        raise ValueError('用户名：字母开头，3-20位，只能包含字母、数字、下划线')
    return v


def validate_password(v: str) -> str:
    """验证密码：8-20位，必须包含大小写字母、数字、特殊字符"""
    if not re.match(PASSWORD_REGEX, v):
        raise ValueError('密码：8-20位，必须包含大小写字母、数字、特殊字符（@$!%*?&）')
    return v


class UserCreate(BaseModel):
    """注册请求"""
    username: str
    email: EmailStr
    password: str
    nickname: Optional[str] = None

    _validate_username = field_validator('username')(validate_username)
    _validate_password = field_validator('password')(validate_password)


class UserUpdate(BaseModel):
    """更新用户信息"""
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, user, avatar_url: str = None):
        """从 User 模型创建，avatar_url 为 presigned URL"""
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname,
            "avatar": avatar_url if avatar_url else user.avatar,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        }
        return cls(**data)


class LoginRequest(BaseModel):
    """登录请求（用户名或邮箱）"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    email: EmailStr
    password: str
    nickname: Optional[str] = None

    _validate_username = field_validator('username')(validate_username)
    _validate_password = field_validator('password')(validate_password)


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    """修改密码"""
    old_password: str
    new_password: str

    _validate_new_password = field_validator('new_password')(validate_password)


class ResetPasswordRequest(BaseModel):
    """重置密码"""
    email: EmailStr
