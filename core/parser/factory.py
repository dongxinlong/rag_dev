from typing import Dict, Type
from core.parser.base import BaseParser
from core.parser.txt_parser import TxtParser
from core.parser.md_parser import MdParser
from core.parser.mineru_parser import MinerUParser


class ParserFactory:
    """解析器工厂，根据文件类型选择解析器"""
    
    _parsers: Dict[str, BaseParser] = {}
    
    @classmethod
    def register(cls, parser: BaseParser):
        """注册解析器"""
        for file_type in parser.supported_types():
            cls._parsers[file_type] = parser
    
    @classmethod
    def get_parser(cls, file_type: str) -> BaseParser:
        """获取解析器"""
        parser = cls._parsers.get(file_type.lower())
        if not parser:
            raise ValueError(f"不支持的文件类型: {file_type}")
        return parser
    
    @classmethod
    def supported_types(cls) -> list:
        """返回所有支持的文件类型"""
        return list(cls._parsers.keys())


# 注册所有解析器
ParserFactory.register(TxtParser())
ParserFactory.register(MdParser())
ParserFactory.register(MinerUParser())
