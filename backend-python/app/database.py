from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models import Base
from loguru import logger

# 全局引擎和会话工厂
engine = None
AsyncSessionLocal = None


async def init_db():
    """初始化数据库"""
    global engine, AsyncSessionLocal

    settings = get_settings()

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=0,
    )

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database initialized")


async def close_db():
    """关闭数据库连接"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database closed")


async def get_db():
    """获取数据库会话依赖"""
    global AsyncSessionLocal

    if not AsyncSessionLocal:
        await init_db()

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
