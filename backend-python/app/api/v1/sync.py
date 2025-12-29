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
from app.services.cache_service import CacheService

router = APIRouter(prefix="", tags=["数据同步"])

# 缓存服务实例
cache = CacheService()

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


async def _crawl_strength_data() -> Dict:
    """爬取弱转强、强转弱、分时强度和市场情绪数据

    从东财实时行情API获取：
    - 弱转强：低开高走（开盘价<昨收，收盘价>昨收）
    - 强转弱：高开低走（开盘价>昨收，收盘价<昨收）
    - 分时强度：个股涨幅相对大盘的强度
    - 市场情绪：涨跌比

    Returns:
        包含 strength_change, relative_strength, market_emotion 的字典
    """
    import httpx

    result = {
        "strength_change": {
            "weak_to_strong": [],
            "strong_to_weak": [],
            "weak_to_strong_count": 0,
            "strong_to_weak_count": 0,
        },
        "relative_strength": {
            "market_chg": 0,
            "stocks": [],
        },
        "market_emotion": {
            "up_count": 0,
            "down_count": 0,
            "flat_count": 0,
            "up_ratio": 0,
            "emotion_level": "中性",
        },
        "market_chg": 0,
    }

    weak_to_strong = []
    strong_to_weak = []
    relative_stocks = []
    up_count = 0
    down_count = 0
    flat_count = 0
    market_chg = 0

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 获取A股实时行情（主板+创业板）
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "500",  # 获取500只股票
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",  # 按涨幅排序
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # 沪深主板+创业板
                "fields": "f2,f3,f12,f14,f15,f16,f17,f18",  # 收盘/涨幅/代码/名称/最高/最低/开盘/昨收
            }

            resp = await client.get(url, params=params)
            data = resp.json()

            if not data or data.get("data") is None:
                logger.warning("Empty response from eastmoney quote API")
                return result

            diff_list = data.get("data", {}).get("diff", [])
            if not diff_list:
                return result

            # 获取大盘涨幅（上证指数）
            try:
                index_url = "https://push2.eastmoney.com/api/qt/stock/get"
                index_params = {
                    "secid": "1.000001",  # 上证指数
                    "fields": "f43,f170",  # 收盘价，涨幅
                }
                index_resp = await client.get(index_url, params=index_params)
                index_data = index_resp.json()
                if index_data and index_data.get("data"):
                    market_chg = float(index_data["data"].get("f170", 0)) / 100 if index_data["data"].get("f170") else 0
            except Exception as e:
                logger.warning(f"Failed to get market index: {e}")

            # 分析每只股票
            for item in diff_list:
                if not item or not isinstance(item, dict):
                    continue

                try:
                    code = item.get("f12", "")
                    name = item.get("f14", "")
                    close = float(item.get("f2", 0)) if item.get("f2") and item.get("f2") != "-" else 0
                    pct_chg = float(item.get("f3", 0)) if item.get("f3") and item.get("f3") != "-" else 0
                    high = float(item.get("f15", 0)) if item.get("f15") and item.get("f15") != "-" else 0
                    low = float(item.get("f16", 0)) if item.get("f16") and item.get("f16") != "-" else 0
                    open_price = float(item.get("f17", 0)) if item.get("f17") and item.get("f17") != "-" else 0
                    pre_close = float(item.get("f18", 0)) if item.get("f18") and item.get("f18") != "-" else 0

                    if not code or not pre_close or pre_close == 0:
                        continue

                    # 统计涨跌
                    if pct_chg > 0:
                        up_count += 1
                    elif pct_chg < 0:
                        down_count += 1
                    else:
                        flat_count += 1

                    # 弱转强：低开高走（开盘<昨收，收盘>昨收）
                    open_chg = round((open_price - pre_close) / pre_close * 100, 2) if pre_close else 0
                    close_chg = round((close - pre_close) / pre_close * 100, 2) if pre_close else 0

                    if open_price < pre_close and close > pre_close:
                        weak_to_strong.append({
                            "code": code,
                            "name": name,
                            "open_chg": open_chg,
                            "close_chg": close_chg,
                            "pct_chg": round(pct_chg, 2),
                        })

                    # 强转弱：高开低走（开盘>昨收，收盘<昨收）
                    if open_price > pre_close and close < pre_close:
                        # 计算最高涨幅
                        high_chg = round((high - pre_close) / pre_close * 100, 2) if pre_close else 0
                        strong_to_weak.append({
                            "code": code,
                            "name": name,
                            "high_chg": high_chg,
                            "close_chg": close_chg,
                            "pct_chg": round(pct_chg, 2),
                        })

                    # 分时强度：个股涨幅相对大盘（只取正向的）
                    relative = round(pct_chg - market_chg, 2)
                    if pct_chg > 0 and relative > 0:
                        relative_stocks.append({
                            "code": code,
                            "name": name,
                            "pct_chg": round(pct_chg, 2),
                            "relative": relative,
                        })

                except (ValueError, TypeError) as e:
                    continue

        # 排序
        weak_to_strong.sort(key=lambda x: x["pct_chg"], reverse=True)
        strong_to_weak.sort(key=lambda x: x["close_chg"])  # 按收盘跌幅排序
        relative_stocks.sort(key=lambda x: x["relative"], reverse=True)

        # 更新结果
        result["market_chg"] = round(market_chg, 2)
        result["relative_strength"]["market_chg"] = round(market_chg, 2)
        result["strength_change"]["weak_to_strong"] = weak_to_strong[:30]
        result["strength_change"]["strong_to_weak"] = strong_to_weak[:30]
        result["strength_change"]["weak_to_strong_count"] = len(weak_to_strong)
        result["strength_change"]["strong_to_weak_count"] = len(strong_to_weak)

        result["relative_strength"]["stocks"] = relative_stocks[:50]

        # 市场情绪
        total = up_count + down_count + flat_count
        up_ratio = round(up_count / total * 100, 1) if total else 0
        result["market_emotion"]["up_count"] = up_count
        result["market_emotion"]["down_count"] = down_count
        result["market_emotion"]["flat_count"] = flat_count
        result["market_emotion"]["up_ratio"] = up_ratio

        # 情绪级别判断
        if up_ratio >= 70:
            result["market_emotion"]["emotion_level"] = "贪婪"
        elif up_ratio >= 55:
            result["market_emotion"]["emotion_level"] = "乐观"
        elif up_ratio >= 45:
            result["market_emotion"]["emotion_level"] = "中性"
        elif up_ratio >= 30:
            result["market_emotion"]["emotion_level"] = "悲观"
        else:
            result["market_emotion"]["emotion_level"] = "恐惧"

        logger.info(f"Strength data: {len(weak_to_strong)} weak_to_strong, {len(strong_to_weak)} strong_to_weak, {len(relative_stocks)} relative, market={market_chg}%")

    except Exception as e:
        logger.error(f"Failed to crawl strength data: {e}")

    return result


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
    """爬取东方财富完整数据 (并发优化版 - 5秒内完成)

    返回数据包含：
    - limit_up_down: 涨跌停数据
    - dragon_tiger: 龙虎榜
    - north_flow: 北向资金
    - sector_flow: 板块资金流向
    - emotion_cycle: 情绪周期
    - leader_stocks: 龙头股评分
    - strength_change: 弱转强/强转弱
    - relative_strength: 分时强度
    - market_emotion: 市场情绪
    """
    if not date:
        return error("缺少交易日期")

    from datetime import datetime
    from app.services.crawler.limit_up import LimitUpCrawler
    from app.services.crawler.dragon_tiger import DragonTigerCrawler
    from app.services.crawler.north_flow import NorthFlowCrawler
    from app.services.crawler.sector_flow import SectorFlowCrawler
    from app.services.crawler.emotion_cycle import EmotionCycleCalculator
    from app.services.crawler.leader_score import LeaderScoreCalculator

    eastmoney_result = {
        "date": date,
        "crawl_time": datetime.now().isoformat(),
        "limit_up_down": {"limit_up_count": 0, "limit_down_count": 0, "limit_up": [], "limit_down": []},
        "dragon_tiger": [],
        "north_flow": {"hk_to_sh": 0, "hk_to_sz": 0, "total": 0, "top_holdings": []},
        "sector_flow": [],
        "sector_strength": {"market_chg": 0},
        "emotion_cycle": {},
        "leader_stocks": {"top_leader": None, "leaders": []},
        "strength_change": {"weak_to_strong": [], "strong_to_weak": [], "weak_to_strong_count": 0, "strong_to_weak_count": 0},
        "relative_strength": {"market_chg": 0, "stocks": []},
        "market_emotion": {"up_count": 0, "down_count": 0, "flat_count": 0, "up_ratio": 0, "emotion_level": "中性"},
    }

    try:
        # ========== 并发爬取所有数据 (5秒内完成) ==========
        async def crawl_limit_up_down():
            try:
                crawler = LimitUpCrawler()
                return await crawler.crawl_limit_up_down(date)
            except Exception as e:
                logger.error(f"Limit crawl failed: {e}")
                return [], []

        async def crawl_dragon_tiger():
            try:
                crawler = DragonTigerCrawler()
                return await crawler.crawl_dragon_tiger(date)
            except Exception as e:
                logger.error(f"Dragon tiger crawl failed: {e}")
                return []

        async def crawl_north_flow():
            try:
                crawler = NorthFlowCrawler()
                return await crawler.crawl_north_flow(date)
            except Exception as e:
                logger.error(f"North flow crawl failed: {e}")
                return {"hk_to_sh": 0, "hk_to_sz": 0, "total": 0, "top_holdings": []}

        async def crawl_sector_flow():
            try:
                crawler = SectorFlowCrawler()
                return await crawler.crawl_sector_flow(date)
            except Exception as e:
                logger.error(f"Sector flow crawl failed: {e}")
                return []

        # 并发执行所有爬虫
        logger.info(f"Starting concurrent crawl for {date}")
        results = await asyncio.gather(
            crawl_limit_up_down(),
            crawl_dragon_tiger(),
            crawl_north_flow(),
            crawl_sector_flow(),
            _crawl_strength_data(),
            return_exceptions=True
        )

        # 处理结果
        limit_result, dragon_result, north_result, sector_result, strength_result = results

        # 1. 涨跌停
        if isinstance(limit_result, tuple) and len(limit_result) == 2:
            limit_up, limit_down = limit_result
            eastmoney_result["limit_up_down"]["limit_up"] = limit_up
            eastmoney_result["limit_up_down"]["limit_down"] = limit_down
            eastmoney_result["limit_up_down"]["limit_up_count"] = len(limit_up)
            eastmoney_result["limit_up_down"]["limit_down_count"] = len(limit_down)
            logger.info(f"Limit: {len(limit_up)} up, {len(limit_down)} down")

        # 2. 龙虎榜
        if isinstance(dragon_result, list):
            eastmoney_result["dragon_tiger"] = dragon_result
            logger.info(f"Dragon tiger: {len(dragon_result)} records")

        # 3. 北向资金
        if isinstance(north_result, dict):
            eastmoney_result["north_flow"] = north_result
            logger.info(f"North flow: {north_result.get('total', 0)}")

        # 4. 板块资金
        if isinstance(sector_result, list):
            eastmoney_result["sector_flow"] = sector_result
            logger.info(f"Sector flow: {len(sector_result)} sectors")

        # 5. 弱转强/强转弱/分时强度
        if isinstance(strength_result, dict):
            eastmoney_result["strength_change"] = strength_result.get("strength_change", eastmoney_result["strength_change"])
            eastmoney_result["relative_strength"] = strength_result.get("relative_strength", eastmoney_result["relative_strength"])
            eastmoney_result["market_emotion"] = strength_result.get("market_emotion", eastmoney_result["market_emotion"])
            eastmoney_result["sector_strength"]["market_chg"] = strength_result.get("market_chg", 0)
            logger.info(f"Strength: {strength_result.get('strength_change', {}).get('weak_to_strong_count', 0)} weak_to_strong")

        # ========== 同步计算 (依赖涨停数据) ==========
        limit_up = eastmoney_result["limit_up_down"]["limit_up"]

        # 6. 情绪周期 - 结合涨停数据和市场情绪
        if limit_up:
            try:
                emotion_calc = EmotionCycleCalculator()
                emotion = emotion_calc.calculate(limit_up, eastmoney_result["limit_up_down"]["limit_down"])

                # 计算连板分布
                continuous_stats = {}
                for stock in limit_up:
                    cont = stock.get("continuous", 1)
                    key = f"{cont}板"
                    continuous_stats[key] = continuous_stats.get(key, 0) + 1

                # 如果市场情绪是贪婪但情绪周期显示其他，需要修正
                market_emotion = eastmoney_result.get("market_emotion", {})
                up_ratio = market_emotion.get("up_ratio", 50)

                # 根据市场情绪修正阶段判断
                if up_ratio >= 70:
                    phase = "高潮期"
                    strategy = "市场情绪高涨，追踪龙头，关注补涨，注意风险"
                elif up_ratio >= 55:
                    phase = "回暖期"
                    strategy = "市场回暖，关注弱转强，首板确认"
                elif up_ratio >= 45:
                    phase = emotion.phase.value  # 使用原计算结果
                    strategy = emotion.strategy
                elif up_ratio >= 30:
                    phase = "退潮期"
                    strategy = "市场退潮，现金为王，等待信号"
                else:
                    phase = "冰点期"
                    strategy = "市场冰点，等待企稳，分批建仓"

                eastmoney_result["emotion_cycle"] = {
                    "cycle_phase": phase,  # 前端期望 cycle_phase
                    "cycle_score": emotion.score,  # 前端期望 cycle_score
                    "phase": phase,  # 兼容
                    "score": emotion.score,  # 兼容
                    "limit_up_count": emotion.limit_up_count,
                    "limit_down_count": emotion.limit_down_count,
                    "max_continuous": emotion.max_continuous,
                    "strategy": strategy,
                    "phase_desc": _get_phase_desc(phase),
                    "indicators": [
                        {"name": "涨停数", "value": len(limit_up), "weight": 40},
                        {"name": "最高连板", "value": emotion.max_continuous, "weight": 20},
                        {"name": "涨跌比", "value": f"{up_ratio}%", "weight": 20},
                        {"name": "跌停数", "value": len(eastmoney_result["limit_up_down"]["limit_down"]), "weight": 20},
                    ],
                    "continuous_stats": continuous_stats,
                }
            except Exception as e:
                logger.error(f"Emotion calc failed: {e}")

        # 7. 龙头评分
        if limit_up:
            try:
                from dataclasses import asdict
                leader_calc = LeaderScoreCalculator()
                leader_scores = leader_calc.batch_calculate(limit_up)
                leader_scores_dict = [asdict(ls) for ls in leader_scores]
                if leader_scores_dict:
                    leader_scores_dict.sort(key=lambda x: x.get("score", 0), reverse=True)
                    eastmoney_result["leader_stocks"]["top_leader"] = leader_scores_dict[0]
                    eastmoney_result["leader_stocks"]["leaders"] = leader_scores_dict[:20]
            except Exception as e:
                logger.error(f"Leader score failed: {e}")

        # 缓存完整的东财数据
        await cache.set(f"eastmoney_data:{date}", eastmoney_result, ttl=86400)
        logger.info(f"Eastmoney crawl completed for {date}")

        # 自动保存情绪历史到数据库（用于情绪走势图）
        try:
            from app.api.v1.emotion import save_emotion_from_eastmoney
            from app.config.database import get_async_session
            async with get_async_session() as db:
                await save_emotion_from_eastmoney(date, eastmoney_result, db)
        except Exception as e:
            logger.warning(f"保存情绪历史失败: {e}")

        return success(eastmoney_result)

    except Exception as e:
        logger.error(f"Failed to crawl eastmoney data: {e}")
        return error(f"爬虫执行失败: {str(e)}")


def _get_phase_desc(phase: str) -> str:
    """获取阶段描述"""
    phases = {
        "冰点期": "市场处于冰点，风险大，建议观望",
        "回暖期": "市场开始回暖，关注龙头股和热点板块",
        "修复期": "市场修复中，可逐步建仓优质标的",
        "高潮期": "市场情绪高涨，追踪强势股，注意高位风险",
        "退潮期": "市场退潮，现金为王，等待新周期",
    }
    return phases.get(phase, "未知阶段")
