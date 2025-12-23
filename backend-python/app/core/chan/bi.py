"""缠论笔划分

笔是连接相邻顶底分型的线段：
- 向上笔：从底分型到顶分型
- 向下笔：从顶分型到底分型
- 有效笔需要满足：顶底交替，且价格突破
"""
from typing import List, Literal
from dataclasses import dataclass
from .fractal import Fractal


@dataclass
class Bi:
    """笔数据"""
    start_date: str
    end_date: str
    direction: Literal[1, -1]  # 1=向上笔, -1=向下笔
    high: float
    low: float
    bi_index: int = 0


def calculate_bi(fractals: List[Fractal]) -> List[Bi]:
    """笔划分

    规则：
    1. 顶底分型必须交替出现
    2. 向上笔：从底分型到顶分型，顶分型高点必须高于底分型高点
    3. 向下笔：从顶分型到底分型，底分型低点必须低于顶分型低点
    4. 同向分型取极值（顶分型取更高的，底分型取更低的）

    Args:
        fractals: 分型列表

    Returns:
        笔列表
    """
    if len(fractals) < 2:
        return []

    bis = []
    bi_index = 0
    last_fractal = None

    for f in fractals:
        if last_fractal is None:
            last_fractal = f
            continue

        # 顶底交替
        if f.fractal_type != last_fractal.fractal_type:
            # 向上笔：从底到顶
            if f.fractal_type == 1 and f.high > last_fractal.high:
                bis.append(Bi(
                    start_date=last_fractal.trade_date,
                    end_date=f.trade_date,
                    direction=1,
                    high=f.high,
                    low=last_fractal.low,
                    bi_index=bi_index,
                ))
                bi_index += 1
                last_fractal = f

            # 向下笔：从顶到底
            elif f.fractal_type == -1 and f.low < last_fractal.low:
                bis.append(Bi(
                    start_date=last_fractal.trade_date,
                    end_date=f.trade_date,
                    direction=-1,
                    high=last_fractal.high,
                    low=f.low,
                    bi_index=bi_index,
                ))
                bi_index += 1
                last_fractal = f

        # 同向分型，取极值
        else:
            if f.fractal_type == 1 and f.high > last_fractal.high:
                # 新的顶分型更高，更新
                last_fractal = f
            elif f.fractal_type == -1 and f.low < last_fractal.low:
                # 新的底分型更低，更新
                last_fractal = f

    return bis


def get_bi_direction_str(direction: int) -> str:
    """获取笔方向描述"""
    return "向上" if direction == 1 else "向下"


def get_latest_bi(bis: List[Bi]) -> Bi | None:
    """获取最新的笔"""
    return bis[-1] if bis else None


def count_bi_by_direction(bis: List[Bi]) -> dict:
    """统计笔的方向分布"""
    up_count = sum(1 for bi in bis if bi.direction == 1)
    down_count = len(bis) - up_count
    return {"up": up_count, "down": down_count, "total": len(bis)}
