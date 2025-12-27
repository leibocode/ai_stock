from typing import List, Dict, Tuple, Optional
from .base import BaseCrawler
from loguru import logger
import asyncio


class LimitUpCrawler(BaseCrawler):
    """涨跌停数据爬虫"""

    async def crawl_limit_up_down(
        self,
        trade_date: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """爬取涨跌停数据

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            (涨停列表, 跌停列表)
        """
        # 方案1: 优先尝试同花顺API（更稳定）
        result = await self._crawl_from_ths(trade_date)
        if result[0] or result[1]:
            return result

        # 方案2: 降级到东财API
        logger.info(f"THS API failed, falling back to Eastmoney API for {trade_date}")
        return await self._crawl_from_eastmoney(trade_date)

    async def _crawl_from_ths(self, trade_date: str) -> Tuple[List[Dict], List[Dict]]:
        """从同花顺爬取涨跌停数据"""
        limit_up_list = []
        limit_down_list = []

        # 日期格式转换 YYYYMMDD -> YYYY-MM-DD
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

        try:
            # 涨停数据
            url = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
            params = {"date": formatted_date}
            data = await self.get(url, params, retry=False)

            if data and isinstance(data, dict) and data.get("data"):
                for item in data.get("data", []):
                    if not item:
                        continue
                    try:
                        limit_up_list.append({
                            "code": item[0] if len(item) > 0 else "",
                            "name": item[1] if len(item) > 1 else "",
                            "price": float(item[2]) if len(item) > 2 else 0,
                            "pct_chg": float(item[3]) if len(item) > 3 else 10.0,
                            "first_time": item[4] if len(item) > 4 else "15:00",
                            "open_times": int(item[5]) if len(item) > 5 else 0,
                            "continuous": int(item[6]) if len(item) > 6 else 1,
                            "reason": item[7] if len(item) > 7 else "涨幅偏离",
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse limit up item {item}: {e}")
                        continue

            # 跌停数据
            url = "https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool"
            data = await self.get(url, params, retry=False)

            if data and isinstance(data, dict) and data.get("data"):
                for item in data.get("data", []):
                    if not item:
                        continue
                    try:
                        limit_down_list.append({
                            "code": item[0] if len(item) > 0 else "",
                            "name": item[1] if len(item) > 1 else "",
                            "price": float(item[2]) if len(item) > 2 else 0,
                            "pct_chg": float(item[3]) if len(item) > 3 else -10.0,
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse limit down item {item}: {e}")
                        continue

        except Exception as e:
            logger.warning(f"THS API failed: {e}")

        return limit_up_list, limit_down_list

    async def _crawl_from_eastmoney(self, trade_date: str) -> Tuple[List[Dict], List[Dict]]:
        """从东财API爬取涨跌停数据（备选方案）"""
        limit_up_list = []
        limit_down_list = []

        try:
            # 东财实时行情接口
            url = "https://push2.eastmoney.com/api/qt/clist/get"

            # 获取A股全部数据，按涨幅排序
            params = {
                "pn": "1",
                "pz": "200",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # 沪深A股
                "fields": "f2,f3,f12,f14",
            }

            data = await self.get(url, params, retry=False)

            # 东财API返回格式: {"data": {"diff": [{f2:价格, f3:涨幅, f12:代码, f14:名称}, ...]}}
            if data and isinstance(data, dict):
                diff_list = data.get("data", {}).get("diff", [])

                for item in diff_list:
                    if not item or not isinstance(item, dict):
                        continue
                    try:
                        pct_chg = float(item.get("f3", 0)) if item.get("f3") else 0
                        price = float(item.get("f2", 0)) if item.get("f2") else 0
                        code = item.get("f12", "")
                        name = item.get("f14", "")

                        if pct_chg >= 9.9:  # 涨停线（考虑四舍五入）
                            limit_up_list.append({
                                "code": code,
                                "name": name,
                                "price": price,
                                "pct_chg": pct_chg,
                                "first_time": "15:00",
                                "open_times": 0,
                                "continuous": 1,
                                "reason": "涨幅偏离",
                            })
                        elif pct_chg <= -9.9:  # 跌停线
                            limit_down_list.append({
                                "code": code,
                                "name": name,
                                "price": price,
                                "pct_chg": pct_chg,
                            })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse eastmoney item {item}: {e}")
                        continue

            logger.info(f"Eastmoney crawled: {len(limit_up_list)} limit up, {len(limit_down_list)} limit down")

        except Exception as e:
            logger.warning(f"Eastmoney API failed: {e}")

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