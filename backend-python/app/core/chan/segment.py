"""缠论线段划分

线段是由至少3笔构成的更大级别的走势：
- 向上线段：以向上笔开始，在新低出现时结束
- 向下线段：以向下笔开始，在新高出现时结束
"""
from typing import List, Literal
from dataclasses import dataclass
from .bi import Bi


@dataclass
class Segment:
    """线段数据"""
    start_date: str
    end_date: str
    direction: Literal[1, -1]  # 1=向上线段, -1=向下线段
    high: float
    low: float
    seg_index: int = 0


def calculate_segment(bis: List[Bi]) -> List[Segment]:
    """线段划分

    规则：
    1. 至少3笔构成一个线段
    2. 向上线段结束条件：出现向下笔创新低（低于前一笔的低点）
    3. 向下线段结束条件：出现向上笔创新高（高于前一笔的高点）

    Args:
        bis: 笔列表

    Returns:
        线段列表
    """
    if len(bis) < 3:
        return []

    segments = []
    seg_index = 0
    seg_start = 0

    for i in range(2, len(bis)):
        bi1 = bis[i - 2]
        bi2 = bis[i - 1]
        bi3 = bis[i]

        # 向上线段结束条件：向下笔创新低
        if bi1.direction == 1 and bi3.low < bi2.low:
            # 计算线段范围内的高低点
            segment_bis = bis[seg_start:i]
            seg_high = max(bi.high for bi in segment_bis)
            seg_low = min(bi.low for bi in segment_bis)

            segments.append(Segment(
                start_date=bis[seg_start].start_date,
                end_date=bi2.end_date,
                direction=1,
                high=seg_high,
                low=seg_low,
                seg_index=seg_index,
            ))
            seg_index += 1
            seg_start = i - 1

        # 向下线段结束条件：向上笔创新高
        elif bi1.direction == -1 and bi3.high > bi2.high:
            segment_bis = bis[seg_start:i]
            seg_high = max(bi.high for bi in segment_bis)
            seg_low = min(bi.low for bi in segment_bis)

            segments.append(Segment(
                start_date=bis[seg_start].start_date,
                end_date=bi2.end_date,
                direction=-1,
                high=seg_high,
                low=seg_low,
                seg_index=seg_index,
            ))
            seg_index += 1
            seg_start = i - 1

    # 处理最后一个线段
    if seg_start < len(bis) - 1:
        last_bis = bis[seg_start:]
        segments.append(Segment(
            start_date=last_bis[0].start_date,
            end_date=last_bis[-1].end_date,
            direction=last_bis[0].direction,
            high=max(bi.high for bi in last_bis),
            low=min(bi.low for bi in last_bis),
            seg_index=seg_index,
        ))

    return segments


def get_latest_segment(segments: List[Segment]) -> Segment | None:
    """获取最新线段"""
    return segments[-1] if segments else None


def get_segment_direction_str(direction: int) -> str:
    """获取线段方向描述"""
    return "向上" if direction == 1 else "向下"
