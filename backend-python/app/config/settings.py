from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_stock.db"

    # Tushare
    TUSHARE_TOKEN: str = ""
    TUSHARE_API_URL: str = "http://api.tushare.pro"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 应用
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api"

    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置(缓存)"""
    settings = Settings()
    # 强制重新加载 .env 文件
    from dotenv import load_dotenv
    import os
    load_dotenv(override=True)
    return Settings()
