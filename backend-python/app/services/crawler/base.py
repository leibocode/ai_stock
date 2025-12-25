import httpx
from typing import Optional, Dict, Any
from loguru import logger


class BaseCrawler:
    """爬虫基类"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.eastmoney.com/",
        }

    async def get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """发送GET请求

        Args:
            url: 请求URL
            params: 查询参数

        Returns:
            JSON响应或None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"GET request failed: {url}, error: {e}")
            return None

    async def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Optional[Dict]:
        """发送POST请求

        Args:
            url: 请求URL
            data: 表单数据
            json: JSON数据

        Returns:
            JSON响应或None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    data=data,
                    json=json,
                    headers=self.headers
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"POST request failed: {url}, error: {e}")
            return None
