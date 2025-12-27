"""东方财富分钟K线爬虫

获取5分钟、15分钟、30分钟、60分钟K线数据
"""
from typing import List, Dict, Optional
import aiohttp
from loguru import logger
from .base import BaseCrawler


class MinuteKlineCrawler(BaseCrawler):
    """东财分钟K线爬虫"""

    # 东财接口配置
    BASE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"

    # K线周期映射
    PERIODS = {
        "5": 5,      # 5分钟
        "15": 15,    # 15分钟
        "30": 30,    # 30分钟
        "60": 60,    # 60分钟（1小时）
        "101": 101,  # 日线
        "102": 102,  # 周线
        "103": 103,  # 月线
    }

    async def get_minute_klines(
        self,
        ts_code: str,
        period: str = "30",
        count: int = 500
    ) -> Optional[List[Dict]]:
        """获取分钟K线数据

        Args:
            ts_code: 股票代码 (格式: "000001.SZ" / "000001.SH")
            period: K线周期 ("5"/"15"/"30"/"60")
            count: 获取数量 (默认500)

        Returns:
            K线数据列表或None
        """
        try:
            # 转换为东财secid格式
            # A股: 0 前缀为深圳，1 前缀为上海
            secid = self._convert_secid(ts_code)
            if not secid:
                logger.error(f"Invalid ts_code: {ts_code}")
                return None

            # 构建请求参数
            params = {
                "secid": secid,
                "ut": "fa5fd1943c7b386f172d6893dbfba059",  # 固定token
                "fields1": "f1,f2,f3,f4,f5",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": self.PERIODS.get(period, 30),  # K线类型
                "fqt": 0,  # 0:不复权, 1:前复权, 2:后复权
                "end": -1,  # -1 表示最后一条
                "lmt": count,
                "v": 7.0,
            }

            # 发起请求
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers=self.get_headers()
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"{ts_code}: HTTP {resp.status}")
                        return None

                    # 处理文本响应，而不是直接解析JSON
                    content = await resp.text()

                    # 尝试解析JSON
                    try:
                        import json
                        data = json.loads(content)
                    except:
                        # 如果是文本响应，尝试手动解析
                        logger.debug(f"{ts_code}: 响应为文本格式，尝试手动解析")
                        data = None

            # 解析响应
            if data is None:
                logger.warning(f"{ts_code}: 无法解析响应数据")
                return None

            klines = self._parse_klines(data, ts_code)
            if not klines:
                logger.warning(f"{ts_code}: 无法解析K线数据")
                return None

            logger.info(f"{ts_code}: 获取 {len(klines)} 条{period}分钟K线")
            return klines

        except Exception as e:
            logger.error(f"{ts_code}: 获取K线失败 - {e}")
            return None

    @staticmethod
    def _convert_secid(ts_code: str) -> Optional[str]:
        """转换为东财secid格式

        Args:
            ts_code: Tushare格式代码 (000001.SZ / 000001.SH)

        Returns:
            东财格式 (0000001 / 1000001)
        """
        try:
            if not ts_code:
                return None

            if "." in ts_code:
                code, market = ts_code.split(".")
            else:
                # 如果没有市场标识，根据开头判断
                code = ts_code
                if code.startswith("6"):
                    market = "SH"  # 60xxxx 是上海
                else:
                    market = "SZ"  # 其他是深圳

            if market == "SZ" or market == "sz":
                # 深圳：0 前缀
                return f"0{code}"
            elif market == "SH" or market == "sh":
                # 上海：1 前缀
                return f"1{code}"
            else:
                return None
        except Exception as e:
            logger.error(f"转换secid失败: {ts_code} - {e}")
            return None

    @staticmethod
    def _parse_klines(data: Dict, ts_code: str) -> Optional[List[Dict]]:
        """解析东财K线数据

        响应格式:
        {
            "data": {
                "code": "000001",
                "name": "平安银行",
                "klines": [
                    "2024-12-25 14:30,10.5,10.4,10.45,10.46,1000000"
                ]
            }
        }

        K线格式: 时间,开,低,高,收,成交量
        """
        try:
            if not data or "data" not in data:
                return None

            data_obj = data.get("data", {})
            klines_raw = data_obj.get("klines", [])

            if not klines_raw:
                return None

            klines = []
            for line in klines_raw:
                parts = line.split(",")
                if len(parts) < 6:
                    continue

                # 日期/时间
                trade_date = parts[0].replace("-", "").replace(" ", "").replace(":", "")

                try:
                    # 开高低收成交量
                    open_price = float(parts[1])
                    low_price = float(parts[2])
                    high_price = float(parts[3])
                    close_price = float(parts[4])
                    vol = float(parts[5])

                    # 验证数据有效性
                    if high_price < low_price or high_price < close_price or low_price > close_price:
                        continue

                    klines.append({
                        "ts_code": ts_code,
                        "trade_date": trade_date,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "vol": vol,
                    })
                except (ValueError, IndexError):
                    continue

            # 按时间排序（正序）
            klines.sort(key=lambda x: x["trade_date"])

            return klines

        except Exception as e:
            logger.error(f"{ts_code}: 解析K线失败 - {e}")
            return None

    async def get_multi_period_klines(
        self,
        ts_code: str,
        periods: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """获取多周期K线数据

        Args:
            ts_code: 股票代码
            periods: 周期列表 (默认 ["5", "30"])

        Returns:
            {period: klines} 字典
        """
        if periods is None:
            periods = ["5", "30"]

        result = {}
        for period in periods:
            klines = await self.get_minute_klines(ts_code, period)
            if klines:
                result[period] = klines

        return result

    @staticmethod
    def get_headers() -> Dict[str, str]:
        """获取请求头"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json",
        }


async def fetch_minute_data(
    ts_code: str,
    period: str = "30",
    count: int = 500
) -> Optional[List[Dict]]:
    """快速获取分钟K线数据的便捷函数

    Args:
        ts_code: 股票代码
        period: K线周期
        count: 获取数量

    Returns:
        K线列表
    """
    crawler = MinuteKlineCrawler()
    return await crawler.get_minute_klines(ts_code, period, count)


async def fetch_multi_period_data(
    ts_code: str,
    periods: List[str] = None
) -> Dict[str, List[Dict]]:
    """快速获取多周期K线数据的便捷函数

    Args:
        ts_code: 股票代码
        periods: 周期列表

    Returns:
        多周期K线数据
    """
    crawler = MinuteKlineCrawler()
    return await crawler.get_multi_period_klines(ts_code, periods)
