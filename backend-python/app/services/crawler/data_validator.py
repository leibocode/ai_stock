# -*- coding: utf-8 -*-
"""爬虫数据验证框架

提供统一的数据验证和清洗功能
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator
from loguru import logger


class DragonTigerItem(BaseModel):
    """龙虎榜数据模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    pct_chg: float = Field(..., description="涨跌幅 (%)")
    net_amount: float = Field(default=0, description="净买入额 (万元)")
    buy_amount: float = Field(default=0, description="买入额 (万元)")
    sell_amount: float = Field(default=0, description="卖出额 (万元)")
    reason: str = Field(default="", description="上榜原因")

    @validator('code')
    def validate_code(cls, v):
        """验证股票代码格式"""
        if not v or len(v) < 6:
            raise ValueError(f"Invalid stock code: {v}")
        return v

    @validator('pct_chg')
    def validate_pct_chg(cls, v):
        """验证涨跌幅范围"""
        if v < -100 or v > 100:
            raise ValueError(f"Invalid pct_chg: {v}")
        return round(v, 2)


class NorthFlowData(BaseModel):
    """北向资金数据模型"""
    hk_to_sh: float = Field(default=0, description="沪股通净流入 (亿元)")
    hk_to_sz: float = Field(default=0, description="深股通净流入 (亿元)")
    total: float = Field(default=0, description="总净流入 (亿元)")
    top_holdings: List[Dict] = Field(default_factory=list, description="持仓TOP10")

    @validator('total', pre=True, always=True)
    def calc_total(cls, v, values):
        """自动计算总值"""
        if 'hk_to_sh' in values and 'hk_to_sz' in values:
            return round(values['hk_to_sh'] + values['hk_to_sz'], 2)
        return v


class LimitUpItem(BaseModel):
    """涨跌停数据模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="价格")
    pct_chg: float = Field(..., description="涨跌幅 (%)")
    first_time: str = Field(default="15:00", description="首封时间")
    open_times: int = Field(default=0, description="开板次数")
    continuous: int = Field(default=1, description="连板数")
    reason: str = Field(default="", description="涨停原因")

    @validator('pct_chg')
    def validate_limit(cls, v):
        """验证涨跌停（±9.9% 以上）"""
        if abs(v) < 9.9:
            raise ValueError(f"Not a limit move: {v}%")
        return round(v, 2)


class SectorFlowItem(BaseModel):
    """板块资金流向数据模型"""
    code: str = Field(..., description="板块代码")
    name: str = Field(..., description="板块名称")
    pct_chg: float = Field(..., description="涨跌幅 (%)")
    main_net: float = Field(default=0, description="主力净流入 (亿元)")

    @validator('pct_chg')
    def validate_pct(cls, v):
        return round(v, 2)


class MinuteKlineItem(BaseModel):
    """分钟K线数据模型"""
    ts_code: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易时间 (YYYYMMDDHHMMSS)")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    vol: float = Field(default=0, description="成交量")

    @validator('trade_date')
    def validate_date(cls, v):
        """验证日期格式"""
        if not v or len(v) < 8:
            raise ValueError(f"Invalid trade_date: {v}")
        return v


class DataValidator:
    """统一的数据验证器"""

    @staticmethod
    def validate_dragon_tiger(items: List[Dict]) -> List[DragonTigerItem]:
        """验证龙虎榜数据"""
        validated = []
        for item in items:
            try:
                validated_item = DragonTigerItem(**item)
                validated.append(validated_item)
            except Exception as e:
                logger.warning(f"Invalid dragon tiger item {item}: {e}")
                continue
        return validated

    @staticmethod
    def validate_north_flow(data: Dict) -> Optional[NorthFlowData]:
        """验证北向资金数据"""
        try:
            return NorthFlowData(**data)
        except Exception as e:
            logger.warning(f"Invalid north flow data {data}: {e}")
            return None

    @staticmethod
    def validate_limit_up(items: List[Dict]) -> List[LimitUpItem]:
        """验证涨停数据"""
        validated = []
        for item in items:
            try:
                validated_item = LimitUpItem(**item)
                validated.append(validated_item)
            except Exception as e:
                logger.debug(f"Invalid limit up item {item}: {e}")
                continue
        return validated

    @staticmethod
    def validate_sector_flow(items: List[Dict]) -> List[SectorFlowItem]:
        """验证板块资金流向数据"""
        validated = []
        for item in items:
            try:
                validated_item = SectorFlowItem(**item)
                validated.append(validated_item)
            except Exception as e:
                logger.warning(f"Invalid sector flow item {item}: {e}")
                continue
        return validated

    @staticmethod
    def validate_minute_kline(items: List[Dict]) -> List[MinuteKlineItem]:
        """验证分钟K线数据"""
        validated = []
        for item in items:
            try:
                validated_item = MinuteKlineItem(**item)
                validated.append(validated_item)
            except Exception as e:
                logger.warning(f"Invalid kline item {item}: {e}")
                continue
        return validated

    @staticmethod
    def get_statistics(validated_items: List) -> Dict:
        """获取验证统计"""
        return {
            "total_count": len(validated_items),
            "valid_count": len(validated_items),
            "invalid_count": 0,
        }
