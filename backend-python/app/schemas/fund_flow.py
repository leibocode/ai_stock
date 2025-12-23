"""资金流向相关Pydantic模型"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class DragonTigerItem(BaseModel):
    """龙虎榜项"""
    ts_code: str
    name: str
    close: float
    pct_chg: float
    amount: float = Field(..., description="成交额")
    net_amount: Optional[float] = Field(None, description="净买入额")
    reason: Optional[str] = Field(None, description="上榜原因")


class DragonTigerResponse(BaseModel):
    """龙虎榜响应"""
    date: str
    dragon_tiger_list: List[DragonTigerItem]


class NorthFlowItem(BaseModel):
    """北向资金项"""
    ts_code: str
    name: str
    buy_amount: float = Field(..., description="买入金额")
    sell_amount: float = Field(..., description="卖出金额")
    net_amount: float = Field(..., description="净买入金额")


class NorthBuyResponse(BaseModel):
    """北向资金买入响应"""
    date: str
    north_buy_list: List[NorthFlowItem]
    total_north_flow: float = Field(..., description="北向资金净流入总额")


class MarginBuyItem(BaseModel):
    """融资买入项"""
    ts_code: str
    name: str
    margin_balance: float = Field(..., description="融资余额")
    margin_buy: float = Field(..., description="融资买入额")
    margin_repay: float = Field(..., description="融资偿还额")


class MarginBuyResponse(BaseModel):
    """融资买入响应"""
    date: str
    margin_buy_list: List[MarginBuyItem]
    total_margin_balance: float = Field(..., description="融资余额总计")


class SectorFlowItem(BaseModel):
    """板块资金流向项"""
    sector: str = Field(..., description="板块名称")
    stock_count: int = Field(..., description="股票数量")
    net_inflow: float = Field(..., description="净流入(亿)")
    main_inflow: float = Field(..., description="主力净流入(亿)")
    pct_chg: float = Field(..., description="涨跌幅(%)")


class EmotionCycleResult(BaseModel):
    """情绪周期结果"""
    phase: str = Field(..., description="当前阶段(冰点/修复/回暖/高潮/退潮)")
    score: int = Field(..., description="情绪得分(0-100)")
    strategy: str = Field(..., description="操作策略建议")
    factors: dict = Field(default_factory=dict, description="各因子得分")


class LeaderScoreItem(BaseModel):
    """龙头评分项"""
    ts_code: str
    name: str
    score: int = Field(..., description="综合评分(0-100)")
    continuous_limit: int = Field(..., description="连板数")
    seal_time: Optional[str] = Field(None, description="封板时间")
    open_count: int = Field(0, description="开板次数")
    amount: float = Field(..., description="成交额")
    turnover_rate: float = Field(..., description="换手率")
    is_leader: bool = Field(..., description="是否龙头(>=50分)")


class EastmoneyDataResponse(BaseModel):
    """东财数据响应"""
    date: str
    dragon_tiger: Optional[Any] = Field(None, description="龙虎榜")
    north_flow: Optional[Any] = Field(None, description="北向资金")
    sector_flow: Optional[Any] = Field(None, description="板块资金")
    emotion_cycle: Optional[EmotionCycleResult] = Field(None, description="情绪周期")
    leader_score: Optional[List[LeaderScoreItem]] = Field(None, description="龙头评分")
    last_update: Optional[str] = None


class EastmoneyListResponse(BaseModel):
    """东财历史列表响应"""
    total: int
    records: List[dict]
    message: Optional[str] = None


class CrawlResult(BaseModel):
    """爬虫执行结果"""
    date: str
    crawled: List[str] = Field(default_factory=list, description="已爬取模块")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    message: Optional[str] = None
