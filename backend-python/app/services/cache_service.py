"""异步缓存服务 - aioredis 集成

提供Redis缓存支持，用于缓存热点数据：
- 涨停数据（每日更新）
- 情绪周期结果（每日15:30更新）
- 龙头评分（每日更新）
- 技术指标（每日更新）

缓存策略：
- 数据同步时清除旧缓存
- TTL: 1小时（指标）到1天（日线数据）
- 批量缓存键管理
"""

import json
import hashlib
from typing import Any, Optional, Dict, List, Callable
from datetime import timedelta
from loguru import logger

try:
    import aioredis
except ImportError:
    aioredis = None


class CacheService:
    """异步缓存服务 - aioredis"""

    # Redis连接实例 (全局单例)
    _redis = None

    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl: int = 3600):
        """初始化缓存服务

        Args:
            redis_url: Redis连接字符串
            ttl: 默认TTL (秒)
        """
        self.redis_url = redis_url
        self.ttl = ttl
        self.key_prefix = "ai_stock:"

    async def connect(self):
        """连接Redis"""
        if not aioredis:
            logger.warning("aioredis not installed, cache disabled")
            return

        if CacheService._redis is None:
            try:
                CacheService._redis = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf8",
                    decode_responses=True
                )
                logger.info("Redis connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")

    async def disconnect(self):
        """断开Redis连接"""
        if CacheService._redis:
            await CacheService._redis.close()
            CacheService._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存的值（JSON反序列化后），不存在返回None
        """
        if not CacheService._redis:
            return None

        try:
            full_key = self.key_prefix + key
            value = await CacheService._redis.get(full_key)

            if value is None:
                return None

            # JSON反序列化
            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值（自动JSON序列化）
            ttl: TTL (秒)，None时使用默认TTL

        Returns:
            是否设置成功
        """
        if not CacheService._redis:
            return False

        try:
            full_key = self.key_prefix + key
            ttl = ttl or self.ttl

            # JSON序列化
            json_value = json.dumps(value, ensure_ascii=False)

            await CacheService._redis.setex(full_key, ttl, json_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not CacheService._redis:
            return False

        try:
            full_key = self.key_prefix + key
            await CacheService._redis.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存

        Args:
            pattern: Redis pattern (支持 * 通配符)
                   例如: "stock:*" 删除所有stock前缀的缓存

        Returns:
            删除的键数量
        """
        if not CacheService._redis:
            return 0

        try:
            full_pattern = self.key_prefix + pattern
            keys = await CacheService._redis.keys(full_pattern)

            if not keys:
                return 0

            deleted = await CacheService._redis.delete(*keys)
            return deleted
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0

    @staticmethod
    def generate_key(prefix: str, *args) -> str:
        """生成缓存键

        Args:
            prefix: 键前缀 (如 'stock', 'emotion_cycle')
            *args: 用于构成键的参数

        Returns:
            格式化后的缓存键

        Examples:
            generate_key('stock', '000001', 'indicators') → 'stock:000001:indicators'
            generate_key('emotion_cycle', '20231215') → 'emotion_cycle:20231215'
        """
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)

    @staticmethod
    def generate_hash_key(prefix: str, data: Dict) -> str:
        """基于数据内容生成哈希键

        用于参数可变的查询，避免键冲突

        Args:
            prefix: 键前缀
            data: 用于生成哈希的字典

        Returns:
            哈希后的缓存键

        Example:
            query = {'symbols': ['000001', '000002'], 'date': '20231215'}
            key = generate_hash_key('resonance', query)
            → 'resonance:a3f5k2m9...'
        """
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash_val = hashlib.md5(json_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_val}"


class CacheDecorator:
    """缓存装饰器 - 用于自动缓存async函数结果"""

    def __init__(self, ttl: int = 3600):
        """初始化装饰器

        Args:
            ttl: 缓存过期时间 (秒)
        """
        self.ttl = ttl
        self.cache = CacheService()

    def __call__(self, func: Callable) -> Callable:
        """装饰async函数

        Example:
            @CacheDecorator(ttl=3600)
            async def get_stock_data(symbol: str):
                return await fetch_from_api(symbol)
        """
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 生成缓存键 (基于函数名和参数)
            key = CacheService.generate_key(
                func.__name__,
                *args,
                *[f"{k}={v}" for k, v in sorted(kwargs.items())]
            )

            # 尝试获取缓存
            cached = await self.cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit: {key}")
                return cached

            # 缓存未命中，执行函数
            result = await func(*args, **kwargs)

            # 保存到缓存
            await self.cache.set(key, result, self.ttl)

            return result

        return wrapper


# 预定义的缓存键策略
class CacheKeys:
    """缓存键常量定义"""

    # 股票数据
    @staticmethod
    def stock_daily(symbol: str, date: str = None) -> str:
        """日线数据缓存键"""
        return CacheService.generate_key("stock_daily", symbol, date or "*")

    @staticmethod
    def stock_indicators(symbol: str) -> str:
        """技术指标缓存键"""
        return CacheService.generate_key("stock_indicators", symbol)

    # 情绪周期
    @staticmethod
    def emotion_cycle(date: str) -> str:
        """情绪周期缓存键"""
        return CacheService.generate_key("emotion_cycle", date)

    # 龙头评分
    @staticmethod
    def leader_scores(date: str) -> str:
        """龙头评分缓存键"""
        return CacheService.generate_key("leader_scores", date)

    # 涨停数据
    @staticmethod
    def limit_up_down(date: str) -> str:
        """涨跌停缓存键"""
        return CacheService.generate_key("limit_up_down", date)

    # 多指标共振
    @staticmethod
    def resonance(symbols: str, date: str) -> str:
        """共振选股缓存键"""
        data = {"symbols": symbols, "date": date}
        return CacheService.generate_hash_key("resonance", data)

    # 缠论分析
    @staticmethod
    def chan_analysis(symbol: str) -> str:
        """缠论分析缓存键"""
        return CacheService.generate_key("chan_analysis", symbol)


# 缓存预热策略
class CacheWarming:
    """缓存预热 - 在应用启动或定时任务时预加载热点数据"""

    def __init__(self, cache: CacheService):
        self.cache = cache

    async def warm_stock_data(self, symbols: List[str], date: str = None):
        """预热股票数据缓存

        Args:
            symbols: 股票代码列表
            date: 日期 (None时使用最新)
        """
        from app.services.data_service import DataService

        logger.info(f"Warming stock data cache for {len(symbols)} symbols")

        for symbol in symbols:
            try:
                df = DataService.get_market_data_akshare(symbol, end_date=date)

                if not df.empty:
                    df = DataService.calculate_indicators(df)
                    key = CacheKeys.stock_indicators(symbol)
                    await self.cache.set(key, df.to_dict(orient='records'), ttl=86400)
            except Exception as e:
                logger.error(f"Failed to warm cache for {symbol}: {e}")

    async def warm_emotion_cycle(self, date: str):
        """预热情绪周期缓存

        Args:
            date: 交易日期
        """
        from app.services.crawler.market_crawler import MarketCrawler

        logger.info(f"Warming emotion cycle cache for {date}")

        try:
            result = await MarketCrawler.crawl_limit_up_down(date)

            if result.get('limit_up') is not None:
                emotion = MarketCrawler.calculate_emotion_cycle(
                    result['limit_up'],
                    result['limit_down']
                )
                key = CacheKeys.emotion_cycle(date)
                await self.cache.set(key, emotion, ttl=86400)
        except Exception as e:
            logger.error(f"Failed to warm emotion cycle cache: {e}")
