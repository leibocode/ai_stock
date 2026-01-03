# -*- coding: utf-8 -*-
"""异常波动预警爬虫

获取交易异常波动的股票预警数据
"""
from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class AbnormalWarningCrawler(BaseCrawler):
    """异常波动预警爬虫"""

    async def crawl_abnormal_stocks(self, trade_date: str = "") -> List[Dict]:
        """爬取异常波动股票

        异常波动类型：
        - 连续涨停或跌停
        - 大幅上涨或下跌（超过阈值）
        - 成交量异常
        - 价格异常变化

        Args:
            trade_date: 交易日期 (YYYYMMDD)，为空则取最新

        Returns:
            异常波动股票列表
        """
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_ABNORMAL_TRADE_STOCK",  # 异常交易预警
                "columns": "ALL",
                "pageNumber": 1,
                "pageSize": 100,
                "sortTypes": "-1",
                "sortColumns": "TRADE_DATE",
            }

            if trade_date:
                # 格式化日期：YYYYMMDD -> YYYY-MM-DD
                formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
                params["filter"] = f"(TRADE_DATE='{formatted_date}')"

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning("Abnormal warning API returned invalid data")
                return []

            result = data.get("result", {})
            if not result or not isinstance(result, dict):
                logger.debug("No result in abnormal warning API response")
                return []

            items = result.get("data", [])
            if not items:
                logger.debug(f"No abnormal stocks found for {trade_date}")
                return []

            stocks = []
            for item in items:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    stock = {
                        "code": item.get("SECURITY_CODE", ""),
                        "name": item.get("SECURITY_NAME", ""),
                        "trade_date": item.get("TRADE_DATE", ""),
                        "price": float(item.get("CLOSE_PRICE", 0)),
                        "pct_chg": round(float(item.get("CHANGE_RATE", 0) or 0), 2),
                        "volume": float(item.get("VOLUME", 0)),
                        "amount": float(item.get("AMOUNT", 0)),
                        "abnormal_reason": item.get("ABNORMAL_REASON", ""),
                        "abnormal_type": item.get("ABNORMAL_TYPE", ""),
                    }
                    stocks.append(stock)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse abnormal item {item}: {e}")
                    continue

            logger.info(f"Crawled {len(stocks)} abnormal stocks")
            return stocks

        except Exception as e:
            logger.error(f"Failed to crawl abnormal stocks: {e}")
            return []

    async def crawl_continuous_limit(self, limit_days: int = 3) -> List[Dict]:
        """爬取连续涨停或跌停的股票

        Args:
            limit_days: 连续涨停或跌停天数

        Returns:
            连续涨跌停股票列表
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "500",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # 沪深A股
                "fields": "f12,f14,f2,f3,f4,f5,f6",
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning("Continuous limit API returned invalid data")
                return []

            diff_list = data.get("data", {}).get("diff", [])
            if not diff_list:
                logger.debug("No continuous limit stocks found")
                return []

            stocks = []
            for item in diff_list:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    pct_chg = float(item.get("f3", 0))
                    # 筛选连续涨停 (>=9.9%) 或连续跌停 (<=-9.9%)
                    if abs(pct_chg) >= 9.9:
                        stock = {
                            "code": item.get("f12", ""),
                            "name": item.get("f14", ""),
                            "price": float(item.get("f2", 0)),
                            "pct_chg": round(pct_chg, 2),
                            "type": "limit_up" if pct_chg >= 9.9 else "limit_down",
                        }
                        stocks.append(stock)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse continuous limit item {item}: {e}")
                    continue

            logger.info(f"Crawled {len(stocks)} continuous limit stocks")
            return stocks

        except Exception as e:
            logger.error(f"Failed to crawl continuous limit stocks: {e}")
            return []

    async def crawl_volatile_stocks(self, threshold_pct: float = 8.0) -> List[Dict]:
        """爬取高波动性股票

        Args:
            threshold_pct: 波动幅度阈值（%），默认8%

        Returns:
            高波动性股票列表
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "500",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8",  # 包含高低价
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning("Volatile stocks API returned invalid data")
                return []

            diff_list = data.get("data", {}).get("diff", [])
            if not diff_list:
                logger.debug("No volatile stocks found")
                return []

            stocks = []
            for item in diff_list:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    pct_chg = abs(float(item.get("f3", 0)))
                    if pct_chg >= threshold_pct:
                        stock = {
                            "code": item.get("f12", ""),
                            "name": item.get("f14", ""),
                            "price": float(item.get("f2", 0)),
                            "pct_chg": round(pct_chg, 2),
                            "high": float(item.get("f7", 0)),
                            "low": float(item.get("f8", 0)),
                            "amplitude": round((float(item.get("f7", 0)) - float(item.get("f8", 0))) / float(item.get("f2", 1)) * 100, 2),
                        }
                        stocks.append(stock)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse volatile item {item}: {e}")
                    continue

            logger.info(f"Crawled {len(stocks)} volatile stocks (>{threshold_pct}%)")
            return stocks

        except Exception as e:
            logger.error(f"Failed to crawl volatile stocks: {e}")
            return []
