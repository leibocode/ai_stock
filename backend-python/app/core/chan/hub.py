"""缠论中枢识别

标准缠论中枢识别规则（基于笔，非线段）：
- 至少3笔的重叠区间形成中枢
- ZG (中枢上沿) = min(3笔的高点)  # 上沿取最小
- ZD (中枢下沿) = max(3笔的低点)  # 下沿取最大
- 有效中枢：ZG > ZD (存在重叠区间)

中枢扩展：
- 如果后续笔进一步扩展中枢的ZG/ZD，形成中枢扩展（不是新中枢）
"""
from typing import List, Literal, Union
from dataclasses import dataclass
from .segment import Segment
from .bi import Bi


@dataclass
class Hub:
    """中枢数据"""
    start_date: str
    end_date: str
    zg: float  # 中枢上沿 - min(高点)
    zd: float  # 中枢下沿 - max(低点)
    gg: float  # 中枢最高点
    dd: float  # 中枢最低点
    hub_index: int = 0
    level: int = 1  # 中枢级别（1=笔级别）
    bi_count: int = 3  # 包含的笔数


def calculate_hub(segments: List[Segment]) -> List[Hub]:
    """基于线段的中枢识别（保留向后兼容）

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

        # 计算重叠区间（标准缠论：上沿=min，下沿=max）
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
                level=1,  # 线段级别的中枢
            ))
            hub_index += 1
            i += 2  # 向前移动2（而非3），允许中枢重叠
        else:
            i += 1

    return hubs


def calculate_hub_from_bis(bis: List[Bi]) -> List[Hub]:
    """基于笔的中枢识别（标准缠论）

    这是标准缠论的中枢定义：至少3笔的重叠区间

    Args:
        bis: 笔列表（需要足够的笔才能形成中枢）

    Returns:
        中枢列表
    """
    if len(bis) < 3:
        return []

    hubs = []
    hub_index = 0
    i = 0

    while i <= len(bis) - 3:
        bi1 = bis[i]
        bi2 = bis[i + 1]
        bi3 = bis[i + 2]

        # 中枢上沿 = 3笔高点的最小值
        zg = min(bi1.high, bi2.high, bi3.high)

        # 中枢下沿 = 3笔低点的最大值
        zd = max(bi1.low, bi2.low, bi3.low)

        # 有效中枢必须满足：上沿 > 下沿
        if zg > zd:
            hubs.append(Hub(
                start_date=bi1.start_date,
                end_date=bi3.end_date,
                zg=zg,
                zd=zd,
                gg=max(bi1.high, bi2.high, bi3.high),
                dd=min(bi1.low, bi2.low, bi3.low),
                hub_index=hub_index,
                level=1,  # 笔级别的中枢
                bi_count=3,
            ))
            hub_index += 1
            i += 2  # 向前移动2，允许中枢重叠或连续
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
