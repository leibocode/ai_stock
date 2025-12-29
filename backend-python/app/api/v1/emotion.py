# -*- coding: utf-8 -*-
"""情绪历史数据 API

提供情绪历史存储和查询功能
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

from app.config.database import get_db
from app.models.emotion_history import EmotionHistory

router = APIRouter(prefix="/emotion", tags=["情绪历史"])


def success(data: Any, msg: str = "success") -> Dict:
    return {"code": 0, "data": data, "msg": msg}


def error(msg: str, code: int = 1) -> Dict:
    return {"code": code, "data": None, "msg": msg}


@router.get("/history")
async def get_emotion_history(
    days: int = Query(7, ge=1, le=30, description="获取最近N天数据"),
    db: AsyncSession = Depends(get_db)
):
    """获取情绪历史数据

    用于前端情绪走势图展示
    """
    try:
        stmt = (
            select(EmotionHistory)
            .order_by(desc(EmotionHistory.trade_date))
            .limit(days)
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        # 按日期正序返回
        history = [r.to_dict() for r in reversed(records)]

        return success({
            "count": len(history),
            "history": history
        })
    except Exception as e:
        logger.error(f"获取情绪历史失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/latest")
async def get_latest_emotion(
    db: AsyncSession = Depends(get_db)
):
    """获取最新情绪数据"""
    try:
        stmt = (
            select(EmotionHistory)
            .order_by(desc(EmotionHistory.trade_date))
            .limit(1)
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            return success(record.to_dict())
        else:
            return success(None, "暂无数据")
    except Exception as e:
        logger.error(f"获取最新情绪失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.post("/save")
async def save_emotion_data(
    trade_date: str,
    emotion_data: Dict,
    db: AsyncSession = Depends(get_db)
):
    """保存情绪数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        emotion_data: 情绪数据字典
    """
    try:
        # 检查是否已存在
        stmt = select(EmotionHistory).where(EmotionHistory.trade_date == trade_date)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新现有记录
            existing.emotion_score = emotion_data.get("score", emotion_data.get("cycle_score", 50))
            existing.emotion_phase = emotion_data.get("phase", emotion_data.get("cycle_phase", "repair"))
            existing.limit_up_count = emotion_data.get("limit_up_count", 0)
            existing.limit_down_count = emotion_data.get("limit_down_count", 0)
            existing.max_continuous = emotion_data.get("max_continuous", 0)
            existing.broken_count = emotion_data.get("broken_count", 0)
            existing.up_count = emotion_data.get("up_count", 0)
            existing.down_count = emotion_data.get("down_count", 0)
            existing.up_ratio = emotion_data.get("up_ratio", 50.0)
            existing.north_flow = emotion_data.get("north_flow", 0.0)
            existing.continuous_stats = json.dumps(emotion_data.get("continuous_stats", {}), ensure_ascii=False)
            existing.updated_at = datetime.now()
        else:
            # 创建新记录
            record = EmotionHistory(
                trade_date=trade_date,
                emotion_score=emotion_data.get("score", emotion_data.get("cycle_score", 50)),
                emotion_phase=emotion_data.get("phase", emotion_data.get("cycle_phase", "repair")),
                limit_up_count=emotion_data.get("limit_up_count", 0),
                limit_down_count=emotion_data.get("limit_down_count", 0),
                max_continuous=emotion_data.get("max_continuous", 0),
                broken_count=emotion_data.get("broken_count", 0),
                up_count=emotion_data.get("up_count", 0),
                down_count=emotion_data.get("down_count", 0),
                up_ratio=emotion_data.get("up_ratio", 50.0),
                north_flow=emotion_data.get("north_flow", 0.0),
                continuous_stats=json.dumps(emotion_data.get("continuous_stats", {}), ensure_ascii=False),
            )
            db.add(record)

        await db.commit()
        return success({"saved": True, "date": trade_date})
    except Exception as e:
        logger.error(f"保存情绪数据失败: {e}")
        await db.rollback()
        return error(f"保存失败: {str(e)}")


async def save_emotion_from_eastmoney(
    trade_date: str,
    eastmoney_data: Dict,
    db: AsyncSession
):
    """从东财数据中提取并保存情绪历史

    在爬取东财数据后调用此函数自动保存历史
    """
    try:
        emotion_cycle = eastmoney_data.get("emotion_cycle", {})
        market_emotion = eastmoney_data.get("market_emotion", {})
        north_flow_data = eastmoney_data.get("north_flow", {})

        emotion_data = {
            "score": emotion_cycle.get("score", emotion_cycle.get("cycle_score", 50)),
            "phase": emotion_cycle.get("phase", emotion_cycle.get("cycle_phase", "repair")),
            "limit_up_count": emotion_cycle.get("limit_up_count", 0),
            "limit_down_count": emotion_cycle.get("limit_down_count", 0),
            "max_continuous": emotion_cycle.get("max_continuous", 1),
            "broken_count": 0,  # 东财数据中可能没有
            "up_count": market_emotion.get("up_count", 0),
            "down_count": market_emotion.get("down_count", 0),
            "up_ratio": market_emotion.get("up_ratio", 50.0),
            "north_flow": north_flow_data.get("total", 0.0),
            "continuous_stats": emotion_cycle.get("continuous_stats", {}),
        }

        # 检查是否已存在
        stmt = select(EmotionHistory).where(EmotionHistory.trade_date == trade_date)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.emotion_score = emotion_data["score"]
            existing.emotion_phase = emotion_data["phase"]
            existing.limit_up_count = emotion_data["limit_up_count"]
            existing.limit_down_count = emotion_data["limit_down_count"]
            existing.max_continuous = emotion_data["max_continuous"]
            existing.up_count = emotion_data["up_count"]
            existing.down_count = emotion_data["down_count"]
            existing.up_ratio = emotion_data["up_ratio"]
            existing.north_flow = emotion_data["north_flow"]
            existing.continuous_stats = json.dumps(emotion_data["continuous_stats"], ensure_ascii=False)
            existing.updated_at = datetime.now()
        else:
            record = EmotionHistory(
                trade_date=trade_date,
                emotion_score=emotion_data["score"],
                emotion_phase=emotion_data["phase"],
                limit_up_count=emotion_data["limit_up_count"],
                limit_down_count=emotion_data["limit_down_count"],
                max_continuous=emotion_data["max_continuous"],
                up_count=emotion_data["up_count"],
                down_count=emotion_data["down_count"],
                up_ratio=emotion_data["up_ratio"],
                north_flow=emotion_data["north_flow"],
                continuous_stats=json.dumps(emotion_data["continuous_stats"], ensure_ascii=False),
            )
            db.add(record)

        await db.commit()
        logger.info(f"已保存情绪历史: {trade_date} - {emotion_data['phase']} ({emotion_data['score']}分)")
        return True
    except Exception as e:
        logger.error(f"保存情绪历史失败: {e}")
        await db.rollback()
        return False
