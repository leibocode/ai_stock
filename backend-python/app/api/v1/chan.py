from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import numpy as np
from app.config import get_db
from app.schemas import success, error
from app.models import Stock, DailyQuote
from app.utils.cache_decorator import with_cache
from app.core.chan import ChanService
from app.core.chan.divergence import (
    detect_buy_points_from_bis,
    detect_sell_points_from_bis,
    detect_bottom_divergence,
    detect_top_divergence,
)
from app.core.indicators.macd import calculate_macd_full
from app.core.chan import (
    merge_klines,
    calculate_fractals,
    calculate_bi,
    calculate_segment,
    calculate_hub_from_bis,
)

router = APIRouter(prefix="", tags=["缠论"])


# ============================================================================
# 辅助函数 - 缠论信号计算
# ============================================================================

async def calculate_stock_signals(ts_code: str, stock_name: str, db: AsyncSession) -> dict:
    """计算单只股票的缠论信号（背驰、买卖点）

    Args:
        ts_code: 股票代码
        stock_name: 股票名称
        db: 数据库连接

    Returns:
        dict: 包含 MACD、分型、笔、中枢、背驰、买卖点信息
    """
    try:
        # 获取历史K线数据（最近200条）
        stmt = (
            select(DailyQuote)
            .where(DailyQuote.ts_code == ts_code)
            .order_by(desc(DailyQuote.trade_date))
            .limit(200)
        )
        result = await db.execute(stmt)
        quotes = result.scalars().all()

        if len(quotes) < 50:
            return None

        # 转换为正序列表
        quotes = list(reversed(quotes))

        # 提取 OHLC 数据
        closes = np.array([float(q.close) for q in quotes])
        highs = np.array([float(q.high) for q in quotes])
        lows = np.array([float(q.low) for q in quotes])
        dates = [q.trade_date for q in quotes]

        # 计算 MACD
        macd_result = calculate_macd_full(closes)

        # 缠论分析
        klines = [
            {'high': float(highs[i]), 'low': float(lows[i]), 'close': float(closes[i])}
            for i in range(len(closes))
        ]
        merged_klines = merge_klines(klines)
        fractals = calculate_fractals(merged_klines)
        bis = calculate_bi(fractals)

        if len(bis) < 3:
            return None

        segments = calculate_segment(bis)
        hubs = calculate_hub_from_bis(bis)

        # 检测背驰信号
        bottom_div = detect_bottom_divergence(closes, lows, macd_result.macd_array, window=20)
        top_div = detect_top_divergence(closes, highs, macd_result.macd_array, window=20)

        # 检测买卖点
        buy_signals = detect_buy_points_from_bis(bis, closes, macd_result.macd_array, hubs)
        sell_signals = detect_sell_points_from_bis(bis, closes, macd_result.macd_array, hubs)

        return {
            'ts_code': ts_code,
            'name': stock_name,
            'last_date': dates[-1] if dates else None,
            'last_price': float(closes[-1]),
            'macd': {
                'dif': float(macd_result.dif),
                'dea': float(macd_result.dea),
                'hist': float(macd_result.macd),
            },
            'fractals_count': len(fractals),
            'bis_count': len(bis),
            'segments_count': len(segments),
            'hubs': hubs,  # 保留中枢对象列表
            'hubs_count': len(hubs),
            'bottom_divergence': bottom_div,
            'top_divergence': top_div,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
        }

    except Exception as e:
        logger.error(f"计算股票信号失败 {ts_code}: {e}")
        return None


@router.get("/chan-bottom-diverge")
async def get_chan_bottom_diverge(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """底背驰 (底部背驰信号)

    底背驰特征：
    - 价格创新低，但成交量或指标不创新低
    - 通常是强势反弹的信号
    - 结合缠论中枢识别，底背驰出现在中枢下方
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 获取该日期的所有股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .where(DailyQuote.trade_date == date)
                .distinct()
            )
            result = await db.execute(stmt)
            stocks = result.scalars().all()

            bottom_diverge_stocks = []

            for stock in stocks[:100]:  # 限制处理100只以避免超时
                signal_data = await calculate_stock_signals(stock.ts_code, stock.name, db)
                if signal_data and signal_data['bottom_divergence']:
                    bottom_diverge_stocks.append({
                        'ts_code': signal_data['ts_code'],
                        'name': signal_data['name'],
                        'price': signal_data['last_price'],
                        'divergence': signal_data['bottom_divergence'],
                    })

            return {
                "date": date,
                "bottom_diverge_stocks": bottom_diverge_stocks,
                "count": len(bottom_diverge_stocks),
            }

        result_data = await with_cache(f"chan_bottom_diverge:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get chan bottom diverge: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/chan-top-diverge")
async def get_chan_top_diverge(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """顶背驰 (顶部背驰信号)

    顶背驰特征：
    - 价格创新高，但成交量或指标不创新高
    - 通常是强势回调的信号
    - 可作为见顶或减仓的参考
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 获取该日期的所有股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .where(DailyQuote.trade_date == date)
                .distinct()
            )
            result = await db.execute(stmt)
            stocks = result.scalars().all()

            top_diverge_stocks = []

            for stock in stocks[:100]:  # 限制处理100只以避免超时
                signal_data = await calculate_stock_signals(stock.ts_code, stock.name, db)
                if signal_data and signal_data['top_divergence']:
                    top_diverge_stocks.append({
                        'ts_code': signal_data['ts_code'],
                        'name': signal_data['name'],
                        'price': signal_data['last_price'],
                        'divergence': signal_data['top_divergence'],
                    })

            return {
                "date": date,
                "top_diverge_stocks": top_diverge_stocks,
                "count": len(top_diverge_stocks),
            }

        result_data = await with_cache(f"chan_top_diverge:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get chan top diverge: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/chan-first-buy")
