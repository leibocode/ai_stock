"""缠论中枢识别

中枢是至少3个连续线段的重叠区间：
- ZG (中枢上沿)：三个线段高点的最小值
- ZD (中枢下沿)：三个线段低点的最大值
- 有效中枢：ZG > ZD (存在重叠区间)
"""
from typing import List, Literal
from dataclasses import dataclass
from .segment import Segment


@dataclass
class Hub:
    """中枢数据"""
    start_date: str
    end_date: str
    zg: float  # 中枢上沿
    zd: float  # 中枢下沿
    gg: float  # 中枢最高点
    dd: float  # 中枢最低点
    hub_index: int = 0
    level: int = 1  # 中枢级别


def calculate_hub(segments: List[Segment]) -> List[Hub]:
    """中枢识别

    规则：
    1. 至少3个线段形成中枢
    2. 中枢上沿 ZG = min(各线段高点)
    3. 中枢下沿 ZD = max(各线段低点)
    4. 有效中枢：ZG > ZD

    Args:
        segments: 线段列表

    Returns:
        中枢列表
    """
    if len(segments) < 3:
        return []

    hubs = []
    hub_index = 0
    i = 0

    while i <= len(segments) - 3:
        seg1 = segments[i]
        seg2 = segments[i + 1]
        seg3 = segments[i + 2]

        # 计算重叠区间
        zg = min(seg1.high, seg2.high, seg3.high)  # 中枢上沿
        zd = max(seg1.low, seg2.low, seg3.low)     # 中枢下沿

        # 有效中枢：上沿 > 下沿
        if zg > zd:
            hubs.append(Hub(
                start_date=seg1.start_date,
                end_date=seg3.end_date,
                zg=zg,
                zd=zd,
                gg=max(seg1.high, seg2.high, seg3.high),
                dd=min(seg1.low, seg2.low, seg3.low),
                hub_index=hub_index,
            ))
            hub_index += 1
            i += 3  # 跳过已使用的线段
        else:
            i += 1

    return hubs


def get_latest_hub(hubs: List[Hub]) -> Hub | None:
    """获取最新中枢"""
    return hubs[-1] if hubs else None


def get_hub_range(hub: Hub) -> float:
    """获取中枢振幅"""
    return round((hub.zg - hub.zd) / hub.zd * 100, 2) if hub.zd > 0 else 0


def is_price_above_hub(price: float, hub: Hub) -> bool:
    """判断价格是否在中枢上方"""
    return price > hub.zg


def is_price_below_hub(price: float, hub: Hub) -> bool:
    """判断价格是否在中枢下方"""
    return price < hub.zd


def is_price_in_hub(price: float, hub: Hub) -> bool:
    """判断价格是否在中枢内"""
    return hub.zd <= price <= hub.zg


def get_price_position(price: float, hub: Hub) -> Literal["above", "below", "inside"]:
    """获取价格相对中枢的位置"""
    if price > hub.zg:
        return "above"
    elif price < hub.zd:
        return "below"
    else:
        return "inside"
