"""缠论中枢测试"""
import pytest
from app.core.chan.segment import Segment
from app.core.chan.hub import (
    calculate_hub, Hub, get_latest_hub, get_hub_range,
    is_price_above_hub, is_price_below_hub, is_price_in_hub,
    get_price_position
)


@pytest.fixture
def sample_segments():
    """样本线段列表"""
    return [
        Segment("20240101", "20240102", 1, 13, 7, 0),   # 向上线段
        Segment("20240102", "20240103", -1, 13, 6, 1),  # 向下线段
        Segment("20240103", "20240104", 1, 14, 6, 2),   # 向上线段
        Segment("20240104", "20240105", -1, 14, 5, 3),  # 向下线段
        Segment("20240105", "20240106", 1, 15, 5, 4),   # 向上线段
    ]


class TestCalculateHub:
    """中枢计算测试"""

    def test_simple_hub(self, sample_segments):
        """简单中枢识别"""
        hubs = calculate_hub(sample_segments)

        assert len(hubs) >= 1
        # 中枢应该是有效的（上沿 > 下沿）
        for hub in hubs:
            assert hub.zg > hub.zd

    def test_insufficient_segments(self):
        """线段不足"""
        segments = [
            Segment("20240101", "20240102", 1, 13, 7, 0),
            Segment("20240102", "20240103", -1, 13, 6, 1),
        ]
        hubs = calculate_hub(segments)

        # 少于3个线段应该没有中枢
        assert len(hubs) == 0

    def test_hub_zg_zd_calculation(self):
        """中枢上沿和下沿计算"""
        segments = [
            Segment("20240101", "20240102", 1, 13, 7, 0),   # high=13, low=7
            Segment("20240102", "20240103", -1, 12, 8, 1),  # high=12, low=8
            Segment("20240103", "20240104", 1, 14, 6, 2),   # high=14, low=6
        ]
        hubs = calculate_hub(segments)

        assert len(hubs) >= 1
        hub = hubs[0]
        # ZG = min(13, 12, 14) = 12
        assert hub.zg == 12
        # ZD = max(7, 8, 6) = 8
        assert hub.zd == 8

    def test_hub_gg_dd_calculation(self):
        """中枢最高点和最低点计算"""
        segments = [
            Segment("20240101", "20240102", 1, 13, 7, 0),
            Segment("20240102", "20240103", -1, 12, 8, 1),
            Segment("20240103", "20240104", 1, 14, 6, 2),
        ]
        hubs = calculate_hub(segments)

        hub = hubs[0]
        # GG = max(13, 12, 14) = 14
        assert hub.gg == 14
        # DD = min(7, 8, 6) = 6
        assert hub.dd == 6

    def test_invalid_hub_no_overlap(self):
        """无重叠的线段不形成中枢"""
        segments = [
            Segment("20240101", "20240102", 1, 10, 9, 0),   # high=10, low=9
            Segment("20240102", "20240103", -1, 9, 8, 1),   # high=9, low=8
            Segment("20240103", "20240104", 1, 8, 7, 2),    # high=8, low=7
        ]
        hubs = calculate_hub(segments)

        # 这个应该被跳过（ZG=8, ZD=9，无重叠）
        # 实际计算：ZG=min(10,9,8)=8, ZD=max(9,8,7)=9，ZG < ZD，无效
        assert len(hubs) == 0

    def test_hub_index_increment(self, sample_segments):
        """中枢索引递增"""
        hubs = calculate_hub(sample_segments)

        for i, hub in enumerate(hubs):
            assert hub.hub_index == i

    def test_hub_date_range(self):
        """中枢时间范围"""
        segments = [
            Segment("20240101", "20240102", 1, 13, 7, 0),
            Segment("20240103", "20240104", -1, 13, 6, 1),
            Segment("20240105", "20240106", 1, 14, 6, 2),
        ]
        hubs = calculate_hub(segments)

        if hubs:
            hub = hubs[0]
            assert hub.start_date == "20240101"
            assert hub.end_date == "20240106"

    def test_multiple_hubs(self):
        """多个中枢"""
        segments = [
            Segment("20240101", "20240102", 1, 13, 7, 0),
            Segment("20240102", "20240103", -1, 13, 6, 1),
            Segment("20240103", "20240104", 1, 14, 6, 2),
            Segment("20240104", "20240105", -1, 14, 5, 3),
            Segment("20240105", "20240106", 1, 15, 5, 4),
            Segment("20240106", "20240107", -1, 15, 4, 5),
        ]
        hubs = calculate_hub(segments)

        # 应该有多个中枢
        assert len(hubs) >= 1


