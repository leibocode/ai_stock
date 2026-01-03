from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class SectorFlowCrawler(BaseCrawler):
    """板块资金流向爬虫"""

    async def crawl_sector_flow(self, trade_date: str) -> List[Dict]:
        """爬取板块资金流向

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            板块资金流向列表
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
                "fs": "m:90+t:2",
                "fields": "f12,f14,f3,f62",
            }

            # 使用BaseCrawler的get方法，获得反爬虫机制
            data = await self.get(url, params, retry=False)

            if not data or not isinstance(data, dict):
                logger.warning(f"Sector flow API returned no data for {trade_date}")
                return []

            # 东财API返回格式: {"data": {"diff": [{f12:代码, f14:名称, f2:收盘, f3:涨跌幅, f62:主力净流}, ...]}}
            diff_list = data.get("data", {}).get("diff", [])
            if not diff_list:
                logger.debug(f"No sector data in API response for {trade_date}")
                return []

            sectors = []
            for item in diff_list:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    # f62是主力净流入（单位：元），转换为亿元
                    main_net_raw = item.get("f62", 0)
                    if main_net_raw is None:
                        main_net_raw = 0
                    main_net = round(float(main_net_raw) / 100000000, 2)

                    sector = {
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "pct_chg": round(float(item.get("f3", 0) or 0), 2),
                        "main_net": main_net,
                    }
                    sectors.append(sector)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse sector item {item}: {e}")
                    continue

            # 按主力净流入排序
            sectors.sort(key=lambda x: x.get("main_net", 0), reverse=True)
            logger.info(f"Crawled {len(sectors)} sector flow records for {trade_date}")
            return sectors

        except Exception as e:
            logger.error(f"Failed to crawl sector flow: {e}")
            return []

    async def calc_sector_strength(
        self,
        sectors: List[Dict],
        market_pct_chg: float
    ) -> Dict[str, List[Dict]]:
        """计算板块强度

        Args:
            sectors: 板块列表
            market_pct_chg: 市场涨跌幅

        Returns:
            {category: [sector...]}
        """
        result = {
            "counter_trend": [],     # 逆势上涨
            "resonance": [],         # 共振板块
            "weakness": [],          # 弱势板块
        }

        for sector in sectors:
            pct_chg = sector.get("pct_chg", 0)

            if pct_chg > market_pct_chg:
                result["counter_trend"].append(sector)
            elif pct_chg > 0 and market_pct_chg > 0:
                result["resonance"].append(sector)
            else:
                result["weakness"].append(sector)

        return result