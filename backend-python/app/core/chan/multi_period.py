"""多周期缠论分析

实现日线+30分钟+5分钟的三层联动分析
- 日线: 方向层（判断做多还是做空）
- 30分钟: 结构层（识别中枢和线段）
- 5分钟: 执行层（进出场信号）
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from .chan_service import ChanService, ChanResult
from .trend import TrendType


class ConfidenceLevel(str, Enum):
    """信号置信度"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass
class PeriodAnalysis:
    """单个周期的分析结果"""
    period: str              # "daily" / "30m" / "5m"
    trend_type: str         # "上涨" / "下跌" / "盘整"
    hub_count: int          # 中枢数量
    segment_direction: str  # "向上" / "向下"
    price_position: str     # "above" / "inside" / "below"
    risk_level: str         # "高" / "中" / "低"
    has_divergence: bool    # 是否有背驰


@dataclass
class MultiPeriodSignal:
    """多周期联动信号"""
    signal_type: str         # "买入" / "卖出" / "观望"
    confidence: ConfidenceLevel
    daily_trend: str         # 日线方向（方向层）
    min30_structure: str     # 30分钟结构（结构层）
    min5_trigger: str        # 5分钟触发（执行层）
    description: str         # 信号描述
    buy_price: Optional[float] = None
    stop_loss: Optional[float] = None


