from sqlalchemy import Column, String, Text, DateTime, Index, Integer
from sqlalchemy.sql import func
from app.config.database import Base


class ReviewRecord(Base):
    """复盘记录表"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True)
    trade_date = Column(String(10), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uk_trade_date", "trade_date", unique=True),
    )

    class Config:
        from_attributes = True
