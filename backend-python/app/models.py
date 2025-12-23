from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, TEXT, BIGINT, TINYINT
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Stock(Base):
    """股票基础信息"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    industry = Column(String(50))
    market = Column(String(20))
    list_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyQuote(Base):
    """日线行情"""
    __tablename__ = "daily_quotes"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False)
    open = Column(DECIMAL(10, 2))
    high = Column(DECIMAL(10, 2))
    low = Column(DECIMAL(10, 2))
    close = Column(DECIMAL(10, 2))
    vol = Column(BIGINT)
    amount = Column(DECIMAL(20, 2))
    pct_chg = Column(DECIMAL(10, 2))


class TechnicalIndicator(Base):
    """技术指标"""
    __tablename__ = "technical_indicators"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False)
    rsi_6 = Column(DECIMAL(10, 2))
    rsi_12 = Column(DECIMAL(10, 2))
    macd = Column(DECIMAL(10, 4))
    macd_signal = Column(DECIMAL(10, 4))
    macd_hist = Column(DECIMAL(10, 4))
    k = Column(DECIMAL(10, 2))
    d = Column(DECIMAL(10, 2))
    j = Column(DECIMAL(10, 2))
    boll_upper = Column(DECIMAL(10, 2))
    boll_mid = Column(DECIMAL(10, 2))
    boll_lower = Column(DECIMAL(10, 2))


class IndustryFlow(Base):
    """行业资金流向"""
    __tablename__ = "industry_flow"

    id = Column(Integer, primary_key=True)
    trade_date = Column(Date, nullable=False)
    industry = Column(String(50), nullable=False)
    net_inflow = Column(DECIMAL(20, 2))
    buy_amount = Column(DECIMAL(20, 2))
    sell_amount = Column(DECIMAL(20, 2))


class ReviewRecord(Base):
    """复盘记录"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True)
    trade_date = Column(Date, nullable=False, unique=True)
    content = Column(TEXT)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChanFractal(Base):
    """缠论分型"""
    __tablename__ = "chan_fractal"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False)
    fractal_type = Column(TINYINT, nullable=False)  # 1: 顶分型, -1: 底分型
    high = Column(DECIMAL(10, 2), nullable=False)
    low = Column(DECIMAL(10, 2), nullable=False)


class ChanBi(Base):
    """缠论笔"""
    __tablename__ = "chan_bi"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    direction = Column(TINYINT, nullable=False)  # 1: 向上笔, -1: 向下笔
    high = Column(DECIMAL(10, 2), nullable=False)
    low = Column(DECIMAL(10, 2), nullable=False)
    bi_index = Column(Integer, nullable=False)


class ChanSegment(Base):
    """缠论线段"""
    __tablename__ = "chan_segment"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    direction = Column(TINYINT, nullable=False)  # 1: 向上线段, -1: 向下线段
    high = Column(DECIMAL(10, 2), nullable=False)
    low = Column(DECIMAL(10, 2), nullable=False)
    seg_index = Column(Integer, nullable=False)


class ChanHub(Base):
    """缠论中枢"""
    __tablename__ = "chan_hub"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    zg = Column(DECIMAL(10, 2), nullable=False)
    zd = Column(DECIMAL(10, 2), nullable=False)
    gg = Column(DECIMAL(10, 2), nullable=False)
    dd = Column(DECIMAL(10, 2), nullable=False)
    hub_index = Column(Integer, nullable=False)
    level = Column(TINYINT, default=1)
