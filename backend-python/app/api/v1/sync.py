import asyncio
from typing import List, Dict
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

# 并发控制：Tushare API有频率限制
BATCH_SIZE = 50  # 每批处理股票数
CONCURRENCY = 10  # 并发请求数


# ============================================================================
# 辅助函数
# ============================================================================

async def _enrich_leader_score_data(limit_up: List[Dict]) -> List[Dict]:
    """为龙头评分补充缺失的数据（成交额、换手率、市值）

    Args:
        limit_up: 涨停股票列表（来自爬虫）

    Returns:
        补充后的涨停列表
    """
    from app.services.tushare_service import TushareService

    if not limit_up:
        return limit_up

    try:
        service = TushareService()

        # 并发获取股票的日线数据以补充缺失信息
        async def fetch_stock_info(stock: Dict) -> Dict:
            code = stock.get("code", "")
            if not code:
                return stock

            try:
                # 尝试获取该股票的日线数据
                ts_code = f"{code}.SZ" if code.startswith(("000", "001", "002", "200", "201")) else f"{code}.SH"
                daily_data = await service.get_daily(ts_code, limit=1)

                if daily_data and len(daily_data) > 0:
                    day = daily_data[0]
                    # 补充缺失数据
                    stock["amount"] = float(day.get("vol", 0)) * float(day.get("close", 1)) / 100000000  # 成交额（亿元）
                    stock["turnover"] = float(day.get("turnover", 0))  # 换手率（%）
                    stock["market_cap"] = float(day.get("total_mv", 0)) / 100 if day.get("total_mv") else 100  # 市值（亿元）
                else:
                    # 无法获取，使用默认值
                    stock.setdefault("amount", 0)
                    stock.setdefault("turnover", 0)
                    stock.setdefault("market_cap", 100)
            except Exception as e:
                logger.debug(f"Failed to fetch info for {code}: {e}")
                # 使用默认值
                stock.setdefault("amount", 0)
                stock.setdefault("turnover", 0)
                stock.setdefault("market_cap", 100)

            return stock

        # 并发处理（限制并发数以避免API限流）
        tasks = [fetch_stock_info(stock) for stock in limit_up[:20]]  # 只补充前20个以节省时间
        enriched = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果，保留原始数据
        result = []
        for i, item in enumerate(enriched):
            if isinstance(item, dict):
                result.append(item)
            elif i < len(limit_up):
                # 发生异常，使用原始数据
                limit_up[i].setdefault("amount", 0)
                limit_up[i].setdefault("turnover", 0)
                limit_up[i].setdefault("market_cap", 100)
                result.append(limit_up[i])

        # 补充剩余的股票（不做数据补充）
        for i in range(20, len(limit_up)):
            limit_up[i].setdefault("amount", 0)
            limit_up[i].setdefault("turnover", 0)
            limit_up[i].setdefault("market_cap", 100)
            result.append(limit_up[i])

        logger.info(f"Enriched {len([s for s in result if s.get('amount', 0) > 0])} stocks with real data")
        return result

    except Exception as e:
        logger.warning(f"Data enrichment failed, using original data: {e}")
        # 给所有股票添加默认的缺失字段
        for stock in limit_up:
            stock.setdefault("amount", 0)
            stock.setdefault("turnover", 0)
            stock.setdefault("market_cap", 100)
        return limit_up


