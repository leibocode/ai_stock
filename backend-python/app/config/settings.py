from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用信息
    APP_NAME: str = "AI Stock Review"
    APP_VERSION: str = "1.0.0"

    # 数据库
    DATABASE_URL: str = "mysql+aiomysql://ai_stock:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock"

    # Tushare
    TUSHARE_TOKEN: str = ""
    TUSHARE_API_URL: str = "http://api.tushare.pro"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 应用
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # CORS 配置
    ALLOWED_HOSTS: list = ["*"]

    # 日志配置
    LOG_LEVEL: str = "INFO"

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
