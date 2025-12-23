"""缠论相关Pydantic模型"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ChanDivergeItem(BaseModel):
    """背驰信号项"""
    ts_code: str
    name: str
    close: float
    pct_chg: float
    diverge_type: Literal["bottom", "top"] = Field(..., description="背驰类型")
    signal_strength: Optional[float] = Field(None, description="信号强度(0-100)")


class ChanBuySignalItem(BaseModel):
    """缠论买点信号项"""
    ts_code: str
    name: str
    close: float
    pct_chg: float
    buy_type: Literal["first", "second", "third"] = Field(..., description="买点类型")
    confidence: Optional[float] = Field(None, description="置信度(0-100)")


class ChanHubShakeItem(BaseModel):
    """中枢震荡股票项"""
    ts_code: str
    name: str
    close: float
    hub_high: float = Field(..., description="中枢上沿")
    hub_low: float = Field(..., description="中枢下沿")
    position: Literal["inside", "above", "below"] = Field(..., description="当前位置")


class ChanFractal(BaseModel):
    """分型"""
    type: Literal["top", "bottom", "none"] = Field(..., description="分型类型")
    index: int = Field(..., description="分型位置索引")
    high: float
    low: float


class ChanBi(BaseModel):
    """笔"""
    start_index: int
    end_index: int
    direction: Literal["up", "down"]
    high: float
    low: float


class ChanSegment(BaseModel):
    """线段"""
    start_index: int
    end_index: int
    direction: Literal["up", "down"]
    high: float
    low: float


class ChanHub(BaseModel):
    """中枢"""
    start_index: int
    end_index: int
    high: float = Field(..., description="中枢上沿")
    low: float = Field(..., description="中枢下沿")
    level: int = Field(1, description="中枢级别")


class ChanDataResponse(BaseModel):
    """单只股票缠论数据响应"""
    ts_code: str
    name: str
    fractal: Optional[ChanFractal] = Field(None, description="最新分型")
    bi: Optional[ChanBi] = Field(None, description="当前笔")
    segment: Optional[ChanSegment] = Field(None, description="当前线段")
    hub: Optional[ChanHub] = Field(None, description="当前中枢")
    buy_signals: List[str] = Field(default_factory=list, description="买点信号")
    sell_signals: List[str] = Field(default_factory=list, description="卖点信号")


class ChanDivergeResponse(BaseModel):
    """背驰信号响应"""
    date: str
    stocks: List[ChanDivergeItem]
    count: int


class ChanBuyResponse(BaseModel):
    """买点信号响应"""
    date: str
    stocks: List[ChanBuySignalItem]
    count: int


class ChanHubShakeResponse(BaseModel):
    """中枢震荡响应"""
    date: str
    stocks: List[ChanHubShakeItem]
    count: int


class CalcChanResponse(BaseModel):
    """缠论计算响应"""
    date: str
    total_stocks: int
    calculated: int
    errors: int
    message: Optional[str] = None
