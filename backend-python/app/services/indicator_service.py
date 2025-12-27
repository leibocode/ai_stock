import numpy as np
from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models import DailyQuote, TechnicalIndicator
from app.core.indicators import (
    calculate_rsi_multi,
    calculate_macd,
    calculate_kdj,
    calculate_boll,
)


class IndicatorService:
    """技术指标服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stock_history(
        self,
        ts_code: str,
        limit: int = 200
    ) -> List[dict]:
        """获取股票历史行情数据

        Args:
            ts_code: 股票代码
            limit: 获取数量

        Returns:
            历史行情列表
        """
        stmt = (
            select(DailyQuote)
            .where(DailyQuote.ts_code == ts_code)
            .order_by(DailyQuote.trade_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        quotes = result.scalars().all()

        # 反向排序 (时间从早到晚)
        return [
            {
                "ts_code": q.ts_code,
                "trade_date": q.trade_date,
                "open": q.open,
                "high": q.high,
                "low": q.low,
                "close": q.close,
                "vol": q.vol,
                "amount": q.amount,
                "pct_chg": q.pct_chg,
            }
            for q in reversed(quotes)
        ]

    async def calculate_indicators(
        self,
        ts_code: str,
        history: List[dict]
    ) -> dict:
        """计算股票的所有技术指标

        Args:
            ts_code: 股票代码
            history: 历史行情列表

        Returns:
            指标字典
        """
        if len(history) < 26:  # MACD需要26条数据
            return {}

        closes = np.array([q.get("close", 0) for q in history], dtype=float)
        highs = np.array([q.get("high", 0) for q in history], dtype=float)
        lows = np.array([q.get("low", 0) for q in history], dtype=float)

        # 计算各指标
        rsi = calculate_rsi_multi(closes, [6, 12])
        dif, dea, macd_hist = calculate_macd(closes)
        k, d, j = calculate_kdj(highs, lows, closes)
        upper, mid, lower = calculate_boll(closes)

        return {
            "ts_code": ts_code,
            "trade_date": history[-1].get("trade_date"),
            "rsi_6": rsi.get("rsi_6"),
            "rsi_12": rsi.get("rsi_12"),
            "macd": dif,
            "macd_signal": dea,
            "macd_hist": macd_hist,
            "k": k,
            "d": d,
            "j": j,
            "boll_upper": upper,
            "boll_mid": mid,
            "boll_lower": lower,
        }

    async def calc_all(
        self,
        trade_date: str,
        stocks: Optional[List[str]] = None
    ) -> int:
        """计算所有股票的指标

        Args:
            trade_date: 交易日期 (YYYYMMDD)
            stocks: 股票列表 (如果为None则计算所有)

        Returns:
            计算数量
        """
        from app.models import Stock

        # 获取股票列表
        if stocks:
            stmt = select(Stock).where(Stock.ts_code.in_(stocks))
        else:
            stmt = select(Stock)

        result = await self.session.execute(stmt)
        all_stocks = result.scalars().all()

        calculated_count = 0

        for stock in all_stocks:
            try:
                # 获取历史数据
                history = await self.get_stock_history(stock.ts_code, 200)
                if len(history) < 26:
                    continue

                # 计算指标
                indicators = await self.calculate_indicators(stock.ts_code, history)
                if not indicators:
                    continue

                # 保存到数据库
                stmt = (
                    select(TechnicalIndicator)
                    .where(TechnicalIndicator.ts_code == stock.ts_code)
                    .where(TechnicalIndicator.trade_date == trade_date)
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新
                    for key, value in indicators.items():
                        if key != "ts_code":
                            setattr(existing, key, value)
                else:
                    # 新增
                    new_indicator = TechnicalIndicator(**indicators)
                    self.session.add(new_indicator)

                calculated_count += 1

            except Exception as e:
                logger.error(f"Failed to calculate indicators for {stock.ts_code}: {e}")
                continue

        await self.session.commit()
        logger.info(f"Calculated indicators for {calculated_count} stocks")
        return calculated_count

    async def get_oversold_stocks(
        self,
        trade_date: str,
        rsi_threshold: int = 30
    ) -> List[dict]:
        """获取RSI超卖股票

        Args:
            trade_date: 交易日期
            rsi_threshold: RSI阈值

        Returns:
            超卖股票列表
        """
        from app.models import Stock

        stmt = (
            select(TechnicalIndicator, Stock)
            .join(Stock, TechnicalIndicator.ts_code == Stock.ts_code)
            .where(TechnicalIndicator.trade_date == trade_date)
            .where(TechnicalIndicator.rsi_6 < rsi_threshold)
            .order_by(TechnicalIndicator.rsi_6.asc())
            .limit(50)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "ts_code": indicator.ts_code,
                "name": stock.name,
                "rsi_6": indicator.rsi_6,
                "rsi_12": indicator.rsi_12,
            }
            for indicator, stock in rows
        ]

    async def get_kdj_bottom_stocks(
        self,
        trade_date: str,
        k_threshold: int = 20,
        d_threshold: int = 20
    ) -> List[dict]:
        """获取KDJ底部信号股票

        Args:
            trade_date: 交易日期
            k_threshold: K值阈值
            d_threshold: D值阈值

        Returns:
            底部信号列表
        """
        from app.models import Stock

        stmt = (
            select(TechnicalIndicator, Stock)
            .join(Stock, TechnicalIndicator.ts_code == Stock.ts_code)
            .where(TechnicalIndicator.trade_date == trade_date)
            .where(TechnicalIndicator.k < k_threshold)
            .where(TechnicalIndicator.d < d_threshold)
            .order_by(TechnicalIndicator.k.asc())
            .limit(50)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "ts_code": indicator.ts_code,
                "name": stock.name,
                "k": indicator.k,
                "d": indicator.d,
                "j": indicator.j,
            }
            for indicator, stock in rows
        ]

    async def get_macd_golden_stocks(
        self,
        trade_date: str
    ) -> List[dict]:
        """获取MACD金叉股票

        Args:
            trade_date: 交易日期

        Returns:
            MACD金叉列表
        """
        from app.models import Stock

        stmt = (
            select(TechnicalIndicator, Stock)
            .join(Stock, TechnicalIndicator.ts_code == Stock.ts_code)
            .where(TechnicalIndicator.trade_date == trade_date)
            .where(TechnicalIndicator.macd_hist > 0)
            .order_by(TechnicalIndicator.macd_hist.desc())
            .limit(50)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "ts_code": indicator.ts_code,
                "name": stock.name,
                "macd": indicator.macd,
                "macd_hist": indicator.macd_hist,
            }
            for indicator, stock in rows
        ]
