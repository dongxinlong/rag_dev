"""
任务模块

所有 Celery 任务放在这里，按业务拆分到不同文件：
- document.py: 文档处理任务
- knowledge.py: 知识库任务
"""
from tasks.document import process_document

__all__ = ["process_document"]