class MultiPeriodAnalyzer:
    """多周期分析器"""

    def __init__(self):
        self.chan_service = ChanService(min_klines=100)

    async def analyze(
        self,
        ts_code: str,
        daily_klines: List[Dict],
        min30_klines: List[Dict],
        min5_klines: List[Dict]
    ) -> Optional[MultiPeriodSignal]:
        """执行三层周期联动分析

        策略规则（文章定义）：
        日线向上 + 30分钟回调 + 5分钟止跌 → 强势买入
        日线向下 + 30分钟反弹 + 5分钟滞涨 → 强势卖出

        Args:
            ts_code: 股票代码
            daily_klines: 日线数据（至少100条）
            min30_klines: 30分钟数据（至少100条）
            min5_klines: 5分钟数据（至少100条）

        Returns:
            多周期信号或None
        """
        try:
            # 1. 分别计算各周期的缠论指标
            daily_result = self.chan_service.calculate(ts_code, daily_klines)
            min30_result = self.chan_service.calculate(ts_code, min30_klines)
            min5_result = self.chan_service.calculate(ts_code, min5_klines)

            if not (daily_result and min30_result and min5_result):
                logger.warning(f"{ts_code}: 某个周期数据不足，无法分析")
                return None

            # 2. 提取各周期的关键信息
            daily_analysis = self._extract_period_info(daily_result, "daily")
            min30_analysis = self._extract_period_info(min30_result, "30m")
            min5_analysis = self._extract_period_info(min5_result, "5m")

            # 3. 执行三层联动逻辑
            signal = self._generate_signal(
                ts_code, daily_analysis, min30_analysis, min5_analysis,
                daily_result, min30_result, min5_result
            )

            return signal

        except Exception as e:
            logger.error(f"{ts_code}: 多周期分析失败 - {e}")
            return None

    @staticmethod
    def _extract_period_info(result: ChanResult, period: str) -> PeriodAnalysis:
        """提取单个周期的关键信息"""
        trend_type = result.trend.trend_type.value if result.trend else "未知"
        hub_count = len(result.hubs)
        segment_direction = result.latest_segment_direction or "未知"
        price_position = result.price_position or "unknown"
        risk_level = result.risk_level
        has_divergence = (result.macd_divergence.has_divergence
                         if result.macd_divergence else False)

        return PeriodAnalysis(
            period=period,
            trend_type=trend_type,
            hub_count=hub_count,
            segment_direction=segment_direction,
            price_position=price_position,
            risk_level=risk_level,
            has_divergence=has_divergence
        )

    @staticmethod
    def _generate_signal(
        ts_code: str,
        daily_analysis: PeriodAnalysis,
        min30_analysis: PeriodAnalysis,
        min5_analysis: PeriodAnalysis,
        daily_result: ChanResult,
        min30_result: ChanResult,
        min5_result: ChanResult
    ) -> MultiPeriodSignal:
        """生成多周期联动信号

        核心规则（来自文章的"系统蓝图"）：

        买入条件：
        - 日线向上（方向许可做多）
        - 30分钟回调（在中枢内或下方）
        - 5分钟止跌（出现2类或3类买点）

        卖出条件：
        - 日线向下（方向许可做空）
        - 30分钟反弹（在中枢内或上方）
        - 5分钟滞涨（出现卖点）
        """
        signal_type = "观望"
        confidence = ConfidenceLevel.LOW
        buy_price = None
        stop_loss = None

        # ===== 买入信号 =====
        if (daily_analysis.trend_type == "上涨" and
            min30_analysis.price_position in ["below", "inside"] and
            min5_analysis.segment_direction == "向上"):

            # 检查5分钟是否有买点
            if min5_result.turning_points:
                latest_tp = min5_result.turning_points[-1]
                if "买" in latest_tp.signal_type.value:
                    signal_type = "买入"

                    # 置信度判断
                    if (daily_analysis.risk_level == "低" and
                        min30_analysis.price_position == "below" and
                        latest_tp.status.value == "confirmed"):
                        confidence = ConfidenceLevel.HIGH
                    elif (daily_analysis.risk_level == "中" or
                          min30_analysis.price_position == "inside"):
                        confidence = ConfidenceLevel.MEDIUM
                    else:
                        confidence = ConfidenceLevel.LOW

                    buy_price = latest_tp.trigger_price
                    stop_loss = latest_tp.stop_loss

        # ===== 卖出信号 =====
        elif (daily_analysis.trend_type == "下跌" and
              min30_analysis.price_position in ["above", "inside"] and
              min5_analysis.segment_direction == "向下"):

            # 检查5分钟是否有卖点
            if min5_result.turning_points:
                latest_tp = min5_result.turning_points[-1]
                if "卖" in latest_tp.signal_type.value:
                    signal_type = "卖出"

                    # 置信度判断
                    if (daily_analysis.risk_level == "低" and
                        min30_analysis.price_position == "above" and
                        latest_tp.status.value == "confirmed"):
                        confidence = ConfidenceLevel.HIGH
                    elif (daily_analysis.risk_level == "中" or
                          min30_analysis.price_position == "inside"):
                        confidence = ConfidenceLevel.MEDIUM
                    else:
                        confidence = ConfidenceLevel.LOW

                    buy_price = latest_tp.trigger_price
                    stop_loss = latest_tp.stop_loss

        # 生成描述
        description = MultiPeriodAnalyzer._generate_description(
            signal_type, daily_analysis, min30_analysis, min5_analysis
        )

        return MultiPeriodSignal(
            signal_type=signal_type,
            confidence=confidence,
            daily_trend=daily_analysis.trend_type,
            min30_structure=f"{min30_analysis.segment_direction}(位置:{min30_analysis.price_position})",
            min5_trigger=min5_analysis.segment_direction,
            description=description,
            buy_price=buy_price,
            stop_loss=stop_loss
        )

    @staticmethod
    def _generate_description(
        signal_type: str,
        daily_analysis: PeriodAnalysis,
        min30_analysis: PeriodAnalysis,
        min5_analysis: PeriodAnalysis
    ) -> str:
        """生成信号描述"""
        parts = []

        # 日线分析
        daily_desc = f"📊 日线: {daily_analysis.trend_type}"
        if daily_analysis.has_divergence:
            daily_desc += "(背驰⚠️)"
        parts.append(daily_desc)

        # 30分钟分析
        min30_desc = f"📈 30m: {min30_analysis.segment_direction}(中枢:{min30_analysis.price_position})"
        if min30_analysis.hub_count >= 2:
            min30_desc += f" {min30_analysis.hub_count}个中枢"
        parts.append(min30_desc)

        # 5分钟分析
        min5_desc = f"⏱️ 5m: {min5_analysis.segment_direction}"
        parts.append(min5_desc)

        # 信号
        if signal_type == "买入":
            parts.append("✅ 三层联动买入信号")
            parts.append("策略: 日线向上做多 → 30m回调加仓 → 5m止跌确认")
        elif signal_type == "卖出":
            parts.append("❌ 三层联动卖出信号")
            parts.append("策略: 日线向下做空 → 30m反弹减仓 → 5m滞涨确认")
        else:
            parts.append("〰️ 观望中，等待突破或跌破")

        return " | ".join(parts)

    @staticmethod
    def get_period_strength(analysis: PeriodAnalysis) -> str:
        """评估单个周期的强势程度"""
        if analysis.hub_count >= 2 and analysis.has_divergence:
            return "极强"
        elif analysis.hub_count >= 2:
            return "强"
        elif analysis.hub_count == 1:
            return "中"
        else:
            return "弱"


def format_multi_period_report(signal: MultiPeriodSignal) -> str:
    """格式化多周期报告"""
    report = []
    report.append("=" * 60)
    report.append("【多周期联动分析报告】")
    report.append("=" * 60)

    report.append(f"\n📊 信号: {signal.signal_type}")
    report.append(f"🎯 置信度: {signal.confidence.value}")

    report.append(f"\n📍 日线方向（方向层）: {signal.daily_trend}")
    report.append(f"📍 30分钟结构（结构层）: {signal.min30_structure}")
    report.append(f"📍 5分钟执行（执行层）: {signal.min5_trigger}")

    if signal.buy_price:
        report.append(f"\n💰 进场价: {signal.buy_price:.2f}")
    if signal.stop_loss:
        report.append(f"🛑 止损价: {signal.stop_loss:.2f}")

    report.append(f"\n📝 {signal.description}")

    report.append("\n" + "=" * 60)

    return "\n".join(report)
