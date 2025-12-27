#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据初始化脚本

功能流程：
1. 初始化数据库（创建表）
2. 从Tushare同步股票列表
3. 批量获取历史日线数据（并发处理）
4. 计算技术指标（RSI/MACD/KDJ/布林带）
5. 计算缠论指标（趋势/拐点/信号）

使用方法：
    python data_init.py --step all          # 完整初始化
    python data_init.py --step db           # 仅初始化数据库
    python data_init.py --step sync-stocks  # 仅同步股票列表
    python data_init.py --step sync-klines  # 仅同步K线数据
    python data_init.py --step indicators   # 仅计算指标
    python data_init.py --step chan         # 仅计算缠论
"""

import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    lambda msg: print(msg),
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

from app.config.settings import get_settings
from app.config.database import Base
from app.models import Stock, DailyQuote
from app.services.tushare_service import TushareService
from app.services.indicator_service import IndicatorService
from app.services.akshare_service import AKShareService
from app.core.chan import ChanService


class DataInitializer:
    """数据初始化器"""

    def __init__(self, database_url: Optional[str] = None):
        """初始化

        Args:
            database_url: 数据库连接URL（如果为None则从设置读取）
        """
        settings = get_settings()
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = None
        self.AsyncSessionLocal = None
        self.tushare = TushareService()

    async def connect(self) -> bool:
        """连接数据库"""
        try:
            logger.info(f"连接数据库: {self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url}")

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

            # 测试连接
            async with self.AsyncSessionLocal() as session:
                await session.execute(select(Stock).limit(1))

            logger.info("✓ 数据库连接成功")
            return True

        except Exception as e:
            logger.error(f"✗ 数据库连接失败: {e}")
            return False

    async def init_db(self) -> bool:
        """初始化数据库（创建所有表）"""
        try:
            logger.info("初始化数据库表...")

            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("✓ 数据库表创建完成")
            return True

        except Exception as e:
            logger.error(f"✗ 数据库初始化失败: {e}")
            return False

    async def sync_stocks(self) -> int:
        """同步股票列表"""
        logger.info("同步股票列表...")

        try:
            async with self.AsyncSessionLocal() as session:
                count = await self.tushare.sync_stocks(session)
                logger.info(f"✓ 同步了 {count} 只股票")
                return count

        except Exception as e:
            logger.error(f"✗ 同步股票失败: {e}")
            return 0

    async def get_all_stocks(self, limit: Optional[int] = None) -> List[Stock]:
        """获取所有股票"""
        try:
            async with self.AsyncSessionLocal() as session:
                stmt = select(Stock)
                if limit:
                    stmt = stmt.limit(limit)

                result = await session.execute(stmt)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"✗ 获取股票列表失败: {e}")
            return []

    async def sync_klines_for_stock(
        self,
        session: AsyncSession,
        ts_code: str,
        days: int = 500
    ) -> int:
        """为单只股票同步K线数据"""
        try:
            # 计算日期范围
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            # 从Tushare获取数据
            klines = await self.tushare.get_daily(ts_code, start_date, end_date, limit=days)

            # 如果Tushare失败，自动尝试AKShare
            if not klines and AKShareService.is_available():
                logger.debug(f"{ts_code}: Tushare失败，尝试AKShare...")
                klines = await AKShareService.get_daily(ts_code, start_date, end_date, limit=days)

            if not klines:
                return 0

            # 检查已存在的数据（查询当日数据以避免重复）
            stmt = select(DailyQuote.trade_date).where(DailyQuote.ts_code == ts_code)
            result = await session.execute(stmt)
            existing_dates = {row[0] for row in result.fetchall()}

            # 只插入新数据
            new_count = 0
            for kline in klines:
                if kline.get("trade_date") not in existing_dates:
                    quote = DailyQuote(
                        ts_code=ts_code,
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
                    new_count += 1

            if new_count > 0:
                await session.flush()

            return new_count

        except Exception as e:
            logger.debug(f"{ts_code}: 同步失败 - {e}")
            return 0

    async def sync_all_klines(self, limit: Optional[int] = None) -> int:
        """批量同步所有股票的K线数据（并发）"""
        logger.info("批量同步K线数据...")

        stocks = await self.get_all_stocks(limit)
        if not stocks:
            logger.warning("✗ 没有找到股票")
            return 0

        logger.info(f"准备同步 {len(stocks)} 只股票的K线数据...")

        total_synced = 0
        failed_count = 0

        async with self.AsyncSessionLocal() as session:
            for i, stock in enumerate(stocks):
                try:
                    if (i + 1) % 10 == 0:
                        logger.info(f"  进度: [{i+1}/{len(stocks)}] {stock.ts_code} {stock.name}")

                    count = await self.sync_klines_for_stock(session, stock.ts_code)
                    total_synced += count

                except Exception as e:
                    logger.debug(f"{stock.ts_code}: 同步失败 - {e}")
                    failed_count += 1

                # 每10只股票提交一次
                if (i + 1) % 10 == 0:
                    await session.commit()

            # 最后提交剩余数据
            await session.commit()

        logger.info(f"✓ 同步完成: 新增 {total_synced} 条K线数据, 失败 {failed_count} 只股票")
        return total_synced

    async def calc_indicators(self, limit: Optional[int] = None) -> int:
        """计算所有股票的技术指标"""
        logger.info("计算技术指标...")

        try:
            async with self.AsyncSessionLocal() as session:
                # 获取今天的交易日期
                trade_date = datetime.now().strftime("%Y%m%d")

                indicator_service = IndicatorService(session)

                # 如果指定了limit，只计算部分股票
                stocks = await self.get_all_stocks(limit)
                if stocks:
                    stock_codes = [s.ts_code for s in stocks]
                    count = await indicator_service.calc_all(trade_date, stock_codes)
                else:
                    count = await indicator_service.calc_all(trade_date)

                logger.info(f"✓ 计算了 {count} 只股票的技术指标")
                return count

        except Exception as e:
            logger.error(f"✗ 计算指标失败: {e}")
            return 0

    async def calc_chan_for_stock(
        self,
        session: AsyncSession,
        ts_code: str
    ) -> bool:
        """为单只股票计算缠论指标"""
        try:
            # 获取K线数据
            stmt = (
                select(DailyQuote)
                .where(DailyQuote.ts_code == ts_code)
                .order_by(desc(DailyQuote.trade_date))
                .limit(200)
            )
            result = await session.execute(stmt)
            quotes = result.scalars().all()

            if len(quotes) < 50:  # 至少需要50条K线
                return False

            # 转换为K线字典
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

            # 计算缠论
            chan_service = ChanService()
            result = chan_service.calculate(ts_code, klines)

            return result is not None

        except Exception as e:
            logger.debug(f"{ts_code}: 缠论计算失败 - {e}")
            return False

    async def calc_all_chan(self, limit: Optional[int] = None) -> int:
        """批量计算所有股票的缠论指标"""
        logger.info("计算缠论指标...")

        stocks = await self.get_all_stocks(limit)
        if not stocks:
            logger.warning("✗ 没有找到股票")
            return 0

        logger.info(f"准备计算 {len(stocks)} 只股票的缠论指标...")

        calculated_count = 0
        failed_count = 0

        async with self.AsyncSessionLocal() as session:
            for i, stock in enumerate(stocks):
                try:
                    if (i + 1) % 20 == 0:
                        logger.info(f"  进度: [{i+1}/{len(stocks)}] {stock.ts_code} {stock.name}")

                    if await self.calc_chan_for_stock(session, stock.ts_code):
                        calculated_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.debug(f"{stock.ts_code}: 计算失败 - {e}")
                    failed_count += 1

        logger.info(f"✓ 缠论计算完成: 成功 {calculated_count} 只, 失败 {failed_count} 只")
        return calculated_count

    async def run_full_init(self, stock_limit: Optional[int] = None) -> bool:
        """完整初始化流程"""
        logger.info("=" * 70)
        logger.info("开始数据初始化流程...")
        logger.info("=" * 70)

        # 1. 连接数据库
        if not await self.connect():
            return False

        # 2. 初始化数据库
        if not await self.init_db():
            return False

        # 3. 同步股票列表
        stock_count = await self.sync_stocks()
        if stock_count == 0:
            logger.warning("✗ 没有同步到任��股票，退出初始化")
            return False

        # 4. 同步K线数据
        kline_count = await self.sync_all_klines(stock_limit)

        # 5. 计算技术指标
        indicator_count = await self.calc_indicators(stock_limit)

        # 6. 计算缠论指标
        chan_count = await self.calc_all_chan(stock_limit)

        # 总结
        logger.info("=" * 70)
        logger.info("数据初始化完成！")
        logger.info("=" * 70)
        logger.info(f"股票数量：{stock_count} 只")
        logger.info(f"K线数据：{kline_count} 条")
        logger.info(f"技术指标：{indicator_count} 只股票")
        logger.info(f"缠论指标：{chan_count} 只股票")
        logger.info("=" * 70)

        await self.close()
        return True

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据初始化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python data_init.py --step all              # 完整初始化
  python data_init.py --step db               # 仅初始化数据库
  python data_init.py --step sync-stocks      # 仅同步股票列表
  python data_init.py --step sync-klines      # 仅同步K线数据
  python data_init.py --step indicators       # 仅计算指标
  python data_init.py --step chan             # 仅计算缠论
  python data_init.py --step all --limit 100  # 初始化前100只股票
        """
    )

    parser.add_argument(
        "--step",
        choices=["all", "db", "sync-stocks", "sync-klines", "indicators", "chan"],
        default="all",
        help="执行的步骤（默认: all）"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制股票数量（仅对stock_limit生效）"
    )

    args = parser.parse_args()

    initializer = DataInitializer()

    # 根据步骤执行
    if args.step == "all":
        success = await initializer.run_full_init(args.limit)
    else:
        if not await initializer.connect():
            return

        if args.step == "db":
            success = await initializer.init_db()
        elif args.step == "sync-stocks":
            await initializer.sync_stocks()
            success = True
        elif args.step == "sync-klines":
            await initializer.sync_all_klines(args.limit)
            success = True
        elif args.step == "indicators":
            await initializer.calc_indicators(args.limit)
            success = True
        elif args.step == "chan":
            await initializer.calc_all_chan(args.limit)
            success = True

        await initializer.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n[!] 用户中断初始化")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[!] 致命错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
