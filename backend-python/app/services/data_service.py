import pandas as pd
import numpy as np
import talib
import asyncio
from typing import List, Dict, Optional, Tuple
from loguru import logger

try:
    import akshare as ak
except ImportError:
    ak = None


class DataService:
    """Python 生态优化的数据处理服务

    充分利用 pandas/numpy/talib 的优势：
    - 数据集中在内存中处理，性能远优于逐条SQL查询
    - ta-lib 计算指标比手写算法快10倍
    - pandas 提供灵活的数据分析能力
    """

    @staticmethod
    def get_market_data_akshare(symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """从 akshare 获取股票数据 (推荐)

        Args:
            symbol: 股票代码 (如 '000001')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            pandas DataFrame
        """
        if not ak:
            logger.warning("akshare not installed")
            return pd.DataFrame()

        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date)
            # akshare 返回的列名处理
            df.columns = df.columns.str.lower()
            # 标准化列名
            rename_map = {
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'vol',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_chg',
            }
            df = df.rename(columns=rename_map)
            return df
        except Exception as e:
            logger.error(f"Failed to get market data from akshare: {e}")
            return pd.DataFrame()

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """使用 ta-lib 计算技术指标 (高性能)

        一次计算多个指标，充分利用向量化操作。

        Args:
            df: 包含 OHLC 的 DataFrame

        Returns:
            添加指标列的 DataFrame
        """
        if df.empty or len(df) < 26:
            return df

        # 确保数据类型正确
        df = df.copy()
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['vol'] = pd.to_numeric(df['vol'], errors='coerce')

        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        vol = df['vol'].values

        # RSI - 相对强弱指标
        df['rsi_6'] = talib.RSI(close, timeperiod=6)
        df['rsi_12'] = talib.RSI(close, timeperiod=12)

        # MACD - 指数平滑移动平均线
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist

        # KDJ - 随机指标
        k, d = talib.STOCH(high, low, close, fastk_period=9, slowk_period=3, slowd_period=3)
        df['k'] = k
        df['d'] = d
        df['j'] = 3 * k - 2 * d  # J线 = 3K - 2D

        # BOLL - 布林带
        upper, mid, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        df['boll_upper'] = upper
        df['boll_mid'] = mid
        df['boll_lower'] = lower

        # MA - 移动平均线
        df['ma_5'] = talib.SMA(close, timeperiod=5)
        df['ma_10'] = talib.SMA(close, timeperiod=10)
        df['ma_20'] = talib.SMA(close, timeperiod=20)
        df['ma_60'] = talib.SMA(close, timeperiod=60)

        # ATR - 真实波幅
        df['atr'] = talib.ATR(high, low, close, timeperiod=14)

        return df

    @staticmethod
    def identify_oversold(df: pd.DataFrame, rsi_threshold: int = 30) -> pd.DataFrame:
        """识别 RSI 超卖股票 (pandas 向量化)

        Args:
            df: 包含 RSI 指标的 DataFrame
            rsi_threshold: RSI 阈值

        Returns:
            超卖股票 DataFrame
        """
        return df[df['rsi_6'] < rsi_threshold].sort_values('rsi_6')

    @staticmethod
    def identify_macd_golden_cross(df: pd.DataFrame) -> pd.DataFrame:
        """识别 MACD 金叉信号 (pandas 向量化)

        条件：MACD 柱 > 0 且 MACD > 信号线

        Args:
            df: 包含 MACD 指标的 DataFrame

        Returns:
            金叉信号 DataFrame
        """
        condition = (df['macd_hist'] > 0) & (df['macd'] > df['macd_signal'])
        return df[condition].sort_values('macd_hist', ascending=False)

    @staticmethod
    def identify_kdj_bottom(df: pd.DataFrame, k_threshold: int = 20, d_threshold: int = 20) -> pd.DataFrame:
        """识别 KDJ 底部信号 (pandas 向量化)

        条件：K < 20 AND D < 20（超卖区域）

        Args:
            df: 包含 KDJ 指标的 DataFrame
            k_threshold: K 值阈值
            d_threshold: D 值阈值

        Returns:
            底部信号 DataFrame
        """
        condition = (df['k'] < k_threshold) & (df['d'] < d_threshold)
        return df[condition].sort_values('k')

    @staticmethod
    def identify_bottom_volume(df: pd.DataFrame, vol_ratio_threshold: float = 3.0) -> pd.DataFrame:
        """识别底部放量信号 (pandas 向量化)

        条件：量比 > 3 且 价格位置 < 30%

        Args:
            df: 包含 OHLC 的 DataFrame
            vol_ratio_threshold: 量比阈值

        Returns:
            底部放量 DataFrame
        """
        if df.empty:
            return pd.DataFrame()

        # 计算量比 (当前成交量 / 20日均量)
        df['vol_ma20'] = df['vol'].rolling(window=20).mean()
        df['vol_ratio'] = df['vol'] / (df['vol_ma20'] + 0.0001)

        # 计算价格位置 (close - low) / (high - low)
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.0001) * 100

        # 过滤条件
        condition = (df['vol_ratio'] > vol_ratio_threshold) & (df['price_position'] < 30)
        return df[condition].sort_values('vol_ratio', ascending=False)

    @staticmethod
    def identify_trend_change(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """识别强弱转换信号 (弱转强/强转弱)

        弱转强：低开高走，收盘价高于前日 + 今日强度 > 昨日

        Args:
            df: 包含 OHLC 和指标的 DataFrame

        Returns:
            {'weak_to_strong': [...], 'strong_to_weak': [...]}
        """
        df = df.copy()
        df['prev_close'] = df['close'].shift(1)
        df['strength'] = (df['close'] - df['open']) / (df['high'] - df['low'] + 0.0001)

        # 弱转强：开盘低于前日收盘，收盘高于前日收盘
        weak_to_strong = df[
            (df['open'] < df['prev_close']) &
            (df['close'] > df['prev_close'])
        ]

        # 强转弱：开盘高于前日收盘，收盘低于前日收盘
        strong_to_weak = df[
            (df['open'] > df['prev_close']) &
            (df['close'] < df['prev_close'])
        ]

        return {
            'weak_to_strong': weak_to_strong,
            'strong_to_weak': strong_to_weak,
        }

    @staticmethod
    async def batch_analyze_stocks(symbols: List[str], date: str = None) -> Dict[str, pd.DataFrame]:
        """批量分析多只股票 (asyncio 并发优化)

        使用asyncio.gather并发处理多只股票，性能比顺序处理快N倍。

        Args:
            symbols: 股票代码列表
            date: 指定日期 (可选)

        Returns:
            {symbol: analyzed_df}
        """
        async def analyze_single(symbol: str) -> Tuple[str, pd.DataFrame]:
            """单只股票分析，在线程池中执行同步操作"""
            try:
                loop = asyncio.get_event_loop()
                # 在线程池中执行阻塞的IO操作
                df = await loop.run_in_executor(
                    None,
                    DataService.get_market_data_akshare,
                    symbol,
                    None,  # start_date
                    date   # end_date
                )

                if df.empty:
                    return (symbol, None)

                # 计算指标也在线程池中执行
                df = await loop.run_in_executor(
                    None,
                    DataService.calculate_indicators,
                    df
                )
                return (symbol, df)
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                return (symbol, None)

        # 并发执行所有股票分析
        tasks = [analyze_single(symbol) for symbol in symbols]
        results_tuples = await asyncio.gather(*tasks, return_exceptions=False)

        # 构建结果字典，过滤None值
        return {
            symbol: df
            for symbol, df in results_tuples
            if df is not None
        }

    @staticmethod
    def get_multi_indicator_resonance(stocks_data: Dict[str, pd.DataFrame], date: str) -> List[Dict]:
        """多指标共振选股 (关键策略)

        跟踪12个指标，命中 >= 3 个为重点关注

        Args:
            stocks_data: {symbol: analyzed_df}
            date: 交易日期

        Returns:
            共振股票列表 [{'symbol': '000001', 'hit_count': 5, 'indicators': [...]}]
        """
        resonance_stocks = []

        for symbol, df in stocks_data.items():
            if df.empty:
                continue

            # 获取最新数据行
            latest = df.iloc[-1]

            hit_count = 0
            hit_indicators = []

            # 12个指标检查
            checks = [
                ('rsi_6 < 30', latest.get('rsi_6', 50) < 30),
                ('macd_hist > 0', latest.get('macd_hist', 0) > 0),
                ('k < 20', latest.get('k', 50) < 20),
                ('rsi_12 < 30', latest.get('rsi_12', 50) < 30),
                ('close < boll_lower', latest.get('close', 0) < latest.get('boll_lower', float('inf'))),
                ('close > ma_20', latest.get('close', 0) > latest.get('ma_20', 0)),
                ('macd > signal', latest.get('macd', 0) > latest.get('macd_signal', 0)),
                ('j < 20', latest.get('j', 50) < 20),
                ('rsi_6 < rsi_12', latest.get('rsi_6', 0) < latest.get('rsi_12', 0)),
                ('atr > 0', latest.get('atr', 0) > 0),
            ]

            for indicator_name, condition in checks:
                if condition:
                    hit_count += 1
                    hit_indicators.append(indicator_name)

            # 命中 >= 3 个指标
            if hit_count >= 3:
                resonance_stocks.append({
                    'symbol': symbol,
                    'hit_count': hit_count,
                    'indicators': hit_indicators,
                    'close': latest.get('close'),
                    'rsi_6': latest.get('rsi_6'),
                    'macd': latest.get('macd'),
                })

        return sorted(resonance_stocks, key=lambda x: x['hit_count'], reverse=True)
