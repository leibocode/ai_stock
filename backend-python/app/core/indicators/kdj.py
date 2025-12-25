import numpy as np
from typing import Tuple


def calculate_kdj(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 9
) -> Tuple[float, float, float]:
    """计算KDJ指标

    公式:
    - RSV = (Close - Lowest) / (Highest - Lowest) * 100
    - K = RSV * 0.67 + K[prev] * 0.33
    - D = K * 0.67 + D[prev] * 0.33
    - J = 3K - 2D

    Args:
        highs: 最高价数组
        lows: 最低价数组
        closes: 收盘价数组
        period: 周期 (默认9)

    Returns:
        (k, d, j)
    """
    if len(closes) < period:
        return 50.0, 50.0, 50.0

    highest = np.max(highs[-period:])
    lowest = np.min(lows[-period:])
    close = closes[-1]

    if highest == lowest:
        rsv = 50.0
    else:
        rsv = (close - lowest) / (highest - lowest) * 100

    # 简化处理: 使用单期RSV直接计算K/D
    k = rsv * 0.67 + 50 * 0.33
    d = k * 0.67 + 50 * 0.33
    j = 3 * k - 2 * d

    return round(k, 2), round(d, 2), round(j, 2)
