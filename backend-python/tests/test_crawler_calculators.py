"""爬虫计算器测试（情绪周期、龙头评分）"""
import pytest
from app.services.crawler.emotion_cycle import (
    EmotionCycleCalculator, EmotionCycleResult, CyclePhase
)
from app.services.crawler.leader_score import (
    LeaderScoreCalculator, LeaderScore
)


class TestEmotionCycleCalculator:
    """情绪周期计算器测试"""

    @pytest.fixture
    def calculator(self):
        return EmotionCycleCalculator()

    def test_calculate_basic(self, calculator):
        """基础计算"""
        limit_up_list = [
            {"continuous": 1, "open_times": 0},
            {"continuous": 1, "open_times": 0},
            {"continuous": 2, "open_times": 0},
        ]
        limit_down_list = []

        result = calculator.calculate(limit_up_list, limit_down_list)

        assert isinstance(result, EmotionCycleResult)
        assert result.limit_up_count == 3
        assert result.limit_down_count == 0

    def test_climax_phase(self, calculator):
        """高潮期（得分>=70）"""
        limit_up_list = [
            {"continuous": 5, "open_times": 0},
            {"continuous": 4, "open_times": 0},
            {"continuous": 3, "open_times": 0},
        ] * 20  # 60家涨停，连板都高
        limit_down_list = [
            {"continuous": 1, "open_times": 0},
        ]

        result = calculator.calculate(limit_up_list, limit_down_list)

        assert result.score >= 70
        assert result.phase == CyclePhase.CLIMAX

    def test_warming_phase(self, calculator):
        """回暖期（得分50-69）"""
        limit_up_list = [
            {"continuous": 3, "open_times": 0},
            {"continuous": 2, "open_times": 0},
            {"continuous": 1, "open_times": 0},
        ] * 8  # 24家涨停
        limit_down_list = []

        result = calculator.calculate(limit_up_list, limit_down_list)

        assert 50 <= result.score < 70
        assert result.phase == CyclePhase.WARMING

    def test_recovery_phase(self, calculator):
        """修复期（得分30-49）"""
        limit_up_list = [
            {"continuous": 2, "open_times": 0},
            {"continuous": 1, "open_times": 0},
        ] * 10  # 20家涨停
        limit_down_list = []

        result = calculator.calculate(limit_up_list, limit_down_list)

        assert 30 <= result.score < 50
        assert result.phase == CyclePhase.RECOVERY

    def test_tide_out_phase(self, calculator):
        """退潮期（得分10-29）"""
        limit_up_list = [
            {"continuous": 1, "open_times": 2},
        ] * 15  # 15家涨停，都是1板，都开板2次
        limit_down_list = []

        result = calculator.calculate(limit_up_list, limit_down_list)

        assert 10 <= result.score < 30
        assert result.phase == CyclePhase.TIDE_OUT

    def test_ice_point_phase(self, calculator):
        """冰点期（得分<10）"""
        limit_up_list = [
            {"continuous": 1, "open_times": 5},
        ]  # 1家涨停，1板，开板5次
        limit_down_list = []

        result = calculator.calculate(limit_up_list, limit_down_list)

        assert result.score < 10
        assert result.phase == CyclePhase.ICE_POINT

    def test_profit_effect_score(self, calculator):
        """赚钱效应评分"""
        # 赚钱效应 >= 70%: 30分
        limit_up_list = [
            {"continuous": 2, "open_times": 0},
            {"continuous": 2, "open_times": 0},
            {"continuous": 2, "open_times": 0},
            {"continuous": 1, "open_times": 0},
        ]  # 75% 是连板

        result = calculator.calculate(limit_up_list, [])
        # 赚钱效应得30分
        assert result.limit_up_count == 4

    def test_continuous_score(self, calculator):
        """连板高度评分"""
        # 最高连板数 >= 5: 20分
        limit_up_list = [
            {"continuous": 5, "open_times": 0},
            {"continuous": 1, "open_times": 0},
        ]

        result = calculator.calculate(limit_up_list, [])
        assert result.max_continuous == 5

    def test_limit_up_count_score(self, calculator):
        """涨停数评分"""
        # >=80家: 20分
        limit_up_list = [
            {"continuous": 1, "open_times": 0},
        ] * 85

        result = calculator.calculate(limit_up_list, [])
        assert result.limit_up_count == 85

    def test_up_down_ratio_score(self, calculator):
        """涨跌比评分"""
        # 涨停数 > 跌停数 * 5: 15分
        limit_up_list = [
            {"continuous": 1, "open_times": 0},
        ] * 50
        limit_down_list = [
            {"continuous": -1, "open_times": 0},
        ] * 9  # 比例约5.5:1

        result = calculator.calculate(limit_up_list, limit_down_list)
        assert result.limit_up_count == 50
        assert result.limit_down_count == 9

    def test_broken_rate_score(self, calculator):
        """炸板率评分"""
        # 开板率低: 10分
        limit_up_list = [
            {"continuous": 1, "open_times": 0},
            {"continuous": 1, "open_times": 0},
            {"continuous": 1, "open_times": 0},
            {"continuous": 1, "open_times": 0},
            {"continuous": 1, "open_times": 1},
        ]  # 炸板率 = 1/5 = 20%

        result = calculator.calculate(limit_up_list, [])
        assert result.broken_rate == 20.0

    def test_promotion_rate_score(self, calculator):
        """晋级率评分"""
        # 2板占1板比例高: 5分
        limit_up_list = [
            {"continuous": 1, "open_times": 0},
            {"continuous": 1, "open_times": 0},
            {"continuous": 2, "open_times": 0},
            {"continuous": 2, "open_times": 0},
            {"continuous": 2, "open_times": 0},
        ]  # 3板占2板，晋级率 150%

        result = calculator.calculate(limit_up_list, [])
        assert result.promotion_rate == 150.0

    def test_empty_lists(self, calculator):
        """空列表"""
        result = calculator.calculate([], [])

        assert result.limit_up_count == 0
        assert result.limit_down_count == 0
        assert result.max_continuous == 0
        assert result.score < 10


