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

        支持两个备选API：
        1. 东财datacenter API（优先）
        2. 东财实时API（备选）
        """
        try:
            # 方案1: 试试datacenter API
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                "reportName": "RPT_HK_IPOLDERS",
                "pageNumber": 1,
                "pageSize": 10,
                "sortTypes": "-1",
                "sortFields": "HOLD_MARKET_CAP",
            }

            data = await self.get(url, params, retry=False)
            if data and data.get("result") and data["result"].get("data"):
                holdings = []
                for item in data["result"]["data"]:
                    if not item:
                        continue
                    try:
                        holdings.append({
                            "code": item.get("SECUCODE", ""),
                            "name": item.get("SECURITY_NAME", ""),
                            "hold_market_cap": round(float(item.get("HOLD_MARKET_CAP", 0)), 2),
                            "hold_ratio": round(float(item.get("HOLD_RATIO", 0)), 2)
                        })
                    except (ValueError, TypeError):
                        continue

                if holdings:
                    return holdings[:10]

            # 方案2: 降级到push2 API（简化版）
            logger.debug("Datacenter API failed, trying push2 API")
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:116",  # 港股通持股排行
                "fields": "f12,f14,f2,f3,f62,f104,f105,f106,f107,f109,f110",
                "pagesize": "10",
                "pageindex": "1",
            }

            data = await self.get(url, params, retry=False)
            if data and data.get("data"):
                holdings = []
                for item in data.get("data", []):
                    if not item or len(item) < 11:
                        continue
                    try:
                        holdings.append({
                            "code": item[0] if len(item) > 0 else "",
                            "name": item[1] if len(item) > 1 else "",
                            "hold_market_cap": float(item[2]) if len(item) > 2 else 0,
                            "hold_ratio": float(item[3]) if len(item) > 3 else 0
                        })
                    except (ValueError, TypeError, IndexError):
                        continue

                return holdings[:10]

            return []
        except Exception as e:
            logger.error(f"Failed to get north holdings: {e}")
            return []
