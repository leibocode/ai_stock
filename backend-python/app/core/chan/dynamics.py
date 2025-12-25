"""缠论动力学

通过顶底强弱、背驰等动力指标判断走势是否见顶/见底
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class FractalStrength:
    """分型强弱评估"""
    fractal_type: str  # "top" / "bottom"
    strength: str      # "极强" / "强" / "中" / "弱"
    score: float       # 0-100 分数


def calc_fractal_strength(klines: List[Dict], fractal_idx: int) -> FractalStrength:
    """计算分型强弱

    文章定义的4个等级：
    1. 极强：跳空突破（新K线与前K线有缝隙）
    2. 强：非跳空突破（完全覆盖对手方向前K）
    3. 中：覆盖1/2以上
    4. 弱：覆盖低于1/2

    Args:
        klines: K线列表
        fractal_idx: 分型K线的索引

    Returns:
        分型强弱评估
    """
    if fractal_idx <= 0 or fractal_idx >= len(klines) - 1:
        return FractalStrength("unknown", "弱", 0)

    prev_k = klines[fractal_idx - 1]
    curr_k = klines[fractal_idx]
    next_k = klines[fractal_idx + 1]

    prev_high = float(prev_k.get("high", 0))
    prev_low = float(prev_k.get("low", 0))
    curr_high = float(curr_k.get("high", 0))
    curr_low = float(curr_k.get("low", 0))
    next_high = float(next_k.get("high", 0))
    next_low = float(next_k.get("low", 0))

    # 判断是顶分型还是底分型
    if curr_high > prev_high and curr_high > next_high:
        fractal_type = "top"
        # 顶分型：看第3根K线是否跳空下行或有效突破

        # 1. 跳空：下一根K的最高点 < 当前K的最低点
        if next_high < curr_low:
            return FractalStrength(fractal_type, "极强", 95)

        # 2. 非跳空但完全覆盖（下一根K的最低点 > 前一根K的最高点）
        if next_low > prev_high:
            return FractalStrength(fractal_type, "强", 75)

        # 3. 覆盖超过1/2
        prev_range = prev_high - prev_low
        coverage = (prev_high - next_low) / prev_range if prev_range > 0 else 0
        if coverage >= 0.5:
            return FractalStrength(fractal_type, "中", 50)

        # 4. 覆盖低于1/2
        return FractalStrength(fractal_type, "弱", 25)

    elif curr_low < prev_low and curr_low < next_low:
        fractal_type = "bottom"
        # 底分型：看第3根K线是否跳空上行或有效突破

        # 1. 跳空：下一根K的最低点 > 当前K的最高点
        if next_low > curr_high:
            return FractalStrength(fractal_type, "极强", 95)

        # 2. 非跳空但完全覆盖（下一根K的最高点 < 前一根K的最低点）
        if next_high < prev_low:
            return FractalStrength(fractal_type, "强", 75)

        # 3. 覆盖超过1/2
        prev_range = prev_high - prev_low
        coverage = (next_high - prev_low) / prev_range if prev_range > 0 else 0
        if coverage >= 0.5:
            return FractalStrength(fractal_type, "中", 50)

        # 4. 覆盖低于1/2
        return FractalStrength(fractal_type, "弱", 25)

    return FractalStrength("unknown", "弱", 0)


@dataclass
class MACDDivergence:
    """MACD背驰"""
    type: str           # "top" / "bottom" / "none"
    has_divergence: bool
    price_high: float   # 价格最高/最低点
    price_low: float
    macd_high: float    # MACD对应高点
    macd_low: float
    strength: float     # 0-100 强度评分


def detect_macd_divergence(
    klines: List[Dict],
    close_prices: np.ndarray,
    use_volume: bool = False
) -> MACDDivergence:
    """检测MACD背驰

    顶背驰：价格创新高，但MACD柱（红柱）未创新高
    底背驰：价格创新低，但MACD柱（绿柱）未创新低

    Args:
        klines: K线数据
        close_prices: 收盘价数组
        use_volume: 是否考虑成交量

    Returns:
        MACD背驰信息
    """
    if len(klines) < 26:  # MACD需要26个周期
        return MACDDivergence("none", False, 0, 0, 0, 0, 0)

    try:
        # 计算 EMA
        ema_fast = _calc_ema(close_prices, 12)
        ema_slow = _calc_ema(close_prices, 26)
        dif = ema_fast - ema_slow
        dea = _calc_ema(dif, 9)
        macd = (dif - dea) * 2

        # 找出最后两个极值点（顶或底）
        # 简化版：只看最近的两个价格极值
        if len(klines) < 3:
            return MACDDivergence("none", False, 0, 0, 0, 0, 0)

        highs = np.array([float(k.get("high", 0)) for k in klines[-10:]])
        lows = np.array([float(k.get("low", 0)) for k in klines[-10:]])
        macd_recent = macd[-10:]

        # 检测顶背驰
        price_peaks = []
        macd_peaks = []
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                price_peaks.append((i, highs[i]))
                macd_peaks.append((i, macd_recent[i]))

        if len(price_peaks) >= 2:
            # 比较最后两个高点
            idx1, price1 = price_peaks[-2]
            idx2, price2 = price_peaks[-1]
            macd1 = macd_recent[idx1]
            macd2 = macd_recent[idx2]

            if price2 > price1 and macd2 < macd1:
                strength = min(100, (price2 - price1) / price1 * 100 *
                             (macd1 - macd2) / max(abs(macd1), 0.001) * 10)
                return MACDDivergence("top", True, price2, price1, macd2, macd1, strength)

        # 检测底背驰
        price_troughs = []
        macd_troughs = []
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                price_troughs.append((i, lows[i]))
                macd_troughs.append((i, macd_recent[i]))

        if len(price_troughs) >= 2:
            idx1, price1 = price_troughs[-2]
            idx2, price2 = price_troughs[-1]
            macd1 = macd_recent[idx1]
            macd2 = macd_recent[idx2]

            if price2 < price1 and macd2 > macd1:
                strength = min(100, (price1 - price2) / price1 * 100 *
                             (macd2 - macd1) / max(abs(macd1), 0.001) * 10)
                return MACDDivergence("bottom", True, price1, price2, macd1, macd2, strength)

        return MACDDivergence("none", False, 0, 0, 0, 0, 0)

    except Exception as e:
        logger.error(f"Failed to detect MACD divergence: {e}")
        return MACDDivergence("none", False, 0, 0, 0, 0, 0)


def _calc_ema(data: np.ndarray, period: int) -> np.ndarray:
    """计算EMA"""
    k = 2.0 / (period + 1)
    ema = np.zeros_like(data, dtype=float)
    ema[0] = data[0]

    for i in range(1, len(data)):
        ema[i] = data[i] * k + ema[i - 1] * (1 - k)

    return ema


@dataclass
class ConsolidationDivergence:
    """盘整背驰"""
    has_divergence: bool
    entry_macd_area: float   # 进入段MACD面积
    exit_macd_area: float    # 离开段MACD面积
    strength: float          # 强度评分


def detect_consolidation_divergence(
    entry_klines: List[Dict],
    exit_klines: List[Dict],
    direction: str  # "up" / "down"
) -> ConsolidationDivergence:
    """盘整背驰：进入段vs离开段

    向上线段进入中枢 + 向上线段离开中枢：
    如果离开段的MACD红柱面积 < 进入段，则形成盘整顶背驰

    Args:
        entry_klines: 进入段K线
        exit_klines: 离开段K线
        direction: 线段方向

    Returns:
        盘整背驰信息
    """
    if len(entry_klines) < 5 or len(exit_klines) < 5:
        return ConsolidationDivergence(False, 0, 0, 0)

    try:
        entry_closes = np.array([float(k.get("close", 0)) for k in entry_klines])
        exit_closes = np.array([float(k.get("close", 0)) for k in exit_klines])

        # 计算MACD
        entry_macd = _calc_macd_series(entry_closes)
        exit_macd = _calc_macd_series(exit_closes)

        # 计算MACD柱面积
        if direction == "up":
            # 向上段看红柱（正值）
            entry_area = np.sum(entry_macd[entry_macd > 0])
            exit_area = np.sum(exit_macd[exit_macd > 0])
        else:
            # 向下段看绿柱（负值）
            entry_area = np.sum(np.abs(entry_macd[entry_macd < 0]))
            exit_area = np.sum(np.abs(exit_macd[exit_macd < 0]))

        has_diverge = exit_area < entry_area
        strength = (entry_area - exit_area) / entry_area * 100 if entry_area > 0 else 0

        return ConsolidationDivergence(has_diverge, entry_area, exit_area, strength)

    except Exception as e:
        logger.error(f"Failed to detect consolidation divergence: {e}")
        return ConsolidationDivergence(False, 0, 0, 0)


def _calc_macd_series(closes: np.ndarray) -> np.ndarray:
    """计算完整的MACD序列"""
    if len(closes) < 26:
        return np.zeros_like(closes)

    ema_fast = _calc_ema(closes, 12)
    ema_slow = _calc_ema(closes, 26)
    dif = ema_fast - ema_slow
    dea = _calc_ema(dif, 9)
    macd = (dif - dea) * 2

    return macd


@dataclass
class TrendDivergence:
    """趋势背驰"""
    has_divergence: bool
    type: str              # "top" / "bottom"
    entry_strength: float  # 进入段强度（走势中第一个中枢）
    exit_strength: float   # 离开段强度（走势中最后一个中枢）
    strength_ratio: float  # 强度比（0-1，越接近1越弱）


def detect_trend_divergence(
    hubs: List[Dict],
    segments: List[Dict],
    klines: List[Dict]
) -> TrendDivergence:
    """趋势背驰：2+中枢走势的背驰

    走势背驰：
    - 上涨走势：第二个中枢的离开段 < 第一个中枢的进入段 → 见顶
    - 下跌走势：第二个中枢的离开段 > 第一个中枢的进入段 → 见底

    文章定义：趋势背驰只发生在趋势走势中（2+同向中枢）
    比较中枢的进入段与离开段的长度，如果离开段长度小于进入段则形成趋势背驰

    Args:
        hubs: 中枢列表
        segments: 线段列表
        klines: K线数据

    Returns:
        趋势背驰信息
    """
    if len(hubs) < 2 or len(segments) < 6:
        return TrendDivergence(False, "none", 0, 0, 1.0)

    try:
        # 取最后两个中枢
        hub1 = hubs[-2]
        hub2 = hubs[-1]

        # 获取对应的线段
        # 简化处理：假设第一个中枢由 segment[0-2] 组成，第二个中枢由 segment[3-5] 组成
        # 进入段是segment[0]，离开段是segment[2]（对于第一个中枢）
        # 进入段是segment[3]，离开段是segment[5]（对于第二个中枢）

        if len(segments) >= 6:
            entry_segment = segments[0]  # 第一个中枢的进入段
            exit_segment = segments[5]   # 第二个中枢的离开段（或最后的离开段）

            entry_length = entry_segment.get("high", 0) - entry_segment.get("low", 0)
            exit_length = exit_segment.get("high", 0) - exit_segment.get("low", 0)

            has_diverge = exit_length < entry_length
            strength_ratio = exit_length / entry_length if entry_length > 0 else 1.0

            # 判断趋势方向（根据段的方向）
            trend_type = "top" if entry_segment.get("direction", 1) == 1 else "bottom"

            strength_score = (1 - strength_ratio) * 100

            return TrendDivergence(has_diverge, trend_type, entry_length, exit_length, strength_ratio)

    except Exception as e:
        logger.error(f"Failed to detect trend divergence: {e}")
        return TrendDivergence(False, "none", 0, 0, 1.0)


def estimate_trend_status(
    klines: List[Dict],
    hubs: List[Dict],
    bis: List[Dict]
) -> str:
    """估算走势状态

    返回值：
    - "延续": 趋势继续，可加仓
    - "完成": 趋势接近尾声，考虑减仓
    - "切换": 趋势即将反转，准备平仓或反向
    """
    if not klines or not hubs:
        return "延续"

    # 简化规则：
    # 1. 如果最近出现背驰，返回"完成"
    # 2. 如果分型强弱变弱，返回"完成"
    # 3. 否则返回"延续"

    try:
        # 检查最近K线的分型强弱
        if len(klines) >= 3:
            latest_strength = calc_fractal_strength(klines, len(klines) - 2)
            if latest_strength.strength in ["弱", "中"]:
                return "完成"

        # 检查MACD背驰
        closes = np.array([float(k.get("close", 0)) for k in klines])
        divergence = detect_macd_divergence(klines, closes)
        if divergence.has_divergence:
            return "完成"

        return "延续"

    except Exception as e:
        logger.error(f"Failed to estimate trend status: {e}")
        return "延续"
