"""
策略API v2.5

提供策略推荐、信号生成、仓位管理、反馈分析等完整接口。

核心流程：
1. 情绪周期分析 → 判断市场阶段
2. 共振检测 → 识别入场机会
3. 信号生成 → 生成买卖信号
4. 仓位管理 → 计算动态仓位
5. 反馈分析 → 评估持仓表现（NEW v2.5）
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from app.services.analyzers import (
    detect_resonance,
    ResonanceDetector,
    generate_buy_signals,
    generate_sell_signals,
    SignalGenerator,
    calc_sector_score,
    SectorStrengthAnalyzer,
    CoreIdentifier,
    calc_phase,
    EmotionPhaseAnalyzer,
    PHASE_DESCRIPTIONS,
    PositionManager,
)
from app.services.analyzers.feedback_analyzer import FeedbackAnalyzer

router = APIRouter(prefix="/strategy", tags=["策略"])


def success(data: Any, msg: str = "success") -> Dict:
    """成功响应"""
    return {"code": 0, "data": data, "msg": msg}


def error(msg: str, code: int = -1) -> Dict:
    """错误响应"""
    return {"code": code, "data": None, "msg": msg}


@router.get("/recommendation")
async def get_recommendation(date: Optional[str] = Query(None)):
    """
    获取今日策略推荐

    综合市场环境、情绪周期、共振信号生成操作建议
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库/缓存获取市场数据
        # 这里提供示例结构
        market_data = {
            "trade_date": trade_date,
            "box_pos": 50,
            "pct_chg": 0,
            "north_flow": 0,
            "north_flow_avg_5d": 0,
            "up_sectors": 0,
            "down_sectors": 0,
            "vol_ratio": 1.0,
            "emotion_score": 50,
            "resonance_score": 0,
            "phase": "repair",
            "feedback_type": "neutral",
        }

        # 共振检测
        detector = ResonanceDetector()
        resonance = detector.detect_from_market_data(market_data)

        # 情绪阶段
        analyzer = EmotionPhaseAnalyzer()
        emotion = analyzer.analyze({
            "limit_up_count": 0,
            "max_continuous": 0,
            "up_ratio": 0.5,
            "broken_count": 0,
            "total_limit_up_attempt": 0,
            "yesterday_score": 50
        })

        # 仓位建议
        pm = PositionManager()
        position = pm.calculate({
            "phase": emotion.phase,
            "resonance_type": resonance.resonance_type,
            "emotion_score": emotion.score,
            "feedback_type": market_data.get("feedback_type", "neutral")
        })

        return success({
            "trade_date": trade_date,
            "resonance": {
                "type": resonance.resonance_type,
                "score": resonance.score,
                "reasons": resonance.reasons
            },
            "emotion": {
                "phase": emotion.phase,
                "score": emotion.score,
                "description": emotion.description,
                "strategy": emotion.strategy
            },
            "position": position,
            "summary": _generate_summary(resonance, emotion, position)
        })
    except Exception as e:
        logger.error(f"获取策略推荐失败: {e}")
        return error(str(e))


def _generate_summary(resonance, emotion, position) -> str:
    """生成策略摘要"""
    parts = []

    # 共振信号
    if resonance.resonance_type != "无共振":
        parts.append(f"检测到{resonance.resonance_type}（{resonance.score}分）")
    else:
        parts.append("无明显共振信号")

    # 情绪阶段
    parts.append(f"情绪处于{emotion.phase}（{emotion.score}分）")

    # 仓位建议
    parts.append(f"建议最大仓位{position['max_position']}%，单票{position['single_position']}%")

    return "；".join(parts)


