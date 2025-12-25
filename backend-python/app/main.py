import os
from dotenv import load_dotenv

# 强制重新加载 .env 文件 (支持 SQLite/MySQL 切换)
load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from app.config.settings import get_settings

# 清除 lru_cache，强制重新读取设置
if hasattr(get_settings, 'cache_clear'):
    get_settings.cache_clear()

settings = get_settings()

# 打印当前数据库配置（仅用于调试）
print(f"[APP-START] DATABASE_URL: {settings.DATABASE_URL}")

from app.api.v1.router import api_router
from app.services.cache_service import CacheService
from app.core.scheduler import get_scheduler

# Redis缓存服务实例
cache_service = CacheService(
    redis_url=settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else "redis://localhost:6379/0",
    ttl=3600
)

# 获取全局调度器实例
scheduler = get_scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    await cache_service.connect()
    scheduler.start()
    logger.info("✅ Application startup completed with scheduler running")
    yield
    # 关闭事件
    scheduler.stop()
    await cache_service.disconnect()
    logger.info("✅ Application shutdown completed")


app = FastAPI(
    title="AI Stock - 股票复盘系统",
    version="2.0.0",
    description="基于情绪周期理论的A股复盘分析系统 (Python FastAPI)",
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


# API 路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG,
    )
