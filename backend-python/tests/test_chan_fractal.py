"""缠论分型测试"""
import pytest
from app.core.chan.fractal import merge_klines, calculate_fractals, Fractal


@pytest.fixture
def sample_klines():
    """样本K线数据"""
    return [
        {"trade_date": "20240101", "high": 10, "low": 8, "close": 9},
        {"trade_date": "20240102", "high": 11, "low": 9, "close": 10},
        {"trade_date": "20240103", "high": 12, "low": 10, "close": 11},
        {"trade_date": "20240104", "high": 11, "low": 9, "close": 10},
        {"trade_date": "20240105", "high": 10, "low": 8, "close": 9},
    ]


class TestMergeKlines:
    """K线包含处理测试"""

    def test_no_contain(self, sample_klines):
        """无包含关系的K线"""
        result = merge_klines(sample_klines)
        # 没有包含，应该返回原样
        assert len(result) == len(sample_klines)

    def test_simple_contain(self):
        """简单的包含关系"""
        klines = [
            {"high": 10, "low": 8},
            {"high": 9, "low": 8.5},  # 被前一根包含
            {"high": 11, "low": 9},
        ]
        result = merge_klines(klines)
        # 第1、2根应该合并
        assert len(result) < len(klines)

    def test_empty_input(self):
        """空输入"""
        result = merge_klines([])
        assert result == []

    def test_single_kline(self):
        """单根K线"""
        klines = [{"high": 10, "low": 8}]
        result = merge_klines(klines)
        assert len(result) == 1


class TestCalculateFractals:
    """分型识别测试"""

    def test_top_fractal(self):
        """顶分型识别"""
        klines = [
            {"high": 10, "low": 8, "trade_date": "20240101"},
            {"high": 12, "low": 10, "trade_date": "20240102"},  # 顶分型
            {"high": 11, "low": 9, "trade_date": "20240103"},
        ]
        fractals = calculate_fractals(klines)

        assert len(fractals) == 1
        assert fractals[0].fractal_type == 1  # 顶分型
        assert fractals[0].high == 12

    def test_bottom_fractal(self):
        """底分型识别"""
        klines = [
            {"high": 12, "low": 10, "trade_date": "20240101"},
            {"high": 10, "low": 8, "trade_date": "20240102"},   # 底分型
            {"high": 11, "low": 9, "trade_date": "20240103"},
        ]
        fractals = calculate_fractals(klines)

        assert len(fractals) == 1
        assert fractals[0].fractal_type == -1  # 底分型
        assert fractals[0].low == 8

    def test_complex_fractals(self):
        """复杂分型序列"""
        klines = [
            {"high": 10, "low": 8, "trade_date": "20240101"},
            {"high": 12, "low": 10, "trade_date": "20240102"},  # 顶
            {"high": 11, "low": 9, "trade_date": "20240103"},
            {"high": 9, "low": 7, "trade_date": "20240104"},    # 底
            {"high": 11, "low": 9, "trade_date": "20240105"},
        ]
        fractals = calculate_fractals(klines)

        assert len(fractals) >= 1
        # 检查分型类型交替
        for i in range(len(fractals) - 1):
            assert fractals[i].fractal_type != fractals[i + 1].fractal_type

    def test_insufficient_klines(self):
        """K线不足"""
        klines = [
            {"high": 10, "low": 8, "trade_date": "20240101"},
            {"high": 12, "low": 10, "trade_date": "20240102"},
        ]
        fractals = calculate_fractals(klines)

        assert len(fractals) == 0

    def test_flat_market(self):
        """平盘（无分型）"""
        klines = [
            {"high": 10, "low": 10, "trade_date": "20240101"},
            {"high": 10, "low": 10, "trade_date": "20240102"},
            {"high": 10, "low": 10, "trade_date": "20240103"},
        ]
        fractals = calculate_fractals(klines)

        assert len(fractals) == 0


class TestFractalDataClass:
    """分型数据类测试"""

    def test_fractal_creation(self):
        """创建分型对象"""
        f = Fractal(
            trade_date="20240101",
            fractal_type=1,
            high=12.5,
            low=10.0,
            index=5,
        )

        assert f.trade_date == "20240101"
        assert f.fractal_type == 1
        assert f.high == 12.5
        assert f.low == 10.0
        assert f.index == 5

    def test_fractal_type_validation(self):
        """分型类型有效性"""
        # 顶分型
        f1 = Fractal("20240101", 1, 12, 10)
        assert f1.fractal_type in (1, -1)

        # 底分型
        f2 = Fractal("20240102", -1, 10, 8)
        assert f2.fractal_type in (1, -1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
