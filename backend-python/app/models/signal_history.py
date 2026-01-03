"""
信号历史记录表 v2.5

记录所有买卖信号，用于回测和准确率统计
"""

from sqlalchemy import Column, String, Float, Date, Integer, Index, DateTime, Text
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime
from app.config.database import Base


class SignalHistory(Base):
    """买卖信号历史表"""
    __tablename__ = "signal_history"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 信号基本信息
    trade_date = Column(String(8), nullable=False, index=True)  # YYYYMMDD
    ts_code = Column(String(20), nullable=False, index=True)  # 股票代码
    stock_name = Column(String(50), nullable=False)  # 股票名称

    # 信号类型
    signal_type = Column(String(20), nullable=False)  # buy / sell
    signal_subtype = Column(String(30), nullable=False)  # chase_high / low_buy / stop_loss / tier_collapse

    # 买入信号特有
    entry_type = Column(String(20), nullable=True)  # limit_order / limit_up_queue
    entry_price_primary = Column(Float, nullable=True)  # 主入场价
    entry_price_fallback = Column(Float, nullable=True)  # 备用入场价
    entry_note = Column(Text, nullable=True)  # 入场说明
    position_limit = Column(Integer, nullable=True)  # 单票仓位%

    # 卖出信号特有
    stop_loss = Column(Float, nullable=True)  # 止损价
    stop_loss_pct = Column(Float, nullable=True)  # 止损幅度%
    exit_reason = Column(Text, nullable=True)  # 卖出原因
    urgency = Column(Integer, nullable=True)  # 紧迫性0-100

    # 信号评分
    signal_score = Column(Integer, nullable=True)  # 0-100
    signal_reasons = Column(JSON, nullable=True)  # {"reason1": "原因", ...}

    # 市场环境
    emotion_phase = Column(String(30), nullable=True)  # high_tide / ebb_tide / ...
    emotion_score = Column(Integer, nullable=True)  # 0-100
    resonance_type = Column(String(20), nullable=True)  # 止跌共振 / 突破共振 / 无共振
    resonance_score = Column(Integer, nullable=True)  # 0-100

    # 持仓信息（如果有）
    holding_profit_pct = Column(Float, nullable=True)  # 如果已持仓，当前盈亏%
    holding_days = Column(Integer, nullable=True)  # 持仓天数

    # 结果记录（后续更新）
    actual_entry_price = Column(Float, nullable=True)  # 实际成交价
    actual_entry_date = Column(String(8), nullable=True)  # 实际成交日期
    actual_exit_price = Column(Float, nullable=True)  # 实际卖出价
    actual_exit_date = Column(String(8), nullable=True)  # 实际卖出日期
    profit_loss_pct = Column(Float, nullable=True)  # 实际盈亏%
    win_status = Column(String(20), nullable=True)  # win / loss / holding / cancelled

    # 备注
    notes = Column(Text, nullable=True)  # 其他说明

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_trade_date", "trade_date"),
        Index("idx_ts_code", "ts_code"),
        Index("idx_signal_type", "signal_type"),
        Index("idx_created_at", "created_at"),
        Index("idx_trade_code", "trade_date", "ts_code"),
    )

    class Config:
        from_attributes = True


class SignalStats(Base):
    """信号准确率统计表"""
    __tablename__ = "signal_stats"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 统计周期
    period_start = Column(String(8), nullable=False)  # YYYYMMDD
    period_end = Column(String(8), nullable=False)  # YYYYMMDD
    period_days = Column(Integer, nullable=False)  # 周期天数

    # 买入信号统计
    buy_signal_total = Column(Integer, default=0)  # 总买入信号数
    buy_signal_win = Column(Integer, default=0)  # 盈利信号数
    buy_signal_loss = Column(Integer, default=0)  # 亏损信号数
    buy_signal_pending = Column(Integer, default=0)  # 未平仓
    buy_win_rate = Column(Float, default=0.0)  # 胜率%
    buy_avg_profit = Column(Float, default=0.0)  # 平均收益%

    # 买入信号细分（chase_high）
    chase_high_count = Column(Integer, default=0)
    chase_high_win_rate = Column(Float, default=0.0)
    chase_high_avg_profit = Column(Float, default=0.0)

    # 买入信号细分（low_buy）
    low_buy_count = Column(Integer, default=0)
    low_buy_win_rate = Column(Float, default=0.0)
    low_buy_avg_profit = Column(Float, default=0.0)

    # 卖出信号统计
    sell_signal_total = Column(Integer, default=0)  # 总卖出信号数
    sell_signal_executed = Column(Integer, default=0)  # 执行数
    sell_signal_accuracy = Column(Float, default=0.0)  # 准确率%

    # 卖出信号细分
    stop_loss_count = Column(Integer, default=0)
    tier_collapse_count = Column(Integer, default=0)
    below_expectation_count = Column(Integer, default=0)
    core_to_misc_count = Column(Integer, default=0)
    sector_fade_count = Column(Integer, default=0)

    # 总体绩效
    total_trades = Column(Integer, default=0)  # 总交易数
    overall_win_rate = Column(Float, default=0.0)  # 整体胜率%
    overall_avg_profit = Column(Float, default=0.0)  # 整体平均收益%
    max_drawdown = Column(Float, default=0.0)  # 最大回撤%

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_period", "period_start", "period_end"),
        Index("idx_created_at", "created_at"),
    )

    class Config:
        from_attributes = True