async def get_chan_first_buy(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """一买信号 (缠论第一类买点)

    一买出现在：
    - 向下笔完成后，开始向上走
    - 下跌段结束，反弹段开始
    - 回踩中枢后向上突破
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 获取该日期的所有股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .where(DailyQuote.trade_date == date)
                .distinct()
            )
            result = await db.execute(stmt)
            stocks = result.scalars().all()

            first_buy_stocks = []

            for stock in stocks[:100]:  # 限制处理100只以避免超时
                signal_data = await calculate_stock_signals(stock.ts_code, stock.name, db)
                if signal_data and signal_data['buy_signals'].get('first_buy'):
                    first_buy_stocks.append({
                        'ts_code': signal_data['ts_code'],
                        'name': signal_data['name'],
                        'price': signal_data['last_price'],
                        'signal': signal_data['buy_signals']['first_buy'],
                    })

            return {
                "date": date,
                "first_buy_stocks": first_buy_stocks,
                "count": len(first_buy_stocks),
            }

        result_data = await with_cache(f"chan_first_buy:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get chan first buy: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/chan-second-buy")
async def get_chan_second_buy(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """二买信号 (缠论第二类买点)

    二买出现在：
    - 一买之后，股价回踩
    - 回踩不破一买点，再次上涨
    - 强势股的加仓信号
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 获取该日期的所有股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .where(DailyQuote.trade_date == date)
                .distinct()
            )
            result = await db.execute(stmt)
            stocks = result.scalars().all()

            second_buy_stocks = []

            for stock in stocks[:100]:  # 限制处理100只以避免超时
                signal_data = await calculate_stock_signals(stock.ts_code, stock.name, db)
                if signal_data and signal_data['buy_signals'].get('second_buy'):
                    second_buy_stocks.append({
                        'ts_code': signal_data['ts_code'],
                        'name': signal_data['name'],
                        'price': signal_data['last_price'],
                        'signal': signal_data['buy_signals']['second_buy'],
                    })

            return {
                "date": date,
                "second_buy_stocks": second_buy_stocks,
                "count": len(second_buy_stocks),
            }

        result_data = await with_cache(f"chan_second_buy:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get chan second buy: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/chan-third-buy")
async def get_chan_third_buy(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """三买信号 (缠论第三类买点)

    三买出现在：
    - 二买回调破一买点
    - 再次在中枢内震荡后上破
    - 强势股确认趋势继续
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 获取该日期的所有股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .where(DailyQuote.trade_date == date)
                .distinct()
            )
            result = await db.execute(stmt)
            stocks = result.scalars().all()

            third_buy_stocks = []

            for stock in stocks[:100]:  # 限制处理100只以避免超时
                signal_data = await calculate_stock_signals(stock.ts_code, stock.name, db)
                if signal_data and signal_data['buy_signals'].get('third_buy'):
                    third_buy_stocks.append({
                        'ts_code': signal_data['ts_code'],
                        'name': signal_data['name'],
                        'price': signal_data['last_price'],
                        'signal': signal_data['buy_signals']['third_buy'],
                    })

            return {
                "date": date,
                "third_buy_stocks": third_buy_stocks,
                "count": len(third_buy_stocks),
            }

        result_data = await with_cache(f"chan_third_buy:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get chan third buy: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/chan-hub-shake")
async def get_chan_hub_shake(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """中枢震荡 (缠论中枢内部震荡)

    中枢震荡特征：
    - K线在中枢区间内反复震荡
    - 突破中枢需要明确的方向确认
    - 适合区间交易
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # 获取该日期的所有股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .where(DailyQuote.trade_date == date)
                .distinct()
            )
            result = await db.execute(stmt)
            stocks = result.scalars().all()

            hub_shake_stocks = []

            for stock in stocks[:100]:  # 限制处理100只以避免超时
                signal_data = await calculate_stock_signals(stock.ts_code, stock.name, db)
                if signal_data and signal_data['hubs_count'] > 0:
                    # 检查最新价格是否在最新中枢内
                    latest_hub = signal_data['hubs'][-1] if signal_data['hubs'] else None
                    if latest_hub:
                        # 如果有中枢信息，检查价格是否在中枢范围内
                        hub_shake_stocks.append({
                            'ts_code': signal_data['ts_code'],
                            'name': signal_data['name'],
                            'price': signal_data['last_price'],
                            'hubs_count': signal_data['hubs_count'],
                        })

            return {
                "date": date,
                "hub_shake_stocks": hub_shake_stocks,
                "count": len(hub_shake_stocks),
            }

        result_data = await with_cache(f"chan_hub_shake:{date}", fetch_data, ttl=86400)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get chan hub shake: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/chan-data")
