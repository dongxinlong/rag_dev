import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from schemas.response import ErrorResponse

from utils.rate_limiter import TokenBucket
from config.settings import settings

# 全局限流器实例
bucket = TokenBucket(
    capacity=settings.RATE_LIMIT_CAPACITY,
    refill_rate=settings.RATE_LIMIT_REFILL_RATE
)

# 并发控制
semaphore = asyncio.Semaphore(settings.MAX_CONCURRENCY)  # 限制同时处理的请求数

class RateLimitMiddleware(BaseHTTPMiddleware):
    # 跳过限流的路径
    SKIP_PATHS = [
        "/api/v1/knowledge/upload",
        "/api/v1/knowledge/folder",
        "/api/v1/user/avatar",
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 文件上传/创建文件夹跳过限流和并发控制
        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        # 获取客户端 IP
        client_ip = request.client.host

        # 1. 限流检查
        if not bucket.acquire(client_ip):
            wait_time = bucket.get_wait_time(client_ip)
            return JSONResponse(
                status_code=429,
                content={"code": 429, "message": f"请求过于频繁，请 {wait_time:.1f} 秒后重试", "data": None}
            )

        # 2. 并发控制
        if semaphore.locked():
            return JSONResponse(
                status_code=503,
                content={"code": 503, "message": "服务器繁忙，请稍后重试", "data": None}
            )

        # 3. 处理请求
        async with semaphore:
            response = await call_next(request)
        return response
