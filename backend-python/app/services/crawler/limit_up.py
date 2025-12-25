from typing import List, Dict, Tuple
from .base import BaseCrawler
from loguru import logger


class LimitUpCrawler(BaseCrawler):
    """涨跌停数据爬虫"""

    async def crawl_limit_up_down(
        self,
        trade_date: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """爬取涨跌停数据 (从同花顺)

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            (涨停列表, 跌停列表)
        """
        limit_up_list = []
        limit_down_list = []

        # 同花顺涨停池 API (日期格式: YYYY-MM-DD)
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

        try:
            # 涨停
            url = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
            params = {"date": formatted_date}
            data = await self.get(url, params)

            if data and data.get("data"):
                limit_up_list = [
                    {
                        "code": item[0],
                        "name": item[1],
                        "price": float(item[2]),
                        "pct_chg": float(item[3]),
                        "first_time": item[4] if len(item) > 4 else "15:00",
                        "open_times": int(item[5]) if len(item) > 5 else 0,
                        "continuous": int(item[6]) if len(item) > 6 else 1,
                    }
                    for item in data.get("data", [])
                ]

            # 跌停
            url = "https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool"
            data = await self.get(url, params)

            if data and data.get("data"):
                limit_down_list = [
                    {
                        "code": item[0],
                        "name": item[1],
                        "price": float(item[2]),
                        "pct_chg": float(item[3]),
                    }
                    for item in data.get("data", [])
                ]

        except Exception as e:
            logger.error(f"Failed to crawl limit up/down: {e}")

        return limit_up_list, limit_down_list

    async def get_limit_up_continuous_stats(
        self,
        limit_up_list: List[Dict]
    ) -> Dict[int, int]:
        """统计连板分布

        Args:
            limit_up_list: 涨停列表

        Returns:
            {连板数: 股票数}
        """
        stats = {}
        for stock in limit_up_list:
            continuous = stock.get("continuous", 1)
            stats[continuous] = stats.get(continuous, 0) + 1
        return stats
