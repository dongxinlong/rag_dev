import os

from abc import ABC, abstractmethod
from typing import List, Dict


class BaseSplitter:
    """
    文档切分器抽象基类
    """
    @abstractmethod
    def split(self, file_path: str) -> List[Dict]:
        """
        将单个文件切分为多个 chunk

        :param file_path: 文件路径
        :return: chunk 列表
        """
        raise NotImplementedError

    def split_batch(self, file_paths: List[str]) -> List[Dict]:
        """
        批量切分文件（可选工具方法）
        """
        results = []
        for path in file_paths:
            results.extend(self.split(path))
        return results
    
    @staticmethod
    def _read_text(file_path: str) -> str:
        """
        基础文本读取（可被子类覆盖）
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
        
    @staticmethod
    def _default_metadata(file_path: str) -> Dict:
        """
        生成默认元数据
        """
        return {
            "file_name": os.path.basename(file_path),
            "file_type": os.path.splitext(file_path)[1][1:],
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "author": None
        }