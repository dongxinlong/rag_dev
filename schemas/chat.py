from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ChatCreate(BaseModel):
    title: str = Field(default="新对话", description="聊天标题")


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


