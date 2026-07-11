from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional

class MessagesCreate(BaseModel):
    chat_id: str = Field(..., description="聊天ID")
    role: str = Field(..., description="角色")
    content: str = Field(..., description="内容")
    tokens_prompt: int = Field(..., description="提示词消耗的token数")
    tokens_completion: int = Field(..., description="生成内容消耗的token数")
    model: str = Field(..., description="模型名称")
    cost: Decimal = Field(..., description="消耗的费用")
    extra_data: Optional[dict] = None
    cache_tokens: int = Field(..., description="缓存token数")
    exchange_id: int = Field(..., description="对话轮次")


class MessagesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chat_id: str = Field(..., description="聊天ID")
    role: str = Field(..., description="角色")
    content: str = Field(..., description="内容")
    tokens_prompt: int = Field(..., description="提示词消耗的token数")
    tokens_completion: int = Field(..., description="生成内容消耗的token数")
    cache_tokens: int = Field(..., description="缓存token数")
    model: str = Field(..., description="模型名称")
    cost: Decimal = Field(..., description="消耗的费用")
    extra_data: Optional[dict] = None
    status: str = Field(..., description="状态")
    created_at: datetime
    updated_at: datetime

