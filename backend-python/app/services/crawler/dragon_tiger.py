from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class DragonTigerCrawler(BaseCrawler):
    """龙虎榜爬虫"""

    async def crawl_dragon_tiger(self, trade_date: str) -> List[Dict]:
        """爬取龙虎榜数据"""
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                "pageNumber": 1,
                "pageSize": 500,
                "sortTypes": "-1",
                "sortFields": "TRADE_DATE",
                "conditions": f"TRADE_DATE={trade_date}",
            }

            data = await self.get(url, params)
            if not data or not data.get("result"):
                return []

            return [
                {
                    "code": item.get("SECURITY_CODE"),
                    "name": item.get("SECURITY_NAME"),
                    "pct_chg": float(item.get("CHGPERCENT", 0)),
                    "buy_amount": float(item.get("BUY_AMOUNT", 0)) / 10000,
                    "sell_amount": float(item.get("SELL_AMOUNT", 0)) / 10000,
                }
                for item in data.get("result", {}).get("data", [])
            ]
        except Exception as e:
            logger.error(f"Failed to crawl dragon tiger: {e}")
            return []
