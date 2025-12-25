"""缠论线段测试"""
import pytest
from app.core.chan.fractal import Fractal
from app.core.chan.bi import Bi, calculate_bi
from app.core.chan.segment import calculate_segment, Segment, get_latest_segment


@pytest.fixture
def sample_bis():
    """样本笔列表"""
    return [
        Bi("20240101", "20240102", 1, 12, 8, 0),    # 向上笔
        Bi("20240102", "20240103", -1, 12, 7, 1),   # 向下笔
        Bi("20240103", "20240104", 1, 13, 7, 2),    # 向上笔
        Bi("20240104", "20240105", -1, 13, 6, 3),   # 向下笔
        Bi("20240105", "20240106", 1, 14, 6, 4),    # 向上笔
    ]


class TestCalculateSegment:
    """线段划分测试"""

    def test_simple_segment(self, sample_bis):
        """简单线段划分"""
        segments = calculate_segment(sample_bis)

        assert len(segments) >= 1
        # 每个线段应该至少3笔
        for seg in segments:
            assert seg.direction in (1, -1)

    def test_insufficient_bis(self):
        """笔不足"""
        bis = [
            Bi("20240101", "20240102", 1, 12, 8),
            Bi("20240102", "20240103", -1, 12, 7),
        ]
        segments = calculate_segment(bis)

        # 少于3笔应该没有线段
        assert len(segments) == 0

    def test_segment_alternation(self, sample_bis):
        """线段方向交替"""
        segments = calculate_segment(sample_bis)

        # 检查方向交替
        for i in range(len(segments) - 1):
            assert segments[i].direction != segments[i + 1].direction

    def test_up_segment_end_condition(self):
        """向上线段结束条件"""
        bis = [
            Bi("20240101", "20240102", 1, 12, 8, 0),    # 向上笔
            Bi("20240102", "20240103", -1, 12, 7, 1),   # 向下笔
            Bi("20240103", "20240104", 1, 13, 7, 2),    # 向上笔
            Bi("20240104", "20240105", -1, 13, 6, 3),   # 向下笔 - 创新低(6 < 7) → 向上线段结束
        ]
        segments = calculate_segment(bis)

        assert len(segments) >= 1
        # 第一个线段应该是向上的
        if segments:
            assert segments[0].direction == 1

    def test_down_segment_end_condition(self):
        """向下线段结束条件"""
        bis = [
            Bi("20240101", "20240102", -1, 12, 8, 0),   # 向下笔
            Bi("20240102", "20240103", 1, 12, 7, 1),    # 向上笔
            Bi("20240103", "20240104", -1, 13, 7, 2),   # 向下笔
            Bi("20240104", "20240105", 1, 13, 6, 3),    # 向上笔 - 创新高(13 > 12) → 向下线段结束
        ]
        segments = calculate_segment(bis)

        assert len(segments) >= 1
        if segments:
            assert segments[0].direction == -1

    def test_segment_high_low_calculation(self, sample_bis):
        """线段高低点计算"""
        segments = calculate_segment(sample_bis)

        for seg in segments:
            # 高点应该是组成笔中的最高点
            assert seg.high > 0
            # 低点应该是组成笔中的最低点
            assert seg.low > 0
            assert seg.high > seg.low


class TestSegmentDataClass:
    """线段数据类测试"""

    def test_segment_creation(self):
        """创建线段对象"""
        seg = Segment(
            start_date="20240101",
            end_date="20240104",
            direction=1,
            high=13.0,
            low=7.0,
            seg_index=0,
        )

        assert seg.start_date == "20240101"
        assert seg.direction == 1
        assert seg.high == 13.0
        assert seg.seg_index == 0

    def test_segment_direction_values(self):
        """线段方向值有效性"""
        seg_up = Segment("20240101", "20240104", 1, 13, 7)
        seg_down = Segment("20240101", "20240104", -1, 13, 7)

        assert seg_up.direction in (1, -1)
        assert seg_down.direction in (1, -1)


class TestGetLatestSegment:
    """获取最新线段"""

    def test_get_latest_segment(self, sample_bis):
        """获取最新线段"""
        segments = calculate_segment(sample_bis)

        if segments:
            latest = get_latest_segment(segments)
            assert latest is not None
            assert latest.seg_index == len(segments) - 1

    def test_empty_segments(self):
        """空线段列表"""
        latest = get_latest_segment([])
        assert latest is None


class TestComplexSegmentScenarios:
    """复杂线段场景"""

    def test_long_uptrend(self):
        """长期上升趋势"""
        bis = [
            Bi(f"2024010{i}", f"2024010{i+1}", (-1)**(i), 15 - i if i % 2 == 0 else 10 - i, i * 2)
            for i in range(1, 8)
        ]
        segments = calculate_segment(bis)

        # 应该有线段形成
        assert len(segments) > 0

    def test_multiple_segments(self):
        """多个线段"""
        bis = [
            Bi("20240101", "20240102", 1, 12, 8, 0),
            Bi("20240102", "20240103", -1, 12, 7, 1),
            Bi("20240103", "20240104", 1, 13, 7, 2),
            Bi("20240104", "20240105", -1, 13, 5, 3),    # 创新低
            Bi("20240105", "20240106", 1, 14, 5, 4),
            Bi("20240106", "20240107", -1, 14, 4, 5),    # 创新低
            Bi("20240107", "20240108", 1, 15, 4, 6),
        ]
        segments = calculate_segment(bis)

        # 应该有多个线段
        assert len(segments) >= 2

    def test_segment_continuity(self):
        """线段连续性"""
        bis = [
            Bi("20240101", "20240102", 1, 12, 8, 0),
            Bi("20240102", "20240103", -1, 12, 6, 1),
            Bi("20240103", "20240104", 1, 14, 6, 2),
            Bi("20240104", "20240105", -1, 14, 5, 3),
            Bi("20240105", "20240106", 1, 15, 5, 4),
        ]
        segments = calculate_segment(bis)

        # 相邻线段的时间应该连续
        for i in range(len(segments) - 1):
            assert segments[i].end_date <= segments[i + 1].start_date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