@router.get("/index-environment")
async def get_index_environment(date: Optional[str] = Query(None)):
    """
    获取指数环境分析

    包含箱体位置、量能、北向资金等
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取指数数据
        return success({
            "trade_date": trade_date,
            "sh_index": {
                "close": 0,
                "pct_chg": 0,
                "box_pos": 50,
                "vol_ratio": 1.0
            },
            "north_flow": {
                "today": 0,
                "avg_5d": 0,
                "ratio": 1.0
            },
            "sector_summary": {
                "up_count": 0,
                "down_count": 0,
                "up_ratio": 0.5
            }
        })
    except Exception as e:
        logger.error(f"获取指数环境失败: {e}")
        return error(str(e))


@router.get("/feedback")
async def get_feedback(date: Optional[str] = Query(None)):
    """
    获取市场反馈分析

    包含昨涨停溢价、高标追踪、封板效率
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库计算反馈数据
        return success({
            "trade_date": trade_date,
            "feedback_type": "neutral",  # positive / negative / neutral
            "yesterday_limit_up": {
                "count": 0,
                "avg_premium": 0,
                "success_rate": 0
            },
            "high_level": {
                "max_continuous": 0,
                "sealed_rate": 0
            },
            "seal_efficiency": {
                "avg_seal_time": "10:00",
                "one_shot_rate": 0
            }
        })
    except Exception as e:
        logger.error(f"获取反馈分析失败: {e}")
        return error(str(e))


@router.get("/sector-strength")
async def get_sector_strength(
    limit: int = Query(20, ge=1, le=100),
    date: Optional[str] = Query(None)
):
    """
    获取板块强度排名

    使用3日/5日/7日涨幅+资金流入综合排名
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取板块数据
        sectors = []

        if sectors:
            result = calc_sector_score(sectors)
            return success({
                "trade_date": trade_date,
                "sectors": result[:limit],
                "total_count": len(result)
            })
        else:
            return success({
                "trade_date": trade_date,
                "sectors": [],
                "total_count": 0,
                "message": "暂无板块数据"
            })
    except Exception as e:
        logger.error(f"获取板块强度失败: {e}")
        return error(str(e))


@router.get("/signals")
async def get_signals(
    signal_type: Optional[str] = Query(None, description="buy/sell"),
    date: Optional[str] = Query(None)
):
    """
    获取买卖信号

    根据当前市场环境生成买入/卖出信号
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取市场数据
        market_data = {
            "emotion_score": 50,
            "resonance_score": 0,
            "sectors": []
        }

        result = {
            "trade_date": trade_date,
            "buy_signals": [],
            "sell_signals": []
        }

        if signal_type in (None, "buy"):
            buy_result = generate_buy_signals(market_data)
            result["buy_signals"] = buy_result.get("signals", [])
            result["buy_mode"] = buy_result.get("mode")
            result["buy_mode_reason"] = buy_result.get("mode_reason")

        if signal_type in (None, "sell"):
            # 需要持仓数据才能生成卖出信号
            result["sell_signals"] = []
            result["sell_note"] = "需要持仓数据才能生成卖出信号"

        return success(result)
    except Exception as e:
        logger.error(f"获取信号失败: {e}")
        return error(str(e))


@router.post("/signals/sell")
async def check_sell_signals(holding: Dict):
    """
    检查卖出信号

    根据持仓数据检查是否需要卖出
    """
    try:
        # TODO: 从数据库获取市场数据
        market_data = {
            "sector_avg_pct_chg": 0,
            "same_tier_stocks": []
        }

        signals = generate_sell_signals(holding, market_data)

        return success({
            "holding_code": holding.get("code"),
            "signals": signals,
            "has_sell_signal": len(signals) > 0,
            "most_urgent": signals[0] if signals else None
        })
    except Exception as e:
        logger.error(f"检查卖出信号失败: {e}")
        return error(str(e))


@router.get("/signal-stats")
async def get_signal_stats(days: int = Query(30, ge=1, le=365)):
    """
    获取信号准确率统计

    统计历史信号的胜率和收益
    """
    try:
        # TODO: 从数据库统计历史信号
        return success({
            "period_days": days,
            "buy_signals": {
                "total": 0,
                "win_count": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "by_type": {
                    "chase_high": {"count": 0, "win_rate": 0, "avg_profit": 0},
                    "low_buy": {"count": 0, "win_rate": 0, "avg_profit": 0}
                }
            },
            "sell_signals": {
                "total": 0,
                "accuracy": 0,
                "by_type": {
                    "stop_loss": {"count": 0, "accuracy": 0},
                    "below_expectation": {"count": 0, "accuracy": 0},
                    "tier_collapse": {"count": 0, "accuracy": 0}
                }
            }
        })
    except Exception as e:
        logger.error(f"获取信号统计失败: {e}")
        return error(str(e))


