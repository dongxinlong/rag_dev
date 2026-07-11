import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, func
from sqlalchemy.orm import DeclarativeBase


def get_uuid_id():
    uid = uuid.uuid4()
    return str(uid).replace("-", "")

class BaseModel(DeclarativeBase):
    pass


class BaseEntity:
    """
    基础实体
    """
    id = Column(String(36), primary_key=True, default=get_uuid_id)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)