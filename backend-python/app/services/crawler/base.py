import httpx
import asyncio
import random
from typing import Optional, Dict, List
from loguru import logger


class BaseCrawler:
    """爬虫基类 - 支持动态IP、随机延迟、自动重试"""

    # User-Agent 池（轮换，规避检测）- 扩充到20个
    USER_AGENTS = [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Mobile
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ]

    # 代理池（免费代理池 - 更新时替换）
    PROXIES: List[str] = [
        # 可选：添加代理，格式 "http://ip:port" 或 "https://ip:port"
        # "http://proxy1.com:8080",
        # "http://proxy2.com:8080",
    ]

    def __init__(
        self,
        timeout: int = 30,
        retry_count: int = 3,
        delay_range: tuple = (0.5, 2.5),
        proxies: Optional[List[str]] = None
    ):
        """初始化爬虫

        Args:
            timeout: 请求超时时间（秒）
            retry_count: 失败重试次数
            delay_range: 请求间延迟范围（秒）
            proxies: 代理列表
        """
        self.timeout = timeout
        self.retry_count = retry_count
        self.delay_range = delay_range
        self.proxies = proxies or self.PROXIES
        self._request_count = 0
        self._last_request_time = 0

    def _get_random_headers(self) -> Dict[str, str]:
        """获取随机请求头（增强版）"""
        user_agent = random.choice(self.USER_AGENTS)

        # 根据User-Agent选择合适的Referer
        if "iPhone" in user_agent or "iPad" in user_agent:
            referer = "https://m.eastmoney.com/"
        else:
            referer = "https://www.eastmoney.com/"

        return {
            "User-Agent": user_agent,
            "Referer": referer,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json;charset=utf-8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _get_random_proxy(self) -> Optional[str]:
        """获取随机代理"""
        if self.proxies:
            return random.choice(self.proxies)
        return None

    async def _random_delay(self):
        """随机延迟（更自然的延迟模式）"""
        # 基础延迟
        base_delay = random.uniform(self.delay_range[0], self.delay_range[1])

        # 有30%的概率添加额外延迟（模拟人类浏览）
        if random.random() < 0.3:
            base_delay += random.uniform(1, 3)

        await asyncio.sleep(base_delay)

    async def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        retry: bool = True
    ) -> Optional[Dict]:
        """发送GET请求（带自动重试和反爬虫）

        Args:
            url: 请求URL
            params: 查询参数
            retry: 是否自动重试

        Returns:
            JSON响应或None
        """
        for attempt in range(self.retry_count if retry else 1):
            try:
                # 随机延迟
                await self._random_delay()

                # 随机请求头
                headers = self._get_random_headers()

                # 随机代理
                proxy = self._get_random_proxy()

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    proxy=proxy,  # httpx 使用 proxy 而非 proxies
                    verify=False  # 忽略SSL验证
                ) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    resp.raise_for_status()

                    self._request_count += 1
                    return resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # 频率限制
                    logger.warning(f"Rate limited, retrying... (attempt {attempt + 1}/{self.retry_count})")
                    await asyncio.sleep(5)  # 等待5秒后重试
                elif e.response.status_code in [403, 405]:  # 被拦截
                    logger.warning(f"Request blocked (status {e.response.status_code}), switching proxy...")
                    await asyncio.sleep(random.uniform(1, 3))
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {url}")
                    return None

            except Exception as e:
                if attempt < self.retry_count - 1:
                    logger.debug(f"Request failed: {url}, retrying... (attempt {attempt + 1}/{self.retry_count})")
                    await asyncio.sleep(random.uniform(1, 3))
                else:
                    logger.error(f"GET request failed after {self.retry_count} attempts: {url}, error: {e}")
                    return None

        return None

    async def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        retry: bool = True
    ) -> Optional[Dict]:
        """发送POST请求（带自动重试和反爬虫）

        Args:
            url: 请求URL
            data: 表单数据
            json: JSON数据
            retry: 是否自动重试

        Returns:
            JSON响应或None
        """
        for attempt in range(self.retry_count if retry else 1):
            try:
                # 随机延迟
                await self._random_delay()

                # 随机请求头
                headers = self._get_random_headers()

                # 随机代理
                proxy = self._get_random_proxy()

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    proxy=proxy,  # httpx 使用 proxy 而非 proxies
                    verify=False
                ) as client:
                    resp = await client.post(
                        url,
                        data=data,
                        json=json,
                        headers=headers
                    )
                    resp.raise_for_status()

                    self._request_count += 1
                    return resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limited, retrying... (attempt {attempt + 1}/{self.retry_count})")
                    await asyncio.sleep(5)
                elif e.response.status_code in [403, 405]:
                    logger.warning(f"Request blocked (status {e.response.status_code}), switching proxy...")
                    await asyncio.sleep(random.uniform(1, 3))
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {url}")
                    return None

            except Exception as e:
                if attempt < self.retry_count - 1:
                    logger.debug(f"Request failed: {url}, retrying... (attempt {attempt + 1}/{self.retry_count})")
                    await asyncio.sleep(random.uniform(1, 3))
                else:
                    logger.error(f"POST request failed after {self.retry_count} attempts: {url}, error: {e}")
                    return None

        return None

    def set_proxies(self, proxies: List[str]):
        """设置代理池

        Args:
            proxies: 代理列表，格式 ['http://ip:port', ...]
        """
        self.proxies = proxies
        logger.info(f"Proxy pool updated: {len(proxies)} proxies")

    def get_request_count(self) -> int:
        """获取请求统计"""
        return self._request_count
