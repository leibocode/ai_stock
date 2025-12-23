from fastapi import APIRouter, Query
from loguru import logger
from app.schemas import success, error
from app.services.cache_service import CacheService
from app.utils.cache_decorator import with_cache

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
