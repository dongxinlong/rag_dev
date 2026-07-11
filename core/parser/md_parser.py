# md_parser.py
import os
from core.parser.base import BaseParser, ParseContent


class MdParser(BaseParser):
    """Markdown 解析器"""
    
    def supported_types(self) -> list:
        return ["md"]
    
    async def parse(self, file_path: str) -> ParseContent:
        file_name = os.path.basename(file_path)
        file_ext = "md"
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return ParseContent(
            content=content,
            file_name=file_name,
            file_type=file_ext,
            metadata={"source": "md_parser"}
        )