class TestLeaderScoreCalculator:
    """龙头股评分计算器测试"""

    @pytest.fixture
    def calculator(self):
        return LeaderScoreCalculator()

    def test_calculate_basic(self, calculator):
        """基础计算"""
        stock = {
            "code": "000001",
            "name": "平安银行",
            "continuous": 3,
            "first_time": "09:30",
            "open_times": 0,
            "amount": 10,
            "turnover": 15,
            "market_cap": 50,
        }

        result = calculator.calculate(stock)

        assert isinstance(result, LeaderScore)
        assert result.code == "000001"
        assert result.continuous == 3

    def test_leader_score_high(self, calculator):
        """高分龙头"""
        stock = {
            "code": "000001",
            "continuous": 3,
            "first_time": "09:30",
            "open_times": 0,
            "amount": 10,
            "turnover": 15,
            "market_cap": 50,
        }

        result = calculator.calculate(stock)

        assert result.score >= 50
        assert result.is_leader

    def test_leader_score_low(self, calculator):
        """低分非龙头"""
        stock = {
            "code": "000001",
            "continuous": 1,
            "first_time": "14:00",
            "open_times": 5,
            "amount": 100,
            "turnover": 50,
            "market_cap": 1000,
        }

        result = calculator.calculate(stock)

        assert result.score < 50
        assert not result.is_leader

    def test_continuous_score(self, calculator):
        """连板高度评分"""
        # 连板数 * 15
        stock = {
            "continuous": 5,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 5 * 15 = 75分，已经是龙头
        assert result.score >= 50
        assert result.is_leader

    def test_first_time_early_morning(self, calculator):
        """早盘开盘评分"""
        # 09:30前: 20分
        stock = {
            "continuous": 1,
            "first_time": "09:30",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 20 = 35分
        assert result.score == 35

    def test_first_time_late_morning(self, calculator):
        """上午晚些开盘评分"""
        # 10:00前: 15分
        stock = {
            "continuous": 1,
            "first_time": "09:45",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 15 = 30分
        assert result.score == 30

    def test_first_time_afternoon(self, calculator):
        """午盘后开盘评分"""
        # 13:00前: 5分
        stock = {
            "continuous": 1,
            "first_time": "12:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 5 = 20分
        assert result.score == 20

    def test_open_times_zero(self, calculator):
        """零开板评分"""
        # 0次: 15分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 15 = 30分
        assert result.score == 30

    def test_open_times_one(self, calculator):
        """一次开板评分"""
        # 1次: 10分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 1,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 10 = 25分
        assert result.score == 25

    def test_open_times_many(self, calculator):
        """多次开板评分"""
        # >3次: -5分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 5,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 - 5 = 10分
        assert result.score == 10

    def test_amount_ideal(self, calculator):
        """理想成交额评分"""
        # 3-15亿: 10分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 10,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 0 + 10 = 25分
        assert result.score == 25

    def test_amount_large(self, calculator):
        """过大成交额评分"""
        # >50亿: -5分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 100,
            "turnover": 0,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 0 - 5 = 10分
        assert result.score == 10

    def test_turnover_ideal(self, calculator):
        """理想换手率评分"""
        # 5-20%: 10分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 15,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 0 + 10 = 25分
        assert result.score == 25

    def test_turnover_high(self, calculator):
        """过高换手率评分"""
        # >40%: -5分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 50,
            "market_cap": 100,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 0 - 5 = 10分
        assert result.score == 10

    def test_market_cap_small(self, calculator):
        """小市值评分"""
        # <=50亿: 10分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 40,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 0 + 10 = 25分
        assert result.score == 25

    def test_market_cap_large(self, calculator):
        """大市值评分"""
        # >500亿: -5分
        stock = {
            "continuous": 1,
            "first_time": "15:00",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 600,
        }

        result = calculator.calculate(stock)
        # 1*15 + 0 + 0 - 5 = 10分
        assert result.score == 10

    def test_batch_calculate(self, calculator):
        """批量计算"""
        stocks = [
            {"code": "001", "continuous": 1, "first_time": "09:30", "open_times": 0, "amount": 10, "turnover": 15, "market_cap": 50},
            {"code": "002", "continuous": 3, "first_time": "10:00", "open_times": 0, "amount": 5, "turnover": 10, "market_cap": 80},
            {"code": "003", "continuous": 5, "first_time": "09:30", "open_times": 0, "amount": 20, "turnover": 20, "market_cap": 40},
        ]

        results = calculator.batch_calculate(stocks)

        # 应该按得分倒序
        assert len(results) == 3
        assert results[0].score >= results[1].score >= results[2].score

    def test_batch_calculate_empty(self, calculator):
        """空列表批量计算"""
        results = calculator.batch_calculate([])
        assert results == []

    def test_invalid_time_format(self, calculator):
        """无效时间格式"""
        stock = {
            "continuous": 1,
            "first_time": "invalid",
            "open_times": 0,
            "amount": 0,
            "turnover": 0,
            "market_cap": 100,
        }

        # 不应该抛出异常
        result = calculator.calculate(stock)
        assert result.score == 15  # 1*15 + 0（无效时间得0分）


class TestEmotionCyclePhases:
    """情绪周期阶段测试"""

    def test_phase_enum_values(self):
        """阶段枚举值"""
        assert CyclePhase.ICE_POINT == "冰点期"
        assert CyclePhase.RECOVERY == "修复期"
        assert CyclePhase.WARMING == "回暖期"
        assert CyclePhase.CLIMAX == "高潮期"
        assert CyclePhase.TIDE_OUT == "退潮期"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
