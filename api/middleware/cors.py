from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有域名，线上替换成具体的域名
        allow_credentials=True,  # 允许携带认证信息
        allow_methods=["*"],  # 允许所有 HTTP 方法
        allow_headers=["*"]  # 允许所有请求头
    )