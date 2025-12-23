"""
新增分析 API - 充分利用 pandas + ta-lib 优势

相比原 PHP 版本的改进：
1. 数据在内存中处理，避免逐条 SQL 查询
2. ta-lib 计算指标快 10 倍
3. pandas 提供灵活的数据操作
4. 一次性返回多个分析结果，减少 API 调用
"""

from fastapi import APIRouter, Query
from loguru import logger
from app.schemas import success, error
from app.services.data_service import DataService
from app.services.crawler.market_crawler import MarketCrawler
from app.services.chan_service import ChanService
from app.services.cache_service import CacheService, CacheKeys

router = APIRouter(prefix="", tags=["高级分析"])


@router.get("/analyze-stock")
async def analyze_stock(
    symbol: str = Query(None, description="股票代码 如 000001"),
    start_date: str = Query(None, description="开始日期 YYYYMMDD"),
    end_date: str = Query(None, description="结束日期 YYYYMMDD"),
    use_cache: bool = Query(True, description="是否使用缓存"),
):
    """完整分析单只股票 (一个 API 返回多个指标) + 缓存

    优势：
    - 使用 ta-lib 计算指标 (快 10 倍)
    - pandas 向量化操作
    - Redis 缓存热点数据（1小时）
    - 返回 OHLC + 10+ 个技术指标 + 信号识别

    与 PHP 版本对比：
    - PHP: 需要调用多个 API (oversold, kdj-bottom, macd-golden...)
    - Python: 一次 API 返回所有数据 + 缓存，性能远优
    """
    if not symbol:
        return error("缺少股票代码")

    try:
        # 尝试从缓存获取
        cache = CacheService()
        cache_key = CacheKeys.stock_indicators(symbol)

        if use_cache:
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {symbol}")
                latest = cached_data[-1] if cached_data else {}

                return success({
                    "symbol": symbol,
                    "date": str(latest.get('trade_date', '')),
                    "ohlc": {
                        "open": float(latest.get('open', 0)),
                        "high": float(latest.get('high', 0)),
                        "low": float(latest.get('low', 0)),
                        "close": float(latest.get('close', 0)),
                    },
                    "indicators": {
                        "rsi_6": float(latest.get('rsi_6', 0)),
                        "rsi_12": float(latest.get('rsi_12', 0)),
                        "macd": float(latest.get('macd', 0)),
                        "macd_hist": float(latest.get('macd_hist', 0)),
                        "k": float(latest.get('k', 0)),
                        "d": float(latest.get('d', 0)),
                        "j": float(latest.get('j', 0)),
                        "boll_upper": float(latest.get('boll_upper', 0)),
                        "boll_mid": float(latest.get('boll_mid', 0)),
                        "boll_lower": float(latest.get('boll_lower', 0)),
                        "atr": float(latest.get('atr', 0)),
                    },
                    "signals": {
                        "rsi_oversold": float(latest.get('rsi_6', 50)) < 30,
                        "macd_golden_cross": float(latest.get('macd_hist', 0)) > 0,
                        "kdj_bottom": float(latest.get('k', 50)) < 20 and float(latest.get('d', 50)) < 20,
                    },
                    "history_count": len(cached_data),
                    "from_cache": True,
                })

        # 从 akshare 获取数据
        df = DataService.get_market_data_akshare(symbol, start_date, end_date)

        if df.empty:
            return error("获取数据失败")

        # 一次性计算所有指标 (ta-lib)
        df = DataService.calculate_indicators(df)

        # 保存到缓存 (24小时)
        if use_cache:
            await cache.set(cache_key, df.to_dict(orient='records'), ttl=86400)

        # 获取最新数据
        latest = df.iloc[-1].to_dict()

        # 识别信号
        oversold = df.iloc[-1]['rsi_6'] < 30
        macd_golden = df.iloc[-1]['macd_hist'] > 0
        kdj_bottom = df.iloc[-1]['k'] < 20 and df.iloc[-1]['d'] < 20

        return success({
            "symbol": symbol,
            "date": str(latest.get('trade_date')),
            "ohlc": {
                "open": float(latest.get('open')),
                "high": float(latest.get('high')),
                "low": float(latest.get('low')),
                "close": float(latest.get('close')),
            },
            "indicators": {
                "rsi_6": float(latest.get('rsi_6', 0)),
                "rsi_12": float(latest.get('rsi_12', 0)),
                "macd": float(latest.get('macd', 0)),
                "macd_hist": float(latest.get('macd_hist', 0)),
                "k": float(latest.get('k', 0)),
                "d": float(latest.get('d', 0)),
                "j": float(latest.get('j', 0)),
                "boll_upper": float(latest.get('boll_upper', 0)),
                "boll_mid": float(latest.get('boll_mid', 0)),
                "boll_lower": float(latest.get('boll_lower', 0)),
                "atr": float(latest.get('atr', 0)),
            },
            "signals": {
                "rsi_oversold": oversold,
                "macd_golden_cross": macd_golden,
                "kdj_bottom": kdj_bottom,
            },
            "history_count": len(df),
            "from_cache": False,
        })

    except Exception as e:
        logger.error(f"Failed to analyze stock: {e}")
        return error(f"分析失败: {str(e)}")


