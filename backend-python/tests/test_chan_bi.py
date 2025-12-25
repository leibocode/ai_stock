"""缠论笔划分测试"""
import pytest
from app.core.chan.fractal import Fractal
from app.core.chan.bi import calculate_bi, Bi, get_latest_bi, count_bi_by_direction


@pytest.fixture
def sample_fractals():
    """样本分型列表（顶底交替）"""
    return [
        Fractal("20240101", -1, 10, 8, 0),   # 底
        Fractal("20240102", 1, 12, 10, 1),   # 顶
        Fractal("20240103", -1, 9, 7, 2),    # 底
        Fractal("20240104", 1, 13, 11, 3),   # 顶
    ]


class TestCalculateBi:
    """笔划分测试"""

    def test_simple_bi(self, sample_fractals):
        """简单笔划分"""
        bis = calculate_bi(sample_fractals)

        assert len(bis) >= 1
        # 第一笔应该从底到顶
        assert bis[0].direction == 1
        assert bis[0].start_date == "20240101"
        assert bis[0].end_date == "20240102"

    def test_bi_alternation(self, sample_fractals):
        """笔方向交替"""
        bis = calculate_bi(sample_fractals)

        # 检查方向交替
        for i in range(len(bis) - 1):
            assert bis[i].direction != bis[i + 1].direction

    def test_bi_index(self, sample_fractals):
        """笔索引递增"""
        bis = calculate_bi(sample_fractals)

        for i in range(len(bis)):
            assert bis[i].bi_index == i

    def test_insufficient_fractals(self):
        """分型不足"""
        fractals = [
            Fractal("20240101", -1, 10, 8),
        ]
        bis = calculate_bi(fractals)

        assert len(bis) == 0

    def test_up_bi(self):
        """向上笔：从底到顶，顶更高"""
        fractals = [
            Fractal("20240101", -1, 10, 8, 0),   # 底 (high=10, low=8)
            Fractal("20240102", 1, 12, 10, 1),   # 顶 (high=12 > 10) ✓
        ]
        bis = calculate_bi(fractals)

        assert len(bis) == 1
        assert bis[0].direction == 1  # 向上
        assert bis[0].high == 12
        assert bis[0].low == 8

    def test_down_bi(self):
        """向下笔：从顶到底，底更低"""
        fractals = [
            Fractal("20240101", 1, 12, 10, 0),   # 顶
            Fractal("20240102", -1, 9, 7, 1),    # 底 (low=7 < 10) ✓
        ]
        bis = calculate_bi(fractals)

        assert len(bis) == 1
        assert bis[0].direction == -1  # 向下
        assert bis[0].high == 12
        assert bis[0].low == 7

    def test_same_direction_take_extreme(self):
        """同向分型取极值"""
        fractals = [
            Fractal("20240101", -1, 10, 8, 0),
            Fractal("20240102", -1, 11, 7, 1),   # 同向，更低 → 更新
            Fractal("20240103", 1, 13, 11, 2),   # 顶
        ]
        bis = calculate_bi(fractals)

        assert len(bis) == 1
        # 应该用第二个底分型的值 (low=7更低)
        assert bis[0].low == 7


class TestBiDataClass:
    """笔数据类测试"""

    def test_bi_creation(self):
        """创建笔对象"""
        bi = Bi(
            start_date="20240101",
            end_date="20240102",
            direction=1,
            high=12.0,
            low=10.0,
            bi_index=0,
        )

        assert bi.start_date == "20240101"
        assert bi.direction == 1
        assert bi.high == 12.0

    def test_bi_direction_values(self):
        """笔方向值有效性"""
        bi_up = Bi("20240101", "20240102", 1, 12, 10)
        bi_down = Bi("20240101", "20240102", -1, 12, 10)

        assert bi_up.direction in (1, -1)
        assert bi_down.direction in (1, -1)


class TestGetLatestBi:
    """获取最新笔"""

    def test_get_latest_bi(self, sample_fractals):
        """获取最新笔"""
        bis = calculate_bi(sample_fractals)

        latest = get_latest_bi(bis)
        assert latest is not None
        assert latest.bi_index == len(bis) - 1

    def test_empty_bis(self):
        """空笔列表"""
        latest = get_latest_bi([])
        assert latest is None


class TestCountBiByDirection:
    """笔方向统计"""

    def test_count_direction(self, sample_fractals):
        """统计笔方向"""
        bis = calculate_bi(sample_fractals)
        stats = count_bi_by_direction(bis)

        assert "up" in stats
        assert "down" in stats
        assert "total" in stats
        assert stats["total"] == len(bis)
        assert stats["up"] + stats["down"] == stats["total"]

    def test_empty_bis_count(self):
        """空笔列表统计"""
        stats = count_bi_by_direction([])

        assert stats["total"] == 0
        assert stats["up"] == 0
        assert stats["down"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
