"""缠论走势类型分析

识别上涨/下跌/盘整趋势，判断走势阶段
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class TrendType(str, Enum):
    """走势类型"""
    UP = "上涨"
    DOWN = "下跌"
    CONSOLIDATION = "盘整"


class TrendPhase(str, Enum):
    """走势阶段"""
    CONTINUING = "延续"      # 趋势继续，第1个中枢已完成，向第2个中枢进行
    COMPLETING = "完成"      # 中枢已出现2个，即将形成趋势背驰或反转
    SWITCHING = "切换"       # 趋势已反转，新趋势开始


@dataclass
class Trend:
    """走势信息"""
    trend_type: TrendType        # 上涨/下跌/盘整
    phase: TrendPhase            # 延续/完成/切换
    hub_count: int               # 中枢数量
    current_hub_index: int       # 当前所在中枢索引
    is_hub_exiting: bool         # 是否正在离开中枢
    current_segment_direction: str  # 当前线段方向 "向上" / "向下"
    price_position: str          # 价格位置 "above" / "inside" / "below"
    confidence: float            # 判断置信度 0-1


class TrendAnalyzer:
    """走势分析器"""

    @staticmethod
    def analyze(
        hubs: List[Dict],
        segments: List[Dict],
        bis: List[Dict],
        current_price: float,
        current_hub: Optional[Dict] = None
    ) -> Trend:
        """分析走势类型和阶段

        缠论规则：
        1. 上涨走势: 2+同向向上的中枢相连接 (即多个向上中枢)
        2. 下跌走势: 2+同向向下的中枢相连接 (即多个向下中枢)
        3. 盘整: 未形成2个同向中枢，或只有1个中枢

        走势阶段：
        - 延续: 趋势形成，可加仓
        - 完成: 中枢数量达2个，可能见顶/底
        - 切换: 趋势即将反转

        Args:
            hubs: 中枢列表
            segments: 线段列表
            bis: 笔列表
            current_price: 当前价格
            current_hub: 当前中枢

        Returns:
            走势信息
        """
        if not hubs:
            return Trend(
                trend_type=TrendType.CONSOLIDATION,
                phase=TrendPhase.CONTINUING,
                hub_count=0,
                current_hub_index=-1,
                is_hub_exiting=False,
                current_segment_direction="未知",
                price_position="unknown",
                confidence=0.0
            )

        # 1. 判断趋势类型
        trend_type = TrendAnalyzer._detect_trend_type(hubs)

        # 2. 判断中枢数量和阶段
        hub_count = len(hubs)
        if hub_count == 0:
            phase = TrendPhase.CONTINUING
            current_hub_index = -1
        elif hub_count == 1:
            phase = TrendPhase.CONTINUING
            current_hub_index = 0
        else:
            # 2+中枢，判断是继续还是完成
            phase = TrendAnalyzer._judge_phase(hubs, segments, bis)
            current_hub_index = hub_count - 1

        # 3. 判断价格位置
        if current_hub is None and hub_count > 0:
            current_hub = hubs[-1]

        price_position = "unknown"
        is_hub_exiting = False
        if current_hub:
            price_position = TrendAnalyzer._get_price_position(
                current_price, current_hub
            )
            is_hub_exiting = TrendAnalyzer._is_exiting_hub(
                current_price, current_hub, trend_type
            )

        # 4. 获取当前线段方向
        current_segment_direction = "未知"
        if segments:
            latest_segment = segments[-1]
            direction = latest_segment.get("direction", 1)
            current_segment_direction = "向上" if direction == 1 else "向下"

        # 5. 计算置信度
        confidence = TrendAnalyzer._calc_confidence(trend_type, phase, hub_count)

        return Trend(
            trend_type=trend_type,
            phase=phase,
            hub_count=hub_count,
            current_hub_index=current_hub_index,
            is_hub_exiting=is_hub_exiting,
            current_segment_direction=current_segment_direction,
            price_position=price_position,
            confidence=confidence
        )

    @staticmethod
    def _detect_trend_type(hubs: List[Dict]) -> TrendType:
        """检测走势类型

        规则：至少2个同向中枢才能判断为上涨/下跌趋势
        """
        if len(hubs) < 2:
            return TrendType.CONSOLIDATION

        # 获取每个中枢的方向（根据离开方向）
        directions = []
        for hub in hubs:
            # 简化：如果中枢上沿 > 下沿的中点，判定为向上中枢
            zg = float(hub.get("zg", 0))
            zd = float(hub.get("zd", 0))
            # 实际应该根据离开时的方向判断，这里用简化方式
            directions.append(1 if zg > zd else -1)

        # 如果最后2个中枢同向，则判定为趋势
        if len(directions) >= 2:
            # 计算最近N个中枢的方向
            recent_directions = directions[-2:]

            # 简化版：看是否同向向上或同向向下
            if all(d == 1 for d in recent_directions):
                return TrendType.UP
            elif all(d == -1 for d in recent_directions):
                return TrendType.DOWN

        return TrendType.CONSOLIDATION

    @staticmethod
    def _judge_phase(
        hubs: List[Dict],
        segments: List[Dict],
        bis: List[Dict]
    ) -> TrendPhase:
        """判断走势阶段

        规则（文章定义）：
        - 延续: 第1个中枢完成，正向第2个中枢运动
        - 完成: 第2个中枢已完成，出现背驰信号或分型强弱变弱
        - 切换: 新的反向笔开始，打破了原有走势结构
        """
        if len(hubs) < 2:
            return TrendPhase.CONTINUING

        # 简化规则：
        # - 2个中枢: 延续
        # - 3+个中枢: 完成或切换（需要检查背驰）
        if len(hubs) == 2:
            return TrendPhase.COMPLETING

        # 3+中枢：判断是否出现背驰
        # 这需要动力学模块支持，暂时返回完成
        return TrendPhase.COMPLETING

    @staticmethod
    def _get_price_position(price: float, hub: Dict) -> str:
        """获取价格相对中枢的位置"""
        zg = float(hub.get("zg", 0))
        zd = float(hub.get("zd", 0))

        if price > zg:
            return "above"
        elif price < zd:
            return "below"
        else:
            return "inside"

    @staticmethod
    def _is_exiting_hub(
        price: float,
        hub: Dict,
        trend_type: TrendType
    ) -> bool:
        """判断是否正在离开中枢

        向上趋势：如果价格 > 中枢上沿，则正在离开
        向下趋势：如果价格 < 中枢下沿，则正在离开
        """
        zg = float(hub.get("zg", 0))
        zd = float(hub.get("zd", 0))

        if trend_type == TrendType.UP:
            return price > zg
        elif trend_type == TrendType.DOWN:
            return price < zd
        else:
            return False

    @staticmethod
    def _calc_confidence(
        trend_type: TrendType,
        phase: TrendPhase,
        hub_count: int
    ) -> float:
        """计算判断的置信度

        规则：
        - 盘整趋势: 0.3
        - 1个中枢: 0.5
        - 2个中枢延续: 0.7
        - 2个中枢完成: 0.8
        - 3+中枢: 0.9
        """
        if trend_type == TrendType.CONSOLIDATION:
            return 0.3

        if hub_count == 1:
            return 0.5
        elif hub_count == 2:
            return 0.7 if phase == TrendPhase.CONTINUING else 0.8
        else:
            return 0.9


def get_trend_suggestion(trend: Trend) -> str:
    """根据走势信息给出交易建议

    Args:
        trend: 走势信息

    Returns:
        交易建议字符串
    """
    suggestions = []

    # 趋势类型建议
    if trend.trend_type == TrendType.UP:
        suggestions.append("🔺 上涨趋势")
        if trend.phase == TrendPhase.CONTINUING:
            suggestions.append("→ 趋势继续中，可考虑加仓")
        elif trend.phase == TrendPhase.COMPLETING:
            suggestions.append("→ 中枢接近完成，考虑获利了结或减仓")
        else:
            suggestions.append("→ 趋势即将反转，准备平仓")

    elif trend.trend_type == TrendType.DOWN:
        suggestions.append("🔻 下跌趋势")
        if trend.phase == TrendPhase.CONTINUING:
            suggestions.append("→ 趋势继续中，空仓或做空")
        elif trend.phase == TrendPhase.COMPLETING:
            suggestions.append("→ 底部接近确认，准备接球")
        else:
            suggestions.append("→ 趋势即将反转，关注买点")

    else:
        suggestions.append("〰️ 盘整走势")
        suggestions.append("→ 区间震荡，等待突破或跌破")

    # 价格位置建议
    if trend.price_position == "above":
        suggestions.append("📍 价格在中枢上方 - 强势")
    elif trend.price_position == "below":
        suggestions.append("📍 价格在中枢下方 - 弱势")
    elif trend.price_position == "inside":
        suggestions.append("📍 价格在中枢内 - 震荡中")

    # 置信度
    if trend.confidence >= 0.8:
        suggestions.append(f"✅ 信号强度: 高 ({trend.confidence:.0%})")
    elif trend.confidence >= 0.5:
        suggestions.append(f"⚠️ 信号强度: 中 ({trend.confidence:.0%})")
    else:
        suggestions.append(f"❓ 信号强度: 弱 ({trend.confidence:.0%})")

    return "\n".join(suggestions)
