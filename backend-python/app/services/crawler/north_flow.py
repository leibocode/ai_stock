from typing import List, Dict
from .base import BaseCrawler
from loguru import logger


class NorthFlowCrawler(BaseCrawler):
    """北向资金爬虫"""

    async def crawl_north_flow(self, trade_date: str) -> Dict:
        """爬取北向资金数据（包括持仓TOP10）"""
        try:
            # 1. 获取实时北向资金
            url = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
            data = await self.get(url, retry=False)

            hk_to_sh = 0
            hk_to_sz = 0
            if data and data.get("data"):
                result = data.get("data", {})
                hk_to_sh = float(result.get("hgt", 0)) / 100000000  # 元转亿元
                hk_to_sz = float(result.get("sgt", 0)) / 100000000

            # 2. 获取北向持仓TOP（大基金持仓）
            top_holdings = await self._get_north_holdings()

            return {
                "hk_to_sh": round(hk_to_sh, 2),
                "hk_to_sz": round(hk_to_sz, 2),
                "total": round(hk_to_sh + hk_to_sz, 2),
                "top_holdings": top_holdings
            }
        except Exception as e:
            logger.error(f"Failed to crawl north flow: {e}")
            return {
                "hk_to_sh": 0,
                "hk_to_sz": 0,
                "total": 0,
                "top_holdings": []
            }

    async def _get_north_holdings(self) -> List[Dict]:
        """获取北向资金持仓TOP10

        使用东财push2实时API获取港股通持股排行
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "10",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:116",  # 港股通持股排行
                "fields": "f12,f14,f2,f3,f62",
                "pagesize": "10",
            }

            data = await self.get(url, params, retry=False)
            if data and data.get("data") and data["data"].get("diff"):
                holdings = []
                for item in data["data"]["diff"]:
                    if not item or not isinstance(item, dict):
                        continue
                    try:
                        holdings.append({
                            "code": item.get("f12", ""),
                            "name": item.get("f14", ""),
                            "price": float(item.get("f2", 0)),
                            "pct_chg": float(item.get("f3", 0)),
                            "net_flow": float(item.get("f62", 0)) / 100000000,  # 转亿
                        })
                    except (ValueError, TypeError):
                        continue

                if holdings:
                    logger.info(f"Crawled {len(holdings)} north holdings records")
                    return holdings[:10]

            logger.debug("No north holdings data from push2 API")
            return []

        except Exception as e:
            logger.error(f"Failed to get north holdings: {e}")
            return []
