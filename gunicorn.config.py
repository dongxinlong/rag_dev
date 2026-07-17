"""
Gunicorn 配置文件

使用方式：
uv run gunicorn main:app -c gunicorn.config.py
"""
import os
import multiprocessing

# 强制设置生产环境
os.environ["APP_ENV"] = "production"

# HuggingFace 国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 服务器配置
bind = "0.0.0.0:8000"

# 工作进程数（推荐 CPU 核心数 * 2 + 1）
workers = 2

# Worker 类（异步，配合 FastAPI）
worker_class = "uvicorn.workers.UvicornWorker"

# 超时配置
timeout = 120
keepalive = 5

# 日志配置
loglevel = "info"
accesslog = "-"
errorlog = "-"

# 进程名
proc_name = "rag-api"

# 启动钩子
def on_starting(server):
    """服务启动时执行"""
    pass

def post_fork(server, worker):
    """Worker 进程 fork 后执行"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")
