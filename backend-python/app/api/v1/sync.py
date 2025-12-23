from fastapi import APIRouter, Depends, Query
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.config import get_db
from app.schemas import success, error
from app.models import DailyQuote
from app.services.tushare_service import TushareService
from app.services.indicator_service import IndicatorService
from app.utils.cache_decorator import with_cache

router = APIRouter(prefix="", tags=["数据同步"])


@router.get("/sync-stocks")
async def sync_stocks(db: AsyncSession = Depends(get_db)):
    """同步股票列表"""
    service = TushareService()
    count = await service.sync_stocks(db)
    return success({"synced": count})


@router.get("/sync-daily")
async def sync_daily(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """同步日线行情"""
    from datetime import datetime, timedelta
    from sqlalchemy import insert, update

    service = TushareService()

    # 获取股票列表
    stocks = await service.get_stock_list()
    if not stocks:
        return success({"synced": 0})

    synced_count = 0

    # 逐个同步日线数据
    for stock in stocks:
        try:
            ts_code = stock.get("ts_code")
            daily_data = await service.get_daily(ts_code, limit=1)

            if not daily_data:
                continue

            for quote in daily_data:
                stmt = (
                    insert(DailyQuote)
                    .values(
                        ts_code=quote.get("ts_code"),
                        trade_date=quote.get("trade_date"),
                        open=quote.get("open"),
                        high=quote.get("high"),
                        low=quote.get("low"),
                        close=quote.get("close"),
                        vol=quote.get("vol"),
                        amount=quote.get("amount"),
                        pct_chg=quote.get("pct_chg"),
                    )
                    .on_duplicate_key_update(
                        open=quote.get("open"),
                        high=quote.get("high"),
                        low=quote.get("low"),
                        close=quote.get("close"),
                        vol=quote.get("vol"),
                        amount=quote.get("amount"),
                        pct_chg=quote.get("pct_chg"),
                    )
                )
                await db.execute(stmt)
                synced_count += 1

        except Exception as e:
            logger.error(f"Failed to sync daily for {stock.get('ts_code')}: {e}")
            continue

    await db.commit()
    return success({"synced": synced_count})


@router.get("/calc-indicators")
async def calc_indicators(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    db: AsyncSession = Depends(get_db)
):
    """计算技术指标"""
    service = IndicatorService(db)
    count = await service.calc_all(date)
    return success({"calculated": count})


@router.get("/crawl-eastmoney")
async def crawl_eastmoney(
    date: str = Query(None, description="交易日期YYYYMMDD")
):
    """爬取东方财富数据 (龙虎榜、北向资金、板块资金、龙头评分、情绪周期等)

    该端点协调以下爬虫和计算模块：
    - 涨跌停池（同花顺）
    - 龙虎榜（东方财富）
    - 北向资金（东方财富）
    - 板块资金（东方财富）
    - 情绪周期计算（基于多因子）
    - 龙头评分（基于涨停和成交额）
    """
    if not date:
        return error("缺少交易日期")

    try:
        results = {
            "date": date,
            "crawled": [],
            "errors": [],
            "message": "各爬虫模块正在开发中，当前返回框架结构"
        }

        # 这些爬虫模块需要按顺序实现：
        # 1. LimitUpCrawler - 同花顺涨跌停池
        # 2. DragonTigerCrawler - 东财龙虎榜
        # 3. NorthFlowCrawler - 北向资金
        # 4. SectorFlowCrawler - 板块资金
        # 5. EmotionCycleCalculator - 情绪周期 (基于涨停、连板等)
        # 6. LeaderScoreCalculator - 龙头评分 (基于连板、成交额等)

        # TODO: 实现各爬虫模块，按以下步骤：
        # step1: LimitUpCrawler.crawl_limit_up_down(date)
        # step2: DragonTigerCrawler.crawl_dragon_tiger(date)
        # step3: NorthFlowCrawler.crawl_north_flow(date)
        # step4: SectorFlowCrawler.crawl_sector_flow(date)
        # step5: EmotionCycleCalculator.calculate(date)
        # step6: LeaderScoreCalculator.batch_calculate(date)

        return success(results)

    except Exception as e:
        logger.error(f"Failed to crawl eastmoney data: {e}")
        return error(f"爬虫执行失败: {str(e)}")
