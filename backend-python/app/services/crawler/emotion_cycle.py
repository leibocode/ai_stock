from dataclasses import dataclass
from enum import Enum
from typing import List, Dict
from loguru import logger


class CyclePhase(str, Enum):
    """情绪周期阶段"""
    ICE_POINT = "冰点期"
    RECOVERY = "修复期"
    WARMING = "回暖期"
    CLIMAX = "高潮期"
    TIDE_OUT = "退潮期"


@dataclass
class EmotionCycleResult:
    """情绪周期结果"""
    phase: CyclePhase
    score: int
    limit_up_count: int
    limit_down_count: int
    max_continuous: int
    broken_rate: float
    promotion_rate: float
    strategy: str


class EmotionCycleCalculator:
    """情绪周期计算器"""

    def calculate(
        self,
        limit_up_list: List[Dict],
        limit_down_list: List[Dict]
    ) -> EmotionCycleResult:
        """计算情绪周期

        评分规则 (满分100):
        - 赚钱效应(30分): >=70%加30分, >=50%加20分, >=30%加10分
        - 连板高度(20分): >=5板加20分, >=3板加10分, >=2板加5分
        - 涨停数(20分): >=80家加20分, >=50家加10分, >=30家加5分
        - 涨跌比(15分): >=5:1加15分, >=2:1加10分, >=1:1加5分
        - 炸板率(10分): <=20%加10分, <=40%加5分
        - 晋级率(5分): >=30%加5分

        Args:
            limit_up_list: 涨停列表
            limit_down_list: 跌停列表

        Returns:
            情绪周期结果
        """
        score = 0
        limit_up_count = len(limit_up_list)
        limit_down_count = len(limit_down_list)

        # 统计连板分布
        continuous_stats = self._count_continuous(limit_up_list)
        max_continuous = max(continuous_stats.keys()) if continuous_stats else 0

        # 计算赚钱效应
        profit_effect = self._calc_profit_effect(limit_up_list)
        score += self._score_profit_effect(profit_effect)

        # 计算连板高度得分
        score += self._score_continuous(max_continuous)

        # 计算涨停数得分
        score += self._score_limit_up_count(limit_up_count)

        # 计算涨跌比得分
        score += self._score_up_down_ratio(limit_up_count, limit_down_count)

        # 计算炸板率得分
        broken_rate = self._calc_broken_rate(limit_up_list)
        score += self._score_broken_rate(broken_rate)

        # 计算晋级率得分
        promotion_rate = self._calc_promotion_rate(continuous_stats)
        score += self._score_promotion_rate(promotion_rate)

        # 确定周期阶段
        phase, strategy = self._determine_phase(score)

        return EmotionCycleResult(
            phase=phase,
            score=score,
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
            max_continuous=max_continuous,
            broken_rate=round(broken_rate, 1),
            promotion_rate=round(promotion_rate, 1),
            strategy=strategy,
        )

    def _count_continuous(self, limit_up_list: List[Dict]) -> Dict[int, int]:
        """统计连板分布"""
        stats = {}
        for stock in limit_up_list:
            continuous = stock.get("continuous", 1)
            stats[continuous] = stats.get(continuous, 0) + 1
        return stats

    def _calc_profit_effect(self, limit_up_list: List[Dict]) -> float:
        """计算赚钱效应 (%)"""
        if not limit_up_list:
            return 0.0
        # 简化: 连板股/涨停股的比例 * 100
        continuous = sum(1 for s in limit_up_list if s.get("continuous", 1) >= 2)
        return round(continuous / len(limit_up_list) * 100, 1)

    def _calc_broken_rate(self, limit_up_list: List[Dict]) -> float:
        """计算炸板率 (%)"""
        if not limit_up_list:
            return 0.0
        total_open = sum(s.get("open_times", 0) for s in limit_up_list)
        return round(total_open / len(limit_up_list) * 100, 1)

    def _calc_promotion_rate(self, continuous_stats: Dict[int, int]) -> float:
        """计算晋级率 (2板/1板的比例)"""
        if not continuous_stats:
            return 0.0
        first_board = continuous_stats.get(1, 0)
        if first_board == 0:
            return 0.0
        second_board = continuous_stats.get(2, 0)
        return round(second_board / first_board * 100, 1)

    def _score_profit_effect(self, effect: float) -> int:
        if effect >= 70:
            return 30
        elif effect >= 50:
            return 20
        elif effect >= 30:
            return 10
        else:
            return -10

    def _score_continuous(self, max_continuous: int) -> int:
        if max_continuous >= 5:
            return 20
        elif max_continuous >= 3:
            return 10
        elif max_continuous >= 2:
            return 5
        return 0

    def _score_limit_up_count(self, count: int) -> int:
        if count >= 80:
            return 20
        elif count >= 50:
            return 10
        elif count >= 30:
            return 5
        return 0

    def _score_up_down_ratio(self, up: int, down: int) -> int:
        if down == 0:
            return 15 if up > 0 else 0
        ratio = up / down
        if ratio >= 5:
            return 15
        elif ratio >= 2:
            return 10
        elif ratio >= 1:
            return 5
        return 0

    def _score_broken_rate(self, rate: float) -> int:
        if rate <= 20:
            return 10
        elif rate <= 40:
            return 5
        return 0

    def _score_promotion_rate(self, rate: float) -> int:
        if rate >= 30:
            return 5
        elif rate >= 20:
            return 3
        return 0

    def _determine_phase(self, score: int) -> tuple:
        """确定周期阶段和策略"""
        if score >= 70:
            return CyclePhase.CLIMAX, "关注龙头换手，谨慎追高"
        elif score >= 50:
            return CyclePhase.WARMING, "参与龙头首板，低吸强势股"
        elif score >= 30:
            return CyclePhase.RECOVERY, "观察龙头能否走出，轻仓试错"
        elif score >= 10:
            return CyclePhase.TIDE_OUT, "减少操作，等待新龙头"
        else:
            return CyclePhase.ICE_POINT, "空仓观望，等待转机信号"
