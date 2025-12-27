"""缠论背驰信号检测

背驰是缠论中最重要的买卖点信号，分为两类：
1. 一笔背驰：价格创新高/低，但同周期指标（MACD）不创新高/低
2. 线段背驰：线段末端价格创新，但指标面积小于线段起点

标准买卖点：
- 一买：下跌趋势中第一个底背驰
- 一卖：上升趋势中第一个顶背驰
- 二买：一买后回踩不破
- 二卖：一卖后反弹不破
- 三买：中枢突破后回踩不进中枢
"""

import numpy as np
from typing import List, Tuple, Literal, Optional
from dataclasses import dataclass
from .bi import Bi
from .hub import Hub
from app.core.indicators.macd import calculate_macd_full


@dataclass
class Divergence:
    """背驰信号"""
    signal_type: Literal["top_divergence", "bottom_divergence"]  # 顶背驰/底背驰
    bar_idx: int  # 信号出现的K线位置
    price: float  # 当前价格
    prev_price: float  # 前一个同类型高/低点的价格
    indicator_value: float  # 当前指标值
    prev_indicator_value: float  # 前一个同类型高/低点的指标值
    divergence_strength: float  # 背驰强度（0-100，值越大背驰越明显）


def detect_top_divergence(
    closes: np.ndarray,
    highs: np.ndarray,
    macd_values: np.ndarray,
    window: int = 10
) -> Optional[Divergence]:
    """检测顶背驰：价格创新高，但MACD不创新高

    Args:
        closes: 收盘价数组
        highs: 最高价数组
        macd_values: MACD值数组（DIF或MACD柱）
        window: 检查窗口（回溯K线数）

    Returns:
        Divergence 对象或 None
    """
    if len(closes) < window or len(macd_values) < window:
        return None

    # 取最近window的数据
    recent_highs = highs[-window:]
    recent_macd = macd_values[-window:]
    recent_closes = closes[-window:]

    # 找最新的最高点
    current_high_idx = np.argmax(recent_highs)
    current_high_price = recent_highs[current_high_idx]

    # 找该最高点对应的MACD值
    current_macd = recent_macd[current_high_idx]

    # 找window内除最新外的次高点
    second_highest_idx = np.argmax(np.delete(recent_highs, current_high_idx))
    if second_highest_idx >= current_high_idx:
        second_highest_idx += 1
    prev_high_price = recent_highs[second_highest_idx]
    prev_macd = recent_macd[second_highest_idx]

    # 判断顶背驰：当前价格 > 前高，但当前MACD < 前MACD
    if current_high_price > prev_high_price and current_macd < prev_macd:
        divergence_strength = (prev_macd - current_macd) / max(abs(prev_macd), 0.001) * 100
        return Divergence(
            signal_type="top_divergence",
            bar_idx=len(closes) - 1,
            price=float(current_high_price),
            prev_price=float(prev_high_price),
            indicator_value=float(current_macd),
            prev_indicator_value=float(prev_macd),
            divergence_strength=min(divergence_strength, 100.0),
        )

    return None


def detect_bottom_divergence(
    closes: np.ndarray,
    lows: np.ndarray,
    macd_values: np.ndarray,
    window: int = 10
) -> Optional[Divergence]:
    """检测底背驰：价格创新低，但MACD不创新低

    Args:
        closes: 收盘价数组
        lows: 最低价数组
        macd_values: MACD值数组（DIF或MACD柱）
        window: 检查窗口（回溯K线数）

    Returns:
        Divergence 对象或 None
    """
    if len(closes) < window or len(macd_values) < window:
        return None

    # 取最近window的数据
    recent_lows = lows[-window:]
    recent_macd = macd_values[-window:]
    recent_closes = closes[-window:]

    # 找最新的最低点
    current_low_idx = np.argmin(recent_lows)
    current_low_price = recent_lows[current_low_idx]

    # 找该最低点对应的MACD值（注意底背驰看MACD绝对值）
    current_macd = abs(recent_macd[current_low_idx])

    # 找window内除最新外的次低点
    second_lowest_idx = np.argmin(np.delete(recent_lows, current_low_idx))
    if second_lowest_idx >= current_low_idx:
        second_lowest_idx += 1
    prev_low_price = recent_lows[second_lowest_idx]
    prev_macd = abs(recent_macd[second_lowest_idx])

    # 判断底背驰：当前价格 < 前低，但当前|MACD| < 前|MACD|
    if current_low_price < prev_low_price and current_macd < prev_macd:
        divergence_strength = (prev_macd - current_macd) / max(abs(prev_macd), 0.001) * 100
        return Divergence(
            signal_type="bottom_divergence",
            bar_idx=len(closes) - 1,
            price=float(current_low_price),
            prev_price=float(prev_low_price),
            indicator_value=float(current_macd),
            prev_indicator_value=float(prev_macd),
            divergence_strength=min(divergence_strength, 100.0),
        )

    return None


