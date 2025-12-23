"""缠论分型识别

分型是缠论的基础，包括：
- K线包含处理：消除K线包含关系
- 顶分型：中间K线高点最高
- 底分型：中间K线低点最低
"""
from typing import List, Dict, Literal
from dataclasses import dataclass


@dataclass
class Kline:
    """K线数据"""
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    vol: float = 0


@dataclass
class Fractal:
    """分型数据"""
    trade_date: str
    fractal_type: Literal[1, -1]  # 1=顶分型, -1=底分型
    high: float
    low: float
    index: int = 0


def merge_klines(klines: List[Dict]) -> List[Dict]:
    """K线包含处理

    包含关系：
    - 当前K线完全在前一根K线范围内
    - 或前一根K线完全在当前K线范围内

    合并规则：
    - 向上时取高高低高 (取两根K线的高点中的高者，低点中的高者)
    - 向下时取低低高低 (取两根K线的高点中的低者，低点中的低者)

    Args:
        klines: K线列表 [{trade_date, high, low, ...}]

    Returns:
        合并后的K线列表
    """
    if len(klines) < 2:
        return klines

    merged = [klines[0].copy()]
    direction = 0  # 0:未知 1:向上 -1:向下

    for i in range(1, len(klines)):
        prev = merged[-1]
        curr = klines[i]

        curr_high = float(curr.get("high", 0))
        curr_low = float(curr.get("low", 0))
        prev_high = float(prev.get("high", 0))
        prev_low = float(prev.get("low", 0))

        # 判断包含关系
        is_contain = (
            (curr_high <= prev_high and curr_low >= prev_low) or
            (curr_high >= prev_high and curr_low <= prev_low)
        )

        if is_contain:
            # 确定方向
            if direction == 0:
                direction = 1 if curr_high > prev_high else -1

            # 合并K线
            if direction == 1:
                # 向上：取高高低高
                merged[-1]["high"] = max(prev_high, curr_high)
                merged[-1]["low"] = max(prev_low, curr_low)
            else:
                # 向下：取低低高低
                merged[-1]["high"] = min(prev_high, curr_high)
                merged[-1]["low"] = min(prev_low, curr_low)
        else:
            # 更新方向
            if curr_high > prev_high:
                direction = 1
            elif curr_low < prev_low:
                direction = -1

            merged.append(curr.copy())

    return merged


def calculate_fractals(klines: List[Dict]) -> List[Fractal]:
    """识别分型

    顶分型：中间K线的高点 > 左右两根K线的高点
    底分型：中间K线的低点 < 左右两根K线的低点

    Args:
        klines: 已合并的K线列表

    Returns:
        分型列表
    """
    if len(klines) < 3:
        return []

    fractals = []

    for i in range(1, len(klines) - 1):
        prev = klines[i - 1]
        curr = klines[i]
        next_k = klines[i + 1]

        prev_high = float(prev.get("high", 0))
        prev_low = float(prev.get("low", 0))
        curr_high = float(curr.get("high", 0))
        curr_low = float(curr.get("low", 0))
        next_high = float(next_k.get("high", 0))
        next_low = float(next_k.get("low", 0))

        # 顶分型
        if curr_high > prev_high and curr_high > next_high:
            fractals.append(Fractal(
                trade_date=curr.get("trade_date", ""),
                fractal_type=1,
                high=curr_high,
                low=curr_low,
                index=i,
            ))
        # 底分型
        elif curr_low < prev_low and curr_low < next_low:
            fractals.append(Fractal(
                trade_date=curr.get("trade_date", ""),
                fractal_type=-1,
                high=curr_high,
                low=curr_low,
                index=i,
            ))

    return fractals


def process_klines_to_fractals(klines: List[Dict]) -> List[Fractal]:
    """完整的分型处理流程

    1. K线包含处理
    2. 分型识别

    Args:
        klines: 原始K线数据 (按时间正序)

    Returns:
        分型列表
    """
    merged = merge_klines(klines)
    return calculate_fractals(merged)
