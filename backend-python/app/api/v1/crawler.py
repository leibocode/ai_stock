from fastapi import APIRouter, Query
from loguru import logger
from typing import Optional
from app.schemas import success, error
from app.services.cache_service import CacheService
from app.utils.cache_decorator import with_cache
from app.services.crawler.crawler_manager import CrawlerManager

# 全局爬虫协调器实例
_crawler_manager: Optional[CrawlerManager] = None

def get_crawler_manager() -> CrawlerManager:
    """获取或初始化爬虫协调器"""
    global _crawler_manager
    if _crawler_manager is None:
        _crawler_manager = CrawlerManager()
    return _crawler_manager

router = APIRouter(prefix="", tags=["爬虫数据"])


@router.get("/eastmoney-data")
async def get_eastmoney_data(date: str = Query(None, description="交易日期YYYYMMDD")):
    """获取东财缓存数据 (龙虎榜、北向资金、板块资金、龙头评分、情绪周期)

    返回该日期的爬虫数据汇总，包括：
    - dragon_tiger: 龙虎榜数据
    - north_flow: 北向资金
    - sector_flow: 板块资金
    - emotion_cycle: 情绪周期分析
    - leader_score: 龙头评分
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            cache = CacheService()

            # 如果缓存中没有，尝试从各个爬虫结果缓存中聚合
            # 这些缓存由 /api/crawl-eastmoney 或定时任务生成
            eastmoney_data = {
                "date": date,
                "dragon_tiger": None,        # 龙虎榜
                "north_flow": None,          # 北向资金
                "sector_flow": None,         # 板块资金
                "emotion_cycle": None,       # 情绪周期
                "leader_score": None,        # 龙头评分
                "last_update": None,
            }

            # 尝试从各子缓存获取
            dragon_tiger = await cache.get(f"dragon_tiger:{date}")
            if dragon_tiger:
                eastmoney_data["dragon_tiger"] = dragon_tiger

            north_flow = await cache.get(f"north_flow:{date}")
            if north_flow:
                eastmoney_data["north_flow"] = north_flow

            sector_flow = await cache.get(f"sector_flow:{date}")
            if sector_flow:
                eastmoney_data["sector_flow"] = sector_flow

            emotion_cycle = await cache.get(f"emotion_cycle:{date}")
            if emotion_cycle:
                eastmoney_data["emotion_cycle"] = emotion_cycle

            leader_score = await cache.get(f"leader_score:{date}")
            if leader_score:
                eastmoney_data["leader_score"] = leader_score

            return eastmoney_data

        data = await with_cache(f"eastmoney_data:{date}", fetch_data, ttl=21600)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get eastmoney data: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/eastmoney-list")
async def get_eastmoney_list(
    limit: int = Query(20, description="返回数量")
):
    """东财爬虫历史列表 (最近N次爬虫运行记录)

    返回爬虫执行历史，用于追踪数据更新情况
    """
    try:
        async def fetch_data():
            # 如果没有缓存，返回空列表结构
            # 实际数据由 /api/crawl-eastmoney 执行时记录
            return {
                "total": 0,
                "records": [],
                "message": "爬虫数据还未生成，请运行 /api/sync/crawl-eastmoney 获取最新数据"
            }

        data = await with_cache(f"eastmoney_list:{limit}", fetch_data, ttl=86400)
        return success(data)

    except Exception as e:
        logger.error(f"Failed to get eastmoney list: {e}")
        return error(f"获取失败: {str(e)}")


# ==================== P3/P4 高级爬虫接口 ====================

@router.get("/all/{trade_date}")
async def crawl_all_data(
    trade_date: str,
    validate: bool = Query(True, description="是否验证数据"),
    use_cache: bool = Query(True, description="是否使用缓存"),
):
    """并发爬取所有数据 - P4 核心接口

    爬取以下8个数据源：
    - 龙虎榜 (dragon_tiger)
    - 北向资金 (north_flow)
    - 涨停数据 (limit_up)
    - 跌停数据 (limit_down)
    - 板块资金 (sectors)
    - 融资融券 (financing)
    - 异常波动 (abnormal)
    - 新股申购 (new_stocks)

    返回结果包含所有爬虫数据 + 统计信息 (success_rate, failure_count等)
    """
    try:
        manager = get_crawler_manager()
        logger.info(f"Starting concurrent crawl for {trade_date}")

        data = await manager.crawl_all(
            trade_date=trade_date,
            validate=validate,
            use_cache=use_cache
        )

        logger.info(f"Crawl completed for {trade_date}")
        return success(data)

    except Exception as e:
        logger.error(f"Crawl all failed: {e}")
        return error(f"并发爬取失败: {str(e)}")


@router.get("/market-overview/{trade_date}")
async def crawl_market_overview(
    trade_date: str,
    use_cache: bool = Query(True, description="是否使用缓存"),
):
    """爬取市场概览 - 轻量级接口

    快速爬取以下数据：
    - 龙虎榜 (dragon_tiger)
    - 涨停数据 (limit_up)
    - 跌停数据 (limit_down)
    - 板块资金 (sectors)

    性能：200-500ms（相比crawl_all的2-3s更快）
    适用场景：快速市场概览、实时盯盘
    """
    try:
        manager = get_crawler_manager()
        logger.info(f"Starting market overview crawl for {trade_date}")

        data = await manager.crawl_market_overview(
            trade_date=trade_date,
            use_cache=use_cache
        )

        logger.info(f"Market overview crawl completed for {trade_date}")
        return success(data)

    except Exception as e:
        logger.error(f"Market overview crawl failed: {e}")
        return error(f"市场概览爬取失败: {str(e)}")


@router.get("/capital-flow")
async def crawl_capital_flow(
    use_cache: bool = Query(True, description="是否使用缓存"),
):
    """爬取资金流向数据

    爬取以下数据：
    - 北向资金 (north_flow)
    - 融资融券 (financing)
    - 板块资金 (sectors)

    用途：分析市场资金面状况
    """
    try:
        manager = get_crawler_manager()
        logger.info("Starting capital flow crawl")

        data = await manager.crawl_capital_flow(use_cache=use_cache)

        logger.info("Capital flow crawl completed")
        return success(data)

    except Exception as e:
        logger.error(f"Capital flow crawl failed: {e}")
        return error(f"资金流向爬取失败: {str(e)}")


@router.get("/status")
async def get_crawler_status():
    """获取爬虫协调器状态

    返回：
    - cache_size: 缓存中的数据数量
    - cache_keys: 缓存中的所有键
    - breakers: 所有熔断器状态（状态/成功率/失败率）

    用途：监控爬虫健康状态、检查缓存情况
    """
    try:
        manager = get_crawler_manager()
        status = manager.get_status()
        return success(status)

    except Exception as e:
        logger.error(f"Failed to get crawler status: {e}")
        return error(f"获取状态失败: {str(e)}")


@router.post("/cache/clear")
async def clear_crawler_cache(
    key: Optional[str] = Query(None, description="要清除的缓存键，不指定则清除全部"),
):
    """清除爬虫缓存

    参数：
    - key: 具体的缓存键（如 'dragon_tiger:20251226'），不指定则清除全部

    用途：当数据需要刷新时调用
    """
    try:
        manager = get_crawler_manager()
        if key:
            manager.clear_cache(key)
            logger.info(f"Cleared cache: {key}")
            return success({"message": f"已清除缓存: {key}"})
        else:
            manager.clear_cache()
            logger.info("Cleared all crawler cache")
            return success({"message": "已清除全部缓存"})

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return error(f"清除缓存失败: {str(e)}")


# ==================== 开盘啦数据接口 ====================

from app.services.crawler.kaipanla import KaipanlaCrawler, KaipanlaAppCrawler

# 全局开盘啦爬虫实例
_kaipanla_crawler: Optional[KaipanlaCrawler] = None
_kaipanla_app_crawler: Optional[KaipanlaAppCrawler] = None

def get_kaipanla_crawler() -> KaipanlaCrawler:
    """获取或初始化开盘啦网页爬虫"""
    global _kaipanla_crawler
    if _kaipanla_crawler is None:
        _kaipanla_crawler = KaipanlaCrawler()
    return _kaipanla_crawler

def get_kaipanla_app_crawler() -> KaipanlaAppCrawler:
    """获取或初始化开盘啦App爬虫（更准确的数据源）"""
    global _kaipanla_app_crawler
    if _kaipanla_app_crawler is None:
        _kaipanla_app_crawler = KaipanlaAppCrawler()
    return _kaipanla_app_crawler


@router.get("/kaipanla/limit-up")
async def get_kaipanla_limit_up(
    date: str = Query(None, description="交易日期YYYYMMDD，默认今天")
):
    """获取开盘啦涨停股列表

    包含：涨停股代码、封单额、封单比、首封时间、开板次数、连板数、涨停原因
    """
    try:
        crawler = get_kaipanla_crawler()
        data = await crawler.get_limit_up_list(date)
        return success(data)
    except Exception as e:
        logger.error(f"获取开盘啦涨停数据失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/kaipanla/broken-board")
async def get_kaipanla_broken_board(
    date: str = Query(None, description="交易日期YYYYMMDD，默认今天")
):
    """获取开盘啦炸板股列表

    包含：炸板股代码、开板次数、炸板时间、最终状态(红/绿)
    """
    try:
        crawler = get_kaipanla_crawler()
        data = await crawler.get_broken_board_list(date)
        return success(data)
    except Exception as e:
        logger.error(f"获取开盘啦炸板数据失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/kaipanla/continuous-ladder")
async def get_kaipanla_continuous_ladder(
    date: str = Query(None, description="交易日期YYYYMMDD，默认今天")
):
    """获取连板梯队

    返回按连板数分组的股票列表：2板、3板、4板...
    """
    try:
        crawler = get_kaipanla_crawler()
        data = await crawler.get_continuous_board_ladder(date)
        return success(data)
    except Exception as e:
        logger.error(f"获取连板梯队失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/kaipanla/limit-down")
async def get_kaipanla_limit_down(
    date: str = Query(None, description="交易日期YYYYMMDD，默认今天")
):
    """获取开盘啦跌停股列表

    包含：跌停股代码、封单额、跌停原因
    """
    try:
        crawler = get_kaipanla_crawler()
        data = await crawler.get_limit_down_list(date)
        return success(data)
    except Exception as e:
        logger.error(f"获取开盘啦跌停数据失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/kaipanla/yesterday-performance")
async def get_kaipanla_yesterday_performance(
    date: str = Query(None, description="交易日期YYYYMMDD，默认今天")
):
    """获取昨日涨停今日表现

    包含：昨日连板数、今日溢价率、今日最终状态
    用于分析涨停溢价率和市场接力情况
    """
    try:
        crawler = get_kaipanla_crawler()
        data = await crawler.get_yesterday_limit_up_performance(date)
        return success(data)
    except Exception as e:
        logger.error(f"获取昨日涨停表现失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/kaipanla/full-emotion")
async def get_kaipanla_full_emotion(
    date: str = Query(None, description="交易日期YYYYMMDD，默认今天")
):
    """获取开盘啦完整决策数据（一站式）

    使用App API获取完整的市场情绪和决策支持数据

    返回：
    - 基础情绪数据：
      - emotion_score: 综合情绪得分(0-100)
      - emotion_phase: 情绪阶段
      - emotion_sign: 趋势判断描述
    - 涨跌停数据：
      - limit_up_count/limit_down_count/broken_count
      - limit_up_stocks: 完整涨停股列表
    - 连板梯队：
      - lianban: 一板/二板/三板/高度板统计
      - continuous_ladder: 按连板数分组的股票列表
    - 板块资金：
      - sector_flow: 涨跌板块TOP10
    - 风险预警：
      - sharp_withdrawal: 大幅回撤股票
    - 关键指标：
      - key_metrics: 晋级率/炸板率/涨跌比/最高连板
    - 策略建议：
      - strategy_detail: 详细策略(仓位/操作/关注点/风险/调整建议)
    """
    try:
        # 使用新的App爬虫获取完整决策数据
        crawler = get_kaipanla_app_crawler()
        data = crawler.crawl_full_decision_data(date)

        # 添加情绪阶段中文名
        phase_names = {
            'high_tide': '高潮期',
            'ebb_tide': '退潮期',
            'ice_point': '冰点期',
            'warming': '回暖期',
            'repair': '修复期'
        }
        data['emotion_phase_name'] = phase_names.get(data.get('emotion_phase', 'repair'), '未知')

        return success(data)
    except Exception as e:
        logger.error(f"获取开盘啦完整决策数据失败: {e}")
        return error(f"获取失败: {str(e)}")