def detect_buy_points_from_bis(
    bis: List[Bi],
    closes: np.ndarray,
    macd_values: np.ndarray,
    hubs: Optional[List[Hub]] = None
) -> dict:
    """检测缠论买点（一买、二买、三买）

    基于笔和中枢的买点判断

    Args:
        bis: 笔列表
        closes: 收盘价数组
        macd_values: MACD值数组
        hubs: 中枢列表（可选，用于三买判断）

    Returns:
        {
            "first_buy": {...} or None,    # 一买：底背驰
            "second_buy": {...} or None,   # 二买：回踩不破
            "third_buy": {...} or None,    # 三买：中枢回踩
        }
    """
    result = {
        "first_buy": None,
        "second_buy": None,
        "third_buy": None,
    }

    if len(bis) < 2:
        return result

    # 一买：下跌趋势中的底背驰
    # 条件：向下笔后跟向上笔，且最后一笔是向上笔，向下笔出现底背驰
    if bis[-2].direction == -1 and bis[-1].direction == 1:
        # 检查这个向下笔是否是底背驰
        down_bi = bis[-2]
        divergence = detect_bottom_divergence(
            closes=closes,
            lows=closes,  # 简化：用收盘价
            macd_values=macd_values,
            window=20
        )
        if divergence:
            result["first_buy"] = {
                "type": "first_buy",
                "price": float(closes[-1]),
                "bi_index": down_bi.bi_index,
                "divergence_strength": divergence.divergence_strength,
                "description": f"下跌笔底背驰，价格:{divergence.price:.2f}，背驰强度:{divergence.divergence_strength:.1f}%"
            }

    # 二买：一买后回调不破前低
    # 条件：最后两笔是"向上笔、向下笔"，且向下笔的低点 > 前一个向上笔的起点低点
    if len(bis) >= 3 and bis[-2].direction == 1 and bis[-1].direction == -1:
        up_bi = bis[-2]
        down_bi = bis[-1]
        if down_bi.low > up_bi.low:
            result["second_buy"] = {
                "type": "second_buy",
                "price": float(closes[-1]),
                "bi_index": down_bi.bi_index,
                "support_level": float(up_bi.low),
                "description": f"一买后回踩不破，当前价:{closes[-1]:.2f}，支撑:{up_bi.low:.2f}"
            }

    # 三买：中枢突破后回踩不进中枢
    if hubs and len(bis) >= 2:
        latest_hub = hubs[-1]
        current_price = float(closes[-1])
        # 如果当前价格在中枢上方，且最后笔是向下的，且价格没有进中枢
        if current_price > latest_hub.zg and bis[-1].direction == -1:
            if current_price > latest_hub.zd:  # 没有进入中枢
                result["third_buy"] = {
                    "type": "third_buy",
                    "price": current_price,
                    "hub_index": latest_hub.hub_index,
                    "hub_top": float(latest_hub.zg),
                    "description": f"中枢上方回踩不进，当前价:{current_price:.2f}，中枢上沿:{latest_hub.zg:.2f}"
                }

    return result


def detect_sell_points_from_bis(
    bis: List[Bi],
    closes: np.ndarray,
    macd_values: np.ndarray,
    hubs: Optional[List[Hub]] = None
) -> dict:
    """检测缠论卖点（一卖、二卖、三卖）

    基于笔和中枢的卖点判断

    Args:
        bis: 笔列表
        closes: 收盘价数组
        macd_values: MACD值数组
        hubs: 中枢列表（可选，用于三卖判断）

    Returns:
        {
            "first_sell": {...} or None,   # 一卖：顶背驰
            "second_sell": {...} or None,  # 二卖：反弹不破
            "third_sell": {...} or None,   # 三卖：中枢反弹
        }
    """
    result = {
        "first_sell": None,
        "second_sell": None,
        "third_sell": None,
    }

    if len(bis) < 2:
        return result

    # 一卖：上升趋势中的顶背驰
    if bis[-2].direction == 1 and bis[-1].direction == -1:
        up_bi = bis[-2]
        divergence = detect_top_divergence(
            closes=closes,
            highs=closes,
            macd_values=macd_values,
            window=20
        )
        if divergence:
            result["first_sell"] = {
                "type": "first_sell",
                "price": float(closes[-1]),
                "bi_index": up_bi.bi_index,
                "divergence_strength": divergence.divergence_strength,
                "description": f"上升笔顶背驰，价格:{divergence.price:.2f}，背驰强度:{divergence.divergence_strength:.1f}%"
            }

    # 二卖：一卖后反弹不破前高
    if len(bis) >= 3 and bis[-2].direction == -1 and bis[-1].direction == 1:
        down_bi = bis[-2]
        up_bi = bis[-1]
        if up_bi.high < down_bi.high:
            result["second_sell"] = {
                "type": "second_sell",
                "price": float(closes[-1]),
                "bi_index": up_bi.bi_index,
                "resistance_level": float(down_bi.high),
                "description": f"一卖后反弹不破，当前价:{closes[-1]:.2f}，压力:{down_bi.high:.2f}"
            }

    # 三卖：中枢突破后反弹不进中枢
    if hubs and len(bis) >= 2:
        latest_hub = hubs[-1]
        current_price = float(closes[-1])
        # 如果当前价格在中枢下方，且最后笔是向上的，且价格没有进中枢
        if current_price < latest_hub.zd and bis[-1].direction == 1:
            if current_price < latest_hub.zg:  # 没有进入中枢
                result["third_sell"] = {
                    "type": "third_sell",
                    "price": current_price,
                    "hub_index": latest_hub.hub_index,
                    "hub_bottom": float(latest_hub.zd),
                    "description": f"中枢下方反弹不进，当前价:{current_price:.2f}，中枢下沿:{latest_hub.zd:.2f}"
                }

    return result
