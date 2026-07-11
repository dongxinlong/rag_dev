"""
限流装饰器
"""
from functools import wraps
from fastapi import Request


def skip_rate_limit(func):
    """跳过限流装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 标记跳过限流
        return await func(*args, **kwargs)
    wrapper._skip_rate_limit = True
    return wrapper


# 在路由中使用：
# @router.post("/upload")
# @skip_rate_limit
# async def upload_file(...):
#     ...