@router.get("/emotion")
async def get_emotion(date: Optional[str] = Query(None)):
    """
    获取市场情绪

    返回情绪阶段、评分和策略建议
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取情绪数据
        emotion_data = {
            "limit_up_count": 0,
            "max_continuous": 0,
            "up_ratio": 0.5,
            "broken_count": 0,
            "total_limit_up_attempt": 0,
            "yesterday_score": 50
        }

        analyzer = EmotionPhaseAnalyzer()
        result = analyzer.analyze(emotion_data)

        return success({
            "trade_date": trade_date,
            "phase": result.phase,
            "score": result.score,
            "description": result.description,
            "strategy": result.strategy,
            "details": result.details,
            "phase_descriptions": PHASE_DESCRIPTIONS
        })
    except Exception as e:
        logger.error(f"获取市场情绪失败: {e}")
        return error(str(e))


@router.get("/resonance")
async def get_resonance(date: Optional[str] = Query(None)):
    """
    获取共振信号

    检测止跌共振和突破共振
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取市场数据
        detector = ResonanceDetector()
        result = detector.detect(
            box_pos=50,
            pct_chg=0,
            north_flow=0,
            north_flow_avg_5d=0,
            up_sectors=0,
            down_sectors=0,
            vol_ratio=1.0,
            emotion_score=50
        )

        return success({
            "trade_date": trade_date,
            "resonance_type": result.resonance_type,
            "score": result.score,
            "reasons": result.reasons,
            "is_resonance": result.resonance_type != "无共振"
        })
    except Exception as e:
        logger.error(f"获取共振信号失败: {e}")
        return error(str(e))


@router.get("/position")
async def get_position_advice(date: Optional[str] = Query(None)):
    """
    获取仓位建议

    根据市场环境动态计算仓位
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取市场数据
        pm = PositionManager()
        result = pm.calculate({
            "phase": "repair",
            "resonance_type": "无共振",
            "emotion_score": 50,
            "feedback_type": "neutral"
        })

        return success({
            "trade_date": trade_date,
            **result
        })
    except Exception as e:
        logger.error(f"获取仓位建议失败: {e}")
        return error(str(e))


@router.post("/position/check-add")
async def check_add_position(
    current_position: float = Query(..., description="当前仓位%"),
    market: Optional[Dict] = None
):
    """
    检查是否应该加仓
    """
    try:
        pm = PositionManager()
        market_data = market or {
            "phase": "repair",
            "resonance_type": "无共振",
            "emotion_score": 50
        }

        result = pm.should_add_position(current_position, market_data)
        return success(result)
    except Exception as e:
        logger.error(f"检查加仓建议失败: {e}")
        return error(str(e))


@router.post("/position/check-reduce")
async def check_reduce_position(
    current_position: float = Query(..., description="当前仓位%"),
    market: Optional[Dict] = None
):
    """
    检查是否应该减仓
    """
    try:
        pm = PositionManager()
        market_data = market or {
            "phase": "repair",
            "resonance_type": "无共振",
            "emotion_score": 50,
            "feedback_type": "neutral"
        }

        result = pm.should_reduce_position(current_position, market_data)
        return success(result)
    except Exception as e:
        logger.error(f"检查减仓建议失败: {e}")
        return error(str(e))


@router.get("/core-stocks")
async def get_core_stocks(
    sector: Optional[str] = Query(None, description="板块名称"),
    date: Optional[str] = Query(None)
):
    """
    获取核心股识别结果
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # TODO: 从数据库获取板块和股票数据
        identifier = CoreIdentifier()

        return success({
            "trade_date": trade_date,
            "sector": sector,
            "core_stocks": [],
            "semi_core_stocks": [],
            "misc_stocks": [],
            "message": "需要提供板块数据"
        })
    except Exception as e:
        logger.error(f"获取核心股失败: {e}")
        return error(str(e))


@router.post("/core-stocks/identify")
async def identify_core_stock(stock: Dict, sector_data: Dict):
    """
    识别单只股票的核心类型
    """
    try:
        identifier = CoreIdentifier()
        result = identifier.identify_core_type(stock, sector_data)

        return success({
            "stock": stock.get("code"),
            "name": stock.get("name"),
            **result
        })
    except Exception as e:
        logger.error(f"识别核心股失败: {e}")
        return error(str(e))


# ==================== v2.5新增：反馈分析模块 ====================

