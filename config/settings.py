"""
统一管理所有的配置，从.env中获取
"""
from pathlib import Path
from pydantic_settings import BaseSettings

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    # LLM配置
    API_KEY: str
    MODEL_NAME: str
    BASE_URL: str
    LLM_MAX_RETRLES: int = 5  # 最大重试次数
    LLM_RETRY_DELAY: int = 1.0  # 初始重试间隔
    LLM_RETRY_BACKOFF: float = 2.0  # 退避倍数
    LLM_TIMEOUT: float = 30.0  # LLM请求超时时间 
    LLM_RATE_LIMIT_DELAY: float = 5.0  # 限流初始等待时间

    # Embedding配置
    EMBEDDING_MODEL: str
    EMBEDDING_BASE_URL: str
    EMBEDDING_API_KEY: str

    # 数据库配置
    PG_HOST: str
    PG_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    PG_MIN_SIZE: int = 5  # 数据库连接池最小大小
    PG_MAX_SIZE: int = 20  # 数据库连接池最大大小

    # Redis配置
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str

    # MinIO配置
    MINIO_ENDPOINT: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET: str
    MINIO_SECURE: bool
    MINIO_EXPIRY: int = 3600  # Presigned URL过期时间（秒）

    @property
    def MINIO_URL(self) -> str:
        """动态拼接 MinIO 访问地址"""
        protocol = "https" if self.MINIO_SECURE else "http"
        return f"{protocol}://{self.MINIO_ENDPOINT}"

    @property
    def MINIO_FULL_URL(self) -> str:
        """MinIO 完整访问地址（带 bucket）"""
        return f"{self.MINIO_URL}/{self.MINIO_BUCKET}"

    # RAG配置
    SIMILARITY_THRESHOLD: float = 0.5  # 余弦相似度阈值
    DISTANCE_THRESHOLD: float = 0.5  # 余弦距离阈值
    CHUNK_SIZE: int = 80  # 文本块大小
    OVERLAP_SENTENCES: int = 2  # 块间重叠的句子数
    MAX_CONTEXT_LENGTH: int = 5000  # 最大上下文长度
    MAX_COMPLETION_TOKENS: int = 5000  # 最大输出token数
    MAX_HISTORY_MESSAGES: int = 20  # 最多使用的历史消息数

    # 限流配置
    RATE_LIMIT_CAPACITY: int = 30  # 限流桶容量
    RATE_LIMIT_REFILL_RATE: float = 5.0  # 限流桶填充速率（个/秒）
    MAX_CONCURRENCY: int = 20  # 最大并发请求数

    # JWT 配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    class Config:
        env_file = str(BASE_DIR / ".env")


settings = Settings()