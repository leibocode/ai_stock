from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class DragonTigerCrawler(BaseCrawler):
    """龙虎榜爬虫"""

    async def crawl_dragon_tiger(self, trade_date: str) -> List[Dict]:
        """爬取龙虎榜数据

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            龙虎榜股票列表
        """
        dragon_tiger_list = []

        try:
            # 格式化日期：YYYYMMDD -> YYYY-MM-DD
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                "columns": "ALL",
                "filter": f"(TRADE_DATE='{formatted_date}')",
                "pageNumber": 1,
                "pageSize": 500,
                "sortTypes": "-1",
                "sortColumns": "CLOSE_PRICE",
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning(f"Dragon tiger API returned invalid data for {trade_date}")
                return []

            result = data.get("result", {})
            if not result or not isinstance(result, dict):
                logger.warning(f"No result in dragon tiger API response for {trade_date}")
                return []

            items = result.get("data", [])
            if not items:
                logger.info(f"No dragon tiger data for {trade_date}")
                return []

            for item in items:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    dragon_tiger_list.append({
                        "code": item.get("SECURITY_CODE", ""),
                        "name": item.get("SECURITY_NAME", ""),
                        "pct_chg": round(float(item.get("CHGPERCENT", 0)), 2),
                        "net_amount": round(float(item.get("BUY_AMOUNT", 0) or 0) - float(item.get("SELL_AMOUNT", 0) or 0)) / 10000,
                        "buy_amount": round(float(item.get("BUY_AMOUNT", 0) or 0) / 10000, 2),
                        "sell_amount": round(float(item.get("SELL_AMOUNT", 0) or 0) / 10000, 2),
                        "reason": item.get("REASON", "龙虎榜"),
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse dragon tiger item: {e}")
                    continue

            logger.info(f"Crawled {len(dragon_tiger_list)} dragon tiger records for {trade_date}")
            return dragon_tiger_list

        except Exception as e:
            logger.error(f"Failed to crawl dragon tiger: {e}")
            return []
