from sqlalchemy import Column, String, Integer, Text, JSON, DECIMAL
from pgvector.sqlalchemy import Vector
from models.base import BaseModel, BaseEntity


class Document(BaseModel, BaseEntity):
    __tablename__ = "documents"

    # 物理关联（不使用级联）
    file_id = Column(Integer, nullable=False, comment="关联文件ID")

    # 文档基本信息
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_type = Column(String(20), nullable=False, comment="文件类型: txt, doc, docx, pdf, md, xlsx")

    # 切片内容
    content = Column(Text, nullable=False, comment="切片内容")
    embedding = Column(Vector(2560), nullable=False, comment="向量")

    # 位置信息
    chunk_index = Column(Integer, comment="块索引")
    page_number = Column(Integer, comment="页码(pdf/excel)")

    # 文档元数据
    title = Column(String(255), comment="文档标题")
    author = Column(String(100), comment="作者")


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