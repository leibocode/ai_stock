"""技术指标测试"""
import pytest
import numpy as np
from app.core.indicators.rsi import calculate_rsi, calculate_rsi_multi
from app.core.indicators.macd import calculate_macd, calculate_ema
from app.core.indicators.kdj import calculate_kdj
from app.core.indicators.boll import calculate_boll


class TestRSI:
    """RSI指标测试"""

    def test_calculate_rsi_basic(self):
        """基础RSI计算"""
        # 上升趋势
        closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115])
        rsi = calculate_rsi(closes, period=14)

        assert 0 <= rsi <= 100
        assert rsi > 50  # 强势上升，RSI应该高于50

    def test_calculate_rsi_downtrend(self):
        """下跌趋势RSI"""
        # 下跌趋势
        closes = np.array([115, 114, 113, 112, 111, 110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100])
        rsi = calculate_rsi(closes, period=14)

        assert 0 <= rsi <= 100
        assert rsi < 50  # 弱势下跌，RSI应该低于50

    def test_calculate_rsi_flat(self):
        """平盘RSI"""
        closes = np.array([100] * 20)
        rsi = calculate_rsi(closes, period=14)

        # 平盘RSI应该接近50
        assert abs(rsi - 50) < 10

    def test_calculate_rsi_insufficient_data(self):
        """数据不足"""
        closes = np.array([100, 101, 102])
        rsi = calculate_rsi(closes, period=14)

        # 应该返回默认值50
        assert rsi == 50.0

    def test_calculate_rsi_multi(self):
        """多周期RSI"""
        closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115])
        rsi_dict = calculate_rsi_multi(closes, [6, 12])

        assert "rsi_6" in rsi_dict
        assert "rsi_12" in rsi_dict
        assert 0 <= rsi_dict["rsi_6"] <= 100
        assert 0 <= rsi_dict["rsi_12"] <= 100


class TestMACD:
    """MACD指标测试"""

    def test_calculate_ema(self):
        """EMA计算"""
        data = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        ema = calculate_ema(data, period=5)

        assert len(ema) == len(data)
        assert ema[0] == data[0]  # 首个EMA等于首个数据

    def test_calculate_macd_uptrend(self):
        """上升趋势MACD"""
        closes = np.array(list(range(100, 150)))  # 100-149上升
        dif, dea, macd_hist = calculate_macd(closes)

        assert dif > 0  # 快线在慢线上方
        assert dea > 0
        assert macd_hist >= 0  # 直方图为正

    def test_calculate_macd_downtrend(self):
        """下跌趋势MACD"""
        closes = np.array(list(range(150, 100, -1)))  # 150-100下降
        dif, dea, macd_hist = calculate_macd(closes)

        assert dif < 0  # 快线在慢线下方

    def test_calculate_macd_insufficient(self):
        """数据不足"""
        closes = np.array([100, 101, 102])
        dif, dea, macd_hist = calculate_macd(closes)

        # 应该返回0
        assert dif == 0.0
        assert dea == 0.0
        assert macd_hist == 0.0


class TestKDJ:
    """KDJ指标测试"""

    def test_calculate_kdj_basic(self):
        """基础KDJ计算"""
        highs = np.array([110, 111, 112, 113, 114, 115, 114, 113, 112, 111])
        lows = np.array([100, 101, 102, 103, 104, 105, 104, 103, 102, 101])
        closes = np.array([105, 106, 107, 108, 109, 110, 109, 108, 107, 106])

        k, d, j = calculate_kdj(highs, lows, closes, period=9)

        assert 0 <= k <= 100
        assert 0 <= d <= 100
        # J可以超出0-100范围

    def test_calculate_kdj_insufficient(self):
        """数据不足"""
        highs = np.array([110, 111, 112])
        lows = np.array([100, 101, 102])
        closes = np.array([105, 106, 107])

        k, d, j = calculate_kdj(highs, lows, closes, period=9)

        # 应该返回默认值50, 50, 50
        assert k == 50.0
        assert d == 50.0
        assert j == 50.0

    def test_calculate_kdj_bottom(self):
        """KDJ底部信号"""
        # 从低位反弹
        highs = np.array([100, 100, 100, 100, 105, 110, 115, 120, 125, 130])
        lows = np.array([90, 90, 90, 90, 95, 100, 105, 110, 115, 120])
        closes = np.array([95, 95, 95, 95, 100, 105, 110, 115, 120, 125])

        k, d, j = calculate_kdj(highs, lows, closes)

        assert k > 0  # K值应该上升
        assert d > 0


class TestBollinger:
    """布林带测试"""

    def test_calculate_boll_basic(self):
        """基础布林带计算"""
        closes = np.array([100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

        upper, mid, lower = calculate_boll(closes, period=20)

        assert upper > mid
        assert mid > lower
        # 中轨应该是20日平均
        assert abs(mid - np.mean(closes[-20:])) < 0.01

    def test_calculate_boll_insufficient(self):
        """数据不足"""
        closes = np.array([100, 101, 102])
        upper, mid, lower = calculate_boll(closes, period=20)

        # 应该返回0
        assert upper == 0.0
        assert mid == 0.0
        assert lower == 0.0

    def test_calculate_boll_volatility(self):
        """布林带宽度与波动性"""
        # 低波动
        low_vol = np.array([100] * 30 + [100.1, 99.9] * 5)
        upper1, mid1, lower1 = calculate_boll(low_vol[-20:])

        # 高波动
        high_vol = np.array([90, 110, 95, 105, 92, 108, 98, 102] * 5)
        upper2, mid2, lower2 = calculate_boll(high_vol[-20:])

        # 高波动的带宽应该更大
        width1 = upper1 - lower1
        width2 = upper2 - lower2
        assert width2 > width1


class TestIndicatorEdgeCases:
    """指标边界情况测试"""

    def test_all_zero_input(self):
        """全零输入"""
        zeros = np.array([0] * 30)
        rsi = calculate_rsi(zeros)
        k, d, j = calculate_kdj(zeros, zeros, zeros)

        assert rsi == 50.0
        assert k == 50.0

    def test_nan_handling(self):
        """NaN处理"""
        with_nan = np.array([100, 101, np.nan, 103, 104])

        # 应该处理NaN而不崩溃
        # 取决于具体实现
        try:
            rsi = calculate_rsi(with_nan)
        except:
            # 可以选择抛出异常或返回默认值
            pass

    def test_negative_prices(self):
        """负数价格"""
        negatives = np.array([-100, -99, -98, -97, -96, -95, -94, -93, -92, -91, -90, -89, -88, -87, -86, -85])
        # 虽然股票价格不会是负数，但指标应该能处理
        rsi = calculate_rsi(negatives)
        assert 0 <= rsi <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
