# 启动 Celery Worker
uv run celery -A celery_app worker -l info -c 4 --logfile=logs/celery.log

# 启动 Celery 监控

uv run celery -A celery_app flower -c config.flower_config

# 启动 FastAPI
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
