"""缠论拐点信号

识别1/2/3类买卖点，判断进出场时机
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SignalType(str, Enum):
    """信号类型"""
    BUY1 = "1买"
    BUY2 = "2买"
    BUY3 = "3买"
    SELL1 = "1卖"
    SELL2 = "2卖"
    SELL3 = "3卖"


class SignalStatus(str, Enum):
    """信号状态"""
    CREATED = "创建"    # 次低点/次高点形成
    CONFIRMED = "确认"  # 突破前高/支撑位确认


@dataclass
class TurningPoint:
    """拐点信号"""
    signal_type: SignalType     # 1/2/3买卖
    status: SignalStatus        # 创建/确认
    trigger_price: float        # 触发价格
    stop_loss: float            # 止损价
    stop_win: Optional[float]   # 止盈价（可选）
    confidence: float           # 信号置信度 0-1
    description: str            # 信号描述


class TurningPointDetector:
    """拐点检测器"""

    @staticmethod
    def detect_buy_signals(
        bis: List[Dict],
        segments: List[Dict],
        hubs: List[Dict],
        current_price: float,
        klines: List[Dict]
    ) -> List[TurningPoint]:
        """检测买入信号

        文章规则：
        一买：下跌走势要出现至少2个或以上的中枢 + 底部趋势背驰
        二买：一买后向上一笔回踩不创新低
        三买：向上突破底部盘整中枢后回踩不触碰中枢上沿

        Args:
            bis: 笔列表
            segments: 线段列表
            hubs: 中枢列表
            current_price: 当前价格
            klines: K线数据

        Returns:
            买入信号列表
        """
        signals = []

        if not bis or not hubs:
            return signals

        try:
            latest_bi = bis[-1]
            latest_segment = segments[-1] if segments else None

            # 一买：下跌走势结束，底背驰
            # 特征：最新笔是向上笔，且价格 > 前一笔的低点很多
            if latest_bi.get("direction") == 1:  # 向上笔
                prev_bi = bis[-2] if len(bis) > 1 else None
                if prev_bi and prev_bi.get("direction") == -1:  # 前一笔是向下
                    # 简化判断：向上笔的高点 > 向下笔的低点
                    if latest_bi.get("high", 0) > prev_bi.get("low", 0):
                        # 这是一个买点信号的起点
                        buy1_signal = TurningPoint(
                            signal_type=SignalType.BUY1,
                            status=SignalStatus.CREATED,
                            trigger_price=latest_bi.get("low", 0),
                            stop_loss=latest_bi.get("low", 0) * 0.98,  # 止损在低点下方2%
                            stop_win=None,
                            confidence=0.7,
                            description="下跌走势结束，底背驰信号，一买创建"
                        )
                        signals.append(buy1_signal)

            # 二买：一买后回踩不创新低
            # 特征：有向上笔后跟向下笔，向下笔的低点 > 前一个向下笔的低点
            if len(bis) >= 4:
                # 找最后的一个向上笔和后续的向下笔
                idx = len(bis) - 1
                if bis[idx].get("direction") == -1:  # 最新是向下笔
                    # 这是回踩阶段
                    idx_up = idx - 1
                    idx_down_prev = idx - 2
                    if (bis[idx_up].get("direction") == 1 and
                        bis[idx_down_prev].get("direction") == -1):
                        # 检查回踩是否创新低
                        if bis[idx].get("low", 0) > bis[idx_down_prev].get("low", 0):
                            # 二买确认：不创新低
                            buy2_signal = TurningPoint(
                                signal_type=SignalType.BUY2,
                                status=SignalStatus.CONFIRMED,
                                trigger_price=bis[idx].get("high", 0),  # 突破本笔高点
                                stop_loss=bis[idx].get("low", 0) * 0.98,
                                stop_win=None,
                                confidence=0.75,
                                description="一买后回踩不创新低，二买确认"
                            )
                            signals.append(buy2_signal)

            # 三买：中枢突破后回踩不触碰中枢上沿
            # 特征：价格突破中枢上沿后回踩，回踩高点 > 中枢上沿
            if hubs and latest_segment:
                latest_hub = hubs[-1]
                zg = float(latest_hub.get("zg", 0))
                zd = float(latest_hub.get("zd", 0))

                # 如果最新线段是向上的，且当前价格 > 中枢上沿
                if (latest_segment.get("direction") == 1 and
                    current_price > zg):
                    # 检查是否有回踩但没有跌回中枢
                    if len(klines) >= 5:
                        recent_low = min(float(k.get("low", 0)) for k in klines[-5:])
                        if recent_low > zg:
                            # 三买信号
                            buy3_signal = TurningPoint(
                                signal_type=SignalType.BUY3,
                                status=SignalStatus.CONFIRMED,
                                trigger_price=zg,
                                stop_loss=zd * 0.99,
                                stop_win=None,
                                confidence=0.8,
                                description="中枢突破后回踩不破，三买确认"
                            )
                            signals.append(buy3_signal)

        except Exception as e:
            from loguru import logger
            logger.error(f"Failed to detect buy signals: {e}")

        return signals

    @staticmethod
    def detect_sell_signals(
        bis: List[Dict],
        segments: List[Dict],
        hubs: List[Dict],
        current_price: float,
        klines: List[Dict]
    ) -> List[TurningPoint]:
        """检测卖出信号

        文章规则：
        一卖：中枢的离开段如果发生背驰，高点就是一卖
        二卖：一卖见顶后向下一笔回抽不创新高
        三卖：之后形成顶部中枢，向下突破中枢下沿且回抽不进中枢

        Args:
            bis: 笔列表
            segments: 线段列表
            hubs: 中枢列表
            current_price: 当前价格
            klines: K线数据

        Returns:
            卖出信号列表
        """
        signals = []

        if not bis or not hubs:
            return signals

        try:
            latest_bi = bis[-1]
            latest_segment = segments[-1] if segments else None

            # 一卖：上涨走势结束，顶背驰
            # 特征：最新笔是向下笔，且价格下降，前一笔是向上笔
            if latest_bi.get("direction") == -1:  # 向下笔
                prev_bi = bis[-2] if len(bis) > 1 else None
                if prev_bi and prev_bi.get("direction") == 1:  # 前一笔是向上
                    # 简化判断：向下笔的低点 < 向上笔的高点
                    if latest_bi.get("low", 0) < prev_bi.get("high", 0):
                        # 这是一个卖点信号的起点
                        sell1_signal = TurningPoint(
                            signal_type=SignalType.SELL1,
                            status=SignalStatus.CREATED,
                            trigger_price=latest_bi.get("high", 0),
                            stop_loss=latest_bi.get("high", 0) * 1.02,  # 止损在高点上方2%
                            stop_win=None,
                            confidence=0.7,
                            description="上涨走势结束，顶背驰信号，一卖创建"
                        )
                        signals.append(sell1_signal)

            # 二卖：一卖后反弹不创新高
            # 特征：有向下笔后跟向上笔，向上笔的高点 < 前一个向上笔的高点
            if len(bis) >= 4:
                idx = len(bis) - 1
                if bis[idx].get("direction") == 1:  # 最新是向上笔（反弹）
                    idx_down = idx - 1
                    idx_up_prev = idx - 2
                    if (bis[idx_down].get("direction") == -1 and
                        bis[idx_up_prev].get("direction") == 1):
                        # 检查反弹是否创新高
                        if bis[idx].get("high", 0) < bis[idx_up_prev].get("high", 0):
                            # 二卖确认：不创新高
                            sell2_signal = TurningPoint(
                                signal_type=SignalType.SELL2,
                                status=SignalStatus.CONFIRMED,
                                trigger_price=bis[idx].get("low", 0),  # 跌破本笔低点
                                stop_loss=bis[idx].get("high", 0) * 1.02,
                                stop_win=None,
                                confidence=0.75,
                                description="一卖后反弹不创新高，二卖确认"
                            )
                            signals.append(sell2_signal)

            # 三卖：中枢跌破后反弹不进中枢
            # 特征：价格跌破中枢下沿后反弹，反弹低点 < 中枢下沿
            if hubs and latest_segment:
                latest_hub = hubs[-1]
                zg = float(latest_hub.get("zg", 0))
                zd = float(latest_hub.get("zd", 0))

                # 如果最新线段是向下的，且当前价格 < 中枢下沿
                if (latest_segment.get("direction") == -1 and
                    current_price < zd):
                    # 检查是否有反弹但没有回到中枢
                    if len(klines) >= 5:
                        recent_high = max(float(k.get("high", 0)) for k in klines[-5:])
                        if recent_high < zd:
                            # 三卖信号
                            sell3_signal = TurningPoint(
                                signal_type=SignalType.SELL3,
                                status=SignalStatus.CONFIRMED,
                                trigger_price=zd,
                                stop_loss=zg * 1.01,
                                stop_win=None,
                                confidence=0.8,
                                description="中枢跌破后反弹不进，三卖确认"
                            )
                            signals.append(sell3_signal)

        except Exception as e:
            from loguru import logger
            logger.error(f"Failed to detect sell signals: {e}")

        return signals

    @staticmethod
    def detect_all_turning_points(
        bis: List[Dict],
        segments: List[Dict],
        hubs: List[Dict],
        current_price: float,
        klines: List[Dict]
    ) -> List[TurningPoint]:
        """检测所有拐点信号

        Args:
            bis: 笔列表
            segments: 线段列表
            hubs: 中枢列表
            current_price: 当前价格
            klines: K线数据

        Returns:
            拐点信号列表（按时间排序）
        """
        buy_signals = TurningPointDetector.detect_buy_signals(
            bis, segments, hubs, current_price, klines
        )
        sell_signals = TurningPointDetector.detect_sell_signals(
            bis, segments, hubs, current_price, klines
        )

        return buy_signals + sell_signals


def get_turning_point_suggestion(signal: TurningPoint) -> str:
    """生成拐点信号的交易建议

    Args:
        signal: 拐点信号

    Returns:
        建议文本
    """
    suggestions = []

    # 信号类型
    suggestions.append(f"📊 信号: {signal.signal_type.value}")

    # 信号状态
    if signal.status == SignalStatus.CREATED:
        suggestions.append("⏳ 状态: 创建中 - 需要等待确认")
    else:
        suggestions.append("✅ 状态: 已确认 - 可以考虑交易")

    # 交易价格
    suggestions.append(f"💰 触发价: {signal.trigger_price:.2f}")
    suggestions.append(f"🛑 止损: {signal.stop_loss:.2f}")

    if signal.stop_win:
        suggestions.append(f"🎯 止盈: {signal.stop_win:.2f}")

    # 置信度
    if signal.confidence >= 0.8:
        suggestions.append(f"⭐ 信号强度: 高 ({signal.confidence:.0%})")
    elif signal.confidence >= 0.6:
        suggestions.append(f"⭐ 信号强度: 中 ({signal.confidence:.0%})")
    else:
        suggestions.append(f"⭐ 信号强度: 低 ({signal.confidence:.0%})")

    # 描述
    suggestions.append(f"📝 {signal.description}")

    return "\n".join(suggestions)
