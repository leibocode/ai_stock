from typing import List, Dict
from loguru import logger


class MultiFactorCalculator:
    """多因子评分计算器"""

    def calculate_multi_factor_score(
        self,
        stock: Dict,
        indicators: Dict = None
    ) -> int:
        """计算多因子评分 (满分100)

        因子权重:
        - 涨幅(20分): >7%满分
        - 相对强度(20分): vs大盘 >10%满分
        - 板块强度(10分): vs大盘 >3%满分
        - 量比(10分): >2满分
        - 弱转强(15分): 低开高走满分
        - 涨速(5分): 分钟涨速>0.5%满分

        Args:
            stock: 股票数据
            indicators: 技术指标

        Returns:
            评分 (0-100)
        """
        score = 0

        # 涨幅
        pct_chg = stock.get("pct_chg", 0)
        if pct_chg > 7:
            score += 20
        elif pct_chg > 3:
            score += 10
        elif pct_chg > 0:
            score += 5

        # 相对强度 (vs大盘)
        relative_strength = stock.get("relative_strength", 0)
        if relative_strength > 10:
            score += 20
        elif relative_strength > 5:
            score += 10
        elif relative_strength > 0:
            score += 5

        # 板块强度
        sector_strength = stock.get("sector_strength", 0)
        if sector_strength > 3:
            score += 10
        elif sector_strength > 0:
            score += 5

        # 量比
        volume_ratio = stock.get("volume_ratio", 1)
        if volume_ratio > 2:
            score += 10
        elif volume_ratio > 1.5:
            score += 5

        # 弱转强
        if stock.get("weak_to_strong", False):
            score += 15

        # 涨速
        price_speed = stock.get("price_speed", 0)
        if price_speed > 0.5:
            score += 5
        elif price_speed > 0:
            score += 2

        return min(score, 100)

    def batch_calculate(
        self,
        stocks: List[Dict]
    ) -> List[Dict]:
        """批量计算多因子评分

        Args:
            stocks: 股票列表

        Returns:
            带评分的股票列表 (按评分倒序)
        """
        results = []
        for stock in stocks:
            score = self.calculate_multi_factor_score(stock)
            stock["multi_factor_score"] = score
            results.append(stock)

        return sorted(results, key=lambda x: x.get("multi_factor_score", 0), reverse=True)
