"""
知识库相关模型
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime
from models.base import BaseModel, BaseEntity


class KnowledgeCategory(BaseModel, BaseEntity):
    """知识库分类表"""
    __tablename__ = "knowledge_categories"

    name = Column(String(100), nullable=False, comment="分类名称")
    description = Column(Text, comment="分类描述")
    icon = Column(String(100), comment="图标")
    parent_id = Column(Integer, default=0, comment="父分类ID，0表示顶级分类")
    sort_order = Column(Integer, default=0, comment="排序")
    creator_id = Column(String(36), comment="创建人ID")


class KnowledgeBase(BaseModel, BaseEntity):
    """知识库表"""
    __tablename__ = "knowledge_bases"

    # 基本信息
    name = Column(String(255), nullable=False, comment="文件名")
    file_ext = Column(String(20), nullable=False, comment="文件扩展名")
    file_size = Column(Integer, comment="文件大小(字节)")

    # MinIO 存储
    minio_key = Column(String(500), nullable=False, comment="原始文件 MinIO 路径")
    parsed_minio_key = Column(String(500), comment="解析后 MD MinIO 路径")
    metadata_minio_key = Column(String(500), comment="元数据(图片) MinIO 路径")

    # 状态
    status = Column(String(20), default="pending", comment="pending/parsing/completed/failed")
    error_message = Column(Text, comment="失败原因")

    # 创建人
    creator_id = Column(String(36), nullable=False, comment="创建人ID")

    # 分类关联
    category_id = Column(String(36), comment="关联分类ID")

    # 文件夹功能
    is_folder = Column(Boolean, default=False, comment="是否是文件夹")
    parent_id = Column(String(36), default="0", comment="父文件夹ID，0表示顶级")
    path = Column(String(500), default="/", comment="完整路径")
    level = Column(Integer, default=0, comment="层级")
    sort_order = Column(Integer, default=0, comment="排序")

    # 元数据
    title = Column(String(255), comment="文档标题")
    extra_data = Column(Text, comment="扩展元数据(JSON)")

    # 回收站
    deleted_at = Column(DateTime, comment="删除时间")
    deleted_by = Column(String(36), comment="删除人ID")
