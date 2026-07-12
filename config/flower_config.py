"""
Flower 配置文件

使用方式：
    celery -A celery_app flower -c config.flower_config
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import settings

# ============ 基础配置 ============
port = settings.FLOWER_PORT
address = settings.FLOWER_ADDRESS

# ============ 认证配置 ============
basic_auth = settings.FLOWER_BASIC_AUTH

# ============ Redis 配置 ============
if settings.REDIS_PASSWORD:
    broker_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
else:
    broker_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# ============ 功能配置 ============
enable_events = True
show_args = True
show_result = True
max_result_length = 200

# ============ 日志配置 ============
logging_level = settings.FLOWER_LOG_LEVEL

# ============ 自动刷新配置 ============
auto_refresh = True
refresh_interval = 5

# ============ 性能配置 ============
max_workers = 100
max_tasks = 10000
