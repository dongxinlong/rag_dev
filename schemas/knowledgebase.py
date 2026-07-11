"""
知识库相关 Schema
"""
from pydantic import BaseModel
from typing import Optional, List, Any


# ========== 分类 ==========

class CategoryCreate(BaseModel):
    """创建分类"""
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    parent_id: int = 0
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """更新分类"""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    """分类响应"""
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    parent_id: int
    sort_order: int
    creator_id: Optional[str] = None
    creator_name: Optional[str] = None
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True


# ========== 知识库 ==========

class KnowledgeBaseCreate(BaseModel):
    """创建知识库"""
    name: str
    parent_id: int = 0
    is_folder: bool = False


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库"""
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    name: str
    file_ext: Optional[str] = None
    file_size: Optional[int] = None
    minio_key: Optional[str] = None
    parsed_minio_key: Optional[str] = None
    status: Optional[str] = None
    creator_id: str
    creator_name: Optional[str] = None
    category_id: Optional[str] = None
    is_folder: bool
    parent_id: str
    path: str
    level: int
    sort_order: int
    title: Optional[str] = None
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    size: int
