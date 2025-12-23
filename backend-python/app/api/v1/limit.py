from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from loguru import logger
from app.config import get_db
from app.schemas import success, error
from app.models import DailyQuote, Stock
from app.services.cache_service import CacheService
from app.utils.cache_decorator import with_cache

router = APIRouter(prefix="", tags=["涨跌停"])


@router.get("/limit-up")
async def get_limit_up(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    limit: int = Query(100, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """涨停列表 (连续涨停追踪)

    涨停识别：当日涨幅 >= 9.9%
    用于追踪强势股票和龙头分析
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date == date)
                .where(DailyQuote.pct_chg >= 9.9)
                .order_by(desc(DailyQuote.pct_chg))
                .limit(limit)
            )
            result = await db.execute(stmt)
            rows = result.all()

            data = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "industry": stock.industry,
                    "close": float(quote.close or 0),
                    "open": float(quote.open or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                    "vol": float(quote.vol or 0),
                    "amount": float(quote.amount or 0),
                }
                for quote, stock in rows
            ]

            if data:
                df = pd.DataFrame(data)
                stats = {
                    "total_count": len(data),
                    "avg_amount": float(df['amount'].mean()),
                    "max_vol": float(df['vol'].max()),
                }
                return {
                    "date": date,
                    "limit_up_list": data,
                    "stats": stats,
                }
            else:
                return {
                    "date": date,
                    "limit_up_list": [],
                    "stats": {"total_count": 0},
                }

        result_data = await with_cache(f"limit_up:{date}:{limit}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get limit up stocks: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/limit-down")
async def get_limit_down(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    limit: int = Query(100, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """跌停列表 (风险预警)

    跌停识别：当日跌幅 <= -9.9%
    用于识别风险股票和底部机会
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date == date)
                .where(DailyQuote.pct_chg <= -9.9)
                .order_by(DailyQuote.pct_chg)
                .limit(limit)
            )
            result = await db.execute(stmt)
            rows = result.all()

            data = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "industry": stock.industry,
                    "close": float(quote.close or 0),
                    "open": float(quote.open or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                    "vol": float(quote.vol or 0),
                    "amount": float(quote.amount or 0),
                }
                for quote, stock in rows
            ]

            if data:
                df = pd.DataFrame(data)
                stats = {
                    "total_count": len(data),
                    "avg_amount": float(df['amount'].mean()),
                    "min_price": float(df['close'].min()),
                }
                return {
                    "date": date,
                    "limit_down_list": data,
                    "stats": stats,
                }
            else:
                return {
                    "date": date,
                    "limit_down_list": [],
                    "stats": {"total_count": 0},
                }

        result_data = await with_cache(f"limit_down:{date}:{limit}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get limit down stocks: {e}")
        return error(f"获取失败: {str(e)}")
