import httpx
from typing import List, Dict, Optional
from loguru import logger
from app.config import get_settings


class TushareService:
    """Tushare API 服务

    官方API文档: https://tushare.pro/
    """

    def __init__(self):
        settings = get_settings()
        self.token = settings.TUSHARE_TOKEN
        self.api_url = settings.TUSHARE_API_URL
        self.timeout = 60

    async def call(
        self,
        api_name: str,
        params: Optional[Dict] = None,
        fields: str = ""
    ) -> List[Dict]:
        """调用Tushare API

        Args:
            api_name: API名称 (如 'stock_basic', 'daily')
            params: 请求参数字典
            fields: 返回字段列表 (逗号分隔)

        Returns:
            数据列表 (字典形式)
        """
        payload = {
            "api_name": api_name,
            "token": self.token,
            "params": params or {},
            "fields": fields,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") != 0:
                logger.error(f"Tushare API error: {data.get('msg')}")
                return []

            items = data.get("data", {}).get("items", [])
            field_list = data.get("data", {}).get("fields", [])

            if not items or not field_list:
                return []

            # 将列表形式转换为字典形式
            return [dict(zip(field_list, item)) for item in items]

        except Exception as e:
            logger.error(f"Tushare API call failed: {e}")
            return []

    async def get_stock_list(
        self,
        market: str = "",
        list_status: str = "L"
    ) -> List[Dict]:
        """获取股票列表

        Args:
            market: 市场 (主板SH/主板SZ/创业板/科创板)
            list_status: 上市状态 (L=上市, D=退市, P=暂停)

        Returns:
            股票列表
        """
        params = {
            "exchange": "",
            "list_status": list_status,
        }
        if market:
            params["market"] = market

        data = await self.call(
            "stock_basic",
            params,
            "ts_code,name,industry,market,list_date"
        )

        # 过滤掉ST、科创板、北交所
        filtered = []
        for stock in data:
            name = stock.get("name", "")
            ts_code = stock.get("ts_code", "")

            # 排除ST
            if "ST" in name:
                continue

            # 排除科创板、北交所
            if ts_code.startswith(("688", "8", "4")):
                continue

            filtered.append(stock)

        return filtered

    async def get_daily(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict]:
        """获取日线行情

        Args:
            ts_code: 股票代码 (如 '000001.SZ')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 获取条数

        Returns:
            日线行情列表
        """
        from datetime import datetime, timedelta

        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (
                datetime.now() - timedelta(days=limit)
            ).strftime("%Y%m%d")

        params = {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
        }

        data = await self.call(
            "daily",
            params,
            "ts_code,trade_date,open,high,low,close,vol,amount,pct_chg"
        )

        # 按日期倒序排列
        return sorted(data, key=lambda x: x.get("trade_date", ""), reverse=True)

    async def get_limit_list(
        self,
        trade_date: str,
        limit_type: str = "U"
    ) -> List[Dict]:
        """获取涨跌停列表

        Args:
            trade_date: 交易日期 (YYYYMMDD)
            limit_type: 涨跌类型 (U=涨停, D=跌停)

        Returns:
            涨跌停列表
        """
        params = {
            "trade_date": trade_date,
            "limit_type": limit_type,
        }

        data = await self.call(
            "limit_list_d",
            params,
            "ts_code,name,close,pct_chg,fd_amount,first_time,open_times"
        )

        return data

    async def get_money_flow(
        self,
        trade_date: str
    ) -> Dict:
        """获取北向资金

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            北向资金数据
        """
        params = {"trade_date": trade_date}

        data = await self.call(
            "moneyflow_hsgt",
            params,
            "trade_date,hgt,sgt,north_money"
        )

        if not data:
            return {"hgt": 0, "sgt": 0, "north_money": 0}

        item = data[0]
        return {
            "hgt": float(item.get("hgt", 0)),
            "sgt": float(item.get("sgt", 0)),
            "north_money": float(item.get("north_money", 0)),
        }

    async def get_top_list(
        self,
        trade_date: str
    ) -> List[Dict]:
        """获取龙虎榜

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            龙虎榜列表
        """
        params = {"trade_date": trade_date}

        data = await self.call(
            "top_list",
            params,
            "ts_code,name,pct_change,l_buy,l_sell,net_amount,reason"
        )

        return data

    async def sync_stocks(self, session) -> int:
        """同步股票列表到数据库 (批量优化版)

        Args:
            session: SQLAlchemy异步session

        Returns:
            同步数量
        """
        from app.models import Stock
        from sqlalchemy import insert
        from sqlalchemy.dialects.mysql import insert as mysql_insert

        stocks = await self.get_stock_list()

        if not stocks:
            logger.warning("No stocks fetched from Tushare")
            return 0

        # 批量插入优化：每500条一批
        BATCH_SIZE = 500
        total_synced = 0

        for i in range(0, len(stocks), BATCH_SIZE):
            batch = stocks[i:i + BATCH_SIZE]

            # 构建批量插入数据
            values_list = [
                {
                    "ts_code": s.get("ts_code"),
                    "name": s.get("name"),
                    "industry": s.get("industry"),
                    "market": s.get("market"),
                    "list_date": s.get("list_date"),
                }
                for s in batch
            ]

            # MySQL批量upsert
            stmt = mysql_insert(Stock).values(values_list)
            stmt = stmt.on_duplicate_key_update(
                name=stmt.inserted.name,
                industry=stmt.inserted.industry,
            )
            await session.execute(stmt)
            total_synced += len(batch)

        await session.commit()
        logger.info(f"Synced {total_synced} stocks in batches")
        return total_synced
