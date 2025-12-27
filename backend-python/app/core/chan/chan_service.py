"""缠论计算服务

整合分型、笔、线段、中枢的完整计算流程
包括形态学和动力学分析
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from loguru import logger
import numpy as np

from .fractal import merge_klines, calculate_fractals, Fractal
from .bi import calculate_bi, Bi
from .segment import calculate_segment, Segment
from .hub import calculate_hub, Hub, get_price_position
from .dynamics import (
    calc_fractal_strength,
    detect_macd_divergence,
    estimate_trend_status,
    FractalStrength,
    MACDDivergence
)
from .trend import TrendAnalyzer, TrendType, TrendPhase, Trend
from .turning_point import TurningPointDetector, TurningPoint


@dataclass
class ChanResult:
    """缠论计算结果（增强版）"""
    ts_code: str
    fractals: List[Fractal]
    bis: List[Bi]
    segments: List[Segment]
    hubs: List[Hub]
    turning_points: List[TurningPoint] = field(default_factory=list)  # 拐点信号

    # 形态学信息
    latest_fractal_type: Optional[str] = None  # "顶分型" / "底分型"
    latest_bi_direction: Optional[str] = None  # "向上" / "向下"
    latest_segment_direction: Optional[str] = None
    current_hub: Optional[Hub] = None
    price_position: Optional[str] = None  # "above" / "below" / "inside"

    # 动力学信息（新增）
    fractal_strength: Optional[FractalStrength] = None  # 分型强弱
    macd_divergence: Optional[MACDDivergence] = None  # MACD背驰
    trend: Optional[Trend] = None  # 走势信息
    trend_status: Optional[str] = None  # "延续" / "完成" / "切换"

    # 交易建议
    suggestion: Optional[str] = None
    risk_level: str = "中"  # "高" / "中" / "低"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "ts_code": self.ts_code,
            "fractals": [asdict(f) for f in self.fractals[-10:]],  # 最近10个分型
            "bis": [asdict(b) for b in self.bis[-10:]],            # 最近10笔
            "segments": [asdict(s) for s in self.segments[-5:]],   # 最近5个线段
            "hubs": [asdict(h) for h in self.hubs[-3:]],           # 最近3个中枢
            "turning_points": [asdict(tp) for tp in self.turning_points[-5:]],  # 最近5个拐点

            # 形态学
            "latest_fractal_type": self.latest_fractal_type,
            "latest_bi_direction": self.latest_bi_direction,
            "latest_segment_direction": self.latest_segment_direction,
            "current_hub": asdict(self.current_hub) if self.current_hub else None,
            "price_position": self.price_position,

            # 动力学
            "fractal_strength": asdict(self.fractal_strength) if self.fractal_strength else None,
            "macd_divergence": asdict(self.macd_divergence) if self.macd_divergence else None,
            "trend": asdict(self.trend) if self.trend else None,
            "trend_status": self.trend_status,

            # 交易建议
            "suggestion": self.suggestion,
            "risk_level": self.risk_level,
        }


class ChanService:
    """缠论计算服务（形态学 + 动力学）"""

    def __init__(self, min_klines: int = 100):
        """初始化

        Args:
            min_klines: 最小K线数量要求
        """
        self.min_klines = min_klines

    def calculate(self, ts_code: str, klines: List[Dict]) -> Optional[ChanResult]:
        """计算完整的缠论指标

        完整流程：
        1. K线包含处理
        2. 分型识别
        3. 笔划分
        4. 线段划分
        5. 中枢识别
        6. 动力学分析（背驰、分型强弱、走势判断）
        7. 拐点信号检测

        Args:
            ts_code: 股票代码
            klines: K线数据列表 (按时间正序)
                   需要包含: trade_date, high, low, close

        Returns:
            ChanResult 或 None (数据不足时)
        """
        if len(klines) < self.min_klines:
            logger.warning(f"{ts_code}: K线数量不足 ({len(klines)} < {self.min_klines})")
            return None

        try:
            # ===== 形态学分析 =====
            # 1. K线包含处理
            merged_klines = merge_klines(klines)

            # 2. 分型识别
            fractals = calculate_fractals(merged_klines)

            # 3. 笔划分
            bis = calculate_bi(fractals)

            # 4. 线段划分
            segments = calculate_segment(bis)

            # 5. 中枢识别
            hubs = calculate_hub(segments)

            # 构建基础结果
            result = ChanResult(
                ts_code=ts_code,
                fractals=fractals,
                bis=bis,
                segments=segments,
                hubs=hubs,
            )

            # ===== 动力学分析 =====
            current_price = float(klines[-1].get("close", 0))
            closes = np.array([float(k.get("close", 0)) for k in klines])

            # 6. 形态学状态填充
            self._fill_morphological_status(result, klines[-1])

            # 7. 动力学分析
            self._fill_dynamics_status(result, klines, closes)

            # 8. 拐点信号检测
            turning_points = TurningPointDetector.detect_all_turning_points(
                [asdict(b) for b in bis],
                [asdict(s) for s in segments],
                [asdict(h) for h in hubs],
                current_price,
                klines
            )
            result.turning_points = turning_points

            # 9. 生成交易建议
            self._generate_suggestion(result, turning_points)

            return result

        except Exception as e:
            logger.error(f"{ts_code}: 缠论计算失败 - {e}")
            return None

    def _fill_morphological_status(self, result: ChanResult, latest_kline: Dict):
        """填充形态学状态（分型、笔、线段、中枢）"""
        # 最新分型
        if result.fractals:
            f = result.fractals[-1]
            result.latest_fractal_type = "顶分型" if f.fractal_type == 1 else "底分型"

        # 最新笔
        if result.bis:
            b = result.bis[-1]
            result.latest_bi_direction = "向上" if b.direction == 1 else "向下"

        # 最新线段
        if result.segments:
            s = result.segments[-1]
            result.latest_segment_direction = "向上" if s.direction == 1 else "向下"

        # 当前中枢和价格位置
        if result.hubs:
            result.current_hub = result.hubs[-1]
            current_price = float(latest_kline.get("close", 0))
            if current_price > 0:
                result.price_position = get_price_position(current_price, result.current_hub)

    def _fill_dynamics_status(self, result: ChanResult, klines: List[Dict], closes: np.ndarray):
        """填充动力学状态（背驰、分型强弱、走势判断）"""
        try:
            current_price = float(klines[-1].get("close", 0))

            # 1. 分型强弱
            if len(klines) >= 3:
                strength = calc_fractal_strength(klines, len(klines) - 2)
                result.fractal_strength = strength

            # 2. MACD背驰
            if len(closes) >= 26:
                macd_div = detect_macd_divergence(klines, closes)
                result.macd_divergence = macd_div

            # 3. 走势判断
            hubs_dict = [asdict(h) for h in result.hubs]
            segments_dict = [asdict(s) for s in result.segments]
            bis_dict = [asdict(b) for b in result.bis]

            trend = TrendAnalyzer.analyze(
                hubs_dict, segments_dict, bis_dict, current_price,
                hubs_dict[-1] if hubs_dict else None
            )
            result.trend = trend

            # 4. 趋势状态（延续/完成/切换）
            result.trend_status = estimate_trend_status(klines, hubs_dict, bis_dict)

            # 5. 风险等级
            if result.fractal_strength and result.fractal_strength.strength == "弱":
                result.risk_level = "高"
            elif result.macd_divergence and result.macd_divergence.has_divergence:
                result.risk_level = "高"
            elif trend.phase == TrendPhase.COMPLETING:
                result.risk_level = "中"
            else:
                result.risk_level = "低"

        except Exception as e:
            logger.warning(f"Failed to fill dynamics status: {e}")

    def _generate_suggestion(self, result: ChanResult, turning_points: List[TurningPoint]):
        """生成交易建议"""
        suggestions = []

        # 根据拐点信号
        if turning_points:
            latest_tp = turning_points[-1]
            suggestions.append(f"拐点: {latest_tp.signal_type.value}")
            if latest_tp.status.value == "confirmed":
                suggestions.append("✅ 已确认，可考虑交易")

        # 根据走势
        if result.trend:
            if result.trend.trend_type == TrendType.UP:
                suggestions.append("📈 上涨趋势")
            elif result.trend.trend_type == TrendType.DOWN:
                suggestions.append("📉 下跌趋势")
            else:
                suggestions.append("〰️ 盘整")

        # 根据背驰
        if result.macd_divergence and result.macd_divergence.has_divergence:
            if result.macd_divergence.type == "top":
                suggestions.append("⚠️ 顶背驰 - 警惕见顶")
            else:
                suggestions.append("⚠️ 底背驰 - 可能见底")

        # 根据分型强弱
        if result.fractal_strength:
            if result.fractal_strength.strength in ["弱", "中"]:
                suggestions.append(f"分型转弱({result.fractal_strength.strength}) - 警惕转折")

        # 风险提示
        if result.risk_level == "高":
            suggestions.append("🛑 高风险 - 谨慎操作")
        elif result.risk_level == "中":
            suggestions.append("⚠️ 中风险 - 设置止损")

        result.suggestion = " | ".join(suggestions) if suggestions else "观望中"

    def get_buy_signals(self, result: ChanResult) -> List[str]:
        """识别买点信号

        一买：底背驰后的第一个向上笔
        二买：一买后回调不破一买低点
        三买：中枢突破后的回踩

        Args:
            result: 缠论计算结果

        Returns:
            买点信号列表
        """
        signals = []

        if not result.bis or len(result.bis) < 3:
            return signals

        latest_bi = result.bis[-1]
        prev_bi = result.bis[-2]

        # 简化判断：最新是向上笔，且在中枢上方
        if latest_bi.direction == 1:
            if result.price_position == "above":
                signals.append("三买信号: 中枢突破")
            elif result.price_position == "inside":
                signals.append("潜在二买: 中枢震荡")

        # 底部反转信号
        if (latest_bi.direction == 1 and
            prev_bi.direction == -1 and
            latest_bi.high > prev_bi.high):
            signals.append("一买信号: 底部反转")

        return signals

    def get_sell_signals(self, result: ChanResult) -> List[str]:
        """识别卖点信号

        一卖：顶背驰后的第一个向下笔
        二卖：一卖后反弹不破一卖高点
        三卖：中枢跌破后的反弹

        Args:
            result: 缠论计算结果

        Returns:
            卖点信号列表
        """
        signals = []

        if not result.bis or len(result.bis) < 3:
            return signals

        latest_bi = result.bis[-1]
        prev_bi = result.bis[-2]

        # 简化判断：最新是向下笔，且在中枢下方
        if latest_bi.direction == -1:
            if result.price_position == "below":
                signals.append("三卖信号: 中枢跌破")
            elif result.price_position == "inside":
                signals.append("潜在二卖: 中枢震荡")

        # 顶部反转信号
        if (latest_bi.direction == -1 and
            prev_bi.direction == 1 and
            latest_bi.low < prev_bi.low):
            signals.append("一卖信号: 顶部反转")

        return signals
