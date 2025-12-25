from sqlalchemy import Column, String, Float, Date, Index, Integer, BIGINT
from app.config.database import Base


class ChanFractal(Base):
    """缠论分型表"""
    __tablename__ = "chan_fractal"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    trade_date = Column(String(8), nullable=False)
    fractal_type = Column(Integer, nullable=False)  # 1:顶 -1:底
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)

    __table_args__ = (
        Index("uk_code_date", "ts_code", "trade_date", unique=True),
        Index("idx_type", "ts_code", "fractal_type", "trade_date"),
    )


class ChanBi(Base):
    """缠论笔表"""
    __tablename__ = "chan_bi"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    start_date = Column(String(8), nullable=False)
    end_date = Column(String(8), nullable=False)
    direction = Column(Integer, nullable=False)  # 1:向上 -1:向下
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    bi_index = Column(Integer, nullable=False)

    __table_args__ = (
        Index("uk_code_index", "ts_code", "bi_index", unique=True),
        Index("idx_date", "ts_code", "end_date"),
    )


class ChanSegment(Base):
    """缠论线段表"""
    __tablename__ = "chan_segment"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    start_date = Column(String(8), nullable=False)
    end_date = Column(String(8), nullable=False)
    direction = Column(Integer, nullable=False)  # 1:向上 -1:向下
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    seg_index = Column(Integer, nullable=False)

    __table_args__ = (
        Index("uk_code_index", "ts_code", "seg_index", unique=True),
        Index("idx_date", "ts_code", "end_date"),
    )


class ChanHub(Base):
    """缠论中枢表"""
    __tablename__ = "chan_hub"

    id = Column(BIGINT, primary_key=True)
    ts_code = Column(String(20), nullable=False)
    start_date = Column(String(8), nullable=False)
    end_date = Column(String(8), nullable=False)
    zg = Column(Float, nullable=False)  # 中枢上沿
    zd = Column(Float, nullable=False)  # 中枢下沿
    gg = Column(Float, nullable=False)  # 中枢最高
    dd = Column(Float, nullable=False)  # 中枢最低
    hub_index = Column(Integer, nullable=False)
    level = Column(Integer, default=1)  # 中枢级别

    __table_args__ = (
        Index("uk_code_index", "ts_code", "hub_index", unique=True),
        Index("idx_date", "ts_code", "end_date"),
    )
