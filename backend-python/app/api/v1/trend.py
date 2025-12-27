"""趋势分析API

包括：
- 单只股票的多周期分析
- 全市场趋势扫描
- 拐点信号扫描
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import get_db
from app.schemas import success, error
from app.core.chan import ChanService
from app.core.chan.multi_period import MultiPeriodAnalyzer, format_multi_period_report
from app.services.trend_scanner import TrendScanner, format_scan_results
from app.services.crawler.minute_kline import fetch_multi_period_data
from app.models import Stock, DailyQuote
from sqlalchemy import select, desc


router = APIRouter(prefix="/trend", tags=["趋势分析"])


@router.get("/analyze")
async def analyze_stock(
    ts_code: str = Query(..., description="股票代码 000001.SZ"),
    db: AsyncSession = Depends(get_db)
):
    """单只股票的完整缠论分析

    返回：
    - 形态学信息（分型、笔、线段、中枢）
    - 动力学信息（背驰、分型强弱、走势）
    - 拐点信号（1/2/3买卖点）
    - 交易建议
    """
    try:
        # 验证股票存在
        stmt = select(Stock).where(Stock.ts_code == ts_code)
        result = await db.execute(stmt)
        stock = result.scalar_one_or_none()

        if not stock:
            return error(f"股票代码不存在: {ts_code}")

        # 获取K线数据
        stmt = (
            select(DailyQuote)
            .where(DailyQuote.ts_code == ts_code)
            .order_by(desc(DailyQuote.trade_date))
            .limit(200)
        )
        result = await db.execute(stmt)
        quotes = result.scalars().all()

        if len(quotes) < 100:
            return error(f"K线数据不足 ({len(quotes)}/100)")

        # 转换为K线格式
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
            return error("缠论计算失败")

        # 返回完整结果
        result_dict = chan_result.to_dict()
        result_dict["name"] = stock.name

        return success(result_dict)

    except Exception as e:
        logger.error(f"分析股票失败: {e}")
        return error(f"分析失败: {str(e)}")


@router.get("/multi-period")
async def analyze_multi_period(
    ts_code: str = Query(..., description="股票代码"),
    db: AsyncSession = Depends(get_db)
):
    """多周期联动分析（日线+30分钟+5分钟）

    返回：
    - 日线方向（方向层）
    - 30分钟结构（结构层）
    - 5分钟触发（执行层）
    - 综合信号（买入/卖出/观望）
    """
    try:
        # 验证股票
        stmt = select(Stock).where(Stock.ts_code == ts_code)
        result = await db.execute(stmt)
        stock = result.scalar_one_or_none()

        if not stock:
            return error(f"股票代码不存在: {ts_code}")

        # 获取日线数据
        stmt = (
            select(DailyQuote)
            .where(DailyQuote.ts_code == ts_code)
            .order_by(desc(DailyQuote.trade_date))
            .limit(200)
        )
        result = await db.execute(stmt)
        quotes = result.scalars().all()

        if len(quotes) < 100:
            return error(f"日线数据不足 ({len(quotes)}/100)")

        daily_klines = [
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

        # 获取分钟数据（从东财爬虫）
        minute_data = await fetch_multi_period_data(ts_code, ["30", "5"])

        if not minute_data or len(minute_data) < 2:
            return error("分钟数据不足，无法进行多周期分析")

        min30_klines = minute_data.get("30", [])
        min5_klines = minute_data.get("5", [])

        if len(min30_klines) < 100 or len(min5_klines) < 100:
            return error("分钟K线数据不足")

        # 执行多周期分析
        analyzer = MultiPeriodAnalyzer()
        signal = await analyzer.analyze(ts_code, daily_klines, min30_klines, min5_klines)

        if not signal:
            return error("多周期分析失败")

        # 生成报告
        report = format_multi_period_report(signal)

        return success({
            "ts_code": ts_code,
            "name": stock.name,
            "signal": signal.signal_type,
            "confidence": signal.confidence.value,
            "daily_trend": signal.daily_trend,
            "min30_structure": signal.min30_structure,
            "min5_trigger": signal.min5_trigger,
            "buy_price": signal.buy_price,
            "stop_loss": signal.stop_loss,
            "description": signal.description,
            "report": report
        })

    except Exception as e:
        logger.error(f"多周期分析失败: {e}")
        return error(f"分析失败: {str(e)}")


@router.get("/scan-market")
async def scan_market(
    limit: int = Query(100, description="扫描股票数量"),
    db: AsyncSession = Depends(get_db)
):
    """全市场趋势扫描

    返回：
    - 所有找到信号的股票
    - 按评分排序（高分在前）
    """
    try:
        scanner = TrendScanner(db)
        results = await scanner.scan_market(limit=limit)

        if not results:
            return success({
                "total": 0,
                "results": [],
                "report": "未找到符合条件的信号"
            })

        report = format_scan_results(results)

        return success({
            "total": len(results),
            "results": [
                {
                    "ts_code": r.ts_code,
                    "name": r.name,
                    "signal": r.signal_type,
                    "confidence": r.signal_confidence,
                    "trend": f"{r.trend_status}-{r.trend_phase}",
                    "risk": r.risk_level,
                    "price": r.current_price,
                    "score": f"{r.score:.0f}",
                    "suggestion": r.suggestion
                }
                for r in results[:50]  # 返回前50个
            ],
            "report": report
        })

    except Exception as e:
        logger.error(f"全市场扫描失败: {e}")
        return error(f"扫描失败: {str(e)}")


@router.get("/scan-buy-signals")
async def scan_buy_signals(
    limit: int = Query(100, description="扫描股票数量"),
    db: AsyncSession = Depends(get_db)
):
    """扫描买入信号

    返回：
    - 包含 1买、2买、3买 信号的股票
    """
    try:
        scanner = TrendScanner(db)
        results = await scanner.scan_buy_signals(limit=limit)

        if not results:
            return success({
                "total": 0,
                "results": [],
                "report": "未找到买入信号"
            })

        report = format_scan_results(results)

        return success({
            "total": len(results),
            "results": [
                {
                    "ts_code": r.ts_code,
                    "name": r.name,
                    "signal": r.signal_type,
                    "confidence": r.signal_confidence,
                    "trend": f"{r.trend_status}-{r.trend_phase}",
                    "risk": r.risk_level,
                    "price": r.current_price,
                    "score": f"{r.score:.0f}"
                }
                for r in results[:30]
            ],
            "report": report
        })

    except Exception as e:
        logger.error(f"买入信号扫描失败: {e}")
        return error(f"扫描失败: {str(e)}")


@router.get("/scan-sell-signals")
async def scan_sell_signals(
    limit: int = Query(100, description="扫描股票数量"),
    db: AsyncSession = Depends(get_db)
):
    """扫描卖出信号

    返回：
    - 包含 1卖、2卖、3卖 信号的股票
    """
    try:
        scanner = TrendScanner(db)
        results = await scanner.scan_sell_signals(limit=limit)

        if not results:
            return success({
                "total": 0,
                "results": [],
                "report": "未找到卖出信号"
            })

        report = format_scan_results(results)

        return success({
            "total": len(results),
            "results": [
                {
                    "ts_code": r.ts_code,
                    "name": r.name,
                    "signal": r.signal_type,
                    "confidence": r.signal_confidence,
                    "trend": f"{r.trend_status}-{r.trend_phase}",
                    "risk": r.risk_level,
                    "price": r.current_price,
                    "score": f"{r.score:.0f}"
                }
                for r in results[:30]
            ],
            "report": report
        })

    except Exception as e:
        logger.error(f"卖出信号扫描失败: {e}")
        return error(f"扫描失败: {str(e)}")
