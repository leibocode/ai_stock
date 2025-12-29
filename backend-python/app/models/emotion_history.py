# -*- coding: utf-8 -*-
"""情绪历史数据模型

存储每日市场情绪数据，用于情绪走势图展示
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Index
from app.config.database import Base


class EmotionHistory(Base):
    """情绪历史数据表"""
    __tablename__ = "emotion_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), nullable=False, unique=True, index=True, comment="交易日期 YYYYMMDD")

    # 情绪指标
    emotion_score = Column(Integer, default=50, comment="情绪得分 0-100")
    emotion_phase = Column(String(20), default="repair", comment="情绪阶段: high_tide/warming/repair/ebb_tide/ice_point")

    # 涨跌停数据
    limit_up_count = Column(Integer, default=0, comment="涨停数")
    limit_down_count = Column(Integer, default=0, comment="跌停数")
    max_continuous = Column(Integer, default=0, comment="最高连板数")
    broken_count = Column(Integer, default=0, comment="炸板数")

    # 涨跌比
    up_count = Column(Integer, default=0, comment="上涨家数")
    down_count = Column(Integer, default=0, comment="下跌家数")
    up_ratio = Column(Float, default=50.0, comment="涨跌比 %")

    # 北向资金
    north_flow = Column(Float, default=0.0, comment="北向资金净流入 亿")

    # 连板分布 (JSON字符串)
    continuous_stats = Column(Text, default="{}", comment="连板统计 JSON")

    # 元数据
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<EmotionHistory {self.trade_date}: {self.emotion_phase} ({self.emotion_score}分)>"

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            "date": self.trade_date,
            "score": self.emotion_score,
            "phase": self.emotion_phase,
            "limit_up": self.limit_up_count,
            "limit_down": self.limit_down_count,
            "max_continuous": self.max_continuous,
            "broken_count": self.broken_count,
            "up_count": self.up_count,
            "down_count": self.down_count,
            "up_ratio": self.up_ratio,
            "north_flow": self.north_flow,
            "continuous_stats": json.loads(self.continuous_stats) if self.continuous_stats else {},
        }
