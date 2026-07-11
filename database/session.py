"""
管理数据库连接和会话，提供统一的数据库操作入口
"""

import asyncpg
from pgvector.asyncpg import register_vector
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.settings import settings

class DatabaseSession:
    """
    数据库会话管理器
    职责：管理引擎生命周期和会话创建
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
    
    async def create_pool(self):
        """创建异步引擎和会话工厂"""
        print("Initializing database pool...")
        DATABASE_URL = (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.POSTGRES_DB}"
        )
        self.engine = create_async_engine(
            DATABASE_URL,
            echo=settings.DEBUG,      # 是否打印 SQL
            pool_size=settings.PG_MIN_SIZE,              # 连接池大小
            max_overflow=settings.PG_MAX_SIZE           # 最大溢出连接数
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False    # 提交后不自动过期
        )
    
    async def get_session(self):
        """获取会话（用于依赖注入）"""
        if not self.session_factory:
            raise RuntimeError("数据库未初始化，请先调用 create_pool()")
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()  # 提交事务
            except Exception:
                await session.rollback()  # 出错回滚
                raise
            finally:
                await session.close()
    
    async def close(self):
        """关闭引擎"""
        if self.engine:
            await self.engine.dispose()
            print("数据库引擎已关闭")


# 全局实例
db_session = DatabaseSession()