@router.post("/feedback/analyze-holding")
async def analyze_holding_feedback(holding: Dict, market_data: Dict):
    """
    分析持仓股的反馈信号（v2.5新增）

    输入：
    - holding: 持仓股数据
        - code: 股票代码
        - name: 股票名称
        - pct_chg: 今日涨幅
        - profit_pct: 浮动盈亏%
        - yesterday_leader_score: 昨日龙头评分
        - today_leader_score: 今日龙头评分
        - yesterday_sector_rank: 昨日板块排名
        - today_sector_rank: 今日板块排名

    - market_data: 市场数据
        - sector_avg_pct_chg: 板块平均涨幅
        - same_tier_stocks: 同梯队股票列表

    返回：
    - feedback_type: 正反馈/中性反馈/负反馈
    - feedback_score: 反馈评分0-100
    - recommendation: 建议说明
    - should_reduce: 是否应该减仓
    - should_add: 是否应该加仓
    """
    try:
        analyzer = FeedbackAnalyzer()
        feedback_result = analyzer.analyze(holding, market_data)

        # 获取仓位决策
        current_pos = holding.get('position_pct', 10)
        max_pos = market_data.get('max_position', 50)

        reduce_decision = analyzer.should_reduce_position(holding, market_data, current_pos)
        add_decision = analyzer.should_add_position(holding, market_data, current_pos, max_pos)

        return success({
            "code": holding.get('code'),
            "name": holding.get('name'),
            "feedback": {
                "type": feedback_result.feedback_type,
                "score": feedback_result.score,
                "reasons": feedback_result.reasons,
                "recommendation": feedback_result.recommendation,
                "urgency": feedback_result.urgency
            },
            "position_action": {
                "should_reduce": reduce_decision['should_reduce'],
                "should_add": add_decision['should_add'],
                "reduce_target": reduce_decision.get('target_position'),
                "max_add": add_decision.get('max_add'),
                "reduce_reason": reduce_decision['reason'],
                "add_reason": add_decision['reason']
            }
        }, "反馈分析完成")
    except Exception as e:
        logger.error(f"反馈分析失败: {e}")
        return error(str(e))


@router.post("/feedback/batch-analyze")
async def batch_analyze_holdings_feedback(
    holdings: List[Dict],
    market_data: Dict
):
    """
    批量分析所有持仓的反馈信号（v2.5新增）

    返回：
    - positive: 正反馈持仓列表
    - neutral: 中性反馈持仓列表
    - negative: 负反馈持仓列表
    - summary: 统计摘要
    """
    try:
        analyzer = FeedbackAnalyzer()
        feedback_map = analyzer.batch_analyze(holdings, market_data)

        summary = {
            "total_holdings": len(holdings),
            "positive_count": len(feedback_map['positive']),
            "neutral_count": len(feedback_map['neutral']),
            "negative_count": len(feedback_map['negative']),
            "positive_ratio": len(feedback_map['positive']) / len(holdings) if holdings else 0,
            "action_required": len(feedback_map['positive']) + len(feedback_map['negative']) > 0
        }

        # 按紧迫性排序负反馈
        feedback_map['negative'].sort(key=lambda x: x.get('urgency', 0), reverse=True)

        return success({
            "positive": feedback_map['positive'],
            "neutral": feedback_map['neutral'],
            "negative": feedback_map['negative'],
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }, "批量反馈分析完成")
    except Exception as e:
        logger.error(f"批量反馈分析失败: {e}")
        return error(str(e))


