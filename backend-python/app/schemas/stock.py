"""股票相关Pydantic模型"""
from typing import Optional, List
from pydantic import BaseModel, Field


class StockBase(BaseModel):
    """股票基础信息"""
    ts_code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")


class DailyQuoteBase(BaseModel):
    """日线行情基础数据"""
    ts_code: str
    name: str
    close: float = Field(..., description="收盘价")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    vol: float = Field(..., description="成交量(手)")
    amount: float = Field(..., description="成交额(千元)")
    pct_chg: float = Field(..., description="涨跌幅(%)")


class VolumeTopItem(DailyQuoteBase):
    """成交额排行项"""
    industry: Optional[str] = None


class LimitUpItem(DailyQuoteBase):
    """涨停股票项"""
    industry: Optional[str] = None


class LimitDownItem(DailyQuoteBase):
    """跌停股票项"""
    industry: Optional[str] = None


class OversoldItem(BaseModel):
    """超卖股票项"""
    ts_code: str
    name: str
    industry: Optional[str] = None
    close: float
    pct_chg: float
    rsi_6: float = Field(..., description="RSI(6)")
    rsi_12: float = Field(..., description="RSI(12)")


class KdjBottomItem(BaseModel):
    """KDJ底部股票项"""
    ts_code: str
    name: str
    close: float
    pct_chg: float
    k: float = Field(..., description="K值")
    d: float = Field(..., description="D值")
    j: float = Field(..., description="J值")


class MacdGoldenItem(BaseModel):
    """MACD金叉股票项"""
    ts_code: str
    name: str
    close: float
    pct_chg: float
    macd: float
    dif: float
    dea: float


class BreakoutItem(BaseModel):
    """突破形态股票项"""
    ts_code: str
    name: str
    close: float
    high: float
    history_high: float
    breakout_pct: float = Field(..., description="突破幅度(%)")
    pct_chg: float


class GapUpItem(BaseModel):
    """跳空高开股票项"""
    ts_code: str
    name: str
    yesterday_high: float
    today_open: float
    today_close: float
    gap_size: float
    gap_pct: float = Field(..., description="跳空幅度(%)")
    pct_chg: float


class GapDownItem(BaseModel):
    """跳空低开股票项"""
    ts_code: str
    name: str
    yesterday_low: float
    today_open: float
    today_close: float
    gap_size: float
    gap_pct: float = Field(..., description="跳空幅度(%)")
    pct_chg: float


class IndustryHotItem(BaseModel):
    """热门行业项"""
    industry: str
    stock_count: int
    total_amount: float = Field(..., description="总成交额")
    avg_pct_chg: float = Field(..., description="平均涨跌幅")


class NorthBuyItem(BaseModel):
    """北向资金买入项"""
    ts_code: str
    name: str
    buy_amount: float = Field(..., description="买入金额")
    net_amount: float = Field(..., description="净买入金额")


class ReviewRecord(BaseModel):
    """复盘记录"""
    id: Optional[int] = None
    trade_date: str
    content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ReviewHistoryItem(BaseModel):
    """复盘历史项"""
    trade_date: str
    preview: str = Field(..., description="内容预览(前50字)")


# 响应数据结构
class LimitUpStats(BaseModel):
    """涨停统计"""
    total_count: int
    avg_amount: Optional[float] = None
    max_vol: Optional[float] = None


class LimitUpResponse(BaseModel):
    """涨停列表响应"""
    date: str
    limit_up_list: List[LimitUpItem]
    stats: LimitUpStats


class LimitDownStats(BaseModel):
    """跌停统计"""
    total_count: int
    avg_amount: Optional[float] = None
    min_price: Optional[float] = None


class LimitDownResponse(BaseModel):
    """跌停列表响应"""
    date: str
    limit_down_list: List[LimitDownItem]
    stats: LimitDownStats


class BreakoutResponse(BaseModel):
    """突破形态响应"""
    date: str
    lookback_days: int
    breakout_stocks: List[BreakoutItem]


class GapUpResponse(BaseModel):
    """跳空高开响应"""
    date: str
    gap_up_list: List[GapUpItem]


class GapDownResponse(BaseModel):
    """跳空低开响应"""
    date: str
    gap_down_list: List[GapDownItem]


class MarketStats(BaseModel):
    """市场统计"""
    date: str
    total_stocks: int = Field(..., description="股票总数")
    up_count: int = Field(..., description="上涨数")
    down_count: int = Field(..., description="下跌数")
    flat_count: int = Field(..., description="平盘数")
    limit_up_count: int = Field(..., description="涨停数")
    limit_down_count: int = Field(..., description="跌停数")
    total_amount: float = Field(..., description="总成交额(亿)")
    avg_pct_chg: float = Field(..., description="平均涨跌幅")


class MarketIndexItem(BaseModel):
    """市场指数项"""
    ts_code: str
    name: str
    close: float
    pct_chg: float
    vol: float
    amount: float
