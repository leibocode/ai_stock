"""全市场趋势扫描服务

扫描全市场股票，筛选出现趋势拐点的股票
支持买入信号、卖出信号、拐点信号扫描
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncio
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chan import ChanService
from app.models import Stock, DailyQuote


@dataclass
class ScanResult:
    """扫描结果"""
    ts_code: str
    name: str
    signal_type: str              # "1买" / "2买" / "3买" / "1卖" / "2卖" / "3卖"
    signal_confidence: str        # "高" / "中" / "低"
    trend_status: str             # "上涨" / "下跌" / "盘整"
    trend_phase: str              # "延续" / "完成" / "切换"
    risk_level: str               # "高" / "中" / "低"
    current_price: float
    turning_points_count: int     # 最近拐点数
    suggestion: str
    score: float                  # 综合评分 0-100


class TrendScanner:
    """趋势扫描器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chan_service = ChanService(min_klines=100)

    async def scan_market(
        self,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[ScanResult]:
        """全市场扫描

        Args:
            date: 扫描日期（可选，默认为最新日期）
            limit: 扫描股票数量上限

        Returns:
            扫描结果列表
        """
        try:
            # 获取有行情数据的股票
            stmt = (
                select(Stock)
                .join(DailyQuote, Stock.ts_code == DailyQuote.ts_code)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            stocks = result.scalars().all()

            logger.info(f"开始扫描 {len(stocks)} 只股票...")

            # 并发扫描
            tasks = [
                self._scan_single_stock(stock)
                for stock in stocks
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤掉异常和None结果
            scan_results = [
                r for r in results
                if isinstance(r, ScanResult)
            ]

            # 按评分排序
            scan_results.sort(key=lambda x: x.score, reverse=True)

            logger.info(f"扫描完成，找到 {len(scan_results)} 只有信号的股票")
            return scan_results[:50]  # 返回前50个

        except Exception as e:
            logger.error(f"全市场扫描失败: {e}")
            return []

    async def scan_buy_signals(
        self,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[ScanResult]:
        """扫描买入信号

        Returns:
            包含买入信号的股票列表
        """
        try:
            results = await self.scan_market(date, limit)
            buy_results = [
                r for r in results
                if "买" in r.signal_type
            ]
            return buy_results

        except Exception as e:
            logger.error(f"买入信号扫描失败: {e}")
            return []

    async def scan_sell_signals(
        self,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[ScanResult]:
        """扫描卖出信号

        Returns:
            包含卖出信号的股票列表
        """
        try:
            results = await self.scan_market(date, limit)
            sell_results = [
                r for r in results
                if "卖" in r.signal_type
            ]
            return sell_results

        except Exception as e:
            logger.error(f"卖出信号扫描失败: {e}")
            return []

    async def _scan_single_stock(self, stock: Stock) -> Optional[ScanResult]:
        """扫描单只股票

        Args:
            stock: 股票对象

        Returns:
            扫描结果或None
        """
        try:
            ts_code = stock.ts_code

            # 获取K线数据
            stmt = (
                select(DailyQuote)
                .where(DailyQuote.ts_code == ts_code)
                .order_by(DailyQuote.trade_date.desc())
                .limit(200)
            )
            result = await self.db.execute(stmt)
            quotes = result.scalars().all()

            if len(quotes) < 100:
                return None

            # 转换为K线格式
            klines = [
                {
                    "trade_date": q.trade_date,
                    "open": float(q.open or 0),
                    "high": float(q.high or 0),
                    "low": float(q.low or 0),
                    "close": float(q.close or 0),
                    "vol": float(q.vol or 0),
                }
                for q in reversed(quotes)
            ]

            # 计算缠论
            chan_result = self.chan_service.calculate(ts_code, klines)

            if not chan_result or not chan_result.turning_points:
                return None

            # 提取最新拐点
            latest_tp = chan_result.turning_points[-1]

            # 生成扫描结果
            current_price = float(quotes[0].close or 0)
            turning_points_count = len(chan_result.turning_points)

            # 评分计算
            score = self._calc_score(chan_result, latest_tp)

            return ScanResult(
                ts_code=ts_code,
                name=stock.name or "",
                signal_type=latest_tp.signal_type.value,
                signal_confidence=self._get_confidence_label(latest_tp.confidence),
                trend_status=chan_result.trend.trend_type.value if chan_result.trend else "未知",
                trend_phase=chan_result.trend.phase.value if chan_result.trend else "未知",
                risk_level=chan_result.risk_level,
                current_price=current_price,
                turning_points_count=turning_points_count,
                suggestion=chan_result.suggestion or "",
                score=score
            )

        except Exception as e:
            logger.debug(f"{stock.ts_code}: 扫描失败 - {e}")
            return None

    @staticmethod
    def _calc_score(chan_result, latest_tp) -> float:
        """计算综合评分

        评分因素：
        - 信号置信度 (0-30)
        - 拐点状态是否确认 (0-20)
        - 风险等级 (0-20)
        - 趋势置信度 (0-20)
        - 拐点强度 (0-10)
        """
        score = 0

        # 1. 信号置信度
        if latest_tp.confidence >= 0.8:
            score += 30
        elif latest_tp.confidence >= 0.6:
            score += 20
        elif latest_tp.confidence >= 0.4:
            score += 10

        # 2. 拐点状态
        if latest_tp.status.value == "confirmed":
            score += 20
        elif latest_tp.status.value == "created":
            score += 10

        # 3. 风险等级（低风险得分高）
        if chan_result.risk_level == "低":
            score += 20
        elif chan_result.risk_level == "中":
            score += 10

        # 4. 趋势置信度
        if chan_result.trend:
            if chan_result.trend.confidence >= 0.8:
                score += 20
            elif chan_result.trend.confidence >= 0.5:
                score += 10

        # 5. 拐点强度（背驰>非背驰）
        if chan_result.macd_divergence and chan_result.macd_divergence.has_divergence:
            score += 10

        return min(100, score)

    @staticmethod
    def _get_confidence_label(confidence: float) -> str:
        """将置信度转换为标签"""
        if confidence >= 0.8:
            return "高"
        elif confidence >= 0.5:
            return "中"
        else:
            return "低"


def format_scan_results(results: List[ScanResult], max_count: int = 20) -> str:
    """格式化扫描结果

    Args:
        results: 扫描结果列表
        max_count: 最大显示数量

    Returns:
        格式化后的文本
    """
    report = []
    report.append("=" * 80)
    report.append("【全市场趋势扫描报告】")
    report.append("=" * 80)

    if not results:
        report.append("\n❌ 未找到符合条件的信号")
        report.append("=" * 80)
        return "\n".join(report)

    report.append(f"\n✅ 找到 {len(results)} 只有信号的股票\n")

    for i, r in enumerate(results[:max_count], 1):
        report.append(f"{i:2d}. 【{r.ts_code} {r.name}】")
        report.append(f"    信号: {r.signal_type} ({r.signal_confidence})")
        report.append(f"    趋势: {r.trend_status} - {r.trend_phase}")
        report.append(f"    价格: {r.current_price:.2f} | 风险: {r.risk_level}")
        report.append(f"    评分: {r.score:.0f}/100 | 拐点数: {r.turning_points_count}")
        report.append("")

    if len(results) > max_count:
        report.append(f"... 还有 {len(results) - max_count} 只股票\n")

    report.append("=" * 80)

    return "\n".join(report)