@router.post("/full-analysis")
async def full_strategy_analysis(
    emotion_data: Dict,
    market_data: Dict,
    holdings: List[Dict] = None,
    date: Optional[str] = Query(None)
):
    """
    完整策略分析（一站式决策，v2.5整合版）

    输入：
    - emotion_data: 情绪周期数据
    - market_data: 市场数据
    - holdings: 持仓列表（可选）
    - date: 交易日期（可选）

    返回：完整的市场分析、信号生成、仓位建议、持仓分析、行动计划
    """
    try:
        trade_date = date or datetime.now().strftime("%Y-%m-%d")

        # 1. 情绪周期分析
        emotion_analyzer = EmotionPhaseAnalyzer()
        emotion_result = emotion_analyzer.analyze(emotion_data)

        # 2. 共振检测
        detector = ResonanceDetector()
        resonance_result = detector.detect(
            market_data.get('box_pos', 50),
            market_data.get('pct_chg', 0),
            market_data.get('north_flow', 0),
            market_data.get('north_flow_avg_5d', 0),
            market_data.get('up_sectors', 0),
            market_data.get('down_sectors', 0),
            market_data.get('vol_ratio', 1.0),
            emotion_result.score
        )

        # 3. 信号生成
        market_with_emotion = {**market_data, "emotion_score": emotion_result.score, "resonance_score": resonance_result.score}
        signal_gen = SignalGenerator()
        buy_result = signal_gen.generate_buy(market_with_emotion)

        # 4. 仓位管理
        market_with_resonance = {
            **market_with_emotion,
            "phase": emotion_result.phase,
            "resonance_type": resonance_result.resonance_type,
            "feedback_type": "neutral"
        }
        pm = PositionManager()
        position_advice = pm.get_advice(market_with_resonance)

        # 5. 反馈分析（仅当有持仓时）
        holdings_feedback = {}
        if holdings:
            feedback_analyzer = FeedbackAnalyzer()
            holdings_feedback = feedback_analyzer.batch_analyze(holdings, market_with_emotion)

        return success({
            "trade_date": trade_date,
            "market_analysis": {
                "emotion": {
                    "phase": emotion_result.phase,
                    "score": emotion_result.score,
                    "description": emotion_result.description,
                    "strategy": emotion_result.strategy
                },
                "resonance": {
                    "type": resonance_result.resonance_type,
                    "score": resonance_result.score,
                    "is_resonance": resonance_result.resonance_type != "无共振"
                }
            },
            "buy_signals": {
                "mode": buy_result.mode,
                "mode_reason": buy_result.mode_reason,
                "signal_count": len(buy_result.signals),
                "signals": [
                    {
                        "code": s.stock.get('code'),
                        "name": s.stock.get('name'),
                        "type": s.signal_type,
                        "score": s.score,
                        "entry_price": s.entry_price_primary
                    }
                    for s in buy_result.signals
                ]
            },
            "position_advice": {
                "max_position": position_advice.max_position,
                "single_position": position_advice.single_position,
                "max_stocks": position_advice.max_stocks,
                "adjustments": position_advice.adjustments
            },
            "holdings_feedback": holdings_feedback if holdings else None,
            "action_plan": _generate_action_plan(
                emotion_result.phase,
                buy_result.mode,
                position_advice,
                holdings_feedback if holdings else {}
            )
        }, "完整策略分析完成")

    except Exception as e:
        logger.error(f"完整分析失败: {e}")
        return error(str(e))


def _generate_action_plan(phase: str, mode: str, position_advice, holdings_feedback: Dict) -> Dict:
    """生成详细的操作建议"""
    actions = []

    # 基于情绪阶段的建议
    phase_actions = {
        "high_tide": "✅ 高潮期：追踪龙头股，关注补涨机会，保持高仓位",
        "high_tide_fading": "⚠️ 衰退期：开始减仓，锁定利润，警惕高位风险",
        "warming": "📈 回暖期：积极参与首板和二板，关注弱转强",
        "repair": "🔧 修复期：选择性参与强势题材，控制仓位",
        "ebb_tide": "📉 退潮期：减少操作，等待明确信号，轻仓观望",
        "ice_point": "❄️ 冰点期：等待企稳，可小仓试错，分批建仓"
    }
    if phase in phase_actions:
        actions.append(phase_actions[phase])

    # 基于买入模式的建议
    mode_actions = {
        "chase_high": "🎯 追高模式：可积极参与龙头股，把握涨停机会",
        "low_buy": "💰 低吸模式：关注超跌品种，耐心等待买点",
        "wait": "⏸️ 观望模式：等待信号确认，不急于操作"
    }
    if mode in mode_actions:
        actions.append(mode_actions[mode])

    # 基于持仓反馈的建议
    if holdings_feedback:
        positive_count = len(holdings_feedback.get('positive', []))
        negative_count = len(holdings_feedback.get('negative', []))

        if positive_count > 0:
            actions.append(f"✨ {positive_count}只股票表现良好，可考虑加仓或持有")
        if negative_count > 0:
            actions.append(f"⛔ {negative_count}只股票表现不佳，建议减仓或止损")

    return {
        "summary": " | ".join(actions) if actions else "观望为主",
        "actions": actions,
        "recommended_position": position_advice.max_position if position_advice else 50,
        "recommended_single": position_advice.single_position if position_advice else 15
    }
