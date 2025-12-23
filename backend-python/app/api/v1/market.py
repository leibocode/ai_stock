from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from loguru import logger
from app.config import get_db
from app.schemas import success, error
from app.models import DailyQuote, Stock, TechnicalIndicator
from app.services.cache_service import CacheService, CacheKeys
from app.utils.cache_decorator import with_cache

router = APIRouter(prefix="", tags=["行情数据"])


@router.get("/volume-top")
async def get_volume_top(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    limit: int = Query(50, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """成交量TOP50 (按成交额排序)

    用于识别主力资金关注的股票
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date == date)
                .order_by(desc(DailyQuote.amount))
                .limit(limit)
            )
            result = await db.execute(stmt)
            rows = result.all()

            return [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "industry": stock.industry,
                    "close": float(quote.close or 0),
                    "vol": float(quote.vol or 0),
                    "amount": float(quote.amount or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                }
                for quote, stock in rows
            ]

        data = await with_cache(f"volume_top:{date}:{limit}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get volume top: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/oversold")
async def get_oversold(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    rsi_threshold: int = Query(30, description="RSI阈值"),
    db: AsyncSession = Depends(get_db)
):
    """RSI超卖股票 (RSI_6 < 30)

    特点：RSI处于超卖区域，通常预示反弹机会
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            stmt = (
                select(TechnicalIndicator, Stock)
                .join(Stock, TechnicalIndicator.ts_code == Stock.ts_code)
                .where(TechnicalIndicator.trade_date == date)
                .where(TechnicalIndicator.rsi_6 < rsi_threshold)
                .order_by(TechnicalIndicator.rsi_6)
                .limit(50)
            )
            result = await db.execute(stmt)
            rows = result.all()

            return [
                {
                    "ts_code": indicator.ts_code,
                    "name": stock.name,
                    "industry": stock.industry,
                    "close": float(indicator.close or 0),
                    "rsi_6": float(indicator.rsi_6 or 0),
                    "rsi_12": float(indicator.rsi_12 or 0),
                    "pct_chg": float(indicator.pct_chg or 0),
                }
                for indicator, stock in rows
            ]

        data = await with_cache(f"oversold:{date}:{rsi_threshold}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get oversold stocks: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/kdj-bottom")
async def get_kdj_bottom(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    k_threshold: int = Query(20, description="K值阈值"),
    d_threshold: int = Query(20, description="D值阈值"),
    db: AsyncSession = Depends(get_db)
):
    """KDJ底部信号 (K<20 AND D<20)

    底部信号：KDJ处于底部，常见于反弹前期
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            stmt = (
                select(TechnicalIndicator, Stock)
                .join(Stock, TechnicalIndicator.ts_code == Stock.ts_code)
                .where(TechnicalIndicator.trade_date == date)
                .where(TechnicalIndicator.k < k_threshold)
                .where(TechnicalIndicator.d < d_threshold)
                .order_by(TechnicalIndicator.k)
                .limit(50)
            )
            result = await db.execute(stmt)
            rows = result.all()

            return [
                {
                    "ts_code": indicator.ts_code,
                    "name": stock.name,
                    "close": float(indicator.close or 0),
                    "k": float(indicator.k or 0),
                    "d": float(indicator.d or 0),
                    "j": float(indicator.j or 0),
                    "pct_chg": float(indicator.pct_chg or 0),
                }
                for indicator, stock in rows
            ]

        data = await with_cache(f"kdj_bottom:{date}:{k_threshold}:{d_threshold}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get kdj bottom stocks: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/macd-golden")
async def get_macd_golden(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """MACD金叉信号 (MACD柱 > 0)

    金叉信号：MACD处于上升期，常见于上升趋势初期
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            stmt = (
                select(TechnicalIndicator, Stock)
                .join(Stock, TechnicalIndicator.ts_code == Stock.ts_code)
                .where(TechnicalIndicator.trade_date == date)
                .where(TechnicalIndicator.macd_hist > 0)
                .order_by(desc(TechnicalIndicator.macd_hist))
                .limit(50)
            )
            result = await db.execute(stmt)
            rows = result.all()

            return [
                {
                    "ts_code": indicator.ts_code,
                    "name": stock.name,
                    "close": float(indicator.close or 0),
                    "macd": float(indicator.macd or 0),
                    "macd_signal": float(indicator.macd_signal or 0),
                    "macd_hist": float(indicator.macd_hist or 0),
                    "pct_chg": float(indicator.pct_chg or 0),
                }
                for indicator, stock in rows
            ]

        data = await with_cache(f"macd_golden:{date}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get macd golden stocks: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/bottom-volume")
async def get_bottom_volume(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """底部放量信号 (价格位置<30%)

    底部放量：价格处于低位且成交量增加，反弹信号明确
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询该日期的行情数据
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date == date)
                .limit(500)
            )
            result = await db.execute(stmt)
            rows = result.all()

            # 用pandas向量化计算价格位置
            data_list = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "close": float(quote.close or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "vol": float(quote.vol or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return []

            df = pd.DataFrame(data_list)

            # 计算价格位置 (close - low) / (high - low)
            df['price_position'] = (
                (df['close'] - df['low']) /
                (df['high'] - df['low'] + 0.0001) * 100
            )

            # 过滤：价格位置 < 30%
            bottom_volume = df[df['price_position'] < 30].copy()
            bottom_volume = bottom_volume.sort_values('vol', ascending=False).head(50)

            result_data = bottom_volume[[
                'ts_code', 'name', 'close', 'price_position', 'pct_chg'
            ]].to_dict('records')

            for item in result_data:
                item['price_position'] = round(item['price_position'], 1)

            return result_data

        data = await with_cache(f"bottom_volume:{date}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get bottom volume stocks: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/industry-hot")
async def get_industry_hot(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """行业热门股票 (该行业上涨个股最多)

    识别当日表现最强的行业及代表股票
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询该日期上涨股票
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date == date)
                .where(DailyQuote.pct_chg > 0)
            )
            result = await db.execute(stmt)
            rows = result.all()

            # pandas分组统计
            data_list = [
                {
                    "industry": stock.industry or "其他",
                    "symbol": quote.ts_code,
                    "name": stock.name,
                    "pct_chg": float(quote.pct_chg or 0),
                    "amount": float(quote.amount or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return []

            df = pd.DataFrame(data_list)

            # 按行业分组，统计上涨个股数和平均涨幅
            industry_stats = df.groupby('industry').agg({
                'symbol': 'count',
                'pct_chg': 'mean',
                'amount': 'sum'
            }).rename(columns={'symbol': 'count'})

            industry_stats = industry_stats.sort_values('pct_chg', ascending=False).head(20)

            return [
                {
                    "industry": industry,
                    "stock_count": int(row['count']),
                    "avg_increase": round(row['pct_chg'], 2),
                    "total_amount": float(row['amount']),
                }
                for industry, row in industry_stats.iterrows()
            ]

        data = await with_cache(f"industry_hot:{date}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get industry hot: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/market-index")
async def get_market_index(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """大盘指数 (沪深京指数)

    获取三大指数的行情数据
    """
    try:
        async def fetch_data():
            # 查询指数股票数据
            index_codes = ["000001.SH", "399001.SZ", "399006.SZ"]
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.ts_code.in_(index_codes))
            )
            if date:
                stmt = stmt.where(DailyQuote.trade_date == date)
            else:
                # 获取最新日期的数据
                stmt = stmt.order_by(desc(DailyQuote.trade_date)).limit(3)

            result = await db.execute(stmt)
            rows = result.all()

            return [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "close": float(quote.close or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                    "amount": float(quote.amount or 0),
                }
                for quote, stock in rows
            ]

        data = await with_cache(f"market_index:{date}", fetch_data, ttl=3600)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get market index: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/market-stats")
async def get_market_stats(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """市场统计数据 (涨停数、跌停数、平均涨幅)

    用于判断当日市场情绪和参与度
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 统计涨停、跌停、上涨、下跌
            limit_up = await db.execute(
                select(func.count(DailyQuote.ts_code)).where(
                    DailyQuote.trade_date == date,
                    DailyQuote.pct_chg >= 9.9
                )
            )
            limit_down = await db.execute(
                select(func.count(DailyQuote.ts_code)).where(
                    DailyQuote.trade_date == date,
                    DailyQuote.pct_chg <= -9.9
                )
            )
            increase = await db.execute(
                select(func.count(DailyQuote.ts_code)).where(
                    DailyQuote.trade_date == date,
                    DailyQuote.pct_chg > 0
                )
            )
            avg_chg = await db.execute(
                select(func.avg(DailyQuote.pct_chg)).where(
                    DailyQuote.trade_date == date
                )
            )

            return {
                "limitUp": int(limit_up.scalar() or 0),
                "limitDown": int(limit_down.scalar() or 0),
                "increase": int(increase.scalar() or 0),
                "avgChange": round(float(avg_chg.scalar() or 0), 2),
            }

        data = await with_cache(f"market_stats:{date}", fetch_data, ttl=3600)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get market stats: {e}")
        return error(f"获取失败: {str(e)}")
