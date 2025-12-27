#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东财数据爬虫工具 - 抓取日K和分时数据

支持：
- 日线数据（K线周期 101）
- 5/15/30/60 分钟K线
- 动态IP代理（可选）
- 自动重试和反爬虫

使用方法：
    # 基础用法（不用代理）
    python fetch_eastmoney_klines.py 000001.SZ

    # 使用代理IP池
    python fetch_eastmoney_klines.py 000001.SZ --proxies http://proxy1:port http://proxy2:port

    # 获取多周期数据
    python fetch_eastmoney_klines.py 000001.SZ --periods 5 15 30

    # 批量抓取
    python fetch_eastmoney_klines.py --batch 100
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from app.services.crawler.minute_kline import MinuteKlineCrawler

logger.remove()
logger.add(
    lambda msg: print(msg),
    format="<level>{level: <8}</level> | <cyan>{asctime}</cyan> - <level>{message}</level>",
    level="INFO"
)


async def fetch_klines_for_stock(
    ts_code: str,
    periods: List[str] = None,
    proxies: Optional[List[str]] = None
):
    """为单只股票抓取K线数据"""
    if periods is None:
        periods = ["5", "30"]

    print(f"\n{'='*70}")
    print(f"抓取 {ts_code} 的K线数据")
    print(f"{'='*70}")
    print(f"周期: {', '.join(periods)}")

    # 创建爬虫实例
    crawler = MinuteKlineCrawler(proxies=proxies)

    results = {}

    for period in periods:
        try:
            print(f"\n[*] 获取 {period} 分钟K线...")
            klines = await crawler.get_minute_klines(ts_code, period=period, count=500)

            if klines:
                results[period] = klines
                print(f"[+] 成功获取 {len(klines)} 条数据")

                # 显示样本数据
                if len(klines) > 0:
                    first = klines[0]
                    last = klines[-1]
                    print(f"    首条: {first.get('trade_date')} - {first.get('open')} / {first.get('close')}")
                    print(f"    末条: {last.get('trade_date')} - {last.get('open')} / {last.get('close')}")
            else:
                print(f"[-] 获取失败或数据为空")

        except Exception as e:
            logger.error(f"获取 {period} 分钟K线失败: {e}")

    print(f"\n{'='*70}")
    print(f"完成！获取了 {len(results)} 种周期的数据")
    print(f"{'='*70}")

    return results


async def batch_fetch_klines(
    stock_codes: List[str],
    periods: List[str] = None,
    proxies: Optional[List[str]] = None
):
    """批量抓取多只股票的K线数据"""
    if periods is None:
        periods = ["5", "30"]

    print(f"\n{'='*70}")
    print(f"批量抓取 {len(stock_codes)} 只股票的K线数据")
    print(f"{'='*70}")

    all_results = {}

    for i, ts_code in enumerate(stock_codes):
        print(f"\n[{i+1}/{len(stock_codes)}] 处理 {ts_code}...")
        try:
            results = await fetch_klines_for_stock(ts_code, periods, proxies)
            all_results[ts_code] = results
        except Exception as e:
            logger.error(f"处理 {ts_code} 失败: {e}")

    print(f"\n{'='*70}")
    print(f"批量抓取完成！")
    print("="*70)
    print(f"成功: {len(all_results)} 只股票")
    print("="*70)

    return all_results


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="东财数据爬虫 - 抓取日K和分时数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python fetch_eastmoney_klines.py 000001.SZ
  python fetch_eastmoney_klines.py 000001.SZ --periods 5 15 30 60
  python fetch_eastmoney_klines.py 000001.SZ --proxies http://proxy1:8080 http://proxy2:8080
  python fetch_eastmoney_klines.py --batch stocks.txt
        """
    )

    parser.add_argument(
        "ts_code",
        nargs="?",
        help="股票代码 (如 000001.SZ)"
    )

    parser.add_argument(
        "--periods",
        nargs="+",
        default=["5", "30"],
        choices=["5", "15", "30", "60", "101"],
        help="K线周期 (5/15/30/60/101分钟或日线)"
    )

    parser.add_argument(
        "--proxies",
        nargs="+",
        help="代理IP列表 (格式: http://ip:port)"
    )

    parser.add_argument(
        "--batch",
        type=str,
        help="批量模式 - 从文件读取股票列表 (每行一个代码)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="请求间延迟（秒），用于反爬虫"
    )

    args = parser.parse_args()

    # 验证参数
    if not args.ts_code and not args.batch:
        parser.print_help()
        return

    # 日志信息
    print(f"\nEastMoney K线数据爬虫")
    print(f"{'='*70}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"周期: {', '.join(args.periods)}")
    if args.proxies:
        print(f"代理: {len(args.proxies)} 个 IP")
    else:
        print(f"代理: 不使用代理（直连）")
    print(f"{'='*70}")

    # 执行爬虫
    if args.batch:
        # 批量模式
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                stock_codes = [line.strip() for line in f if line.strip()]

            if not stock_codes:
                logger.error(f"文件为空: {args.batch}")
                return

            await batch_fetch_klines(stock_codes, args.periods, args.proxies)

        except FileNotFoundError:
            logger.error(f"文件不存在: {args.batch}")
        except Exception as e:
            logger.error(f"批量处理失败: {e}")

    else:
        # 单只股票模式
        await fetch_klines_for_stock(args.ts_code, args.periods, args.proxies)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n用户中断爬虫")
    except Exception as e:
        logger.error(f"错误: {e}")
        import traceback
        traceback.print_exc()
