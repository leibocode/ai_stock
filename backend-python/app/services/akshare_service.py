#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据源 - 免费获取K线数据

支持：
- 日线数据（无限制）
- 完整的 OHLCV 数据
- 无API额度限制
"""

from typing import Optional, List, Dict
from datetime import datetime
from loguru import logger

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


class AKShareService:
    """AKShare 数据服务"""

    @staticmethod
    def is_available() -> bool:
        """检查AKShare是否可用"""
        return AKSHARE_AVAILABLE

    @staticmethod
    async def get_daily(
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500
    ) -> Optional[List[Dict]]:
        """获取日线数据

        Args:
            ts_code: 股票代码 (格式: "000001.SZ" / "000001.SH")
            start_date: 开始日期 (格式: "20250101")
            end_date: 结束日期 (格式: "20251225")
            limit: 获取数量限制

        Returns:
            K线数据列表或None

        数据格式:
        {
            "ts_code": "000001.SZ",
            "trade_date": "20250101",
            "open": 10.5,
            "high": 10.6,
            "low": 10.4,
            "close": 10.55,
            "vol": 1000000,
            "amount": 10550000.0,
            "pct_chg": 0.5
        }
        """
        if not AKSHARE_AVAILABLE:
            logger.warning("AKShare 未安装，请运行: pip install akshare")
            return None

        try:
            # 提取股票代码（去掉市场后缀）
            symbol = ts_code.split(".")[0] if "." in ts_code else ts_code

            logger.debug(f"[AKShare] 获取 {ts_code} ({symbol}) 的K线数据...")

            # 调用AKShare API
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date or "20200101",
                end_date=end_date or datetime.now().strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                logger.debug(f"[AKShare] {ts_code}: 无数据")
                return None

            # 转换为标准格式
            klines = []
            for idx, row in df.iterrows():
                try:
                    # AKShare 返回的列名：
                    # '日期', '开盘', '最高', '最低', '收盘', '成交量'
                    # 或
                    # 'date', 'open', 'high', 'low', 'close', 'volume'

                    # 获取日期
                    trade_date = None
                    if "日期" in row.index:
                        date_str = str(row["日期"])
                    elif "date" in row.index:
                        date_str = str(row["date"])
                    else:
                        continue

                    # 移除所有非数字字符（保留日期格式）
                    trade_date = "".join(
                        c for c in date_str if c.isdigit()
                    )

                    if len(trade_date) != 8:
                        continue

                    # 获取价格数据
                    def get_value(col_names):
                        for col_name in col_names:
                            if col_name in row.index:
                                try:
                                    return float(row[col_name])
                                except (ValueError, TypeError):
                                    continue
                        return 0.0

                    open_price = get_value(["开盘", "open"])
                    high_price = get_value(["最高", "high"])
                    low_price = get_value(["最低", "low"])
                    close_price = get_value(["收盘", "close"])
                    volume = get_value(["成交量", "volume"])

                    # 数据有效性检查
                    if high_price < low_price or high_price < close_price or low_price > close_price:
                        continue

                    kline = {
                        "ts_code": ts_code,
                        "trade_date": trade_date,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "vol": volume,
                        "amount": open_price * volume if volume > 0 else 0,
                        "pct_chg": 0.0  # AKShare 需要手动计算
                    }

                    klines.append(kline)

                except Exception as e:
                    logger.debug(f"[AKShare] 解析行 {idx} 失败: {e}")
                    continue

            if not klines:
                logger.debug(f"[AKShare] {ts_code}: 解析失败")
                return None

            # 限制数量
            klines = klines[:limit]

            logger.info(f"[AKShare] {ts_code}: 成功获取 {len(klines)} 条K线")
            return klines

        except Exception as e:
            logger.debug(f"[AKShare] {ts_code}: 获取失败 - {e}")
            return None

    @staticmethod
    async def test_connection() -> bool:
        """测试连接"""
        if not AKSHARE_AVAILABLE:
            logger.error("AKShare 未安装")
            return False

        try:
            logger.info("[AKShare] 测试连接...")

            df = ak.stock_zh_a_hist(
                symbol="000001",
                period="daily",
                start_date="20250101",
                end_date="20251225",
                adjust="qfq"
            )

            if df is not None and not df.empty:
                logger.info(f"[AKShare] 连接成功! 获取了 {len(df)} 条数据")
                return True
            else:
                logger.error("[AKShare] 无法获取数据")
                return False

        except Exception as e:
            logger.error(f"[AKShare] 连接失败: {e}")
            return False
