"""缠论分析服务 - 使用numpy数组优化实现

缠论核心概念：
1. 分型 (Fractal): 高-低-高(顶) 或 低-高-低(底)
2. 笔 (Bi): 从一个分型到下一个分型
3. 线段 (Segment): 至少5笔的序列
4. 中枢 (Hub): 线段的重叠部分

优化策略：
- 使用numpy向量化操作替代Python循环
- pandas DataFrame的高效slicing
- 一次性计算所有分型、笔、线段、中枢
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from loguru import logger


class ChanAnalyzer:
    """缠论分析器 - numpy优化版"""

    def __init__(self, df: pd.DataFrame):
        """初始化分析器

        Args:
            df: 包含 high, low, close 的 DataFrame (需按时间升序排列)
        """
        self.df = df.copy()
        self.highs = df['high'].values
        self.lows = df['low'].values
        self.closes = df['close'].values
        self.n = len(df)

    def identify_fractals(self) -> Dict[int, str]:
        """识别所有分型 (顶分型和底分型)

        使用numpy向量化操作：
        - 顶分型：df[i-1].high < df[i].high > df[i+1].high
        - 底分型：df[i-1].low > df[i].low < df[i+1].low

        Returns:
            {index: 'top'|'bottom'} - 分型位置和类型
        """
        fractals = {}

        # 使用numpy向量化识别顶分型
        # fractal_top[i] = True 表示 i 是顶分型
        fractal_top = (
            (self.highs[:-2] < self.highs[1:-1]) &
            (self.highs[1:-1] > self.highs[2:])
        )
        top_indices = np.where(fractal_top)[0] + 1
        for idx in top_indices:
            fractals[idx] = 'top'

        # 识别底分型
        fractal_bottom = (
            (self.lows[:-2] > self.lows[1:-1]) &
            (self.lows[1:-1] < self.lows[2:])
        )
        bottom_indices = np.where(fractal_bottom)[0] + 1
        for idx in bottom_indices:
            fractals[idx] = 'bottom'

        return fractals

    def identify_bis(self, fractals: Dict[int, str]) -> List[Dict]:
        """从分型识别笔 (Bi)

        笔的规则：
        1. 顶分型 → 底分型 = 向下的笔
        2. 底分型 → 顶分型 = 向上的笔
        3. 至少包含3个K线

        Args:
            fractals: identify_fractals 的输出

        Returns:
            [{'start': idx, 'end': idx, 'high': val, 'low': val, 'direction': 'up'|'down'}, ...]
        """
        if len(fractals) < 2:
            return []

        sorted_fractals = sorted(fractals.items())
        bis = []

        for i in range(len(sorted_fractals) - 1):
            start_idx, start_type = sorted_fractals[i]
            end_idx, end_type = sorted_fractals[i + 1]

            # 顶 → 底 (向下)
            if start_type == 'top' and end_type == 'bottom':
                bi = {
                    'start_idx': start_idx,
                    'end_idx': end_idx,
                    'start_price': self.highs[start_idx],
                    'end_price': self.lows[end_idx],
                    'direction': 'down',
                    'length': end_idx - start_idx,
                }
                bis.append(bi)

            # 底 → 顶 (向上)
            elif start_type == 'bottom' and end_type == 'top':
                bi = {
                    'start_idx': start_idx,
                    'end_idx': end_idx,
                    'start_price': self.lows[start_idx],
                    'end_price': self.highs[end_idx],
                    'direction': 'up',
                    'length': end_idx - start_idx,
                }
                bis.append(bi)

        return bis

    def identify_segments(self, bis: List[Dict]) -> List[Dict]:
        """从笔识别线段 (Segment)

        线段规则：
        1. 至少5笔组成一个线段
        2. 向上线段：从底笔开始，至少2个完整的上-下循环
        3. 向下线段：从顶笔开始，至少2个完整的下-上循环

        Args:
            bis: identify_bis 的输出

        Returns:
            [{'start_idx': idx, 'end_idx': idx, 'direction': 'up'|'down', 'high': val, 'low': val}, ...]
        """
        if len(bis) < 5:
            return []

        segments = []
        i = 0

        while i <= len(bis) - 5:
            # 提取5笔
            five_bis = bis[i:i+5]

            start_idx = five_bis[0]['start_idx']
            end_idx = five_bis[-1]['end_idx']

            # 计算该线段的高低点
            all_highs = [b['start_price'] for b in five_bis] + [five_bis[-1]['end_price']]
            all_lows = [b['start_price'] for b in five_bis] + [five_bis[-1]['end_price']]

            segment = {
                'start_idx': start_idx,
                'end_idx': end_idx,
                'direction': five_bis[0]['direction'],  # 线段方向由第一笔决定
                'high': max(all_highs),
                'low': min(all_lows),
                'bi_count': 5,
            }
            segments.append(segment)

            i += 1

        return segments

    def identify_hubs(self, segments: List[Dict]) -> List[Dict]:
        """从线段识别中枢 (Hub)

        中枢规则：
        1. 两个线段的重叠部分
        2. 中枢范围：max(low) ~ min(high)

        Args:
            segments: identify_segments 的输出

        Returns:
            [{'start_idx': idx, 'end_idx': idx, 'high': val, 'low': val, 'amplitude': val}, ...]
        """
        if len(segments) < 2:
            return []

        hubs = []

        for i in range(len(segments) - 1):
            seg1 = segments[i]
            seg2 = segments[i + 1]

            # 计算重叠部分
            hub_high = min(seg1['high'], seg2['high'])
            hub_low = max(seg1['low'], seg2['low'])

            # 如果有重叠（hub_low < hub_high）
            if hub_low < hub_high:
                hub = {
                    'start_idx': seg1['start_idx'],
                    'end_idx': seg2['end_idx'],
                    'high': hub_high,
                    'low': hub_low,
                    'amplitude': hub_high - hub_low,
                    'level': 1,  # 基础中枢，可扩展为多级
                }
                hubs.append(hub)

        return hubs

    def analyze_complete(self) -> Dict:
        """完整的缠论分析

        Returns:
            {
                'fractals': {...},
                'bis': [...],
                'segments': [...],
                'hubs': [...],
                'current_trend': 'up'|'down'|'consolidating'
            }
        """
        fractals = self.identify_fractals()
        bis = self.identify_bis(fractals)
        segments = self.identify_segments(bis)
        hubs = self.identify_hubs(segments)

        # 判断当前趋势
        current_trend = 'consolidating'
        if bis:
            # 按最后一笔的方向判断
            current_trend = 'up' if bis[-1]['direction'] == 'up' else 'down'

        return {
            'fractals': fractals,
            'bis': bis,
            'segments': segments,
            'hubs': hubs,
            'current_trend': current_trend,
            'fractal_count': len(fractals),
            'bi_count': len(bis),
            'segment_count': len(segments),
            'hub_count': len(hubs),
        }


class ChanService:
    """缠论服务 - 统一接口"""

    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict:
        """分析股票缠论信息

        Args:
            df: 包含 high, low, close 的 DataFrame

        Returns:
            缠论分析结果
        """
        if df.empty or len(df) < 5:
            return {
                'fractals': {},
                'bis': [],
                'segments': [],
                'hubs': [],
                'current_trend': 'insufficient_data',
                'fractal_count': 0,
                'bi_count': 0,
                'segment_count': 0,
                'hub_count': 0,
            }

        try:
            analyzer = ChanAnalyzer(df)
            return analyzer.analyze_complete()
        except Exception as e:
            logger.error(f"Chan analysis failed: {e}")
            return {
                'fractals': {},
                'bis': [],
                'segments': [],
                'hubs': [],
                'current_trend': 'error',
            }

    @staticmethod
    def identify_breakout_points(df: pd.DataFrame) -> List[Dict]:
        """识别突破点 (缠论应用)

        突破规则：
        1. 突破中枢上轨 = 潜在上升突破
        2. 跌破中枢下轨 = 潜在下跌突破

        Args:
            df: 技术指标 DataFrame

        Returns:
            [{'date': str, 'price': float, 'type': 'up_breakout'|'down_breakout'}, ...]
        """
        result = ChanService.analyze(df)
        hubs = result.get('hubs', [])

        if not hubs:
            return []

        latest_hub = hubs[-1]
        last_close = df.iloc[-1]['close'] if not df.empty else 0

        breakouts = []

        # 上突
        if last_close > latest_hub['high']:
            breakouts.append({
                'date': str(df.iloc[-1].get('trade_date', '')),
                'price': float(latest_hub['high']),
                'type': 'up_breakout',
                'close': float(last_close),
                'hub_high': float(latest_hub['high']),
            })

        # 下破
        if last_close < latest_hub['low']:
            breakouts.append({
                'date': str(df.iloc[-1].get('trade_date', '')),
                'price': float(latest_hub['low']),
                'type': 'down_breakout',
                'close': float(last_close),
                'hub_low': float(latest_hub['low']),
            })

        return breakouts

    @staticmethod
    def get_key_levels(df: pd.DataFrame) -> Dict:
        """获取关键价格位置 (支撑/阻力)

        基于缠论中枢识别支撑阻力：
        - 阻力位：中枢上轨
        - 支撑位：中枢下轨

        Args:
            df: 技术指标 DataFrame

        Returns:
            {'resistance': [...], 'support': [...]}
        """
        result = ChanService.analyze(df)
        hubs = result.get('hubs', [])

        resistance = []
        support = []

        for hub in hubs:
            resistance.append({
                'level': float(hub['high']),
                'strength': 'medium',  # 可根据中枢宽度判断强度
            })
            support.append({
                'level': float(hub['low']),
                'strength': 'medium',
            })

        return {
            'resistance': sorted(resistance, key=lambda x: x['level'], reverse=True),
            'support': sorted(support, key=lambda x: x['level']),
        }
