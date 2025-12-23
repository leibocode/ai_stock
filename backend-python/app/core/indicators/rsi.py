import numpy as np
from typing import Tuple


def calculate_rsi(
    closes: np.ndarray,
    period: int = 14
) -> float:
    """计算RSI (Relative Strength Index)

    公式: RSI = 100 - 100 / (1 + RS)
    其中 RS = 平均上升幅度 / 平均下降幅度

    Args:
        closes: 收盘价数组
        period: 周期数 (常用6, 12, 14)

    Returns:
        RSI值 (0-100)
    """
    if len(closes) < period + 1:
        return 50.0  # 数据不足返回50

    changes = np.diff(closes)
    gains = np.where(changes > 0, changes, 0)
    losses = np.where(changes < 0, -changes, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


def calculate_rsi_multi(
    closes: np.ndarray,
    periods: list[int] | None = None
) -> dict[str, float]:
    """计算多个周期的RSI

    Args:
        closes: 收盘价数组
        periods: 周期列表 (默认 [6, 12])

    Returns:
        {period: rsi_value}
    """
    if periods is None:
        periods = [6, 12]

    return {
        f"rsi_{period}": calculate_rsi(closes, period)
        for period in periods
    }
