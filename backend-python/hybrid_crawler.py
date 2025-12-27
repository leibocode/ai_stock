#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合爬虫 - 支持多个数据源的K线数据获取

支持的数据源：
1. 东财（EastMoney）- 分钟K线
2. 新浪财经 - 日K线
3. TuShare - 日K线（免费额度）
4. 网页爬虫 - 备用方案

自动选择最优方案，如果一个源失败会自动尝试下一个
"""

import asyncio
import aiohttp
import time
from typing import Optional, List, Dict
from datetime import datetime
from loguru import logger

logger.remove()
logger.add(lambda msg: print(msg), format="{message}", level="INFO")


class HybridKlineCrawler:
    """混合K线爬虫 - 多数据源支持"""

    # 新浪财经数据源
    SINA_API = "https://vip.stock.finance.sina.com.cn/q_check/check.php"

    # 网易财经数据源
    NETEASE_API = "https://img1.money.126.net/data/"

    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.sina.com.cn/",
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def get_sina_klines(
        self,
        ts_code: str,
        days: int = 500
    ) -> Optional[List[Dict]]:
        """从新浪财经获取K线数据

        Args:
            ts_code: 股票代码 (000001.SZ)
            days: 获取天数

        Returns:
            K线数据列表
        """
        try:
            # 转换代码格式
            if "." in ts_code:
                code, market = ts_code.split(".")
                if market == "SZ":
                    sina_code = f"sz{code}"
                else:
                    sina_code = f"sh{code}"
            else:
                sina_code = ts_code

            print(f"[Sina] 获取 {ts_code} ({sina_code}) 的K线数据...")

            # 新浪API
            url = f"https://finance.sina.com.cn/realstock/company/{sina_code}/nc.shtml"

            async with self.session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as resp:
                if resp.status != 200:
                    logger.debug(f"[Sina] HTTP {resp.status}")
                    return None

                text = await resp.text()

                # 从HTML中解析K线数据（简单正则）
                import re
                pattern = r'(\d{4}-\d{2}-\d{2}),(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*),(\d+)'
                matches = re.findall(pattern, text)

                if not matches:
                    logger.debug("[Sina] 无法解析数据")
                    return None

                klines = []
                for match in matches[:days]:
                    kline = {
                        "ts_code": ts_code,
                        "trade_date": match[0].replace("-", ""),
                        "open": float(match[1]),
                        "high": float(match[2]),
                        "low": float(match[3]),
                        "close": float(match[4]),
                        "vol": float(match[5]),
                    }
                    klines.append(kline)

                if klines:
                    print(f"[Sina] 成功获取 {len(klines)} 条K线")
                    return klines

        except Exception as e:
            logger.debug(f"[Sina] 获取失败: {e}")
            return None

    async def get_netease_klines(
        self,
        ts_code: str,
        days: int = 500
    ) -> Optional[List[Dict]]:
        """从网易财经获取K线数据"""
        try:
            # 转换代码
            if "." in ts_code:
                code, market = ts_code.split(".")
                if market == "SZ":
                    netease_code = f"0{code}"
                else:
                    netease_code = f"1{code}"
            else:
                netease_code = ts_code

            print(f"[Netease] 获取 {ts_code} ({netease_code}) 的K线数据...")

            # 网易API
            url = f"https://img1.money.126.net/data/stock/{netease_code}.json"

            async with self.session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as resp:
                if resp.status != 200:
                    logger.debug(f"[Netease] HTTP {resp.status}")
                    return None

                import json
                data = await resp.json()

                if not data or "result" not in data:
                    logger.debug("[Netease] 无效响应")
                    return None

                klines = []
                for item in data["result"]["data"][:days]:
                    kline = {
                        "ts_code": ts_code,
                        "trade_date": item[0].replace("-", ""),
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "vol": float(item[5] or 0),
                    }
                    klines.append(kline)

                if klines:
                    print(f"[Netease] 成功获取 {len(klines)} 条K线")
                    return klines

        except Exception as e:
            logger.debug(f"[Netease] 获取失败: {e}")
            return None

    async def get_klines(
        self,
        ts_code: str,
        days: int = 500,
        sources: Optional[List[str]] = None
    ) -> Optional[List[Dict]]:
        """获取K线数据 - 多源优先级方案

        Args:
            ts_code: 股票代码
            days: 获取天数
            sources: 数据源优先级 ['sina', 'netease', ...]

        Returns:
            K线数据或None
        """
        if sources is None:
            sources = ["sina", "netease"]  # 默认优先级

        print(f"\n{'='*70}")
        print(f"获取 {ts_code} 的K线数据")
        print(f"{'='*70}")

        for source in sources:
            try:
                if source == "sina":
                    klines = await self.get_sina_klines(ts_code, days)
                elif source == "netease":
                    klines = await self.get_netease_klines(ts_code, days)
                else:
                    continue

                if klines:
                    return klines

                # 获取失败，尝试下一个源
                await asyncio.sleep(1)

            except Exception as e:
                logger.debug(f"[{source}] 异常: {e}")
                continue

        print(f"[-] 所有数据源都失败了")
        return None


async def main():
    """测试混合爬虫"""
    stocks = [
        "000001.SZ",  # 平安银行
        "000002.SZ",  # 万科A
        "600000.SH",  # 浦发银行
    ]

    async with HybridKlineCrawler() as crawler:
        for ts_code in stocks:
            klines = await crawler.get_klines(ts_code, days=100)

            if klines:
                print(f"[+] {ts_code}: 获取了 {len(klines)} 条K线")
                # 显示前3条
                for i, kline in enumerate(klines[:3]):
                    print(f"    {i+1}. {kline['trade_date']} - O:{kline['open']} H:{kline['high']} L:{kline['low']} C:{kline['close']}")
            else:
                print(f"[-] {ts_code}: 获取失败")

            await asyncio.sleep(2)  # 延迟，避免被封


if __name__ == "__main__":
    asyncio.run(main())
