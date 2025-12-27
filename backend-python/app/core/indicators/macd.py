import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class MACDValues:
    """MACD完整数据"""
    dif: float      # DIF线（快线）
    dea: float      # DEA线（信号线）
    macd: float     # MACD柱
    dif_array: np.ndarray  # 完整DIF序列
    dea_array: np.ndarray  # 完整DEA序列
    macd_array: np.ndarray  # 完整MACD序列


def calculate_ema(
    data: np.ndarray,
    period: int
) -> np.ndarray:
    """计算EMA (Exponential Moving Average)

    公式: EMA = Data[i] * k + EMA[i-1] * (1-k)
    其中 k = 2/(period+1)

    Args:
        data: 数据数组
        period: 周期

    Returns:
        EMA值数组
    """
    k = 2.0 / (period + 1)
    ema = np.zeros_like(data, dtype=float)
    ema[0] = data[0]

    for i in range(1, len(data)):
        ema[i] = data[i] * k + ema[i - 1] * (1 - k)

    return ema


def calculate_macd(
    closes: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[float, float, float]:
    """计算MACD指标（返回最后一个值）

    标准MACD计算：
    1. DIF = EMA(12) - EMA(26)
    2. DEA = EMA(DIF, 9)  # DEA是DIF的9日EMA，不是信号线
    3. MACD = DIF - DEA   # MACD柱（不需要乘以2）

    Args:
        closes: 收盘价数组
        fast: 快线周期 (默认12)
        slow: 慢线周期 (默认26)
        signal: 信号线周期 (默认9)

    Returns:
        (dif, dea, macd_hist) - 四舍五入到4位小数
    """
    if len(closes) < slow:
        return 0.0, 0.0, 0.0

    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)

    # DIF = 快线 - 慢线
    dif_array = ema_fast - ema_slow
    dif = dif_array[-1]

    # DEA = DIF的9日EMA（不需要乘以2）
    dea_array = calculate_ema(dif_array, signal)
    dea = dea_array[-1]

    # MACD柱 = DIF - DEA
    macd_hist = dif - dea

    return round(dif, 4), round(dea, 4), round(macd_hist, 4)


def calculate_macd_full(
    closes: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> MACDValues:
    """计算完整的MACD指标序列

    用于背驰检测和面积计算

    Args:
        closes: 收盘价数组
        fast: 快线周期 (默认12)
        slow: 慢线周期 (默认26)
        signal: 信号线周期 (默认9)

    Returns:
        MACDValues 对象，包含完整序列和最后一个值
    """
    if len(closes) < slow:
        empty_array = np.array([])
        return MACDValues(0.0, 0.0, 0.0, empty_array, empty_array, empty_array)

    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)

    # DIF = 快线 - 慢线
    dif_array = ema_fast - ema_slow

    # DEA = DIF的9日EMA
    dea_array = calculate_ema(dif_array, signal)

    # MACD柱 = DIF - DEA（标准计算，无需乘以2）
    macd_array = dif_array - dea_array

    return MACDValues(
        dif=float(dif_array[-1]),
        dea=float(dea_array[-1]),
        macd=float(macd_array[-1]),
        dif_array=dif_array,
        dea_array=dea_array,
        macd_array=macd_array
    )


def calculate_macd_histogram_area(
    macd_values: np.ndarray,
    positive_only: bool = True
) -> float:
    """计算MACD柱面积

    用于盘整背驰和趋势背驰判断

    Args:
        macd_values: MACD柱序列
        positive_only: 只计算正值面积（红柱），否则计算绝对值

    Returns:
        MACD柱面积（累计）
    """
    if len(macd_values) == 0:
        return 0.0

    if positive_only:
        # 只计算正值（红柱）
        area = np.sum(macd_values[macd_values > 0])
    else:
        # 计算绝对值面积
        area = np.sum(np.abs(macd_values))

    return float(area)


def compare_macd_areas(
    entry_macd: np.ndarray,
    exit_macd: np.ndarray,
    direction: str
) -> Tuple[float, float, bool]:
    """比较两个MACD序列的面积（用于盘整背驰判断）

    Args:
        entry_macd: 进入段MACD序列
        exit_macd: 离开段MACD序列
        direction: 线段方向 "up" / "down"

    Returns:
        (entry_area, exit_area, is_divergence)
        - entry_area: 进入段面积
        - exit_area: 离开段面积
        - is_divergence: 是否存在背驰（离开段面积 < 进入段面积）
    """
    if direction == "up":
        # 向上线段看红柱（正值）
        entry_area = calculate_macd_histogram_area(entry_macd, positive_only=True)
        exit_area = calculate_macd_histogram_area(exit_macd, positive_only=True)
    else:
        # 向下线段看绿柱（负值），用绝对值比较
        entry_area = calculate_macd_histogram_area(entry_macd, positive_only=False)
        exit_area = calculate_macd_histogram_area(exit_macd, positive_only=False)

    is_divergence = exit_area < entry_area

    return entry_area, exit_area, is_divergence


def detect_macd_divergence(
    dif_array: np.ndarray,
    dea_array: np.ndarray,
    closes: np.ndarray,
    window: int = 10
) -> Tuple[bool, str]:
    """快速检测MACD顶/底背驰

    Args:
        dif_array: DIF序列
        dea_array: DEA序列
        closes: 收盘价数组
        window: 检查窗口大小

    Returns:
        (has_divergence, divergence_type)
        - has_divergence: 是否存在背驰
        - divergence_type: "top" / "bottom" / "none"
    """
    if len(closes) < window or len(dif_array) < window:
        return False, "none"

    # 取最近window的数据
    recent_closes = closes[-window:]
    recent_dif = dif_array[-window:]

    # 找价格最高点和对应的DIF值
    price_peak_idx = np.argmax(recent_closes)
    dif_peak_idx = np.argmax(recent_dif)

    # 找价格最低点和对应的DIF值
    price_trough_idx = np.argmin(recent_closes)
    dif_trough_idx = np.argmin(recent_dif)

    # 顶背驰：价格创新高，但DIF不创新高
    if price_peak_idx > dif_peak_idx:
        # 说明最新的价格高点出现在之前的DIF最高点之后
        if recent_closes[price_peak_idx] > recent_closes[dif_peak_idx]:
            if recent_dif[price_peak_idx] < recent_dif[dif_peak_idx]:
                return True, "top"

    # 底背驰：价格创新低，但DIF不创新低
    if price_trough_idx > dif_trough_idx:
        if recent_closes[price_trough_idx] < recent_closes[dif_trough_idx]:
            if recent_dif[price_trough_idx] > recent_dif[dif_trough_idx]:
                return True, "bottom"

    return False, "none"
