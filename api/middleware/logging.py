import time
import logging

from fastapi import FastAPI, Request

from config.logging import get_logger


logger = get_logger("middleware")

def setup_logging(app: FastAPI):

    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        # 记录开始时间
        start_time = time.time()

        # 请求处理
        response = await call_next(request)

        # 记录结束时间
        end_time = time.time()

        
        # 计算耗时
        process_time = end_time - start_time

        # 记录日志
        logger.info(
            f"Request: {request.method} {request.url}, Response: {response.status_code}, Processing Time: {process_time}"
        )
        return response
    
