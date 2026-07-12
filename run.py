"""
统一启动脚本

使用方式：
    python run.py              # 启动 FastAPI（默认）
    python run.py server       # 启动 FastAPI
    python run.py worker       # 启动 Celery Worker
    python run.py flower       # 启动 Flower
    python run.py all          # 启动 Worker + Flower
"""
import sys
import os
import subprocess
from pathlib import Path

# 切换工作目录到当前目录
os.chdir(Path(__file__).parent)


def start_server():
    """启动 FastAPI"""
    from config.settings import settings
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )


def start_worker():
    """启动 Celery Worker"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "celery_app", "worker",
        "-l", "info", "-c", "4",
        "--logfile=logs/celery_worker.log"
    ]
    subprocess.run(cmd)


def start_flower():
    """启动 Flower"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "celery_app", "flower",
        "-c", "config.flower_config"
    ]
    subprocess.run(cmd)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "server"

    if command == "server":
        start_server()
    elif command == "worker":
        start_worker()
    elif command == "flower":
        start_flower()
    else:
        print(f"未知命令: {command}")
