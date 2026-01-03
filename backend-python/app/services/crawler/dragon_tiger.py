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
        # 尝试多个reportName方案，从新到旧
        report_names = [
            "RPT_DAILYBILLBOARD_DETAILSNEW",  # 新版本（2024+）
            "RPT_DAILYBILLBOARD_DETAILS",      # 旧版本（备选）
        ]

        for report_name in report_names:
            result = await self._crawl_with_report(trade_date, report_name)
            if result:
                return result

        logger.warning(f"Failed to crawl dragon tiger from all sources for {trade_date}")
        return []

    async def _crawl_with_report(self, trade_date: str, report_name: str) -> List[Dict]:
        """使用指定reportName爬取龙虎榜数据"""
        dragon_tiger_list = []

        try:
            # 格式化日期：YYYYMMDD -> YYYY-MM-DD
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": report_name,
                "columns": "ALL",
                "filter": f"(TRADE_DATE='{formatted_date}')",
                "pageNumber": 1,
                "pageSize": 500,
                "sortTypes": "-1",
                "sortColumns": "CLOSE_PRICE",
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.debug(f"Invalid response for {report_name} on {trade_date}")
                return []

            result = data.get("result", {})
            if not result or not isinstance(result, dict):
                logger.debug(f"No result in response for {report_name} on {trade_date}")
                return []

            items = result.get("data", [])
            if not items:
                logger.debug(f"No dragon tiger data for {report_name} on {trade_date}")
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

            if dragon_tiger_list:
                logger.info(f"Crawled {len(dragon_tiger_list)} dragon tiger records for {trade_date} using {report_name}")
                return dragon_tiger_list

            return []

        except Exception as e:
            logger.debug(f"Failed to crawl dragon tiger with {report_name}: {e}")
            return []
