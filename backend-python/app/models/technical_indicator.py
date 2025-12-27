from sqlalchemy import Column, String, Float, Date, Index, BIGINT
from app.config.database import Base


class TechnicalIndicator(Base):
    """技术指标表"""
    __tablename__ = "technical_indicators"

    ts_code = Column(String(20), primary_key=True)
    trade_date = Column(String(8), primary_key=True)
    rsi_6 = Column(Float, nullable=True)
    rsi_12 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    k = Column(Float, nullable=True)
    d = Column(Float, nullable=True)
    j = Column(Float, nullable=True)
    boll_upper = Column(Float, nullable=True)
    boll_mid = Column(Float, nullable=True)
    boll_lower = Column(Float, nullable=True)

    __table_args__ = (
        Index("uk_code_date", "ts_code", "trade_date", unique=True),
        Index("idx_rsi", "trade_date", "rsi_6"),
    )

    class Config:
        from_attributes = True
