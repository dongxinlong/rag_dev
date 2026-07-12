"""
文件解析日志 Schema
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ParseLogResponse(BaseModel):
    """解析日志响应"""
    model_config = ConfigDict(from_attributes=True)

    # ============ 基本信息 ============
    id: str
    kb_id: str
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    kb_name: Optional[str] = None  # 知识库名称

    # ============ Celery 任务信息 ============
    task_id: Optional[str] = None
    task_status: Optional[str] = None
    task_retry_count: Optional[int] = None

    # ============ 处理阶段 ============
    stage: Optional[str] = None
    stage_message: Optional[str] = None

    # ============ MinerU 解析信息 ============
    mineru_status: Optional[str] = None
    mineru_start_time: Optional[datetime] = None
    mineru_end_time: Optional[datetime] = None
    mineru_duration: Optional[float] = None
    mineru_output_chars: Optional[int] = None
    mineru_error: Optional[str] = None

    # ============ 图片处理信息 ============
    image_status: Optional[str] = None
    image_total_count: Optional[int] = None
    image_processed_count: Optional[int] = None
    image_success_count: Optional[int] = None
    image_failed_count: Optional[int] = None
    image_skipped_count: Optional[int] = None
    image_start_time: Optional[datetime] = None
    image_end_time: Optional[datetime] = None
    image_duration: Optional[float] = None

    # ============ MinIO 存储信息 ============
    minio_status: Optional[str] = None
    minio_original_key: Optional[str] = None
    minio_parsed_key: Optional[str] = None
    minio_result_key: Optional[str] = None

    # ============ 输出信息 ============
    result_chars: Optional[int] = None

    # ============ 错误信息 ============
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None

    # ============ 性能信息 ============
    total_duration: Optional[float] = None

    # ============ 时间 ============
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
