"""
用户相关模型
"""
from sqlalchemy import Column, String, Integer, Text, Boolean
from models.base import BaseModel, BaseEntity


class User(BaseModel, BaseEntity):
    """用户表"""
    __tablename__ = "users"

    # 基本信息
    username = Column(String(50), nullable=False, unique=True, comment="用户名")
    email = Column(String(100), nullable=False, unique=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(50), comment="昵称")
    avatar = Column(String(500), comment="头像(MinIO路径)")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")

    # 登录信息
    last_login_at = Column(String(30), comment="最后登录时间")
    login_count = Column(Integer, default=0, comment="登录次数")
