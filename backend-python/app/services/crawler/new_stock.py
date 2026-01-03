# -*- coding: utf-8 -*-
"""新股申购爬虫

获取新股申购数据，包括申购代码、发行价、中签率等
"""
from typing import List, Dict, Optional
from .base import BaseCrawler
from loguru import logger


class NewStockCrawler(BaseCrawler):
    """新股申购爬虫"""

    async def crawl_new_stocks(self) -> List[Dict]:
        """爬取新股申购列表

        包括待申购、已申购、已上市的新股数据

        Returns:
            新股列表 [{code, name, issue_price, list_price, lot_size, ...}]
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
                "fs": "m:0+t:87",  # 新股申购
                "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f62",
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning("New stocks API returned invalid data")
                return []

            diff_list = data.get("data", {}).get("diff", [])
            if not diff_list:
                logger.debug("No new stocks found")
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
                        "volume": float(item.get("f4", 0)),
                        "amount": float(item.get("f5", 0)),
                        "high": float(item.get("f7", 0)),
                        "low": float(item.get("f8", 0)),
                    }
                    stocks.append(stock)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse new stock item {item}: {e}")
                    continue

            logger.info(f"Crawled {len(stocks)} new stocks")
            return stocks

        except Exception as e:
            logger.error(f"Failed to crawl new stocks: {e}")
            return []

    async def crawl_ipo_schedule(self) -> List[Dict]:
        """爬取IPO日程

        包括申购日期、发行价、发行量、中签率等

        Returns:
            IPO日程列表
        """
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_NEWSTOCKLIST",  # 新股上市日程
                "columns": "ALL",
                "pageNumber": 1,
                "pageSize": 50,
                "sortTypes": "-1",
                "sortColumns": "APPLY_DATE",
            }

            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning("IPO schedule API returned invalid data")
                return []

            result = data.get("result", {})
            if not result or not isinstance(result, dict):
                logger.debug("No result in IPO schedule API response")
                return []

            items = result.get("data", [])
            if not items:
                logger.debug("No IPO schedule found")
                return []

            ipos = []
            for item in items:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    ipo = {
                        "code": item.get("SECURITY_CODE", ""),
                        "name": item.get("SECURITY_NAME", ""),
                        "apply_date": item.get("APPLY_DATE", ""),
                        "apply_code": item.get("APPLY_CODE", ""),
                        "issue_price": float(item.get("ISSUE_PRICE", 0)),
                        "issue_volume": float(item.get("ISSUE_VOLUME", 0)),
                        "lot_size": int(item.get("LOT_SIZE", 0)),
                        "online_issue": float(item.get("ONLINE_ISSUE", 0)),
                        "online_apply_amount": float(item.get("ONLINE_APPLY_AMOUNT", 0)),
                        "win_rate": float(item.get("WIN_RATE", 0)),
                        "list_date": item.get("LIST_DATE", ""),
                    }
                    ipos.append(ipo)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse IPO item {item}: {e}")
                    continue

            logger.info(f"Crawled {len(ipos)} IPO schedules")
            return ipos

        except Exception as e:
            logger.error(f"Failed to crawl IPO schedule: {e}")
            return []

    async def get_hot_new_stocks(self, top_n: int = 20) -> List[Dict]:
        """获取热门新股

        按成交额排序

        Args:
            top_n: 返回前N条

        Returns:
            热门新股列表
        """
        stocks = await self.crawl_new_stocks()
        stocks.sort(key=lambda x: x.get("amount", 0), reverse=True)
        return stocks[:top_n]

    async def get_new_stocks_by_price_range(
        self,
        min_price: float = 0,
        max_price: float = 100
    ) -> List[Dict]:
        """按价格范围获取新股

        Args:
            min_price: 最低价格
            max_price: 最高价格

        Returns:
            符合条件的新股列表
        """
        stocks = await self.crawl_new_stocks()
        filtered = [
            s for s in stocks
            if min_price <= s.get("price", 0) <= max_price
        ]
        return filtered

    async def get_upcoming_ipos(self, days: int = 30) -> List[Dict]:
        """获取即将申购的新股

        Args:
            days: 未来天数

        Returns:
            即将申购的新股列表
        """
        ipos = await self.crawl_ipo_schedule()

        from datetime import datetime, timedelta
        today = datetime.now().date()
        future_date = today + timedelta(days=days)

        upcoming = []
        for ipo in ipos:
            try:
                apply_date_str = ipo.get("apply_date", "")
                if apply_date_str:
                    apply_date = datetime.strptime(apply_date_str, "%Y-%m-%d").date()
                    if today <= apply_date <= future_date:
                        upcoming.append(ipo)
            except ValueError:
                continue

        logger.info(f"Found {len(upcoming)} upcoming IPOs in {days} days")
        return upcoming
