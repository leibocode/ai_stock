from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from app.config import get_db
from app.schemas import success, error
from app.models import DailyQuote, Stock
from app.utils.cache_decorator import with_cache

router = APIRouter(prefix="", tags=["技术形态"])


def subtract_days(date_str: str, days: int) -> str:
    """从日期字符串减去天数"""
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    new_date = date_obj - timedelta(days=days)
    return new_date.strftime("%Y%m%d")


@router.get("/counter-trend")
async def get_counter_trend(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """逆势上涨股票 (大盘跌但个股涨)

    逆势股：大盘下跌时仍然上涨的股票
    通常代表强势个股或有主力资金介入
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询当日所有股票行情
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date == date)
            )
            result = await db.execute(stmt)
            rows = result.all()

            if not rows:
                return []

            # 计算市场平均涨跌幅
            all_pct_chg = [float(quote.pct_chg or 0) for quote, _ in rows]
            market_avg = sum(all_pct_chg) / len(all_pct_chg) if all_pct_chg else 0

            # 筛选逆势股：大盘跌（市场平均<0）但个股涨
            counter_trend_stocks = []
            for quote, stock in rows:
                pct_chg = float(quote.pct_chg or 0)
                # 市场下跌时，个股上涨
                if market_avg < 0 and pct_chg > 0:
                    counter_trend_stocks.append({
                        "ts_code": quote.ts_code,
                        "name": stock.name,
                        "industry": stock.industry or "未分类",
                        "close": float(quote.close or 0),
                        "pct_chg": pct_chg,
                        "vol": float(quote.vol or 0),
                        "amount": float(quote.amount or 0),
                    })

            # 按涨幅排序
            counter_trend_stocks.sort(key=lambda x: x['pct_chg'], reverse=True)

            return {
                "date": date,
                "market_avg": round(market_avg, 2),
                "counter_trend_stocks": counter_trend_stocks[:50]
            }

        data = await with_cache(f"counter_trend:{date}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get counter trend: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/breakout")
async def get_breakout(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    lookback: int = Query(20, description="回看天数"),
    db: AsyncSession = Depends(get_db)
):
    """突破形态 (突破20日高点)

    突破：今日最高价 > 过去N天最高价
    通常预示上升趋势开始
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询该日期和往前lookback天的数据
            start_date = subtract_days(date, lookback)
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(
                    DailyQuote.trade_date <= date,
                    DailyQuote.trade_date >= start_date
                )
                .order_by(DailyQuote.ts_code, desc(DailyQuote.trade_date))
            )
            result = await db.execute(stmt)
            rows = result.all()

            # 转为DataFrame进行分组计算
            data_list = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "trade_date": quote.trade_date,
                    "close": float(quote.close or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return {
                    "date": date,
                    "lookback_days": lookback,
                    "breakout_stocks": [],
                }

            df = pd.DataFrame(data_list)

            # 按股票分组，计算历史最高价
            breakout_stocks = []
            for ts_code, group in df.groupby('ts_code'):
                group = group.sort_values('trade_date', ascending=False)
                latest = group.iloc[0]
                history_high = group.iloc[1:]['high'].max() if len(group) > 1 else latest['high']

                # 突破判定：今日高点 > 历史高点
                if latest['high'] > history_high:
                    breakout_stocks.append({
                        "ts_code": ts_code,
                        "name": latest['name'],
                        "close": latest['close'],
                        "high": latest['high'],
                        "history_high": float(history_high),
                        "breakout_pct": round((latest['high'] - history_high) / history_high * 100, 2),
                        "pct_chg": latest['pct_chg'],
                    })

            # 按突破幅度排序
            breakout_stocks.sort(key=lambda x: x['breakout_pct'], reverse=True)

            return {
                "date": date,
                "lookback_days": lookback,
                "breakout_stocks": breakout_stocks[:50],
            }

        result_data = await with_cache(f"breakout:{date}:{lookback}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get breakout: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/top-volume")
async def get_top_volume(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """顶部放量 (价格>70%且放量)

    顶部放量：价格在高位，成交量明显增加
    通常预示上升趋势可能见顶
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

            data_list = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "close": float(quote.close or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "vol": float(quote.vol or 0),
                    "amount": float(quote.amount or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return []

            df = pd.DataFrame(data_list)

            # 计算价格位置 (0-100%)
            df['price_position'] = (
                (df['close'] - df['low']) /
                (df['high'] - df['low'] + 0.0001) * 100
            )

            # 过滤：价格位置 > 70% 且 成交额相对较高
            top_volume = df[df['price_position'] > 70].copy()
            top_volume = top_volume.sort_values('amount', ascending=False).head(50)

            return [
                {
                    "ts_code": row['ts_code'],
                    "name": row['name'],
                    "close": row['close'],
                    "price_position": round(row['price_position'], 1),
                    "amount": row['amount'],
                    "pct_chg": row['pct_chg'],
                }
                for _, row in top_volume.iterrows()
            ]

        data = await with_cache(f"top_volume:{date}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get top volume: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/gap-up")
async def get_gap_up(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """跳空高开 (今日开盘 > 昨日最高)

    跳空高开：个股出现向上跳空
    通常预示强势上升
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询当日和前一日的数据
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date <= date)
                .order_by(DailyQuote.ts_code, desc(DailyQuote.trade_date))
                .limit(1000)
            )
            result = await db.execute(stmt)
            rows = result.all()

            data_list = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "trade_date": quote.trade_date,
                    "open": float(quote.open or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "close": float(quote.close or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return {
                    "date": date,
                    "gap_up_list": [],
                }

            df = pd.DataFrame(data_list)

            # 使用 pandas 向量化识别跳空高开
            # 对每只股票，比较最新日期 vs 前一日期
            def identify_gap_up(group):
                group = group.sort_values('trade_date', ascending=False)
                if len(group) < 2:
                    return None

                today = group.iloc[0]
                yesterday = group.iloc[1]

                # 跳空高开判定
                if today['open'] <= yesterday['high']:
                    return None

                gap_size = today['open'] - yesterday['high']
                return {
                    "ts_code": today['ts_code'],
                    "name": today['name'],
                    "yesterday_high": float(yesterday['high']),
                    "today_open": float(today['open']),
                    "today_close": float(today['close']),
                    "gap_size": round(gap_size, 2),
                    "gap_pct": round(gap_size / yesterday['high'] * 100, 2),
                    "pct_chg": float(today['pct_chg']),
                }

            # 向量化处理：对每个股票组应用识别函数，过滤 None 值
            gap_up_stocks = [
                result for result in df.groupby('ts_code').apply(identify_gap_up).dropna()
            ]

            # 按跳空幅度排序（pandas 方式比手工 sort 更高效）
            if gap_up_stocks:
                gap_up_df = pd.DataFrame(gap_up_stocks)
                gap_up_df = gap_up_df.sort_values('gap_pct', ascending=False)
                gap_up_stocks = gap_up_df.to_dict('records')[:50]

            return {
                "date": date,
                "gap_up_list": gap_up_stocks[:50],
            }

        result_data = await with_cache(f"gap_up:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get gap up: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/gap-down")
async def get_gap_down(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """跳空低开 (今日开盘 < 昨日最低)

    跳空低开：个股出现向下跳空
    通常预示下跌压力
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询当日和前一日的数据
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date <= date)
                .order_by(DailyQuote.ts_code, desc(DailyQuote.trade_date))
                .limit(1000)
            )
            result = await db.execute(stmt)
            rows = result.all()

            data_list = [
                {
                    "ts_code": quote.ts_code,
                    "name": stock.name,
                    "trade_date": quote.trade_date,
                    "open": float(quote.open or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "close": float(quote.close or 0),
                    "pct_chg": float(quote.pct_chg or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return {
                    "date": date,
                    "gap_down_list": [],
                }

            df = pd.DataFrame(data_list)

            # 使用 pandas 向量化识别跳空低开
            def identify_gap_down(group):
                group = group.sort_values('trade_date', ascending=False)
                if len(group) < 2:
                    return None

                today = group.iloc[0]
                yesterday = group.iloc[1]

                # 跳空低开判定
                if today['open'] >= yesterday['low']:
                    return None

                gap_size = yesterday['low'] - today['open']
                return {
                    "ts_code": today['ts_code'],
                    "name": today['name'],
                    "yesterday_low": float(yesterday['low']),
                    "today_open": float(today['open']),
                    "today_close": float(today['close']),
                    "gap_size": round(gap_size, 2),
                    "gap_pct": round(gap_size / yesterday['low'] * 100, 2),
                    "pct_chg": float(today['pct_chg']),
                }

            # 向量化处理
            gap_down_stocks = [
                result for result in df.groupby('ts_code').apply(identify_gap_down).dropna()
            ]

            # 按跳空幅度排序
            if gap_down_stocks:
                gap_down_df = pd.DataFrame(gap_down_stocks)
                gap_down_df = gap_down_df.sort_values('gap_pct', ascending=False)
                gap_down_stocks = gap_down_df.to_dict('records')[:50]

            return {
                "date": date,
                "gap_down_list": gap_down_stocks[:50],
            }

        result_data = await with_cache(f"gap_down:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get gap down: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/industry-gap")
async def get_industry_gap(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """行业跳空 (行业平均跳空幅度)

    行业跳空：整个行业的平均跳空幅度
    用于识别行业性跳空机会
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 查询当日和前一日的数据
            stmt = (
                select(DailyQuote, Stock)
                .join(Stock, DailyQuote.ts_code == Stock.ts_code)
                .where(DailyQuote.trade_date <= date)
                .order_by(DailyQuote.ts_code, desc(DailyQuote.trade_date))
                .limit(2000)
            )
            result = await db.execute(stmt)
            rows = result.all()

            data_list = [
                {
                    "ts_code": quote.ts_code,
                    "industry": stock.industry or "未分类",
                    "trade_date": quote.trade_date,
                    "open": float(quote.open or 0),
                    "high": float(quote.high or 0),
                    "low": float(quote.low or 0),
                    "close": float(quote.close or 0),
                }
                for quote, stock in rows
            ]

            if not data_list:
                return []

            df = pd.DataFrame(data_list)

            # 识别行业跳空
            industry_gaps = []
            for (ts_code, industry), group in df.groupby(['ts_code', 'industry']):
                group = group.sort_values('trade_date', ascending=False)
                if len(group) < 2:
                    continue

                today = group.iloc[0]
                yesterday = group.iloc[1]

                # 计算跳空
                if today['open'] > yesterday['high']:
                    gap = 'up'
                    gap_pct = (today['open'] - yesterday['high']) / yesterday['high'] * 100
                elif today['open'] < yesterday['low']:
                    gap = 'down'
                    gap_pct = -(yesterday['low'] - today['open']) / yesterday['low'] * 100
                else:
                    continue

                industry_gaps.append({
                    "industry": industry,
                    "ts_code": ts_code,
                    "gap_type": gap,
                    "gap_pct": round(gap_pct, 2),
                })

            if not industry_gaps:
                return []

            gap_df = pd.DataFrame(industry_gaps)

            # 按行业统计平均跳空
            industry_stats = gap_df.groupby('industry').agg({
                'ts_code': 'count',
                'gap_pct': 'mean',
            }).rename(columns={'ts_code': 'stock_count'})

            industry_stats = industry_stats.sort_values('gap_pct', ascending=False).head(20)

            return [
                {
                    "industry": industry,
                    "stock_count": int(row['stock_count']),
                    "avg_gap_pct": round(row['gap_pct'], 2),
                }
                for industry, row in industry_stats.iterrows()
            ]

        data = await with_cache(f"industry_gap:{date}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get industry gap: {e}")
        return error(f"获取失败: {str(e)}")