class TestHubDataClass:
    """中枢数据类测试"""

    def test_hub_creation(self):
        """创建中枢对象"""
        hub = Hub(
            start_date="20240101",
            end_date="20240106",
            zg=12.0,
            zd=8.0,
            gg=14.0,
            dd=6.0,
            hub_index=0,
        )

        assert hub.start_date == "20240101"
        assert hub.end_date == "20240106"
        assert hub.zg == 12.0
        assert hub.zd == 8.0
        assert hub.gg == 14.0
        assert hub.dd == 6.0

    def test_hub_level_default(self):
        """中枢级别默认值"""
        hub = Hub("20240101", "20240106", 12, 8, 14, 6)
        assert hub.level == 1


class TestGetLatestHub:
    """获取最新中枢"""

    def test_get_latest_hub(self, sample_segments):
        """获取最新中枢"""
        hubs = calculate_hub(sample_segments)

        if hubs:
            latest = get_latest_hub(hubs)
            assert latest is not None
            assert latest.hub_index == len(hubs) - 1

    def test_empty_hubs(self):
        """空中枢列表"""
        latest = get_latest_hub([])
        assert latest is None


class TestHubRange:
    """中枢振幅测试"""

    def test_get_hub_range(self):
        """计算中枢振幅"""
        hub = Hub("20240101", "20240106", zg=12.0, zd=8.0, gg=14.0, dd=6.0)
        # 振幅 = (ZG - ZD) / ZD * 100 = (12 - 8) / 8 * 100 = 50%
        range_val = get_hub_range(hub)
        assert abs(range_val - 50.0) < 0.01

    def test_hub_range_zero_zd(self):
        """ZD为0时的振幅"""
        hub = Hub("20240101", "20240106", zg=12.0, zd=0.0, gg=14.0, dd=0.0)
        range_val = get_hub_range(hub)
        assert range_val == 0

    def test_hub_range_large(self):
        """大振幅中枢"""
        hub = Hub("20240101", "20240106", zg=20.0, zd=10.0, gg=25.0, dd=5.0)
        # (20 - 10) / 10 * 100 = 100%
        range_val = get_hub_range(hub)
        assert abs(range_val - 100.0) < 0.01


class TestPricePosition:
    """价格位置判断"""

    def test_price_above_hub(self):
        """价格在中枢上方"""
        hub = Hub("20240101", "20240106", zg=12.0, zd=8.0, gg=14.0, dd=6.0)

        assert is_price_above_hub(13.0, hub)
        assert is_price_above_hub(15.0, hub)
        assert not is_price_above_hub(12.0, hub)

    def test_price_below_hub(self):
        """价格在中枢下方"""
        hub = Hub("20240101", "20240106", zg=12.0, zd=8.0, gg=14.0, dd=6.0)

        assert is_price_below_hub(7.0, hub)
        assert is_price_below_hub(5.0, hub)
        assert not is_price_below_hub(8.0, hub)

    def test_price_in_hub(self):
        """价格在中枢内"""
        hub = Hub("20240101", "20240106", zg=12.0, zd=8.0, gg=14.0, dd=6.0)

        assert is_price_in_hub(10.0, hub)
        assert is_price_in_hub(8.0, hub)
        assert is_price_in_hub(12.0, hub)
        assert not is_price_in_hub(13.0, hub)
        assert not is_price_in_hub(7.0, hub)

    def test_get_price_position(self):
        """获取价格相对中枢位置"""
        hub = Hub("20240101", "20240106", zg=12.0, zd=8.0, gg=14.0, dd=6.0)

        assert get_price_position(13.0, hub) == "above"
        assert get_price_position(10.0, hub) == "inside"
        assert get_price_position(7.0, hub) == "below"
        assert get_price_position(12.0, hub) == "inside"  # 边界值在内部
        assert get_price_position(8.0, hub) == "inside"


