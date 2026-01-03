# -*- coding: utf-8 -*-
"""融资融券爬虫

获取融资融券数据，包括余额、余额占比、融资融券比例等
"""
from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class FinanceFinancingCrawler(BaseCrawler):
    """融资融券数据爬虫"""

    async def crawl_financing_stocks(self) -> List[Dict]:
        """爬取融资融券活跃股

        Returns:
            融资融券股票列表 [{code, name, margin_balance, short_balance, ratio, ...}]
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "100",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:71",  # 融资融券股票
                "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f62,f104,f105,f106,f107,f109,f110",
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning("Financing API returned invalid data")
                return []

            diff_list = data.get("data", {}).get("diff", [])
            if not diff_list:
                logger.debug("No financing stocks found")
                return []

            stocks = []
            for item in diff_list:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    stock = {
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "price": float(item.get("f2", 0)),
                        "pct_chg": round(float(item.get("f3", 0) or 0), 2),
                        "margin_balance": float(item.get("f104", 0)) / 100000000,  # 融资余额（亿）
                        "short_balance": float(item.get("f105", 0)) / 100000000,   # 融券余额（亿）
                        "margin_volume": float(item.get("f106", 0)),               # 融资买入额
                        "short_volume": float(item.get("f107", 0)),               # 融券卖出额
                        "financing_ratio": round(float(item.get("f109", 0) or 0), 2),  # 融资占比
                        "net_financing": float(item.get("f110", 0)) / 100000000,  # 融资净额（亿）
                    }
                    stocks.append(stock)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse financing item {item}: {e}")
                    continue

            logger.info(f"Crawled {len(stocks)} financing stocks")
            return stocks

        except Exception as e:
            logger.error(f"Failed to crawl financing stocks: {e}")
            return []

    async def crawl_financing_summary(self) -> Dict:
        """爬取融资融券市场汇总数据

        Returns:
            市场汇总数据 {total_margin, total_short, margin_pct_chg, ...}
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
            params = {
                "fields1": "f1,f2,f3,f4",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            }

            data = await self.get(url, params, retry=False)

            if not data or not data.get("data"):
                logger.warning("Financing summary API returned no data")
                return {
                    "total_margin": 0,
                    "total_short": 0,
                    "margin_buy": 0,
                    "short_sell": 0,
                }

            d = data.get("data", {})
            return {
                "total_margin": round(float(d.get("rzye", 0)) / 100000000, 2),      # 融资余额
                "total_short": round(float(d.get("rqye", 0)) / 100000000, 2),       # 融券余额
                "total_financing": round(float(d.get("rzye", 0) or 0) / 100000000 + float(d.get("rqye", 0) or 0) / 100000000, 2),
                "margin_buy": float(d.get("rzmbe", 0)) / 100000000,                 # 融资买入额
                "short_sell": float(d.get("rqmce", 0)) / 100000000,                # 融券卖出额
                "update_time": d.get("timetimestamp", ""),
            }

        except Exception as e:
            logger.error(f"Failed to crawl financing summary: {e}")
            return {}

    async def get_financing_rank(self, top_n: int = 20) -> List[Dict]:
        """获取融资余额排行

        Args:
            top_n: 返回前N条

        Returns:
            融资余额排行榜
        """
        stocks = await self.crawl_financing_stocks()
        # 按融资余额排序
        stocks.sort(key=lambda x: x.get("margin_balance", 0), reverse=True)
        return stocks[:top_n]

    async def get_financing_increase_rank(self, top_n: int = 20) -> List[Dict]:
        """获取融资余额增幅排行

        Args:
            top_n: 返回前N条

        Returns:
            融资余额增幅排行榜
        """
        stocks = await self.crawl_financing_stocks()
        # 按融资占比排序（净增幅）
        stocks.sort(key=lambda x: x.get("financing_ratio", 0), reverse=True)
        return stocks[:top_n]
