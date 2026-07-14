from sqlalchemy import Column, String, Integer, Text, JSON, DECIMAL, Boolean
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR
from models.base import BaseModel, BaseEntity


class Document(BaseModel, BaseEntity):
    __tablename__ = "documents"

    # ============ 物理关联 ============
    file_id = Column(String(36), nullable=False, comment="关联知识库文件ID")

    # ============ 文档基本信息 ============
    file_name = Column(String(500), nullable=False, comment="文件名")
    file_type = Column(String(20), nullable=False, comment="文件类型: txt, doc, docx, pdf, md, xlsx")

    # ============ 切片内容 ============
    content = Column(Text, nullable=False, comment="切片内容")
    embedding = Column(Vector(2560), nullable=False, comment="向量")

    # ============ 全文搜索 ============
    search_vector = Column(TSVECTOR, comment="全文搜索向量（用于BM25）")

    # ============ 位置信息 ============
    chunk_index = Column(Integer, comment="块在文档中的序号")
    heading = Column(String(255), comment="所属标题")
    heading_level = Column(Integer, comment="标题级别(1-6)")
    heading_path = Column(JSON, comment="完整标题路径")

    # ============ 统计信息 ============
    token_count = Column(Integer, comment="token数量")
    char_count = Column(Integer, comment="字符数量")

    # ============ 分块元数据 ============
    chunk_strategy = Column(String(50), comment="分块策略: paragraph/sentence/atomic/merged")
    is_atomic = Column(Boolean, default=False, comment="是否原子块")


class Chat(BaseModel, BaseEntity):
    __tablename__ = "chats"

    title = Column(String(255), default="新对话", nullable=False, comment="聊天标题")


class Messages(BaseModel, BaseEntity):
    __tablename__ = "messages"

    chat_id = Column(String(255), nullable=False, comment="聊天ID")
    role = Column(String(20), nullable=False, comment="角色: user, assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    tokens_prompt = Column(Integer, default=0, comment="输入token数")
    tokens_completion = Column(Integer, default=0, comment="输出token数")
    cache_tokens = Column(Integer, default=0, comment="缓存token数")
    model = Column(String(20), nullable=False, comment="模型类型")
    cost = Column(DECIMAL(12, 6), default=0, comment="消费成本")
    extra_data = Column(JSON, default={}, comment="元数据")
    status = Column(String(20), default="generating", comment="状态: generating, complated, failed")
    exchange_id = Column(Integer, default=0, comment="对话轮次")  # 用来解决上下文污染，一个问题回答有问题，则本轮的用户问题+ai回复，再检索时都要过滤掉