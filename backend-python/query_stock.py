#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票查询工具 - 查看单只股票的完整分析结果

支持以下查询：
- 基本信息
- K线数据
- 技术指标
- 缠论分析
- 多周期分析

使用方法：
    python query_stock.py 000001.SZ                # 查看股票基本信息
    python query_stock.py 000001.SZ --klines 50    # 查看最近50条K线
    python query_stock.py 000001.SZ --indicators   # 查看技术指标
    python query_stock.py 000001.SZ --chan         # 查看缠论分析
    python query_stock.py 000001.SZ --multi-period # 查看多周期分析
    python query_stock.py 000001.SZ --all          # 查看所有信息
"""

import sys
import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from loguru import logger
import pandas as pd

logger.remove()
logger.add(lambda msg: print(msg), format="{message}", level="INFO")

from app.config.settings import get_settings
from app.models import Stock, DailyQuote, TechnicalIndicator
from app.services.tushare_service import TushareService
from app.services.indicator_service import IndicatorService
from app.core.chan import ChanService
from app.core.chan.multi_period import MultiPeriodAnalyzer, format_multi_period_report
from app.services.crawler.minute_kline import fetch_multi_period_data


class StockQuerier:
    """股票查询器"""

    def __init__(self):
        settings = get_settings()
        self.database_url = settings.DATABASE_URL
        self.engine = None
        self.AsyncSessionLocal = None
        self.tushare = TushareService()

    async def connect(self) -> bool:
        """连接数据库"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True,
                pool_size=5,
                max_overflow=10,
            )

            self.AsyncSessionLocal = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

            async with self.AsyncSessionLocal() as session:
                await session.execute(select(Stock).limit(1))

            return True

        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    async def get_stock(self, ts_code: str) -> Optional[Stock]:
        """获取股票信息"""
        try:
            async with self.AsyncSessionLocal() as session:
                stmt = select(Stock).where(Stock.ts_code == ts_code)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
            return None

    async def get_klines(self, ts_code: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            async with self.AsyncSessionLocal() as session:
                stmt = (
                    select(DailyQuote)
                    .where(DailyQuote.ts_code == ts_code)
                    .order_by(desc(DailyQuote.trade_date))
                    .limit(limit)
                )
                result = await session.execute(stmt)
                quotes = result.scalars().all()

                if not quotes:
                    return None

                data = []
                for q in reversed(quotes):
                    data.append({
                        '日期': q.trade_date,
                        '开': float(q.open or 0),
                        '高': float(q.high or 0),
                        '低': float(q.low or 0),
                        '收': float(q.close or 0),
                        '成交量': float(q.vol or 0),
                        '成交额': float(q.amount or 0),
                        '涨跌幅': float(q.pct_chg or 0),
                    })

                return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return None

    async def get_indicators(self, ts_code: str) -> Optional[dict]:
        """获取最新技术指标"""
        try:
            async with self.AsyncSessionLocal() as session:
                stmt = (
                    select(TechnicalIndicator)
                    .where(TechnicalIndicator.ts_code == ts_code)
                    .order_by(desc(TechnicalIndicator.trade_date))
                    .limit(1)
                )
                result = await session.execute(stmt)
                indicator = result.scalar_one_or_none()

                if not indicator:
                    return None

                return {
                    '日期': indicator.trade_date,
                    'RSI6': float(indicator.rsi_6 or 0),
                    'RSI12': float(indicator.rsi_12 or 0),
                    'MACD': float(indicator.macd or 0),
                    'MACD_Signal': float(indicator.macd_signal or 0),
                    'MACD_Hist': float(indicator.macd_hist or 0),
                    'K': float(indicator.k or 0),
                    'D': float(indicator.d or 0),
                    'J': float(indicator.j or 0),
                    '布林上': float(indicator.boll_upper or 0),
                    '布林中': float(indicator.boll_mid or 0),
                    '布林下': float(indicator.boll_lower or 0),
                }

        except Exception as e:
            logger.error(f"获取指标失败: {e}")
            return None

    async def get_chan_analysis(self, ts_code: str) -> Optional[dict]:
        """获取缠论分析"""
        try:
            klines_df = await self.get_klines(ts_code, 200)
            if klines_df is None or len(klines_df) < 50:
                logger.warning("K线数据不足")
                return None

            klines = [
                {
                    'trade_date': str(row['日期']),
                    'open': row['开'],
                    'high': row['高'],
                    'low': row['低'],
                    'close': row['收'],
                    'vol': row['成交量'],
                }
                for _, row in klines_df.iterrows()
            ]

            chan_service = ChanService()
            result = chan_service.calculate(ts_code, klines)

            if not result:
                return None

            return result.to_dict()

        except Exception as e:
            logger.error(f"缠论分析失败: {e}")
            return None

    async def get_multi_period_analysis(self, ts_code: str) -> Optional[dict]:
        """获取多周期分析"""
        try:
            # 获取日线
            daily_klines_df = await self.get_klines(ts_code, 200)
            if daily_klines_df is None or len(daily_klines_df) < 50:
                logger.warning("日线数据不足")
                return None

            daily_klines = [
                {
                    'trade_date': str(row['日期']),
                    'open': row['开'],
                    'high': row['高'],
                    'low': row['低'],
                    'close': row['收'],
                    'vol': row['成交量'],
                }
                for _, row in daily_klines_df.iterrows()
            ]

            # 获取分钟K线
            logger.info("获取分钟K线数据...")
            minute_data = await fetch_multi_period_data(ts_code, ["30", "5"])

            if not minute_data or len(minute_data) < 2:
                logger.warning("分钟K线数据不足")
                return None

            min30_klines = minute_data.get("30", [])
            min5_klines = minute_data.get("5", [])

            if len(min30_klines) < 50 or len(min5_klines) < 50:
                logger.warning("分钟K线数据不足")
                return None

            # 多周期分析
            analyzer = MultiPeriodAnalyzer()
            signal = await analyzer.analyze(ts_code, daily_klines, min30_klines, min5_klines)

            if not signal:
                return None

            return {
                'signal': signal.signal_type,
                'confidence': signal.confidence.value,
                'daily_trend': signal.daily_trend,
                'min30_structure': signal.min30_structure,
                'min5_trigger': signal.min5_trigger,
                'buy_price': signal.buy_price,
                'stop_loss': signal.stop_loss,
                'description': signal.description,
            }

        except Exception as e:
            logger.error(f"多周期分析失败: {e}")
            return None

    async def query_stock(
        self,
        ts_code: str,
        show_klines: bool = False,
        show_indicators: bool = False,
        show_chan: bool = False,
        show_multi_period: bool = False,
        show_all: bool = False,
        kline_limit: int = 10
    ):
        """查询股票"""
        if not await self.connect():
            return

        # 获取股票基本信息
        stock = await self.get_stock(ts_code)
        if not stock:
            logger.error(f"股票不存在: {ts_code}")
            return

        print("\n" + "=" * 70)
        print("【股票信息】")
        print("=" * 70)
        print(f"代码: {stock.ts_code}")
        print(f"名称: {stock.name}")
        print(f"行业: {stock.industry or 'N/A'}")
        print(f"市场: {stock.market or 'N/A'}")
        print(f"上市日期: {stock.list_date or 'N/A'}")

        # K线数据
        if show_klines or show_all:
            print("\n" + "=" * 70)
            print(f"【K线数据 - 最近{kline_limit}条】")
            print("=" * 70)
            klines_df = await self.get_klines(ts_code, kline_limit)
            if klines_df is not None:
                print(klines_df.to_string(index=False))
            else:
                print("未找到K线数据")

        # 技术指标
        if show_indicators or show_all:
            print("\n" + "=" * 70)
            print("【技术指标】")
            print("=" * 70)
            indicators = await self.get_indicators(ts_code)
            if indicators:
                for key, value in indicators.items():
                    if isinstance(value, float):
                        print(f"{key:15s}: {value:10.2f}")
                    else:
                        print(f"{key:15s}: {value}")
            else:
                print("未找到指标数据")

        # 缠论分析
        if show_chan or show_all:
            print("\n" + "=" * 70)
            print("【缠论分析】")
            print("=" * 70)
            chan_result = await self.get_chan_analysis(ts_code)
            if chan_result:
                # 只显示关键信息
                if 'trend' in chan_result:
                    trend = chan_result['trend']
                    if isinstance(trend, dict):
                        print(f"趋势类型: {trend.get('type', 'N/A')}")
                        print(f"趋势阶段: {trend.get('phase', 'N/A')}")
                        print(f"中枢数量: {trend.get('hub_count', 0)}")
                if 'suggestion' in chan_result:
                    print(f"建议: {chan_result['suggestion']}")
                print(f"\n完整结果: {json.dumps(chan_result, ensure_ascii=False, indent=2)}")
            else:
                print("缠论分析失败")

        # 多周期分析
        if show_multi_period or show_all:
            print("\n" + "=" * 70)
            print("【多周期分析】")
            print("=" * 70)
            print("获取分钟K线数据中...")
            multi_result = await self.get_multi_period_analysis(ts_code)
            if multi_result:
                print(f"买卖信号: {multi_result.get('signal', 'N/A')}")
                print(f"置信度: {multi_result.get('confidence', 'N/A')}")
                print(f"日线方向: {multi_result.get('daily_trend', 'N/A')}")
                print(f"30分钟结构: {multi_result.get('min30_structure', 'N/A')}")
                print(f"5分钟触发: {multi_result.get('min5_trigger', 'N/A')}")
                if multi_result.get('buy_price'):
                    print(f"进场价: {multi_result['buy_price']:.2f}")
                if multi_result.get('stop_loss'):
                    print(f"止损价: {multi_result['stop_loss']:.2f}")
                print(f"\n描述: {multi_result.get('description', 'N/A')}")
            else:
                print("多周期分析失败")

        print("\n" + "=" * 70)
        await self.close()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="股票查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python query_stock.py 000001.SZ                # 查看基本信息
  python query_stock.py 000001.SZ --klines 50   # 查看最近50条K线
  python query_stock.py 000001.SZ --indicators  # 查看技术指标
  python query_stock.py 000001.SZ --chan        # 查看缠论分析
  python query_stock.py 000001.SZ --all         # 查看所有信息
        """
    )

    parser.add_argument("ts_code", help="股票代码 (如: 000001.SZ)")
    parser.add_argument("--klines", action="store_true", help="显示K线数据")
    parser.add_argument("--kline-limit", type=int, default=10, help="K线显示数量 (默认: 10)")
    parser.add_argument("--indicators", action="store_true", help="显示技术指标")
    parser.add_argument("--chan", action="store_true", help="显示缠论分析")
    parser.add_argument("--multi-period", action="store_true", help="显示多周期分析")
    parser.add_argument("--all", action="store_true", help="显示所有信息")

    args = parser.parse_args()

    querier = StockQuerier()
    await querier.query_stock(
        args.ts_code,
        show_klines=args.klines or args.all,
        show_indicators=args.indicators or args.all,
        show_chan=args.chan or args.all,
        show_multi_period=args.multi_period or args.all,
        show_all=args.all,
        kline_limit=args.kline_limit
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n中断查询")
    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()