async def get_chan_data(
    ts_code: str = Query(None, description="股票代码"),
    db: AsyncSession = Depends(get_db)
):
    """单只股票缠论数据 (完整的缠论分析)

    返回指定股票的缠论分析数据，包括：
    - 最新K线的缠论分型
    - 当前所在的笔和线段
    - 中枢识别结果
    - 当前买卖点信号
    """
    if not ts_code:
        return error("缺少股票代码")

    try:
        async def fetch_data():
            # 验证股票存在
            stmt = select(Stock).where(Stock.ts_code == ts_code)
            result = await db.execute(stmt)
            stock = result.scalar_one_or_none()

            if not stock:
                return None

            # 获取K线历史数据 (至少200条)
            stmt = (
                select(DailyQuote)
                .where(DailyQuote.ts_code == ts_code)
                .order_by(desc(DailyQuote.trade_date))
                .limit(200)
            )
            result = await db.execute(stmt)
            quotes = result.scalars().all()

            if len(quotes) < 100:
                return {
                    "ts_code": ts_code,
                    "name": stock.name,
                    "error": f"K线数据不足 ({len(quotes)}条)"
                }

            # 转换为正序列表
            klines = [
                {
                    "trade_date": q.trade_date,
                    "open": float(q.open or 0),
                    "high": float(q.high or 0),
                    "low": float(q.low or 0),
                    "close": float(q.close or 0),
                    "vol": float(q.vol or 0),
                }
                for q in reversed(quotes)
            ]

            # 计算缠论
            chan_service = ChanService()
            chan_result = chan_service.calculate(ts_code, klines)

            if not chan_result:
                return {
                    "ts_code": ts_code,
                    "name": stock.name,
                    "error": "缠论计算失败"
                }

            # 获取买卖点信号
            buy_signals = chan_service.get_buy_signals(chan_result)
            sell_signals = chan_service.get_sell_signals(chan_result)

            # 返回结果
            result_dict = chan_result.to_dict()
            result_dict["name"] = stock.name
            result_dict["buy_signals"] = buy_signals
            result_dict["sell_signals"] = sell_signals

            return result_dict

        chan_data = await with_cache(f"chan_data:{ts_code}", fetch_data, ttl=86400)

        if chan_data is None:
            return error(f"股票代码不存在: {ts_code}")

        return success(chan_data)

    except Exception as e:
        logger.error(f"Failed to get chan data: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/calc-chan")
async def calc_chan(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    limit: int = Query(100, description="处理股票数量"),
    db: AsyncSession = Depends(get_db)
):
    """计算缠论指标 (批量计算股票的缠论数据)

    该端点计算指定日期股票的缠论指标，包括：
    - 分型识别
    - 笔的划分
    - 线段的识别
    - 中枢的确认
    - 买卖点的判定
    """
    if not date:
        return error("缺少交易日期")

    try:
        # 获取有该日期行情的股票
        stmt = (
            select(Stock)
            .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
            .where(DailyQuote.trade_date == date)
            .limit(limit)
        )
        result = await db.execute(stmt)
        stocks = result.scalars().all()

        total_stocks = len(stocks)
        calculated = 0
        errors = 0
        chan_service = ChanService()

        for stock in stocks:
            try:
                # 获取K线历史
                stmt = (
                    select(DailyQuote)
                    .where(DailyQuote.ts_code == stock.ts_code)
                    .order_by(desc(DailyQuote.trade_date))
                    .limit(200)
                )
                result = await db.execute(stmt)
                quotes = result.scalars().all()

                if len(quotes) < 100:
                    continue

                klines = [
                    {
                        "trade_date": q.trade_date,
                        "open": float(q.open or 0),
                        "high": float(q.high or 0),
                        "low": float(q.low or 0),
                        "close": float(q.close or 0),
                    }
                    for q in reversed(quotes)
                ]

                # 计算缠论
                chan_result = chan_service.calculate(stock.ts_code, klines)
                if chan_result:
                    calculated += 1

            except Exception as e:
                logger.warning(f"Chan calc failed for {stock.ts_code}: {e}")
                errors += 1

        result_data = {
            "date": date,
            "total_stocks": total_stocks,
            "calculated": calculated,
            "errors": errors,
        }

        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to calc chan: {e}")
        return error(f"计算失败: {str(e)}")
