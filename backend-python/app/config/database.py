from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 基类
Base = declarative_base()

# 延迟初始化的变量
_engine = None
_AsyncSessionLocal = None


def _get_or_create_engine():
    """懒加载: 获取或创建数据库引擎"""
    global _engine
    if _engine is None:
        from .settings import get_settings
        settings = get_settings()

        print(f"[DATABASE] Creating engine with: {settings.DATABASE_URL}")

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )
    return _engine


def _get_or_create_session_factory():
    """懒加载: 获取或创建 session 工厂"""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        engine = _get_or_create_engine()
        _AsyncSessionLocal = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _AsyncSessionLocal


# 用于兼容性的访问函数
def get_engine():
    """获取数据库引擎"""
    return _get_or_create_engine()


def get_async_session_local():
    """获取 AsyncSession 工厂"""
    return _get_or_create_session_factory()


async def get_db():
    """依赖注入: 获取数据库session"""
    factory = _get_or_create_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
