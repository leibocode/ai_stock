import numpy as np
from typing import Tuple


def calculate_boll(
    closes: np.ndarray,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[float, float, float]:
    """计算布林带(Bollinger Bands)

    公式:
    - 中轨(MB) = SMA(Close, 20)
    - 标准差σ = sqrt(Σ(Close - MB)² / n)
    - 上轨(UP) = MB + 2σ
    - 下轨(DN) = MB - 2σ

    Args:
        closes: 收盘价数组
        period: 周期 (默认20)
        std_dev: 标准差倍数 (默认2.0)

    Returns:
        (upper, mid, lower)
    """
    if len(closes) < period:
        return 0.0, 0.0, 0.0

    slice_data = closes[-period:]
    mid = np.mean(slice_data)

    variance = np.sum((slice_data - mid) ** 2) / period
    std = np.sqrt(variance)

    upper = mid + std_dev * std
    lower = mid - std_dev * std

    return round(upper, 2), round(mid, 2), round(lower, 2)