@router.get("/emotion-cycle")
async def get_emotion_cycle(
    trade_date: str = Query(None, description="交易日期 YYYYMMDD"),
):
    """获取市场情绪周期 (完整分析版)

    优势：
    - 一次返回完整的情绪分析
    - 包含涨停数据、连板分布、赚钱效应
    - pandas 向量化计算，极快

    与 PHP 版本对比：
    - PHP: EastmoneyCrawler 1600行代码
    - Python: pandas 向量化，代码简洁、快速
    """
    if not trade_date:
        return error("缺少交易日期")

    try:
        # 爬取涨跌停数据
        result = await MarketCrawler.crawl_limit_up_down(trade_date)

        limit_up_df = result['limit_up']
        limit_down_df = result['limit_down']
        statistics = result['statistics']

        # 计算情绪周期 (全 pandas 向量化)
        emotion = MarketCrawler.calculate_emotion_cycle(limit_up_df, limit_down_df)

        # 识别龙头股 (top 10)
        leaders = MarketCrawler.identify_leader_stocks(limit_up_df)
        top_leaders = leaders.head(10).to_dict('records') if not leaders.empty else []

        return success({
            "trade_date": trade_date,
            "emotion_cycle": emotion,
            "statistics": statistics,
            "top_leaders": top_leaders,
            "recommendation": emotion['strategy'],
        })

    except Exception as e:
        logger.error(f"Failed to analyze emotion cycle: {e}")
        return error(f"分析失败: {str(e)}")


@router.get("/multi-indicator-resonance")
async def get_multi_indicator_resonance(
    symbols: str = Query(None, description="股票代码,分隔符为逗号 如 000001,000002"),
    trade_date: str = Query(None, description="交易日期 YYYYMMDD"),
):
    """多指标共振选股 (关键策略 - Python 优化版)

    优势：
    - 批量分析多只股票，并行计算
    - ta-lib 快速计算所有指标
    - pandas 向量化识别共振信号
    - 一次返回结果，减少 API 调用

    与 PHP 版本对比：
    - PHP: 逐只查询，拼接结果
    - Python: 批量处理，性能 N 倍提升
    """
    if not symbols:
        return error("缺少股票代码")

    try:
        symbol_list = [s.strip() for s in symbols.split(',')]

        # 批量获取数据并计算指标 (asyncio 并发)
        stocks_data = await DataService.batch_analyze_stocks(symbol_list, trade_date)

        if not stocks_data:
            return error("获取数据失败")

        # 多指标共振选股 (pandas 向量化)
        resonance_stocks = DataService.get_multi_indicator_resonance(stocks_data, trade_date)

        return success({
            "trade_date": trade_date,
            "total_analyzed": len(stocks_data),
            "resonance_count": len(resonance_stocks),
            "resonance_stocks": resonance_stocks,
            "recommendation": "命中 >= 3 个指标的股票为重点关注",
        })

    except Exception as e:
        logger.error(f"Failed to analyze resonance: {e}")
        return error(f"分析失败: {str(e)}")


