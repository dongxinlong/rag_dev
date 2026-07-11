# txt_parser.py
import os
from core.parser.base import BaseParser, ParseContent


class TxtParser(BaseParser):
    """纯文本解析器"""
    
    def supported_types(self) -> list:
        return ["txt"]
    
    async def parse(self, file_path: str) -> ParseContent:
        file_name = os.path.basename(file_path)
        file_ext = "txt"
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return ParseContent(
            content=content,
            file_name=file_name,
            file_type=file_ext,
            metadata={"source": "txt_parser"}
        )
