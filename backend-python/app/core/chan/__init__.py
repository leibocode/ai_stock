"""缠论模块

缠论是一种技术分析方法，核心概念：
- 分型：顶分型和底分型
- 笔：连接相邻顶底分型
- 线段：由至少3笔构成
- 中枢：至少3笔的重叠区间（标准缠论）

买卖点（基于背驰）：
- 一买/一卖：第一个底/顶背驰（价格创新低/高，指标不创新）
- 二买/二卖：回调/反弹不破前低/高
- 三买/三卖：中枢下方/上方回踩/反弹不进中枢

关键改进：
- 中枢从线段级别升级为笔级别（calculate_hub_from_bis）
- 完整的背驰信号检测（顶/底背驰、一二三买卖点）
- MACD改正（标准计算，无乘2）
"""
from .fractal import Fractal, merge_klines, calculate_fractals, process_klines_to_fractals
from .bi import Bi, calculate_bi, get_latest_bi
from .segment import Segment, calculate_segment, get_latest_segment
from .hub import Hub, calculate_hub, calculate_hub_from_bis, get_latest_hub, get_price_position
from .divergence import (
    Divergence,
    detect_top_divergence,
    detect_bottom_divergence,
    detect_buy_points_from_bis,
    detect_sell_points_from_bis,
)
from .chan_service import ChanService, ChanResult

__all__ = [
    # 数据结构
    "Fractal", "Bi", "Segment", "Hub", "Divergence", "ChanResult",
    # 分型、笔、线段、中枢计算
    "merge_klines", "calculate_fractals", "process_klines_to_fractals",
    "calculate_bi", "get_latest_bi",
    "calculate_segment", "get_latest_segment",
    "calculate_hub", "calculate_hub_from_bis", "get_latest_hub", "get_price_position",
    # 背驰和买卖点检测（核心）
    "detect_top_divergence", "detect_bottom_divergence",
    "detect_buy_points_from_bis", "detect_sell_points_from_bis",
    # 服务
    "ChanService",
]