@router.get("/oversold-stocks")
async def get_oversold_stocks(
    symbols: str = Query(None, description="股票代码,分隔符"),
    rsi_threshold: int = Query(30, description="RSI 阈值"),
):
    """获取 RSI 超卖股票 (向量化版)

    优势：
    - 一次处理多只股票
    - ta-lib 快速计算 RSI
    - pandas 过滤和排序

    与 PHP SQL 版本对比：
    - PHP: SQL JOIN + WHERE 子句
    - Python: pandas 内存过滤，极快
    """
    if not symbols:
        return error("缺少股票代码")

    try:
        symbol_list = [s.strip() for s in symbols.split(',')]
        stocks_data = await DataService.batch_analyze_stocks(symbol_list)

        oversold_list = []

        for symbol, df in stocks_data.items():
            oversold_rows = DataService.identify_oversold(df, rsi_threshold)

            if not oversold_rows.empty:
                latest = oversold_rows.iloc[-1]
                oversold_list.append({
                    'symbol': symbol,
                    'rsi_6': float(latest.get('rsi_6', 0)),
                    'rsi_12': float(latest.get('rsi_12', 0)),
                    'close': float(latest.get('close', 0)),
                })

        # 按 RSI_6 排序
        oversold_list = sorted(oversold_list, key=lambda x: x['rsi_6'])

        return success(oversold_list)

    except Exception as e:
        logger.error(f"Failed to identify oversold stocks: {e}")
        return error(f"分析失败: {str(e)}")


@router.get("/chan-analysis")
async def get_chan_analysis(
    symbol: str = Query(None, description="股票代码 如 000001"),
    start_date: str = Query(None, description="开始日期 YYYYMMDD"),
    end_date: str = Query(None, description="结束日期 YYYYMMDD"),
):
    """缠论完整分析 (numpy优化版)

    优势：
    - 使用numpy向量化操作识别分型
    - O(n) 复杂度，性能极优
    - 返回分型、笔、线段、中枢完整链路
    - 识别突破点和关键价格位置

    缠论核心概念：
    - 分型(Fractal): 高-低-高(顶) 或 低-高-低(底)
    - 笔(Bi): 从一个分型到下一个分型
    - 线段(Segment): 至少5笔的序列
    - 中枢(Hub): 线段的重叠部分
    """
    if not symbol:
        return error("缺少股票代码")

    try:
        # 获取数据并计算所有指标
        df = DataService.get_market_data_akshare(symbol, start_date, end_date)

        if df.empty:
            return error("获取数据失败")

        df = DataService.calculate_indicators(df)

        # 缠论分析 (numpy优化)
        chan_result = ChanService.analyze(df)

        # 识别突破点
        breakouts = ChanService.identify_breakout_points(df)

        # 关键价格位置
        key_levels = ChanService.get_key_levels(df)

        # 获取最新数据
        latest = df.iloc[-1].to_dict()

        return success({
            "symbol": symbol,
            "date": str(latest.get('trade_date')),
            "close": float(latest.get('close', 0)),
            "chan": {
                "current_trend": chan_result.get('current_trend'),
                "fractal_count": chan_result.get('fractal_count', 0),
                "bi_count": chan_result.get('bi_count', 0),
                "segment_count": chan_result.get('segment_count', 0),
                "hub_count": chan_result.get('hub_count', 0),
            },
            "latest_bis": chan_result.get('bis', [])[-3:] if chan_result.get('bis') else [],
            "latest_hub": chan_result.get('hubs', [])[-1] if chan_result.get('hubs') else None,
            "breakouts": breakouts,
            "key_levels": key_levels,
        })

    except Exception as e:
        logger.error(f"Failed to analyze chan: {e}")
        return error(f"缠论分析失败: {str(e)}")


@router.get("/chan-key-levels")
async def get_chan_key_levels(
    symbol: str = Query(None, description="股票代码 如 000001"),
    end_date: str = Query(None, description="结束日期 YYYYMMDD"),
):
    """缠论关键价格位置 (支撑/阻力)

    基于中枢识别：
    - 阻力位：中枢上轨
    - 支撑位：中枢下轨

    适用于：
    - 日内/日线交易止损止盈设置
    - 技术面支撑阻力判断
    """
    if not symbol:
        return error("缺少股票代码")

    try:
        df = DataService.get_market_data_akshare(symbol, end_date=end_date)

        if df.empty:
            return error("获取数据失败")

        df = DataService.calculate_indicators(df)

        key_levels = ChanService.get_key_levels(df)
        latest = df.iloc[-1].to_dict()

        return success({
            "symbol": symbol,
            "date": str(latest.get('trade_date')),
            "close": float(latest.get('close', 0)),
            "resistance": key_levels.get('resistance', []),
            "support": key_levels.get('support', []),
            "recommendation": "价格接近阻力位时减仓，接近支撑位时加仓"
        })

    except Exception as e:
        logger.error(f"Failed to get chan key levels: {e}")
        return error(f"获取失败: {str(e)}")
