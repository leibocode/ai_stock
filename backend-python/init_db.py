#!/usr/bin/env python
"""数据库初始化脚本 - 创建所有表"""
import asyncio
import os
from pathlib import Path

# 强制加载 .env
from dotenv import load_dotenv
load_dotenv(override=True)

from sqlalchemy.ext.asyncio import create_async_engine
from app.config.database import Base
from app.models.stock import Stock
from app.models.daily_quote import DailyQuote
from app.models.technical_indicator import TechnicalIndicator
from app.models.review_record import ReviewRecord
from app.models.chan import ChanFractal, ChanBi, ChanSegment, ChanHub


async def init_db():
    """创建数据库和所有表"""
    from app.config.settings import get_settings

    settings = get_settings()
    database_url = settings.DATABASE_URL

    print(f"[*] Using database: {database_url}")

    # 创建引擎
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("[*] All tables created successfully!")

    # 验证表是否创建
    async with engine.begin() as conn:
        result = await conn.run_sync(lambda c: Base.metadata.tables.keys())
        tables = list(result) if result else []
        print(f"[*] Database tables: {tables}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
    print("[*] Database initialization completed!")
