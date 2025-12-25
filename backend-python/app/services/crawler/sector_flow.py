from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class SectorFlowCrawler(BaseCrawler):
    """板块资金流向爬虫"""

    async def crawl_sector_flow(
        self,
        trade_date: str
    ) -> List[Dict]:
        """爬取板块资金流向

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            板块资金流向列表
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90+t:2",
                "fields": "f12,f14,f2,f3,f62,f104,f105,f106,f107,f109,f110",
                "pagesize": "500",
                "pageindex": "1",
            }

            data = await self.get(url, params)
            if not data or not data.get("data"):
                return []

            sectors = []
            for item in data.get("data", []):
                if len(item) < 11:
                    continue

                sector = {
                    "code": item[0],
                    "name": item[1],
                    "close": float(item[2]) / 100,
                    "pct_chg": float(item[3]) / 100,
                    "main_net": float(item[4]) if item[4] else 0,  # 主力净流
                    "up_count": int(item[5]),
                    "down_count": int(item[6]),
                    "flat_count": int(item[7]),
                }
                sectors.append(sector)

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
            sector_chg = sector.get("pct_chg", 0)

            # 逆势上涨
            if market_pct_chg < 0 and sector_chg > 0:
                result["counter_trend"].append(sector)
            # 共振板块
            elif market_pct_chg >= 0 and sector_chg > market_pct_chg + 0.5:
                result["resonance"].append(sector)
            elif market_pct_chg < 0 and sector_chg < market_pct_chg - 0.5:
                result["resonance"].append(sector)
            else:
                result["weakness"].append(sector)

        return result
