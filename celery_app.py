"""
Celery 应用配置

使用方式：
1. 启动 Worker: celery -A celery_app worker -l info
2. 启动 Beat: celery -A celery_app beat -l info（定时任务需要）
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from celery import Celery

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import settings

# 创建 Redis 连接地址（带密码）
def get_redis_url(db: int = 0) -> str:
    """构建 Redis 连接地址"""
    if settings.REDIS_PASSWORD:
        return f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{db}"
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{db}"

# 创建 Celery 实例
celery_app = Celery(
    "rag_worker",
    broker=get_redis_url(settings.REDIS_DB),
    backend=get_redis_url(settings.REDIS_DB + 1)
)

# Celery 配置（从 settings 读取）
celery_app.conf.update(
    # ============ 序列化配置 ============
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # ============ 时区配置 ============
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,

    # ============ 任务配置 ============
    result_expires=settings.CELERY_RESULT_EXPIRES,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS,

    # ============ 重试配置 ============
    task_default_retry_delay=settings.CELERY_RETRY_DELAY,
    task_max_retries=settings.CELERY_MAX_RETRIES,

    # ============ 队列配置 ============
    task_default_queue="default",
    # 暂时不区分队列，所有任务走 default
    # task_routes={
    #     "tasks.process_document": {"queue": "document"},
    # },

    # ============ Worker 配置 ============
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
    worker_pool=settings.CELERY_WORKER_POOL,
)

# 自动发现任务
celery_app.autodiscover_tasks(["tasks"])


# ============ Celery 日志配置 ============
def setup_celery_logging():
    """配置 Celery 日志，输出到文件"""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Worker 日志
    worker_handler = RotatingFileHandler(
        os.path.join(log_dir, "celery_worker.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    worker_handler.setFormatter(formatter)

    # 任务日志
    task_handler = RotatingFileHandler(
        os.path.join(log_dir, "celery_task.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    task_handler.setFormatter(formatter)

    celery_logger = logging.getLogger("celery")
    celery_logger.addHandler(worker_handler)

    task_logger = logging.getLogger("celery.task")
    task_logger.addHandler(task_handler)


setup_celery_logging()
