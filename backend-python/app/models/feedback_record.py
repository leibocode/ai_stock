"""
反馈记录表 v2.5

记录每日持仓股的反馈分析，用于优化策略
"""

from sqlalchemy import Column, String, Float, Date, Integer, Index, DateTime, Text
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime
from app.config.database import Base


class FeedbackRecord(Base):
    """持仓反馈记录表"""
    __tablename__ = "feedback_record"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    record_date = Column(String(8), nullable=False, index=True)  # YYYYMMDD
    ts_code = Column(String(20), nullable=False, index=True)  # 股票代码
    stock_name = Column(String(50), nullable=False)  # 股票名称

    # 反馈评分
    feedback_type = Column(String(20), nullable=False)  # positive / neutral / negative
    feedback_score = Column(Integer, nullable=False)  # 0-100

    # 评分细分（共100分）
    relative_performance_score = Column(Integer, default=0)  # 相对表现40分
    tier_rank_score = Column(Integer, default=0)  # 梯队排名30分
    leader_stability_score = Column(Integer, default=0)  # 龙头稳定性20分
    sector_trend_score = Column(Integer, default=0)  # 板块趋势10分

    # 反馈原因
    feedback_reasons = Column(JSON, nullable=True)  # 反馈原因列表

    # 持仓数据快照
    holding_pct = Column(Float, nullable=True)  # 当前仓位%
    entry_price = Column(Float, nullable=True)  # 成本价
    current_price = Column(Float, nullable=True)  # 当前价
    pct_chg = Column(Float, nullable=True)  # 今日涨幅%
    profit_pct = Column(Float, nullable=True)  # 浮动盈亏%
    holding_days = Column(Integer, nullable=True)  # 持仓天数

    # 龙头属性
    yesterday_leader_score = Column(Integer, nullable=True)  # 昨日龙头评分
    today_leader_score = Column(Integer, nullable=True)  # 今日龙头评分
    leader_score_change = Column(Integer, nullable=True)  # 评分变化

    # 板块排名
    yesterday_sector_rank = Column(Integer, nullable=True)  # 昨日板块排名
    today_sector_rank = Column(Integer, nullable=True)  # 今日板块排名
    sector_rank_change = Column(Integer, nullable=True)  # 排名变化

    # 梯队表现
    same_tier_count = Column(Integer, nullable=True)  # 同梯队数
    tier_rank_in_total = Column(Integer, nullable=True)  # 梯队内排名
    sector_avg_pct_chg = Column(Float, nullable=True)  # 板块均值涨幅

    # 建议
    recommendation = Column(Text, nullable=True)  # 建议说明
    should_reduce = Column(Integer, default=0)  # 是否应该减仓 (0/1)
    should_add = Column(Integer, default=0)  # 是否应该加仓 (0/1)
    reduce_reason = Column(Text, nullable=True)  # 减仓原因
    add_reason = Column(Text, nullable=True)  # 加仓原因
    reduce_target = Column(Float, nullable=True)  # 减仓目标仓位%
    max_add = Column(Float, nullable=True)  # 最大可加仓位%

    # 市场环境快照
    emotion_phase = Column(String(30), nullable=True)  # 情绪阶段
    emotion_score = Column(Integer, nullable=True)  # 情绪评分0-100
    market_resonance_type = Column(String(20), nullable=True)  # 共振类型

    # 后续执行结果（可选，待后续补充）
    action_taken = Column(String(50), nullable=True)  # hold / reduce / add / clear
    action_date = Column(String(8), nullable=True)  # 执行日期
    action_amount = Column(Float, nullable=True)  # 执行数量或%
    action_price = Column(Float, nullable=True)  # 执行价格

    # 效果评估（待后续补充）
    result_pct = Column(Float, nullable=True)  # 执行后收益%
    result_status = Column(String(20), nullable=True)  # effective / ineffective / pending

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_record_date", "record_date"),
        Index("idx_ts_code", "ts_code"),
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_created_at", "created_at"),
        Index("idx_date_code", "record_date", "ts_code"),
    )

    class Config:
        from_attributes = True


class FeedbackStats(Base):
    """反馈统计表"""
    __tablename__ = "feedback_stats"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 统计周期
    period_start = Column(String(8), nullable=False)  # YYYYMMDD
    period_end = Column(String(8), nullable=False)  # YYYYMMDD
    period_days = Column(Integer, nullable=False)

    # 反馈分布
    positive_count = Column(Integer, default=0)  # 正反馈数
    neutral_count = Column(Integer, default=0)  # 中性反馈数
    negative_count = Column(Integer, default=0)  # 负反馈数
    positive_ratio = Column(Float, default=0.0)  # 正反馈占比%

    # 建议执行率
    reduce_suggested = Column(Integer, default=0)  # 建议减仓次数
    reduce_executed = Column(Integer, default=0)  # 实际减仓次数
    reduce_execution_rate = Column(Float, default=0.0)  # 执行率%
    reduce_avg_result = Column(Float, default=0.0)  # 平均收益%

    add_suggested = Column(Integer, default=0)  # 建议加仓次数
    add_executed = Column(Integer, default=0)  # 实际加仓次数
    add_execution_rate = Column(Float, default=0.0)  # 执行率%
    add_avg_result = Column(Float, default=0.0)  # 平均收益%

    # 反馈准确率
    positive_avg_result = Column(Float, default=0.0)  # 正反馈后平均涨幅%
    negative_avg_result = Column(Float, default=0.0)  # 负反馈后平均幅度%
    feedback_accuracy = Column(Float, default=0.0)  # 反馈准确率%

    # 持仓优化效果
    avg_holding_profit_before = Column(Float, default=0.0)  # 反馈前平均收益%
    avg_holding_profit_after = Column(Float, default=0.0)  # 反馈后平均收益%
    optimization_benefit = Column(Float, default=0.0)  # 优化收益提升%

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_period", "period_start", "period_end"),
        Index("idx_created_at", "created_at"),
    )

    class Config:
        from_attributes = True
