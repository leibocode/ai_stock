#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Complete Batch Stock Analysis Demo

Simulates analyzing 100+ stocks using Chan theory algorithm
Shows the complete workflow:
1. Generate simulated stock data
2. Run Chan analysis for each stock
3. Identify trends and trading signals
4. Generate comprehensive report
5. Export results to CSV
"""

import sys
import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
import random

sys.path.insert(0, r'C:\Users\02584\Desktop\新建文件夹\ai_stock\backend-python')

from app.services.chan_service import ChanService
from loguru import logger

# Configure logging
logger.remove()


class MockStock:
    """模拟股票数据"""

    def __init__(self, ts_code: str, name: str):
        self.ts_code = ts_code
        self.name = name


def generate_stock_klines(ts_code: str, days: int = 200) -> pd.DataFrame:
    """为每只股票生成模拟K线数据"""

    # Generate random price movement
    start_price = random.uniform(10, 100)
    prices = [start_price]

    for _ in range(days - 1):
        # Random walk with trend
        trend = random.choice([-1, -1, -1, 0, 1, 1, 1])  # Bias for uptrend
        change = random.uniform(-2, 3) + trend * 0.5
        prices.append(max(prices[-1] + change, 5))

    data = []
    for i, close in enumerate(prices):
        high = close + random.uniform(0, 1.5)
        low = close - random.uniform(0, 1.5)
        low = min(low, close)

        data.append({
            'trade_date': datetime(2024, 1, 1) + timedelta(days=i),
            'open': close + random.uniform(-0.5, 0.5),
            'high': high,
            'low': low,
            'close': close,
            'vol': random.uniform(1000000, 10000000),
        })

    df = pd.DataFrame(data)
    return df


def analyze_stock(stock: MockStock) -> Dict:
    """分析单只股票"""
    try:
        # Generate K-lines
        klines = generate_stock_klines(stock.ts_code)

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

        # Get buy/sell signals based on current price and hub
        if result['hubs'] and len(result['hubs']) > 0:
            latest_hub = result['hubs'][-1]
            last_price = float(klines.iloc[-1]['close'])

            analysis['latest_price'] = last_price
            analysis['hub_high'] = float(latest_hub['high'])
            analysis['hub_low'] = float(latest_hub['low'])

            if last_price > latest_hub['high']:
                analysis['signal'] = 'BUY (Above Hub)'
                analysis['price_position'] = 'above'
            elif last_price < latest_hub['low']:
                analysis['signal'] = 'SELL (Below Hub)'
                analysis['price_position'] = 'below'
            else:
                analysis['signal'] = 'HOLD (Inside Hub)'
                analysis['price_position'] = 'inside'
        else:
            analysis['signal'] = 'NO SIGNAL'
            analysis['price_position'] = 'unknown'

        return analysis

    except Exception as e:
        print(f"[-] Analysis failed for {stock.ts_code}: {e}")
        return None


def main():
    """主函数"""

    print("="*80)
    print("  BATCH STOCK CHAN THEORY ANALYSIS SYSTEM - DEMO VERSION")
    print("="*80)
    print()

    # Generate mock stock data
    stock_codes = [
        ("000001.SZ", "平安银行"),
        ("000002.SZ", "万科A"),
        ("000333.SZ", "美的集团"),
        ("000858.SZ", "五粮液"),
        ("000961.SZ", "中南建筑"),
        ("600000.SH", "浦发银行"),
        ("600009.SH", "上海电影"),
        ("600016.SH", "民生银行"),
        ("600028.SH", "中国石化"),
        ("600030.SH", "中信证券"),
        ("600031.SH", "三一重工"),
        ("600036.SH", "招商银行"),
        ("600048.SH", "上海临港"),
        ("600050.SH", "中国联通"),
        ("600060.SH", "海信家电"),
        ("600061.SH", "国投电力"),
        ("600062.SH", "华夏能源"),
        ("600066.SH", "宇通客车"),
        ("600074.SH", "华纺股份"),
        ("600078.SH", "澄星股份"),
        ("600089.SH", "特变电工"),
        ("600100.SH", "同方股份"),
        ("600104.SH", "上汽集团"),
        ("600109.SH", "国金证券"),
        ("600115.SH", "东方航空"),
        ("600118.SH", "中国平安"),
        ("600125.SH", "铁流股份"),
        ("600132.SH", "重庆啤酒"),
        ("600138.SH", "中青旅"),
        ("600143.SH", "金发科技"),
        ("600145.SH", "新兴铸管"),
        ("600150.SH", "中国船舶"),
        ("600161.SH", "天坛生物"),
        ("600170.SH", "上海建工"),
        ("600176.SH", "兖州煤业"),
        ("600177.SH", "益阳纸业"),
        ("600183.SH", "生益科技"),
        ("600188.SH", "兖矿能源"),
        ("600196.SH", "复星医药"),
        ("600208.SH", "新华制药"),
        ("600209.SH", "ST罗顿"),
        ("600210.SH", "紫江企业"),
        ("600211.SH", "西藏药业"),
        ("600213.SH", "亚星客车"),
        ("600215.SH", "长春经开"),
        ("600216.SH", "浙江医药"),
        ("600219.SH", "南山铝业"),
        ("600221.SH", "海南航空"),
        ("600222.SH", "太阳能"),
        ("600223.SH", "莱钢股份"),
        ("600225.SH", "天津松江"),
    ]

    stocks = [MockStock(code, name) for code, name in stock_codes]

    print(f"[*] Generating simulated K-line data for {len(stocks)} stocks...")
    print(f"[*] Running Chan theory analysis...\n")

    results = {
        'uptrend': [],
        'downtrend': [],
        'consolidating': [],
        'buy_signals': [],
        'sell_signals': [],
        'hold_signals': [],
    }

    total = len(stocks)

    # Analyze each stock
    for i, stock in enumerate(stocks):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"    [{i+1:3d}/{total}] Analyzing {stock.ts_code:10s} ({stock.name:15s})... ", end='', flush=True)

        analysis = analyze_stock(stock)

        if analysis:
            trend = analysis['trend']

            # Categorize by trend
            if trend == 'up':
                results['uptrend'].append(analysis)
            elif trend == 'down':
                results['downtrend'].append(analysis)
            else:
                results['consolidating'].append(analysis)

            # Categorize by signal
            if 'BUY' in analysis['signal']:
                results['buy_signals'].append(analysis)
            elif 'SELL' in analysis['signal']:
                results['sell_signals'].append(analysis)
            else:
                results['hold_signals'].append(analysis)

            if (i + 1) % 10 == 0 or i == 0:
                print("OK")

    # Print results
    print("\n" + "="*80)
    print("  ANALYSIS RESULTS")
    print("="*80)

    print(f"\n[OVERALL STATISTICS]")
    print(f"  Total stocks analyzed:     {len(stocks):4d}")
    print(f"  Uptrend stocks:            {len(results['uptrend']):4d} ({len(results['uptrend'])*100/len(stocks):.1f}%)")
    print(f"  Downtrend stocks:          {len(results['downtrend']):4d} ({len(results['downtrend'])*100/len(stocks):.1f}%)")
    print(f"  Consolidating stocks:      {len(results['consolidating']):4d} ({len(results['consolidating'])*100/len(stocks):.1f}%)")

    print(f"\n[TRADING SIGNALS]")
    print(f"  Buy signals (Price > Hub):       {len(results['buy_signals']):4d}")
    print(f"  Sell signals (Price < Hub):      {len(results['sell_signals']):4d}")
    print(f"  Hold signals (Price in Hub):     {len(results['hold_signals']):4d}")

    # Top uptrend stocks
    if results['uptrend']:
        print(f"\n[TOP 15 UPTREND STOCKS]")
        print(f"{'Rank':>4s} {'Code':10s} {'Name':15s} {'Trend':8s} {'Bi':4s} {'Seg':4s} {'Hub':4s} {'Signal':20s}")
        print("-" * 80)

        sorted_up = sorted(results['uptrend'],
                          key=lambda x: (x['hub_count'], x['bi_count']), reverse=True)[:15]

        for i, stock in enumerate(sorted_up, 1):
            print(f"{i:4d}. {stock['ts_code']:10s} {stock['name']:15s} {'UP':8s} "
                  f"{stock['bi_count']:4d} {stock['segment_count']:4d} {stock['hub_count']:4d} "
                  f"{stock['signal']:20s}")

    # Buy signals
    if results['buy_signals']:
        print(f"\n[BUY OPPORTUNITY STOCKS - Price Above Hub Upper Level]")
        print(f"{'Rank':>4s} {'Code':10s} {'Name':15s} {'Price':10s} {'Hub High':10s} {'Gap':10s}")
        print("-" * 70)

        sorted_buy = sorted(results['buy_signals'],
                           key=lambda x: x['bi_count'], reverse=True)[:10]

        for i, stock in enumerate(sorted_buy, 1):
            gap = ((stock['latest_price'] - stock['hub_high']) / stock['hub_high']) * 100
            print(f"{i:4d}. {stock['ts_code']:10s} {stock['name']:15s} "
                  f"{stock['latest_price']:10.2f} {stock['hub_high']:10.2f} {gap:+10.2f}%")

    # Sell signals
    if results['sell_signals']:
        print(f"\n[SELL OPPORTUNITY STOCKS - Price Below Hub Lower Level]")
        print(f"{'Rank':>4s} {'Code':10s} {'Name':15s} {'Price':10s} {'Hub Low':10s} {'Gap':10s}")
        print("-" * 70)

        sorted_sell = sorted(results['sell_signals'],
                            key=lambda x: x['bi_count'], reverse=True)[:10]

        for i, stock in enumerate(sorted_sell, 1):
            gap = ((stock['latest_price'] - stock['hub_low']) / stock['hub_low']) * 100
            print(f"{i:4d}. {stock['ts_code']:10s} {stock['name']:15s} "
                  f"{stock['latest_price']:10.2f} {stock['hub_low']:10.2f} {gap:+10.2f}%")

    # Key metrics
    print(f"\n[DISTRIBUTION STATISTICS]")

    all_stocks = (results['uptrend'] + results['downtrend'] +
                 results['consolidating'])

    if all_stocks:
        bi_counts = [s['bi_count'] for s in all_stocks]
        seg_counts = [s['segment_count'] for s in all_stocks]
        hub_counts = [s['hub_count'] for s in all_stocks]

        print(f"  Bi count:       avg={sum(bi_counts)/len(bi_counts):6.1f}, min={min(bi_counts):3d}, max={max(bi_counts):3d}")
        print(f"  Segment count:  avg={sum(seg_counts)/len(seg_counts):6.1f}, min={min(seg_counts):3d}, max={max(seg_counts):3d}")
        print(f"  Hub count:      avg={sum(hub_counts)/len(hub_counts):6.1f}, min={min(hub_counts):3d}, max={max(hub_counts):3d}")

    # Export results
    print(f"\n[EXPORTING RESULTS TO CSV]")

    if results['uptrend']:
        df = pd.DataFrame(results['uptrend'])
        df.to_csv('uptrend_stocks.csv', index=False, encoding='utf-8-sig')
        print(f"  [+] Saved uptrend stocks to: uptrend_stocks.csv")

    if results['downtrend']:
        df = pd.DataFrame(results['downtrend'])
        df.to_csv('downtrend_stocks.csv', index=False, encoding='utf-8-sig')
        print(f"  [+] Saved downtrend stocks to: downtrend_stocks.csv")

    if results['buy_signals']:
        df = pd.DataFrame(results['buy_signals'])
        df.to_csv('buy_signals.csv', index=False, encoding='utf-8-sig')
        print(f"  [+] Saved buy signals to: buy_signals.csv")

    if results['sell_signals']:
        df = pd.DataFrame(results['sell_signals'])
        df.to_csv('sell_signals.csv', index=False, encoding='utf-8-sig')
        print(f"  [+] Saved sell signals to: sell_signals.csv")

    if results['hold_signals']:
        df = pd.DataFrame(results['hold_signals'])
        df.to_csv('hold_signals.csv', index=False, encoding='utf-8-sig')
        print(f"  [+] Saved hold signals to: hold_signals.csv")

    print(f"\n[+] All CSV files saved in current directory!")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Analysis interrupted by user")
    except Exception as e:
        print(f"\n[-] Fatal error: {e}")
        import traceback
        traceback.print_exc()
