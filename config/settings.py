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
    # ============ Embedding 配置 ============
    # Embedding 每批处理数量
    EMBEDDING_BATCH_SIZE: int = 500

    # ============ 视觉模型配置（Ollama） ============
    # Ollama 服务地址
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # 视觉模型名称
    VISION_MODEL: str = "minicpm-v"
    # 图片描述提示词
    VISION_PROMPT: str = "请详细描述这张图片的内容，包括文字、图表、电路等所有可见信息"
    # 图片处理最大并发数（限制同时调用视觉模型的数量）
    VISION_MAX_CONCURRENT: int = 1
    # 图片处理每批数量
    VISION_BATCH_SIZE: int = 5
    # 图片处理最大重试次数
    VISION_MAX_RETRIES: int = 3

    

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

    # Redis 配置（Celery Broker）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # ============ Celery 配置 ============
    # 时区
    CELERY_TIMEZONE: str = "Asia/Shanghai"
    # 任务结果过期时间（秒），7 天
    CELERY_RESULT_EXPIRES: int = 604800
    # 任务软超时（秒），2 小时
    CELERY_TASK_SOFT_TIME_LIMIT: int = 7200
    # 任务硬超时（秒），2 小时 5 分钟
    CELERY_TASK_TIME_LIMIT: int = 7500
    # Worker 并发数
    CELERY_WORKER_CONCURRENCY: int = 4
    # Worker 最大任务数（超过后重启，防内存泄漏）
    CELERY_WORKER_MAX_TASKS: int = 100
    # Worker 进程池类型
    # 可选值：prefork（多进程，默认）、threads（多线程）、solo（单进程调试）
    # Windows 建议用 threads（prefork 有权限问题）
    # Linux 建议用 prefork（性能最好）
    CELERY_WORKER_POOL: str = "threads"
    # 重试延迟（秒）
    CELERY_RETRY_DELAY: int = 60
    # 最大重试次数
    CELERY_MAX_RETRIES: int = 3

    # ============ Flower 配置 ============
    # 监听端口
    FLOWER_PORT: int = 5555
    # 绑定地址
    FLOWER_ADDRESS: str = "0.0.0.0"
    # 认证（格式：["用户名:密码"]，空列表表示无认证）
    FLOWER_BASIC_AUTH: list = []
    # 日志级别
    FLOWER_LOG_LEVEL: str = "INFO"

    # RAG配置
    SIMILARITY_THRESHOLD: float = 0.5  # 余弦相似度阈值
    DISTANCE_THRESHOLD: float = 0.5  # 余弦距离阈值
    # 分块配置
    CHUNK_SIZE: int = 1024  # 单 chunk 最大 token 数
    CHUNK_OVERLAP: int = 150  # 重叠 token 数（句子边界）
    CHUNK_MIN_SIZE: int = 50  # 最小 chunk token 数
    # 语义完整性检查配置
    CHUNK_TRANSITION_WORDS: list = ["但是", "然而", "不过", "除外", "此外", "另外", "同时"]  # 转折词列表
    # 句子分割配置
    CHUNK_SENTENCE_PATTERNS: str = r'[。！？.!?]'  # 句子结束符正则
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