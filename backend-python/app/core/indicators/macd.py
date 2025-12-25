import numpy as np
from typing import Tuple


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
    ema = np.zeros_like(data)
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
    """计算MACD指标

    Args:
        closes: 收盘价数组
        fast: 快线周期 (默认12)
        slow: 慢线周期 (默认26)
        signal: 信号线周期 (默认9)

    Returns:
        (dif, dea, macd_hist)
    """
    if len(closes) < slow:
        return 0.0, 0.0, 0.0

    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)

    dif = ema_fast[-1] - ema_slow[-1]

    # 计算DIF的EMA作为SIGNAL线
    dif_array = ema_fast - ema_slow
    dea = calculate_ema(dif_array, signal)[-1]

    macd_hist = (dif - dea) * 2

    return round(dif, 4), round(dea, 4), round(macd_hist, 4)
