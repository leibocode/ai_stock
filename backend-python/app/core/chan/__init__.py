"""缠论模块

缠论是一种技术分析方法，核心概念：
- 分型：顶分型和底分型
- 笔：连接相邻顶底分型
- 线段：由至少3笔构成
- 中枢：至少3个线段的重叠区间

买卖点：
- 一买/一卖：背驰后的反转
- 二买/二卖：回调/反弹不破前高低
- 三买/三卖：中枢突破/跌破后的回踩/反弹
"""
from .fractal import Fractal, merge_klines, calculate_fractals, process_klines_to_fractals
from .bi import Bi, calculate_bi, get_latest_bi
from .segment import Segment, calculate_segment, get_latest_segment
from .hub import Hub, calculate_hub, get_latest_hub, get_price_position
from .chan_service import ChanService, ChanResult

__all__ = [
    # 数据结构
    "Fractal", "Bi", "Segment", "Hub", "ChanResult",
    # 计算函数
    "merge_klines", "calculate_fractals", "process_klines_to_fractals",
    "calculate_bi", "get_latest_bi",
    "calculate_segment", "get_latest_segment",
    "calculate_hub", "get_latest_hub", "get_price_position",
    # 服务
    "ChanService",
]
