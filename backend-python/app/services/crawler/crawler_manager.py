# -*- coding: utf-8 -*-
"""爬虫协调器

统一管理所有爬虫，支持并发、降级、熔断
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from loguru import logger

from .dragon_tiger import DragonTigerCrawler
from .north_flow import NorthFlowCrawler
from .limit_up import LimitUpCrawler
from .sector_flow import SectorFlowCrawler
from .minute_kline import MinuteKlineCrawler
from .finance_financing import FinanceFinancingCrawler
from .abnormal_warning import AbnormalWarningCrawler
from .new_stock import NewStockCrawler
from .data_validator import DataValidator
from .strategies.circuit_breaker import CircuitBreakerManager


class CrawlerManager:
    """爬虫协调器

    统一管理所有爬虫模块，提供：
    - 并发爬取
    - 数据验证
    - 错误处理
    - 熔断控制
    - 结果缓存
    """

    def __init__(self):
        self.dragon_tiger = DragonTigerCrawler()
        self.north_flow = NorthFlowCrawler()
        self.limit_up = LimitUpCrawler()
        self.sector_flow = SectorFlowCrawler()
        self.minute_kline = MinuteKlineCrawler()
        self.financing = FinanceFinancingCrawler()
        self.abnormal = AbnormalWarningCrawler()
        self.new_stock = NewStockCrawler()

        self.breaker_manager = CircuitBreakerManager()
        self._init_breakers()

        self.validator = DataValidator()
        self.cache: Dict[str, Any] = {}

    def _init_breakers(self) -> None:
        """初始化熔断器"""
        crawlers = [
            "dragon_tiger", "north_flow", "limit_up", "sector_flow",
            "minute_kline", "financing", "abnormal", "new_stock"
        ]
        for crawler_name in crawlers:
            self.breaker_manager.create_breaker(
                name=crawler_name,
                failure_threshold=5,
                recovery_timeout=300,  # 5分钟恢复超时
            )

    async def crawl_all(
        self,
        trade_date: str,
        validate: bool = True,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """并发爬取所有数据

        Args:
            trade_date: 交易日期 (YYYYMMDD)
            validate: 是否验证数据
            use_cache: 是否使用缓存

        Returns:
            所有爬虫的结果汇总
        """
        cache_key = f"all:{trade_date}"
        if use_cache and cache_key in self.cache:
            logger.info(f"Using cached data for {trade_date}")
            return self.cache[cache_key]

        logger.info(f"Starting concurrent crawl for {trade_date}")
        start_time = datetime.now()

        # 并发执行所有爬虫
        results = await asyncio.gather(
            self._safe_crawl_dragon_tiger(trade_date),
            self._safe_crawl_north_flow(trade_date),
            self._safe_crawl_limit_up(trade_date),
            self._safe_crawl_sector_flow(trade_date),
            self._safe_crawl_financing(),
            self._safe_crawl_abnormal(trade_date),
            self._safe_crawl_new_stocks(),
            return_exceptions=True,
        )

        data = {
            "timestamp": datetime.now().isoformat(),
            "trade_date": trade_date,
            "dragon_tiger": results[0] if not isinstance(results[0], Exception) else None,
            "north_flow": results[1] if not isinstance(results[1], Exception) else None,
            "limit_up": results[2][0] if not isinstance(results[2], Exception) else None,
            "limit_down": results[2][1] if not isinstance(results[2], Exception) else None,
            "sectors": results[3] if not isinstance(results[3], Exception) else None,
            "financing": results[4] if not isinstance(results[4], Exception) else None,
            "abnormal": results[5] if not isinstance(results[5], Exception) else None,
            "new_stocks": results[6] if not isinstance(results[6], Exception) else None,
            "statistics": self._calculate_statistics(results),
        }

        # 缓存结果
        if use_cache:
            self.cache[cache_key] = data

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Crawl completed in {elapsed:.2f}s")

        return data

    async def crawl_market_overview(self, trade_date: str) -> Dict[str, Any]:
        """爬取市场概览（轻量级）

        包括龙虎榜、涨跌停、板块数据

        Args:
            trade_date: 交易日期

        Returns:
            市场概览数据
        """
        results = await asyncio.gather(
            self._safe_crawl_dragon_tiger(trade_date),
            self._safe_crawl_limit_up(trade_date),
            self._safe_crawl_sector_flow(trade_date),
            return_exceptions=True,
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "dragon_tiger": results[0] if not isinstance(results[0], Exception) else [],
            "limit_up": results[1][0] if not isinstance(results[1], Exception) else [],
            "limit_down": results[1][1] if not isinstance(results[1], Exception) else [],
            "sectors": results[2] if not isinstance(results[2], Exception) else [],
        }

    async def crawl_capital_flow(self) -> Dict[str, Any]:
        """爬取资金流向数据

        包括北向资金、融资融券、板块资金

        Returns:
            资金流向数据
        """
        results = await asyncio.gather(
            self._safe_crawl_north_flow(""),
            self._safe_crawl_financing(),
            self._safe_crawl_sector_flow(""),
            return_exceptions=True,
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "north_flow": results[0] if not isinstance(results[0], Exception) else None,
            "financing": results[1] if not isinstance(results[1], Exception) else None,
            "sectors": results[2] if not isinstance(results[2], Exception) else None,
        }

    # 受保护的爬虫方法（带熔断器）

    async def _safe_crawl_dragon_tiger(self, trade_date: str) -> Optional[List]:
        """受保护的龙虎榜爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("dragon_tiger")
            result = await breaker.call(
                self.dragon_tiger.crawl_dragon_tiger,
                trade_date
            )
            return self.validator.validate_dragon_tiger(result) if result else []
        except Exception as e:
            logger.error(f"Dragon tiger crawl failed: {e}")
            return None

    async def _safe_crawl_north_flow(self, trade_date: str) -> Optional[Dict]:
        """受保护的北向资金爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("north_flow")
            result = await breaker.call(
                self.north_flow.crawl_north_flow,
                trade_date
            )
            return self.validator.validate_north_flow(result) if result else None
        except Exception as e:
            logger.error(f"North flow crawl failed: {e}")
            return None

    async def _safe_crawl_limit_up(self, trade_date: str) -> tuple:
        """受保护的涨跌停爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("limit_up")
            limit_up, limit_down = await breaker.call(
                self.limit_up.crawl_limit_up_down,
                trade_date
            )
            return (
                self.validator.validate_limit_up(limit_up) if limit_up else [],
                self.validator.validate_limit_up(limit_down) if limit_down else []
            )
        except Exception as e:
            logger.error(f"Limit up crawl failed: {e}")
            return (None, None)

    async def _safe_crawl_sector_flow(self, trade_date: str) -> Optional[List]:
        """受保护的板块资金爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("sector_flow")
            result = await breaker.call(
                self.sector_flow.crawl_sector_flow,
                trade_date
            )
            return self.validator.validate_sector_flow(result) if result else []
        except Exception as e:
            logger.error(f"Sector flow crawl failed: {e}")
            return None

    async def _safe_crawl_financing(self) -> Optional[List]:
        """受保护的融资融券爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("financing")
            result = await breaker.call(
                self.financing.crawl_financing_stocks
            )
            return result if result else []
        except Exception as e:
            logger.error(f"Financing crawl failed: {e}")
            return None

    async def _safe_crawl_abnormal(self, trade_date: str) -> Optional[List]:
        """受保护的异常波动爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("abnormal")
            result = await breaker.call(
                self.abnormal.crawl_abnormal_stocks,
                trade_date
            )
            return result if result else []
        except Exception as e:
            logger.error(f"Abnormal crawl failed: {e}")
            return None

    async def _safe_crawl_new_stocks(self) -> Optional[List]:
        """受保护的新股爬取"""
        try:
            breaker = self.breaker_manager.get_breaker("new_stock")
            result = await breaker.call(
                self.new_stock.crawl_new_stocks
            )
            return result if result else []
        except Exception as e:
            logger.error(f"New stock crawl failed: {e}")
            return None

    def _calculate_statistics(self, results: List) -> Dict[str, Any]:
        """计算统计信息

        Args:
            results: 所有爬虫的结果列表

        Returns:
            统计信息
        """
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
        total_count = len(results)

        return {
            "total_crawlers": total_count,
            "success_count": success_count,
            "failure_count": total_count - success_count,
            "success_rate": f"{success_count/total_count*100:.1f}%",
            "breaker_status": self.breaker_manager.get_all_status(),
        }

    def clear_cache(self, key: Optional[str] = None) -> None:
        """清除缓存

        Args:
            key: 缓存键，为 None 则清除所有
        """
        if key:
            self.cache.pop(key, None)
            logger.info(f"Cleared cache: {key}")
        else:
            self.cache.clear()
            logger.info("Cleared all cache")

    def get_status(self) -> Dict[str, Any]:
        """获取协调器状态

        Returns:
            状态信息
        """
        return {
            "breakers": self.breaker_manager.get_all_status(),
            "cache_size": len(self.cache),
            "cache_keys": list(self.cache.keys()),
        }
