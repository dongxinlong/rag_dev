"""
文件解析日志模型

记录文档解析过程的详细信息
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, JSON
from models.base import BaseModel, BaseEntity


class ParseLog(BaseModel, BaseEntity):
    """文件解析日志表"""
    __tablename__ = "parse_logs"

    # ============ 基本信息 ============
    kb_id = Column(String(36), nullable=False, index=True, comment="关联知识库 ID")
    file_id = Column(String(36), index=True, comment="关联文件 ID")
    file_name = Column(String(255), comment="文件名")
    file_path = Column(String(500), comment="MinIO 文件路径")

    # ============ Celery 任务信息 ============
    task_id = Column(String(255), comment="Celery 任务 ID")
    task_status = Column(String(20), default="pending", comment="任务状态: pending/started/success/failed/retry")
    task_retry_count = Column(Integer, default=0, comment="重试次数")

    # ============ 处理阶段 ============
    stage = Column(String(50), comment="当前阶段: uploading/parsing/image_processing/saving/completed")
    stage_message = Column(Text, comment="阶段描述")

    # ============ MinerU 解析信息 ============
    mineru_status = Column(String(20), comment="MinerU 状态: pending/processing/completed/failed")
    mineru_start_time = Column(DateTime, comment="MinerU 开始时间")
    mineru_end_time = Column(DateTime, comment="MinerU 结束时间")
    mineru_duration = Column(Float, comment="MinerU 耗时(秒)")
    mineru_output_chars = Column(Integer, comment="MinerU 输出字符数")
    mineru_error = Column(Text, comment="MinerU 错误信息")

    # ============ 图片处理信息 ============
    image_status = Column(String(20), comment="图片处理状态: pending/processing/completed/failed/skipped")
    image_total_count = Column(Integer, default=0, comment="图片总数")
    image_processed_count = Column(Integer, default=0, comment="已处理图片数")
    image_success_count = Column(Integer, default=0, comment="成功处理数")
    image_failed_count = Column(Integer, default=0, comment="失败处理数")
    image_skipped_count = Column(Integer, default=0, comment="跳过数")
    image_start_time = Column(DateTime, comment="图片处理开始时间")
    image_end_time = Column(DateTime, comment="图片处理结束时间")
    image_duration = Column(Float, comment="图片处理耗时(秒)")

    # ============ MinIO 存储信息 ============
    minio_status = Column(String(20), comment="MinIO 状态: pending/uploading/completed/failed")
    minio_original_key = Column(String(500), comment="原始文件 MinIO 路径")
    minio_parsed_key = Column(String(500), comment="解析文件 MinIO 路径")
    minio_result_key = Column(String(500), comment="最终文件 MinIO 路径")
    minio_images_key = Column(String(500), comment="图片目录 MinIO 路径")

    # ============ 输出信息 ============
    result_chars = Column(Integer, comment="最终文件字符数")
    result_md5 = Column(String(32), comment="最终文件 MD5")

    # ============ 错误信息 ============
    error_code = Column(String(50), comment="错误码")
    error_message = Column(Text, comment="错误信息")
    error_stack = Column(Text, comment="错误堆栈")
    error_stage = Column(String(50), comment="出错阶段")
    errors = Column(JSON, comment="所有错误记录(JSON 数组)")

    # ============ 分块信息 ============
    chunk_status = Column(String(20), comment="分块状态: pending/processing/completed/failed")
    chunk_count = Column(Integer, default=0, comment="分块数量")

    # ============ 性能信息 ============
    total_duration = Column(Float, comment="总耗时(秒)")
    memory_usage = Column(Integer, comment="内存使用(MB)")

    # ============ 扩展信息 ============
    extra_data = Column(JSON, comment="扩展信息(JSON)")

    def __repr__(self):
        return f"<ParseLog(id={self.id}, kb_id={self.kb_id}, status={self.task_status})>"
