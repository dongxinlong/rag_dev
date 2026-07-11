"""
文档解析器
"""
from pydantic import BaseModel
from typing import Optional
from abc import ABC, abstractmethod


class ParseContent(BaseModel):
    """
    解析结果统一格式
    """
    content: str  # Markdown内容
    file_name: str   # 文件名
    file_type: str  # 文件类型
    page_count: Optional[int] = None  # 页数
    metadata: Optional[dict] = None  # 元数据


class BaseParser(ABC):
    """
    解析器基类
    """
    @abstractmethod
    async def parse(self, file_path: str) -> ParseContent:
        """
        解析文件内容
        :param file_path: 文件路径
        :return: 解析结果
        """
        pass

    @abstractmethod
    def supported_types(self) -> list:
        """
        支持的文件类型
        """
        pass
