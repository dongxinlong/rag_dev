
from fastapi import FastAPI
from fastapi_pagination import add_pagination
from contextlib import asynccontextmanager
from api.middleware import cors, logging
from api.middleware.rate_limiter import RateLimitMiddleware
from config.settings import settings
from config.logging import setup_logging, get_logger
from database.session import db_session
from routers.rag import rag_router
from routers.chat import chat_router
from routers.knowledgebase import router as knowledge_router
from routers.user import router as user_router
from routers.messages import messages_router
from routers.parse_log import router as parse_log_router

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    setup_logging()
    logger.info(f"服务启动：{settings.HOST}:{settings.PORT}")
    logger.info(f"调试模式：{settings.DEBUG}")
    # 初始化数据库连接
    await db_session.create_pool()
    # Rerank 使用 API 调用（硅基流动），无需本地加载
    logger.info("Rerank 使用 API 模式（硅基流动）")
    # 初始化服务
    yield
    # 关闭时执行
    logger.info("服务关闭中...")
    await db_session.close()
    # 关闭数据库连接

# 1. 创建 FastAPI 实例
app = FastAPI(
    title="RAG API",
    description="基于 RAG 的智能问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# 2. 注册中间件
cors.setup_cors(app)  # 跨域中间件
logging.setup_logging(app)  # 日志中间件
app.add_middleware(RateLimitMiddleware)  # 添加限流中间件

# 4. 注册路由
router_prefix = "/api/v1"
app.include_router(rag_router, prefix=router_prefix)
app.include_router(chat_router, prefix=router_prefix)
app.include_router(messages_router, prefix=router_prefix)
app.include_router(knowledge_router, prefix=router_prefix)
app.include_router(user_router, prefix=router_prefix)
app.include_router(parse_log_router, prefix=router_prefix)

# 5. 健康检查
@app.get("/health")
async def health():
    return {"status": "ok"}


