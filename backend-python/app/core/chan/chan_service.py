"""缠论计算服务

整合分型、笔、线段、中枢的计算流程
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from loguru import logger

from .fractal import merge_klines, calculate_fractals, Fractal
from .bi import calculate_bi, Bi
from .segment import calculate_segment, Segment
from .hub import calculate_hub, Hub, get_price_position


@dataclass
class ChanResult:
    """缠论计算结果"""
    ts_code: str
    fractals: List[Fractal]
    bis: List[Bi]
    segments: List[Segment]
    hubs: List[Hub]

    # 最新状态
    latest_fractal_type: Optional[str] = None  # "顶分型" / "底分型"
    latest_bi_direction: Optional[str] = None  # "向上" / "向下"
    latest_segment_direction: Optional[str] = None
    current_hub: Optional[Hub] = None
    price_position: Optional[str] = None  # "above" / "below" / "inside"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "ts_code": self.ts_code,
            "fractals": [asdict(f) for f in self.fractals[-10:]],  # 最近10个分型
            "bis": [asdict(b) for b in self.bis[-10:]],            # 最近10笔
            "segments": [asdict(s) for s in self.segments[-5:]],   # 最近5个线段
            "hubs": [asdict(h) for h in self.hubs[-3:]],           # 最近3个中枢
            "latest_fractal_type": self.latest_fractal_type,
            "latest_bi_direction": self.latest_bi_direction,
            "latest_segment_direction": self.latest_segment_direction,
            "current_hub": asdict(self.current_hub) if self.current_hub else None,
            "price_position": self.price_position,
        }


class ChanService:
    """缠论计算服务"""

    def __init__(self, min_klines: int = 100):
        """初始化

        Args:
            min_klines: 最小K线数量要求
        """
        self.min_klines = min_klines

    def calculate(self, ts_code: str, klines: List[Dict]) -> Optional[ChanResult]:
        """计算缠论指标

        完整流程：
        1. K线包含处理
        2. 分型识别
        3. 笔划分
        4. 线段划分
        5. 中枢识别

        Args:
            ts_code: 股票代码
            klines: K线数据列表 (按时间正序)
                   需要包含: trade_date, high, low, close

        Returns:
            ChanResult 或 None (数据不足时)
        """
        if len(klines) < self.min_klines:
            logger.warning(f"{ts_code}: K线数量不足 ({len(klines)} < {self.min_klines})")
            return None

        try:
            # 1. K线包含处理
            merged_klines = merge_klines(klines)

            # 2. 分型识别
            fractals = calculate_fractals(merged_klines)

            # 3. 笔划分
            bis = calculate_bi(fractals)

            # 4. 线段划分
            segments = calculate_segment(bis)

            # 5. 中枢识别
            hubs = calculate_hub(segments)

            # 构建结果
            result = ChanResult(
                ts_code=ts_code,
                fractals=fractals,
                bis=bis,
                segments=segments,
                hubs=hubs,
            )

            # 填充最新状态
            self._fill_latest_status(result, klines[-1])

            return result

        except Exception as e:
            logger.error(f"{ts_code}: 缠论计算失败 - {e}")
            return None

    def _fill_latest_status(self, result: ChanResult, latest_kline: Dict):
        """填充最新状态信息"""
        # 最新分型
        if result.fractals:
            f = result.fractals[-1]
            result.latest_fractal_type = "顶分型" if f.fractal_type == 1 else "底分型"

        # 最新笔
        if result.bis:
            b = result.bis[-1]
            result.latest_bi_direction = "向上" if b.direction == 1 else "向下"

        # 最新线段
        if result.segments:
            s = result.segments[-1]
            result.latest_segment_direction = "向上" if s.direction == 1 else "向下"

        # 当前中枢和价格位置
        if result.hubs:
            result.current_hub = result.hubs[-1]
            current_price = float(latest_kline.get("close", 0))
            if current_price > 0:
                result.price_position = get_price_position(current_price, result.current_hub)

    def get_buy_signals(self, result: ChanResult) -> List[str]:
        """识别买点信号

        一买：底背驰后的第一个向上笔
        二买：一买后回调不破一买低点
        三买：中枢突破后的回踩

        Args:
            result: 缠论计算结果

        Returns:
            买点信号列表
        """
        signals = []

        if not result.bis or len(result.bis) < 3:
            return signals

        latest_bi = result.bis[-1]
        prev_bi = result.bis[-2]

        # 简化判断：最新是向上笔，且在中枢上方
        if latest_bi.direction == 1:
            if result.price_position == "above":
                signals.append("三买信号: 中枢突破")
            elif result.price_position == "inside":
                signals.append("潜在二买: 中枢震荡")

        # 底部反转信号
        if (latest_bi.direction == 1 and
            prev_bi.direction == -1 and
            latest_bi.high > prev_bi.high):
            signals.append("一买信号: 底部反转")

        return signals

    def get_sell_signals(self, result: ChanResult) -> List[str]:
        """识别卖点信号

        一卖：顶背驰后的第一个向下笔
        二卖：一卖后反弹不破一卖高点
        三卖：中枢跌破后的反弹

        Args:
            result: 缠论计算结果

        Returns:
            卖点信号列表
        """
        signals = []

        if not result.bis or len(result.bis) < 3:
            return signals

        latest_bi = result.bis[-1]
        prev_bi = result.bis[-2]

        # 简化判断：最新是向下笔，且在中枢下方
        if latest_bi.direction == -1:
            if result.price_position == "below":
                signals.append("三卖信号: 中枢跌破")
            elif result.price_position == "inside":
                signals.append("潜在二卖: 中枢震荡")

        # 顶部反转信号
        if (latest_bi.direction == -1 and
            prev_bi.direction == 1 and
            latest_bi.low < prev_bi.low):
            signals.append("一卖信号: 顶部反转")

        return signals
