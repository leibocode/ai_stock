from sqlalchemy import Column, String, Float, Date, Index, BIGINT
from app.config.database import Base


class DailyQuote(Base):
    """日线行情表"""
    __tablename__ = "daily_quotes"

    ts_code = Column(String(20), primary_key=True)
    trade_date = Column(String(8), primary_key=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    vol = Column(BIGINT, nullable=True)
    amount = Column(Float, nullable=True)
    pct_chg = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_trade_date", "trade_date"),
        Index("idx_vol", "trade_date", "vol"),
    )

    class Config:
        from_attributes = True
