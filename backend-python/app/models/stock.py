from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Index
from sqlalchemy.sql import func
from app.config.database import Base


class Stock(Base):
    """股票基础信息表"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    industry = Column(String(50), nullable=True)
    market = Column(String(20), nullable=True)
    list_date = Column(String(8), nullable=True)
    created_at = Column(DateTime, nullable=True, server_default=func.now())

    class Config:
        from_attributes = True
