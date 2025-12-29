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

        # 针对远程 MySQL 优化连接配置
        connect_args = {}
        if 'mysql' in settings.DATABASE_URL:
            connect_args = {
                'connect_timeout': 30,      # 连接超时30秒
            }

        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=5,                    # 减少连接池大小
            max_overflow=10,                # 减少溢出连接
            pool_recycle=180,               # 3分钟回收连接（远程服务器可能会断开空闲连接）
            pool_pre_ping=True,             # 使用前检查连接是否有效
            pool_timeout=30,                # 获取连接超时30秒
            connect_args=connect_args,
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


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session():
    """上下文管理器: 获取数据库session（非依赖注入场景使用）"""
    factory = _get_or_create_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()