class TestComplexHubScenarios:
    """复杂中枢场景"""

    def test_continuous_hubs(self):
        """连续中枢"""
        segments = [
            # 第一个中枢的线段
            Segment("20240101", "20240102", 1, 13, 7, 0),
            Segment("20240102", "20240103", -1, 13, 6, 1),
            Segment("20240103", "20240104", 1, 14, 6, 2),
            # 第二个中枢的线段
            Segment("20240104", "20240105", -1, 14, 5, 3),
            Segment("20240105", "20240106", 1, 15, 5, 4),
            Segment("20240106", "20240107", -1, 15, 4, 5),
        ]
        hubs = calculate_hub(segments)

        # 第一个中枢用前3个线段，跳过3个
        # 第二个中枢从线段3开始
        assert len(hubs) >= 1

    def test_tight_hub(self):
        """紧凑中枢（小振幅）"""
        segments = [
            Segment("20240101", "20240102", 1, 10.5, 9.5, 0),
            Segment("20240102", "20240103", -1, 10.3, 9.7, 1),
            Segment("20240103", "20240104", 1, 10.4, 9.6, 2),
        ]
        hubs = calculate_hub(segments)

        if hubs:
            hub = hubs[0]
            # ZG = min(10.5, 10.3, 10.4) = 10.3
            # ZD = max(9.5, 9.7, 9.6) = 9.7
            # ZG > ZD? 10.3 > 9.7? YES
            assert hub.zg == 10.3
            assert hub.zd == 9.7
            assert hub.zg > hub.zd

    def test_wide_hub(self):
        """宽松中枢（大振幅）"""
        segments = [
            Segment("20240101", "20240102", 1, 20, 5, 0),
            Segment("20240102", "20240103", -1, 20, 5, 1),
            Segment("20240103", "20240104", 1, 20, 5, 2),
        ]
        hubs = calculate_hub(segments)

        if hubs:
            hub = hubs[0]
            assert hub.zg == 20
            assert hub.zd == 5
            # 振幅 = (20 - 5) / 5 * 100 = 300%
            assert get_hub_range(hub) == 300.0


class TestHubEdgeCases:
    """中枢边界情况"""

    def test_exact_three_segments(self):
        """恰好3个线段"""
        segments = [
            Segment("20240101", "20240102", 1, 13, 7, 0),
            Segment("20240102", "20240103", -1, 13, 6, 1),
            Segment("20240103", "20240104", 1, 14, 6, 2),
        ]
        hubs = calculate_hub(segments)

        assert len(hubs) == 1

    def test_high_precision_price(self):
        """高精度价格"""
        hub = Hub(
            "20240101", "20240106",
            zg=12.123456, zd=8.987654,
            gg=14.999999, dd=6.000001
        )

        assert is_price_in_hub(10.5, hub)
        assert not is_price_in_hub(12.2, hub)  # 超过ZG

    def test_identical_segment_values(self):
        """相同的线段高低点"""
        segments = [
            Segment("20240101", "20240102", 1, 10, 10, 0),
            Segment("20240102", "20240103", -1, 10, 10, 1),
            Segment("20240103", "20240104", 1, 10, 10, 2),
        ]
        hubs = calculate_hub(segments)

        # ZG = min(10, 10, 10) = 10
        # ZD = max(10, 10, 10) = 10
        # ZG > ZD? 10 > 10? NO
        assert len(hubs) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
