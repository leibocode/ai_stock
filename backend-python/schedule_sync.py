#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时更新脚本 - 使用APScheduler定时同步数据和计算指标

定时任务：
- 16:00 更新日线数据（收盘后）
- 16:30 计算技术指标
- 17:00 计算缠论指标

使用方法：
    python schedule_sync.py              # 启动定时任务（仅工作日）
    python schedule_sync.py --test       # 测试模式（立即执行一次）
    python schedule_sync.py --interval 5 # 自定义间隔（分钟）
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, time
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from loguru import logger

logger.remove()
logger.add(
    lambda msg: print(msg),
    format="<level>{level: <8}</level> | <cyan>{asctime}</cyan> - <level>{message}</level>",
    level="INFO"
)

from app.config.settings import get_settings
from app.models import Stock, DailyQuote
from app.services.tushare_service import TushareService
from app.services.indicator_service import IndicatorService
from app.core.chan import ChanService


class ScheduledSync:
    """定时同步器"""

    def __init__(self, database_url: Optional[str] = None):
        settings = get_settings()
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = None
        self.AsyncSessionLocal = None
        self.tushare = TushareService()
        self.tz = timezone('Asia/Shanghai')

    async def connect(self) -> bool:
        """连接数据库"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True,
                pool_size=10,
                max_overflow=20,
            )

            self.AsyncSessionLocal = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

            async with self.AsyncSessionLocal() as session:
                await session.execute(select(Stock).limit(1))

            logger.info("✓ 数据库连接成功")
            return True

        except Exception as e:
            logger.error(f"✗ 数据库连接失败: {e}")
            return False

    async def sync_daily_klines(self):
        """同步日线数据"""
        logger.info("开始同步日线数据...")

        try:
            async with self.AsyncSessionLocal() as session:
                # 获取所有股票
                stmt = select(Stock)
                result = await session.execute(stmt)
                stocks = list(result.scalars().all())

                logger.info(f"准备更新 {len(stocks)} 只股票...")

                synced_count = 0
                failed_count = 0

                for i, stock in enumerate(stocks):
                    try:
                        # 获取最近5天的数据
                        klines = await self.tushare.get_daily(stock.ts_code, limit=10)

                        if not klines:
                            continue

                        # 检查已存在的数据
                        for kline in klines:
                            stmt = (
                                select(DailyQuote)
                                .where(DailyQuote.ts_code == stock.ts_code)
                                .where(DailyQuote.trade_date == kline.get("trade_date"))
                            )
                            result = await session.execute(stmt)
                            existing = result.scalar_one_or_none()

                            if existing:
                                # 更新
                                existing.open = float(kline.get("open", 0))
                                existing.high = float(kline.get("high", 0))
                                existing.low = float(kline.get("low", 0))
                                existing.close = float(kline.get("close", 0))
                                existing.vol = float(kline.get("vol", 0))
                                existing.amount = float(kline.get("amount", 0))
                                existing.pct_chg = float(kline.get("pct_chg", 0))
                            else:
                                # 新增
                                quote = DailyQuote(
                                    ts_code=stock.ts_code,
                                    trade_date=kline.get("trade_date"),
                                    open=float(kline.get("open", 0)),
                                    high=float(kline.get("high", 0)),
                                    low=float(kline.get("low", 0)),
                                    close=float(kline.get("close", 0)),
                                    vol=float(kline.get("vol", 0)),
                                    amount=float(kline.get("amount", 0)),
                                    pct_chg=float(kline.get("pct_chg", 0)),
                                )
                                session.add(quote)

                        synced_count += 1

                        if (i + 1) % 50 == 0:
                            logger.info(f"进度: [{i+1}/{len(stocks)}] {stock.ts_code}")

                    except Exception as e:
                        logger.debug(f"{stock.ts_code}: 同步失败 - {e}")
                        failed_count += 1

                    # 每50只提交一次
                    if (i + 1) % 50 == 0:
                        await session.commit()

                # 最后提交
                await session.commit()

                logger.info(f"✓ 日线同步完成: {synced_count} 只成功, {failed_count} 只失败")

        except Exception as e:
            logger.error(f"✗ 日线同步失败: {e}")

    async def calc_indicators_batch(self):
        """计算技术指标"""
        logger.info("开始计算技术指标...")

        try:
            async with self.AsyncSessionLocal() as session:
                trade_date = datetime.now().strftime("%Y%m%d")
                indicator_service = IndicatorService(session)

                # 获取所有股票
                stmt = select(Stock)
                result = await session.execute(stmt)
                stocks = list(result.scalars().all())

                logger.info(f"准备计算 {len(stocks)} 只股票的指标...")

                calculated = 0
                for i, stock in enumerate(stocks):
                    try:
                        history = await indicator_service.get_stock_history(stock.ts_code)
                        if len(history) < 26:
                            continue

                        indicators = await indicator_service.calculate_indicators(
                            stock.ts_code, history
                        )

                        if indicators:
                            from app.models import TechnicalIndicator

                            stmt = (
                                select(TechnicalIndicator)
                                .where(TechnicalIndicator.ts_code == stock.ts_code)
                                .where(TechnicalIndicator.trade_date == trade_date)
                            )
                            result = await session.execute(stmt)
                            existing = result.scalar_one_or_none()

                            if existing:
                                for key, value in indicators.items():
                                    if key != "ts_code":
                                        setattr(existing, key, value)
                            else:
                                new_indicator = TechnicalIndicator(**indicators)
                                session.add(new_indicator)

                            calculated += 1

                        if (i + 1) % 50 == 0:
                            logger.info(f"进度: [{i+1}/{len(stocks)}]")

                    except Exception as e:
                        logger.debug(f"{stock.ts_code}: 计算失败 - {e}")

                    if (i + 1) % 50 == 0:
                        await session.commit()

                await session.commit()
                logger.info(f"✓ 技术指标计算完成: {calculated} 只股票")

        except Exception as e:
            logger.error(f"✗ 技术指标计算失败: {e}")

    async def calc_chan_batch(self):
        """计算缠论指标"""
        logger.info("开始计算缠论指标...")

        try:
            async with self.AsyncSessionLocal() as session:
                # 获取所有股票
                stmt = select(Stock)
                result = await session.execute(stmt)
                stocks = list(result.scalars().all())

                logger.info(f"准备计算 {len(stocks)} 只股票的缠论指标...")

                calculated = 0
                failed = 0

                for i, stock in enumerate(stocks):
                    try:
                        stmt = (
                            select(DailyQuote)
                            .where(DailyQuote.ts_code == stock.ts_code)
                            .order_by(desc(DailyQuote.trade_date))
                            .limit(200)
                        )
                        result = await session.execute(stmt)
                        quotes = result.scalars().all()

                        if len(quotes) < 50:
                            continue

                        klines = [
                            {
                                "trade_date": q.trade_date,
                                "open": float(q.open or 0),
                                "high": float(q.high or 0),
                                "low": float(q.low or 0),
                                "close": float(q.close or 0),
                                "vol": float(q.vol or 0),
                            }
                            for q in reversed(quotes)
                        ]

                        chan_service = ChanService()
                        result = chan_service.calculate(stock.ts_code, klines)

                        if result:
                            calculated += 1

                        if (i + 1) % 50 == 0:
                            logger.info(f"进度: [{i+1}/{len(stocks)}]")

                    except Exception as e:
                        logger.debug(f"{stock.ts_code}: 缠论计算失败 - {e}")
                        failed += 1

                logger.info(f"✓ 缠论指标计算完成: {calculated} 只成功, {failed} 只失败")

        except Exception as e:
            logger.error(f"✗ 缠论指标计算失败: {e}")

    async def cleanup(self):
        """清理资源"""
        if self.engine:
            await self.engine.dispose()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="定时数据同步工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python schedule_sync.py              # 启动定时任务（16:00, 16:30, 17:00）
  python schedule_sync.py --test       # 测试模式（立即执行）
  python schedule_sync.py --once klines # 一次性执行K线同步
        """
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式（立即执行一次）"
    )

    parser.add_argument(
        "--once",
        choices=["klines", "indicators", "chan"],
        help="一次性执行指定任务"
    )

    args = parser.parse_args()

    syncer = ScheduledSync()

    if not await syncer.connect():
        return

    try:
        if args.once:
            # 一次性执行
            if args.once == "klines":
                await syncer.sync_daily_klines()
            elif args.once == "indicators":
                await syncer.calc_indicators_batch()
            elif args.once == "chan":
                await syncer.calc_chan_batch()
        elif args.test:
            # 测试模式：立即执行一次
            logger.info("测试模式：立即执行所有任务...")
            await syncer.sync_daily_klines()
            await syncer.calc_indicators_batch()
            await syncer.calc_chan_batch()
        else:
            # 启动定时任务
            scheduler = AsyncIOScheduler(timezone=syncer.tz)

            # 配置定时任务
            # 16:00 更新K线
            scheduler.add_job(
                syncer.sync_daily_klines,
                "cron",
                hour=16,
                minute=0,
                day_of_week="0-4",  # 仅工作日
                id="sync_klines",
                name="同步日线数据"
            )

            # 16:30 计算指标
            scheduler.add_job(
                syncer.calc_indicators_batch,
                "cron",
                hour=16,
                minute=30,
                day_of_week="0-4",
                id="calc_indicators",
                name="计算技术指标"
            )

            # 17:00 计算缠论
            scheduler.add_job(
                syncer.calc_chan_batch,
                "cron",
                hour=17,
                minute=0,
                day_of_week="0-4",
                id="calc_chan",
                name="计算缠论指标"
            )

            logger.info("=" * 70)
            logger.info("定时同步服务已启动")
            logger.info("=" * 70)
            logger.info("定时任务：")
            logger.info("  16:00 - 同步日线数据")
            logger.info("  16:30 - 计算技术指标")
            logger.info("  17:00 - 计算缠论指标")
            logger.info("（仅工作日执行）")
            logger.info("=" * 70)

            scheduler.start()

            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("\n定时任务已停止")
                scheduler.shutdown()

    except Exception as e:
        logger.error(f"错误: {e}")
    finally:
        await syncer.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n服务已停止")
    except Exception as e:
        logger.error(f"致命错误: {e}")
        import traceback
        traceback.print_exc()
