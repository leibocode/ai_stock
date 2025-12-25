import pandas as pd
import numpy as np
from typing import Dict, List
from loguru import logger

try:
    import akshare as ak
except ImportError:
    ak = None


class MarketCrawler:
    """市场数据爬虫 - 用 pandas 替代逐条处理

    充分利用 pandas 的向量化操作，性能远优于循环
    """

    @staticmethod
    async def crawl_limit_up_down(trade_date: str) -> Dict:
        """爬取涨跌停数据 (返回 DataFrame，而不是列表)

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            {
                'limit_up': DataFrame,
                'limit_down': DataFrame,
                'statistics': {涨停数, 跌停数, 连板分布}
            }
        """
        if not ak:
            return {'limit_up': pd.DataFrame(), 'limit_down': pd.DataFrame()}

        try:
            # akshare 获取涨跌停数据
            limit_up_df = ak.limit_up_down(trade_date=trade_date, limit_type='U')
            limit_down_df = ak.limit_up_down(trade_date=trade_date, limit_type='D')

            # 向量化处理：提取连板数 (从名称中解析)
            limit_up_df['continuous'] = limit_up_df['名称'].str.extract(r'(\d+)板', expand=False).fillna(1).astype(int)

            # 计算连板分布
            continuous_dist = limit_up_df['continuous'].value_counts().to_dict()

            statistics = {
                'limit_up_count': len(limit_up_df),
                'limit_down_count': len(limit_down_df),
                'max_continuous': limit_up_df['continuous'].max() if len(limit_up_df) > 0 else 0,
                'continuous_distribution': continuous_dist,
            }

            return {
                'limit_up': limit_up_df,
                'limit_down': limit_down_df,
                'statistics': statistics,
            }

        except Exception as e:
            logger.error(f"Failed to crawl limit up/down: {e}")
            return {
                'limit_up': pd.DataFrame(),
                'limit_down': pd.DataFrame(),
                'statistics': {}
            }

    @staticmethod
    async def crawl_industry_performance(trade_date: str) -> pd.DataFrame:
        """爬取行业板块表现 (返回 DataFrame)

        Args:
            trade_date: 交易日期

        Returns:
            行业表现 DataFrame（涨幅、上涨家数、资金流向）
        """
        if not ak:
            return pd.DataFrame()

        try:
            # 获取行业板块数据
            industry_df = ak.gn_rank(date=trade_date.replace('', '-'))

            # 向量化计算：涨幅排序
            industry_df = industry_df.sort_values('涨跌幅', ascending=False)

            return industry_df

        except Exception as e:
            logger.error(f"Failed to crawl industry data: {e}")
            return pd.DataFrame()

    @staticmethod
    def calculate_emotion_cycle(limit_up_df: pd.DataFrame, limit_down_df: pd.DataFrame) -> Dict:
        """计算情绪周期 (用 pandas 向量化操作)

        Args:
            limit_up_df: 涨停 DataFrame
            limit_down_df: 跌停 DataFrame

        Returns:
            情绪周期结果
        """
        if limit_up_df.empty:
            return {'phase': '冰点期', 'score': 0}

        score = 0
        up_count = len(limit_up_df)
        down_count = len(limit_down_df)

        # 计算赚钱效应 (连板股占比)
        continuous_ge_2 = (limit_up_df['continuous'] >= 2).sum()
        profit_effect = continuous_ge_2 / max(up_count, 1) * 100

        # 计算得分
        if profit_effect >= 70:
            score += 30
        elif profit_effect >= 50:
            score += 20
        elif profit_effect >= 30:
            score += 10

        # 连板高度
        max_continuous = limit_up_df['continuous'].max() if len(limit_up_df) > 0 else 0
        if max_continuous >= 5:
            score += 20
        elif max_continuous >= 3:
            score += 10

        # 涨停数
        if up_count >= 80:
            score += 20
        elif up_count >= 50:
            score += 10

        # 涨跌比
        if down_count > 0:
            up_down_ratio = up_count / down_count
            if up_down_ratio >= 5:
                score += 15
            elif up_down_ratio >= 2:
                score += 10

        # 确定周期
        if score >= 70:
            phase = '高潮期'
            strategy = '追踪龙头，谨慎追高'
        elif score >= 50:
            phase = '回暖期'
            strategy = '参与龙头首板'
        elif score >= 30:
            phase = '修复期'
            strategy = '轻仓试错'
        elif score >= 10:
            phase = '退潮期'
            strategy = '减少操作'
        else:
            phase = '冰点期'
            strategy = '空仓观望'

        return {
            'phase': phase,
            'score': score,
            'limit_up_count': up_count,
            'limit_down_count': down_count,
            'profit_effect': round(profit_effect, 1),
            'max_continuous': int(max_continuous),
            'strategy': strategy,
        }

    @staticmethod
    def identify_leader_stocks(limit_up_df: pd.DataFrame) -> pd.DataFrame:
        """识别龙头股 (使用 pandas 向量化评分)

        Args:
            limit_up_df: 涨停 DataFrame (需包含 '连板数', '首封时间', '开板次数', '成交额', '换手率')

        Returns:
            龙头股 DataFrame (按评分排序)
        """
        if limit_up_df.empty:
            return pd.DataFrame()

        df = limit_up_df.copy()

        # 向量化评分
        df['score'] = 0

        # 连班高度 (权重最高)
        df['score'] += df.get('continuous', 1) * 15

        # 简化版龙头评分 (可根据实际数据调整)
        # 如果需要更复杂的评分，继续添加条件

        # 按评分排序
        df = df.sort_values('score', ascending=False)

        # 龙头判定: score >= 50
        df['is_leader'] = df['score'] >= 50

        return df
