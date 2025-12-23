from fastapi import APIRouter, Query
from loguru import logger
from app.schemas import success, error
from app.utils.cache_decorator import with_cache

router = APIRouter(prefix="", tags=["资金流向"])


@router.get("/dragon-tiger")
async def get_dragon_tiger(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    limit: int = Query(20, description="返回数量")
):
    """龙虎榜 (涨幅最大成交量最高个股)

    龙虎榜：沪深两市成交量最高的20只股票
    用于识别主力资金关注的热点

    注：真实龙虎榜需要从东方财富爬虫获取，当前返回成交量最高的股票
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # TODO: 实现从爬虫获取龙虎榜数据
            return {
                "date": date,
                "dragon_tiger_list": [],
                "note": "需要配置爬虫数据源"
            }

        result_data = await with_cache(f"dragon_tiger:{date}:{limit}", fetch_data, ttl=3600)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get dragon tiger: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/north-buy")
async def get_north_buy(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    top: int = Query(20, description="返回排名数")
):
    """北向资金买入排名 (沪深港通)

    北向资金：香港及海外资金通过沪深港通买入的股票
    用于识别外资关注的优质公司

    注：真实北向资金数据需要从爬虫获取
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # TODO: 从爬虫获取北向资金数据
            return {
                "date": date,
                "north_buy_list": [],
                "total_north_flow": 0,
                "note": "需要配置爬虫数据源"
            }

        result_data = await with_cache(f"north_buy:{date}:{top}", fetch_data, ttl=3600)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get north buy: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/margin-buy")
async def get_margin_buy(
    date: str = Query(None, description="交易日期YYYYMMDD"),
    top: int = Query(20, description="返回排名数")
):
    """融资买入排名 (融资余额最高)

    融资买入：A股投资者借入资金买入股票
    用于识别杠杆资金关注的热点

    注：真实融资数据需要从爬虫获取
    """
    if not date:
        return error("缺少交易日期")

    try:
        async def fetch_data():
            # TODO: 从爬虫获取融资买入数据
            return {
                "date": date,
                "margin_buy_list": [],
                "total_margin_balance": 0,
                "note": "需要配置爬虫数据源"
            }

        result_data = await with_cache(f"margin_buy:{date}:{top}", fetch_data, ttl=3600)
        return success(result_data)

    except Exception as e:
        logger.error(f"Failed to get margin buy: {e}")
        return error(f"获取失败: {str(e)}")
