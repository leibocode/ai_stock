"""
缓存工具 - 使用 functools 和 aioredis 实现
充分利用 Python 的高阶函数和装饰器特性
"""
from functools import wraps
from typing import Callable, Any, Optional, TypeVar, Awaitable
from app.services.cache_service import CacheService
from loguru import logger

T = TypeVar('T')


def cache_with_ttl(ttl: int = 86400, key_builder: Optional[Callable] = None):
    """
    通用异步缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_builder: 自定义缓存 key 生成函数，
                    若不提供则自动从函数名和参数生成

    示例：
        @cache_with_ttl(ttl=3600)
        async def get_stocks(date: str):
            return await db.query(...)

        @cache_with_ttl(ttl=86400, key_builder=lambda fn, *args, **kwargs: f"custom:{args[0]}")
        async def get_data(date: str):
            return await service.fetch(date)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 生成缓存 key
            if key_builder:
                cache_key = key_builder(func, *args, **kwargs)
            else:
                # 自动生成：函数名:参数哈希
                params_str = "|".join(
                    str(arg) for arg in args[1:] if not hasattr(arg, '__call__')
                ) + "|" + "|".join(f"{k}={v}" for k, v in kwargs.items())
                cache_key = f"{func.__name__}:{params_str}" if params_str else func.__name__

            # 尝试从缓存获取
            cache = CacheService()
            cached = await cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
                logger.debug(f"Cache set: {cache_key}")

            return result

        return wrapper
    return decorator


async def with_cache(
    cache_key: str,
    fetch_fn: Callable[[], Awaitable[T]],
    ttl: int = 86400,
    cache_service: Optional[CacheService] = None
) -> T:
    """
    缓存查询助手 - 消除重复的缓存检查和存储代码

    这个函数完全消除了这样的模式：
        cache = CacheService()
        cached = await cache.get(key)
        if cached:
            return cached
        result = await fetch_data()
        await cache.set(key, result, ttl)
        return result

    改为一行代码：
        result = await with_cache(key, fetch_data)

    Args:
        cache_key: 缓存键
        fetch_fn: 异步获取数据的函数
        ttl: 缓存过期时间
        cache_service: 可选的 CacheService 实例，不提供会创建新的

    示例用法：
        # 标准用法
        data = await with_cache(
            f"volume_top:{date}:{limit}",
            lambda: query_database(date, limit),
            ttl=86400
        )

        # 返回 success 对象
        return success(data)
    """
    if cache_service is None:
        cache_service = CacheService()

    # 尝试从缓存获取
    cached = await cache_service.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit: {cache_key}")
        return cached

    # 获取数据
    result = await fetch_fn()

    # 存储到缓存
    if result is not None:
        await cache_service.set(cache_key, result, ttl=ttl)
        logger.debug(f"Cache set: {cache_key}")

    return result


def batch_process_with_window(
    data: list[T],
    window_size: int = 100,
    process_fn: Optional[Callable[[list[T]], list[T]]] = None
) -> list[T]:
    """
    分批处理大数据集，避免内存溢出

    使用 pandas 的分组功能替代传统的 for 循环

    示例：
        results = batch_process_with_window(
            stocks,
            window_size=100,
            process_fn=lambda batch: calculate_indicators(batch)
        )
    """
    if not data:
        return []

    results = []
    for i in range(0, len(data), window_size):
        batch = data[i:i + window_size]
        if process_fn:
            batch_result = process_fn(batch)
            results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
        else:
            results.extend(batch)

    return results
