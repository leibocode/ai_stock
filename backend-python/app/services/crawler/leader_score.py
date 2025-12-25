from dataclasses import dataclass
from typing import List, Dict
from loguru import logger


@dataclass
class LeaderScore:
    """龙头股评分"""
    code: str
    name: str
    continuous: int
    first_time: str
    open_times: int
    amount: float
    turnover: float
    market_cap: float
    score: int
    is_leader: bool


class LeaderScoreCalculator:
    """龙头股评分计算器

    评分规则 (满分80+):
    - 连板高度: continuous * 15 (最高45分)
    - 封板时间: 09:30前20分, 10:00前15分, 11:00前10分, 13:00前5分
    - 开板次数: 0次15分, 1次10分, <=3次5分, >3次-5分
    - 成交额: 3-15亿10分, 1-30亿5分, >50亿-5分
    - 换手率: 5-20%10分, 3-30%5分, >40%-5分
    - 市值: <=50亿10分, <=100亿5分, >500亿-5分

    龙头判定: 得分 >= 50
    """

    def calculate(self, stock: Dict) -> LeaderScore:
        """计算龙头评分

        Args:
            stock: 股票数据

        Returns:
            评分结果
        """
        score = 0
        continuous = stock.get("continuous", 1)
        first_time = stock.get("first_time", "15:00")
        open_times = stock.get("open_times", 0)
        amount = stock.get("amount", 0)
        turnover = stock.get("turnover", 0)
        market_cap = stock.get("market_cap", 100)

        # 连班高度得分
        score += continuous * 15

        # 封板时间得分
        score += self._score_first_time(first_time)

        # 开板次数得分
        score += self._score_open_times(open_times)

        # 成交额得分
        score += self._score_amount(amount)

        # 换手率得分
        score += self._score_turnover(turnover)

        # 市值得分
        score += self._score_market_cap(market_cap)

        return LeaderScore(
            code=stock.get("code", ""),
            name=stock.get("name", ""),
            continuous=continuous,
            first_time=first_time,
            open_times=open_times,
            amount=amount,
            turnover=turnover,
            market_cap=market_cap,
            score=score,
            is_leader=score >= 50,
        )

    def batch_calculate(self, stocks: List[Dict]) -> List[LeaderScore]:
        """批量计算龙头评分

        Args:
            stocks: 股票列表

        Returns:
            评分列表 (按评分倒序)
        """
        results = [self.calculate(stock) for stock in stocks]
        return sorted(results, key=lambda x: x.score, reverse=True)

    def _score_first_time(self, time_str: str) -> int:
        """封板时间评分"""
        try:
            parts = time_str.split(":")
            minutes = int(parts[0]) * 60 + int(parts[1])
            if minutes <= 570:  # 09:30
                return 20
            elif minutes <= 600:  # 10:00
                return 15
            elif minutes <= 660:  # 11:00
                return 10
            elif minutes <= 780:  # 13:00
                return 5
            return 0
        except Exception as e:
            logger.warning(f"Failed to score first_time: {e}")
            return 0

    def _score_open_times(self, times: int) -> int:
        """开板次数评分"""
        if times == 0:
            return 15
        elif times == 1:
            return 10
        elif times <= 3:
            return 5
        else:
            return -5

    def _score_amount(self, amount: float) -> int:
        """成交额评分 (亿)"""
        if 3 <= amount <= 15:
            return 10
        elif 1 <= amount <= 30:
            return 5
        elif amount > 50:
            return -5
        return 0

    def _score_turnover(self, turnover: float) -> int:
        """换手率评分 (%)"""
        if 5 <= turnover <= 20:
            return 10
        elif 3 <= turnover <= 30:
            return 5
        elif turnover > 40:
            return -5
        return 0

    def _score_market_cap(self, market_cap: float) -> int:
        """市值评分 (亿)"""
        if market_cap <= 50:
            return 10
        elif market_cap <= 100:
            return 5
        elif market_cap > 500:
            return -5
        return 0