async def fetch_daily_batch(
    service: TushareService,
    stocks: List[Dict],
    semaphore: asyncio.Semaphore
) -> List[Dict]:
    """并发获取一批股票的日线数据"""
    async def fetch_one(stock: Dict) -> List[Dict]:
        async with semaphore:
            ts_code = stock.get("ts_code")
            try:
                data = await service.get_daily(ts_code, limit=1)
                return data if data else []
            except Exception as e:
                logger.warning(f"Fetch failed for {ts_code}: {e}")
                return []

    tasks = [fetch_one(s) for s in stocks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 展平结果，过滤异常
    all_quotes = []
    for r in results:
        if isinstance(r, list):
            all_quotes.extend(r)
    return all_quotes


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
    """同步日线行情 (并发优化版)

    使用asyncio.gather并发获取数据，控制并发数避免API限流
    """
    service = TushareService()

    # 获取股票列表
    stocks = await service.get_stock_list()
    if not stocks:
        return success({"synced": 0})

    synced_count = 0
    error_count = 0
    semaphore = asyncio.Semaphore(CONCURRENCY)

    # 分批处理
    for i in range(0, len(stocks), BATCH_SIZE):
        batch = stocks[i:i + BATCH_SIZE]

        # 并发获取这批股票的日线数据
        quotes = await fetch_daily_batch(service, batch, semaphore)

        # 批量写入数据库
        for quote in quotes:
            try:
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
                logger.error(f"DB write failed: {e}")
                error_count += 1

        # 每批提交一次
        await db.commit()
        logger.info(f"Batch {i // BATCH_SIZE + 1}: synced {len(quotes)} quotes")

    return success({
        "synced": synced_count,
        "errors": error_count,
        "total_stocks": len(stocks)
    })


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
    date: str = Query(None, description="交易日期YYYYMMDD"),
    source: str = Query("eastmoney", description="数据源: eastmoney|php")
):
    """爬取东方财富完整数据 (涵盖前端所有需要的模块)

    返回数据包含：
    - limit_up_down: 涨跌停数据
    - dragon_tiger: 龙虎榜
    - north_flow: 北向资金（含持仓TOP10）
    - sector_flow: 板块资金流向
    - emotion_cycle: 情绪周期
    - leader_stocks: 龙头股评分

    参数：
    - source: "php" 调用PHP后端 | "eastmoney" 直接爬取（推荐用PHP）
    """
    import httpx

    if not date:
        return error("缺少交易日期")

    # 优先尝试从PHP后端获取（更稳定）
    if source == "php":
        try:
            logger.info(f"Fetching eastmoney data from PHP backend for {date}")
            php_url = f"http://127.0.0.1:8000/api/crawlEastmoney?date={date}"
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(php_url)
                if resp.status_code == 200:
                    php_data = resp.json()
                    if isinstance(php_data, dict) and php_data.get("code") == 0:
                        logger.info(f"Successfully fetched eastmoney data from PHP backend")
                        return success(php_data.get("data", {}))
                    elif isinstance(php_data, dict) and not php_data.get("code"):
                        # PHP直接返回数据结构
                        return success(php_data)
        except Exception as e:
            logger.warning(f"Failed to fetch from PHP backend: {e}, falling back to direct crawl")

    # 降级到直接爬取
    from app.services.crawler.limit_up import LimitUpCrawler
    from app.services.crawler.dragon_tiger import DragonTigerCrawler
    from app.services.crawler.north_flow import NorthFlowCrawler
    from app.services.crawler.sector_flow import SectorFlowCrawler
    from app.services.crawler.emotion_cycle import EmotionCycleCalculator
    from app.services.crawler.leader_score import LeaderScoreCalculator
    from app.services.cache_service import CacheService

    eastmoney_result = {
        "date": date,
        "crawl_time": None,
        "limit_up_down": {
            "limit_up_count": 0,
            "limit_down_count": 0,
            "limit_up": [],
            "limit_down": [],
        },
        "dragon_tiger": [],
        "north_flow": {
            "hk_to_sh": 0,
            "hk_to_sz": 0,
            "total": 0,
            "top_holdings": [],
        },
        "sector_flow": [],
        "emotion_cycle": {},
        "leader_stocks": {
            "top_leader": None,
            "leaders": [],
        }
    }

    cache = CacheService()

    try:
        from datetime import datetime
        eastmoney_result["crawl_time"] = datetime.now().isoformat()

        # 1. 涨跌停数据
        try:
            limit_crawler = LimitUpCrawler()
            limit_up, limit_down = await limit_crawler.crawl_limit_up_down(date)
            eastmoney_result["limit_up_down"]["limit_up"] = limit_up
            eastmoney_result["limit_up_down"]["limit_down"] = limit_down
            eastmoney_result["limit_up_down"]["limit_up_count"] = len(limit_up)
            eastmoney_result["limit_up_down"]["limit_down_count"] = len(limit_down)

            # 缓存
            await cache.set(f"limit_up:{date}", limit_up, ttl=86400)
            await cache.set(f"limit_down:{date}", limit_down, ttl=86400)
            logger.info(f"Crawled {len(limit_up)} limit up, {len(limit_down)} limit down")
        except Exception as e:
            logger.error(f"Limit up/down crawl failed: {e}")

        # 2. 龙虎榜
        try:
            dragon_crawler = DragonTigerCrawler()
            dragon_tiger = await dragon_crawler.crawl_dragon_tiger(date)
            eastmoney_result["dragon_tiger"] = dragon_tiger
            await cache.set(f"dragon_tiger:{date}", dragon_tiger, ttl=86400)
            logger.info(f"Crawled {len(dragon_tiger)} dragon tiger records")
        except Exception as e:
            logger.error(f"Dragon tiger crawl failed: {e}")

        # 3. 北向资金
        try:
            north_crawler = NorthFlowCrawler()
            north_flow = await north_crawler.crawl_north_flow(date)
            eastmoney_result["north_flow"] = north_flow
            await cache.set(f"north_flow:{date}", north_flow, ttl=86400)
            logger.info(f"Crawled north flow: {north_flow.get('total', 0)}亿")
        except Exception as e:
            logger.error(f"North flow crawl failed: {e}")

        # 4. 板块资金
        try:
            sector_crawler = SectorFlowCrawler()
            sector_flow = await sector_crawler.crawl_sector_flow(date)
            eastmoney_result["sector_flow"] = sector_flow
            await cache.set(f"sector_flow:{date}", sector_flow, ttl=86400)
            logger.info(f"Crawled {len(sector_flow)} sector flow records")
        except Exception as e:
            logger.error(f"Sector flow crawl failed: {e}")

        # 5. 情绪周期计算
        try:
            limit_up = eastmoney_result["limit_up_down"]["limit_up"]
            limit_down = eastmoney_result["limit_up_down"]["limit_down"]

            if limit_up or limit_down:
                emotion_calc = EmotionCycleCalculator()
                emotion = emotion_calc.calculate(limit_up, limit_down)
                eastmoney_result["emotion_cycle"] = {
                    "phase": emotion.phase.value,
                    "score": emotion.score,
                    "limit_up_count": emotion.limit_up_count,
                    "limit_down_count": emotion.limit_down_count,
                    "max_continuous": emotion.max_continuous,
                    "strategy": emotion.strategy,
                    "phase_desc": _get_phase_desc(emotion.phase.value),
                    "indicators": [],
                    "continuous_stats": {},
                }
                await cache.set(f"emotion_cycle:{date}", eastmoney_result["emotion_cycle"], ttl=86400)
                logger.info(f"Emotion cycle: {emotion.phase.value} (score: {emotion.score})")
        except Exception as e:
            logger.error(f"Emotion cycle calc failed: {e}")

        # 6. 补充龙头评分的缺失数据（成交额、换手率、市值）
        try:
            limit_up = eastmoney_result["limit_up_down"]["limit_up"]
            if limit_up:
                # 为每个股票补充 amount、turnover、market_cap
                limit_up = await _enrich_leader_score_data(limit_up)
        except Exception as e:
            logger.warning(f"Failed to enrich leader score data: {e}")
            # 继续处理，使用原始数据

        # 7. 龙头评分
        try:
            limit_up = eastmoney_result["limit_up_down"]["limit_up"]
            if limit_up:
                from dataclasses import asdict
                leader_calc = LeaderScoreCalculator()
                leader_scores = leader_calc.batch_calculate(limit_up)
                leader_scores_dict = [asdict(ls) for ls in leader_scores]

                # 找出top leader
                if leader_scores_dict:
                    leader_scores_dict.sort(key=lambda x: x.get("score", 0), reverse=True)
                    top_leader = leader_scores_dict[0] if leader_scores_dict else None
                    eastmoney_result["leader_stocks"]["top_leader"] = top_leader
                    eastmoney_result["leader_stocks"]["leaders"] = leader_scores_dict[:20]

                await cache.set(f"leader_score:{date}", eastmoney_result["leader_stocks"], ttl=86400)
                logger.info(f"Calculated leader scores for {len(leader_scores_dict)} stocks")
        except Exception as e:
            logger.error(f"Leader score calc failed: {e}")

        # 缓存完整的东财数据
        await cache.set(f"eastmoney_data:{date}", eastmoney_result, ttl=86400)
        logger.info(f"Eastmoney crawl completed for {date}")

        return success(eastmoney_result)

    except Exception as e:
        logger.error(f"Failed to crawl eastmoney data: {e}")
        return error(f"爬虫执行失败: {str(e)}")


def _get_phase_desc(phase: str) -> str:
    """获取阶段描述"""
    phases = {
        "冰点期": "市场处于冰点，风险大，建议观望",
        "回暖期": "市场开始回暖，谨慎关注",
        "修复期": "市场修复，逐步建仓",
        "高潮期": "市场高潮，风险较大，适当减仓",
        "退潮期": "市场退潮，继续减仓",
    }
    return phases.get(phase, "未知阶段")
