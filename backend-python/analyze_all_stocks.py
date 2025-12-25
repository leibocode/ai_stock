#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch Stock Chan Theory Analysis Script

Analyzes all stocks in the database using Chan theory algorithm:
1. Fetch all stocks from database
2. Get historical K-line data for each stock
3. Run Chan algorithm (Fractal -> Bi -> Segment -> Hub)
4. Identify buy/sell signals
5. Generate comprehensive analysis report
"""

import sys
import asyncio
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, r'C:\Users\02584\Desktop\新建文件夹\ai_stock\backend-python')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from app.models import Stock, DailyQuote
from app.services.chan_service import ChanService
from loguru import logger

# Configure logging
logger.remove()
logger.add(lambda msg: print(msg), format="{message}")


class StockAnalyzer:
    """批量股票分析器"""

    def __init__(self, database_url: str):
        """初始化分析器

        Args:
            database_url: MySQL连接字符串
        """
        self.database_url = database_url
        self.engine = None
        self.AsyncSessionLocal = None

    async def connect(self) -> bool:
        """连接数据库

        Returns:
            成功返回True，失败返回False
        """
        try:
            print("[*] Connecting to database...")
            print(f"    URL: {self.database_url}")

            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
            )

            self.AsyncSessionLocal = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )

            # Test connection
            async with self.AsyncSessionLocal() as session:
                result = await session.execute(select(Stock).limit(1))
                result.scalar_one_or_none()

            print("[+] Database connection successful!")
            return True

        except Exception as e:
            print(f"[-] Database connection failed: {e}")
            return False

    async def get_all_stocks(self) -> List[Stock]:
        """获取所有股票"""
        try:
            async with self.AsyncSessionLocal() as session:
                stmt = select(Stock).limit(500)  # 限制500只，避免过量
                result = await session.execute(stmt)
                stocks = result.scalars().all()
                return list(stocks)
        except Exception as e:
            print(f"[-] Failed to fetch stocks: {e}")
            return []

    async def get_klines_for_stock(self, ts_code: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """获取股票的K线数据"""
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

                if len(quotes) < 50:  # 至少需要50条K线
                    return None

                # 转换为DataFrame并按时间升序排列
                data = []
                for q in reversed(quotes):
                    data.append({
                        'trade_date': q.trade_date,
                        'high': float(q.high or 0),
                        'low': float(q.low or 0),
                        'close': float(q.close or 0),
                        'vol': float(q.vol or 0),
                    })

                return pd.DataFrame(data)

        except Exception as e:
            logger.debug(f"Failed to fetch klines for {ts_code}: {e}")
            return None

    async def analyze_stock(self, stock: Stock) -> Optional[Dict]:
        """分析单只股票"""
        try:
            # Get K-lines
            klines = await self.get_klines_for_stock(stock.ts_code)
            if klines is None or len(klines) < 50:
                return None

            # Run Chan analysis
            result = ChanService.analyze(klines)

            if not result:
                return None

            # Extract key information
            analysis = {
                'ts_code': stock.ts_code,
                'name': stock.name,
                'fractal_count': result['fractal_count'],
                'bi_count': result['bi_count'],
                'segment_count': result['segment_count'],
                'hub_count': result['hub_count'],
                'trend': result['current_trend'],
                'kline_count': len(klines),
            }

            # Get buy/sell signals
            if result['hubs'] and len(result['hubs']) > 0:
                latest_hub = result['hubs'][-1]
                last_price = float(klines.iloc[-1]['close'])

                analysis['latest_hub_high'] = float(latest_hub['high'])
                analysis['latest_hub_low'] = float(latest_hub['low'])
                analysis['price_position'] = 'above' if last_price > latest_hub['high'] else ('below' if last_price < latest_hub['low'] else 'inside')

            return analysis

        except Exception as e:
            logger.debug(f"Analysis failed for {stock.ts_code}: {e}")
            return None

    async def analyze_all(self) -> Dict:
        """分析所有股票"""
        print("\n[*] Fetching all stocks from database...")
        stocks = await self.get_all_stocks()

        if not stocks:
            print("[-] No stocks found in database")
            return {}

        print(f"[+] Found {len(stocks)} stocks\n")
        print("[*] Starting Chan theory analysis for all stocks...")
        print("    (This may take a few minutes)\n")

        results = {
            'uptrend': [],
            'downtrend': [],
            'consolidating': [],
            'buy_signals': [],
            'sell_signals': [],
            'failed': [],
        }

        total = len(stocks)
        analyzed = 0
        failed = 0

        for i, stock in enumerate(stocks):
            # Progress indicator
            if (i + 1) % 10 == 0 or i == 0:
                print(f"    [{i+1}/{total}] Processing {stock.ts_code} ({stock.name})...", end='')

            try:
                analysis = await self.analyze_stock(stock)

                if analysis:
                    analyzed += 1
                    trend = analysis['trend']

                    # Categorize by trend
                    if trend == 'up':
                        results['uptrend'].append(analysis)
                    elif trend == 'down':
                        results['downtrend'].append(analysis)
                    else:
                        results['consolidating'].append(analysis)

                    # Identify signals
                    if analysis.get('price_position') == 'above':
                        results['buy_signals'].append(analysis)
                    elif analysis.get('price_position') == 'below':
                        results['sell_signals'].append(analysis)

                    if (i + 1) % 10 == 0 or i == 0:
                        print(" OK")
                else:
                    failed += 1
                    if (i + 1) % 10 == 0 or i == 0:
                        print(" (insufficient data)")

            except Exception as e:
                failed += 1
                results['failed'].append({
                    'ts_code': stock.ts_code,
                    'name': stock.name,
                    'error': str(e)
                })

        print(f"\n[+] Analysis complete!")
        print(f"    Analyzed: {analyzed}/{total}")
        print(f"    Failed: {failed}")

        return results

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()


async def main():
    """主函数"""

    # Database configuration
    database_url = "mysql+aiomysql://root:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock"

    print("="*70)
    print("  BATCH STOCK CHAN THEORY ANALYSIS SYSTEM")
    print("="*70)

    analyzer = StockAnalyzer(database_url)

    # Connect to database
    if not await analyzer.connect():
        print("\n[!] Cannot proceed without database connection")
        return

    # Analyze all stocks
    results = await analyzer.analyze_all()

    # Print results
    print("\n" + "="*70)
    print("  ANALYSIS RESULTS")
    print("="*70)

    print(f"\n[TREND SUMMARY]")
    print(f"  Uptrend stocks:      {len(results['uptrend']):4d}")
    print(f"  Downtrend stocks:    {len(results['downtrend']):4d}")
    print(f"  Consolidating:       {len(results['consolidating']):4d}")
    print(f"  Buy signals:         {len(results['buy_signals']):4d}")
    print(f"  Sell signals:        {len(results['sell_signals']):4d}")

    # Top uptrend stocks
    if results['uptrend']:
        print(f"\n[TOP 10 UPTREND STOCKS]")
        sorted_up = sorted(results['uptrend'],
                          key=lambda x: x['bi_count'], reverse=True)[:10]
        for i, stock in enumerate(sorted_up, 1):
            print(f"  {i:2d}. {stock['ts_code']:10s} {stock['name']:20s} | "
                  f"Trend:UP | Bi:{stock['bi_count']:2d} Seg:{stock['segment_count']:2d} "
                  f"Hub:{stock['hub_count']:2d}")

    # Top downtrend stocks
    if results['downtrend']:
        print(f"\n[TOP 10 DOWNTREND STOCKS]")
        sorted_down = sorted(results['downtrend'],
                            key=lambda x: x['bi_count'], reverse=True)[:10]
        for i, stock in enumerate(sorted_down, 1):
            print(f"  {i:2d}. {stock['ts_code']:10s} {stock['name']:20s} | "
                  f"Trend:DOWN | Bi:{stock['bi_count']:2d} Seg:{stock['segment_count']:2d} "
                  f"Hub:{stock['hub_count']:2d}")

    # Buy opportunity stocks
    if results['buy_signals']:
        print(f"\n[BUY OPPORTUNITY STOCKS - Price Above Hub Upper Level]")
        sorted_buy = sorted(results['buy_signals'],
                           key=lambda x: x['bi_count'], reverse=True)[:10]
        for i, stock in enumerate(sorted_buy, 1):
            print(f"  {i:2d}. {stock['ts_code']:10s} {stock['name']:20s} | "
                  f"Position:ABOVE | Hub:{stock['latest_hub_high']:.2f}")

    # Sell opportunity stocks
    if results['sell_signals']:
        print(f"\n[SELL OPPORTUNITY STOCKS - Price Below Hub Lower Level]")
        sorted_sell = sorted(results['sell_signals'],
                            key=lambda x: x['bi_count'], reverse=True)[:10]
        for i, stock in enumerate(sorted_sell, 1):
            print(f"  {i:2d}. {stock['ts_code']:10s} {stock['name']:20s} | "
                  f"Position:BELOW | Hub:{stock['latest_hub_low']:.2f}")

    # Statistics
    print(f"\n[KEY METRICS DISTRIBUTION]")

    all_stocks = (results['uptrend'] + results['downtrend'] +
                 results['consolidating'])

    if all_stocks:
        bi_counts = [s['bi_count'] for s in all_stocks]
        seg_counts = [s['segment_count'] for s in all_stocks]
        hub_counts = [s['hub_count'] for s in all_stocks]

        print(f"  Bi count:       avg={sum(bi_counts)/len(bi_counts):.1f}, "
              f"min={min(bi_counts)}, max={max(bi_counts)}")
        print(f"  Segment count:  avg={sum(seg_counts)/len(seg_counts):.1f}, "
              f"min={min(seg_counts)}, max={max(seg_counts)}")
        print(f"  Hub count:      avg={sum(hub_counts)/len(hub_counts):.1f}, "
              f"min={min(hub_counts)}, max={max(hub_counts)}")

    # Export detailed results
    print(f"\n[DETAILED RESULTS]")
    print("  Uptrend stocks saved to: uptrend_stocks.csv")
    print("  Downtrend stocks saved to: downtrend_stocks.csv")
    print("  Buy signals saved to: buy_signals.csv")
    print("  Sell signals saved to: sell_signals.csv")

    # Save to CSV
    if results['uptrend']:
        df = pd.DataFrame(results['uptrend'])
        df.to_csv('uptrend_stocks.csv', index=False, encoding='utf-8')

    if results['downtrend']:
        df = pd.DataFrame(results['downtrend'])
        df.to_csv('downtrend_stocks.csv', index=False, encoding='utf-8')

    if results['buy_signals']:
        df = pd.DataFrame(results['buy_signals'])
        df.to_csv('buy_signals.csv', index=False, encoding='utf-8')

    if results['sell_signals']:
        df = pd.DataFrame(results['sell_signals'])
        df.to_csv('sell_signals.csv', index=False, encoding='utf-8')

    # Close database connection
    await analyzer.close()

    print("\n[+] All analysis complete!")
    print("="*70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] Analysis interrupted by user")
    except Exception as e:
        print(f"\n[-] Fatal error: {e}")
        import traceback
        traceback.print_exc()
