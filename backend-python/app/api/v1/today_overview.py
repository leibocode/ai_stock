# -*- coding: utf-8 -*-
"""今日决策综合接口 - 整合所有市场情绪和决策支持数据"""

from fastapi import APIRouter, Query
from loguru import logger
from datetime import datetime, timedelta
import json

from app.schemas import success, error
from app.services.crawler.kaipanla import KaipanlaAppCrawler
from app.services.crawler.kaipanla_extended import KaipanlaAppCrawlerExtended

router = APIRouter(prefix="/today-overview", tags=["今日决策"])

# 全局爬虫实例
_crawler = None
_crawler_extended = None

def get_crawler():
    """获取爬虫实例"""
    global _crawler
    if _crawler is None:
        _crawler = KaipanlaAppCrawler()
    return _crawler

def get_crawler_extended():
    """获取扩展爬虫实例"""
    global _crawler_extended
    if _crawler_extended is None:
        base_crawler = get_crawler()
        _crawler_extended = KaipanlaAppCrawlerExtended(base_crawler.api)
        # 绑定爬虫方法
        _crawler_extended.crawl_market_emotion = base_crawler.crawl_market_emotion
    return _crawler_extended


@router.get("/summary")
async def get_today_summary(
    date: str = Query(None, description="日期 YYYY-MM-DD，默认昨天")
):
    """获取今日决策 - 完整概览

    返回：
    - 情绪周期 (强度、阶段、趋势)
    - 涨跌停统计 (涨停数、跌停数、破板数)
    - 连板梯队 (一板、二板、三板、高度板)
    - 大幅回撤 (个数和TOP股票)
    - 龙头评分 (评分、等级、分析)
    - 情绪走势 (近7日数据)
    - 操作建议 (仓位、操作、风险等级)
    """
    try:
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        crawler = get_crawler_extended()

        # 获取完整数据
        decision_data = crawler.get_today_decision_data(date)

        if not decision_data:
            return error("无法获取数据")

        # 格式化响应
        return success({
            "date": date,
            "emotion_cycle": {
                "score": decision_data['emotion_cycle']['score'],
                "phase": decision_data['emotion_cycle']['phase'],
                "phase_name": _get_phase_name(decision_data['emotion_cycle']['phase']),
                "sign": decision_data['emotion_cycle']['sign'],
            },
            "market_stats": decision_data['market_stats'],
            "lianban_info": decision_data['lianban_info'],
            "withdrawal_warning": decision_data['withdrawal_warning'],
            "leader_score": decision_data['leader_score'],
            "emotion_trend": decision_data['emotion_trend'],
            "key_metrics": decision_data['key_metrics'],
            "operation_advice": decision_data['operation_advice'],
        })

    except Exception as e:
        logger.error(f"获取今日决策数据失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/emotion-trend")
async def get_emotion_trend(
    date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    days: int = Query(7, description="统计天数，默认7天")
):
    """获取情绪走势数据（用于图表）

    返回：
    - dates: 日期数组
    - emotion_scores: 情绪得分数组
    - limit_up_counts: 涨停数数组
    - limit_down_counts: 跌停数数组
    - broken_counts: 破板数数组

    前端可直接用于绘制组合图表
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        crawler = get_crawler_extended()
        trend_data = crawler.get_market_emotion_trend(date)

        return success({
            "date": date,
            "days": days,
            "dates": trend_data.get('dates', []),
            "emotion_scores": trend_data.get('emotion_scores', []),
            "limit_up_counts": trend_data.get('limit_up_counts', []),
            "limit_down_counts": trend_data.get('limit_down_counts', []),
            "broken_counts": trend_data.get('broken_counts', []),
        })

    except Exception as e:
        logger.error(f"获取情绪走势失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/leader-analysis")
async def get_leader_analysis(
    date: str = Query(None, description="日期 YYYY-MM-DD")
):
    """获取龙头评分分析

    用于展示：
    - 龙头热度评分
    - 龙头等级
    - 详细分析说明
    - 操作建议
    """
    try:
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        base_crawler = get_crawler()
        emotion_data = base_crawler.crawl_market_emotion(date)

        crawler_extended = get_crawler_extended()
        leader_score = crawler_extended.calculate_leader_score(emotion_data, {})

        return success({
            "date": date,
            "score": leader_score.get('total_score', 0),
            "level": leader_score.get('level', '☆☆☆☆☆'),
            "analysis": leader_score.get('analysis', []),
            "recommendation": leader_score.get('recommendation', ''),
        })

    except Exception as e:
        logger.error(f"获取龙头分析失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/withdrawal-warning")
async def get_withdrawal_warning(
    date: str = Query(None, description="日期 YYYY-MM-DD"),
    limit: int = Query(10, description="返回股票数量，默认10")
):
    """获取大幅回撤预警

    用于展示：
    - 大幅回撤股票个数
    - 回撤最多的TOP股票
    - 代码、名称、回撤幅度、振幅等
    """
    try:
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        crawler_extended = get_crawler_extended()
        withdrawal_list = crawler_extended.get_sharp_withdrawal_detail(date)

        return success({
            "date": date,
            "total_count": len(withdrawal_list),
            "stocks": withdrawal_list[:limit] if withdrawal_list else [],
            "warning": "关注大幅回撤，可能预示风险" if len(withdrawal_list) > 5 else "回撤股票较少，市场相对稳定",
        })

    except Exception as e:
        logger.error(f"获取回撤预警失败: {e}")
        return error(f"获取失败: {str(e)}")


@router.get("/operation-advice")
async def get_operation_advice(
    date: str = Query(None, description="日期 YYYY-MM-DD")
):
    """获取操作建议

    根据当前市场情绪，提供：
    - 建议仓位
    - 操作策略
    - 重点关注
    - 风险等级
    """
    try:
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        base_crawler = get_crawler()
        emotion_data = base_crawler.crawl_market_emotion(date)

        crawler_extended = get_crawler_extended()
        advice = crawler_extended._generate_advice(emotion_data)

        return success({
            "date": date,
            "emotion_phase": emotion_data.get('emotion_phase', 'repair'),
            "emotion_phase_name": _get_phase_name(emotion_data.get('emotion_phase', 'repair')),
            "position": advice.get('position', '40-60%'),
            "action": advice.get('action', '观望'),
            "focus": advice.get('focus', ''),
            "risk": advice.get('risk', '中等风险'),
        })

    except Exception as e:
        logger.error(f"获取操作建议失败: {e}")
        return error(f"获取失败: {str(e)}")


# ==================== 辅助函数 ====================

def _get_phase_name(phase: str) -> str:
    """将英文阶段转换为中文"""
    phase_names = {
        'high_tide': '高潮期',
        'warming': '回暖期',
        'repair': '修复期',
        'ebb_tide': '退潮期',
        'ice_point': '冰点期',
    }
    return phase_names.get(phase, '未知')
