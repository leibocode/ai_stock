from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class NorthFlowCrawler(BaseCrawler):
    """北向资金爬虫"""

    async def crawl_north_flow(self, trade_date: str) -> Dict:
        """爬取北向资金数据"""
        try:
            url = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
            data = await self.get(url)

            if not data:
                return {"hgt": 0, "sgt": 0, "north_money": 0}

            result = data.get("data", {})
            return {
                "hgt": float(result.get("hgt", 0)) / 10000,  # 万元转亿元
                "sgt": float(result.get("sgt", 0)) / 10000,
                "north_money": (float(result.get("hgt", 0)) + float(result.get("sgt", 0))) / 10000,
            }
        except Exception as e:
            logger.error(f"Failed to crawl north flow: {e}")
            return {"hgt": 0, "sgt": 0, "north_money": 0}
