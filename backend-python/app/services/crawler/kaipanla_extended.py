# -*- coding: utf-8 -*-
"""开盘啦爬虫扩展 - 补充所有缺失的 API 接口"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json

class KaipanlaAppCrawlerExtended:
    """扩展的开盘啦爬虫，包含所有核心数据接口"""

    def __init__(self, api=None):
        self.api = api

    # ==================== 市场情绪走势数据 ====================

    def get_market_emotion_trend(self, date: str) -> Dict[str, Any]:
        """获取市场情绪走势数据（近7日）"""
        try:
            # 获取7天的数据
            trend_data = {
                'dates': [],
                'emotion_scores': [],
                'limit_up_counts': [],
                'limit_down_counts': [],
                'broken_counts': [],
            }

            for i in range(6, -1, -1):  # 最近7天
                target_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')

                # 获取该天的情绪数据
                emotion_data = self.api.get_disk_review(target_date)
                if emotion_data and 'info' in emotion_data:
                    emotion_score = int(emotion_data['info'].get('strong', 0))
                else:
                    emotion_score = 0

                # 获取涨跌停统计
                stats = self.api.get_statistics_num(target_date)
                limit_up = stats.get('nums', {}).get('ZT', 0) if stats and 'nums' in stats else 0
                limit_down = stats.get('nums', {}).get('DT', 0) if stats and 'nums' in stats else 0
                broken = stats.get('nums', {}).get('PB', 0) if stats and 'nums' in stats else 0

                trend_data['dates'].append(target_date)
                trend_data['emotion_scores'].append(emotion_score)
                trend_data['limit_up_counts'].append(limit_up)
                trend_data['limit_down_counts'].append(limit_down)
                trend_data['broken_counts'].append(broken)

            return trend_data

        except Exception as e:
            logger.error(f"获取情绪走势失败: {e}")
            return {}

    # ==================== 大幅回撤数据 ====================

    def get_sharp_withdrawal_detail(self, date: str = None) -> List[Dict]:
        """获取大幅回撤股票的完整列表（带详细信息）"""
        try:
            withdrawal_list = []

            # 尝试调用完整列表接口
            if hasattr(self.api, 'get') and callable(getattr(self.api, 'get')):
                # 使用通用的 _request 方法
                result = self.api._request('his', 'HisHomeDingPan', 'SharpWithdrawalList', {'Day': date})
                if result and 'list' in result:
                    for item in result['list']:
                        if isinstance(item, list) and len(item) >= 5:
                            withdrawal_list.append({
                                'code': str(item[0]),
                                'name': str(item[1]),
                                'high_withdrawal': float(item[2]) if item[2] else 0,
                                'close_withdrawal': float(item[3]) if item[3] else 0,
                                'amplitude': float(item[4]) if item[4] else 0,
                            })

            return withdrawal_list

        except Exception as e:
            logger.error(f"获取大幅回撤列表失败: {e}")
            return []

    # ==================== 龙头评分数据 ====================

    def calculate_leader_score(self, emotion_data: Dict, market_data: Dict) -> Dict[str, Any]:
        """计算龙头评分

        基于：
        - 连板高度 (最重要)
        - 封板时间
        - 开板次数
        - 成交额
        - 换手率
        """
        try:
            lianban = emotion_data.get('lianban', {})
            high_board = lianban.get('high_board', 0)
            third_board = lianban.get('third_board', 0)

            score = 0
            analysis = []

            # 1. 连板高度 (最重要，0-50分)
            if high_board >= 5:
                score += 50
                analysis.append(f"高度板{high_board}只，龙头效应明显 (+50分)")
            elif high_board >= 3:
                score += 30
                analysis.append(f"高度板{high_board}只，龙头效应较好 (+30分)")
            elif high_board > 0:
                score += 15
                analysis.append(f"高度板{high_board}只，龙头效应一般 (+15分)")
            else:
                analysis.append("暂无龙头，市场缺乏人气 (0分)")

            # 2. 封板质量 (0-20分)
            broken_rate = emotion_data.get('key_metrics', {}).get('broken_rate', 100)
            if broken_rate <= 15:
                score += 20
                analysis.append(f"炸板率{broken_rate}%，封板质量优 (+20分)")
            elif broken_rate <= 30:
                score += 10
                analysis.append(f"炸板率{broken_rate}%，封板质量良 (+10分)")
            else:
                analysis.append(f"炸板率{broken_rate}%，封板质量一般 (0分)")

            # 3. 连板晋级率 (0-15分)
            promotion_rate = emotion_data.get('key_metrics', {}).get('promotion_rate', 0)
            if promotion_rate >= 30:
                score += 15
                analysis.append(f"晋级率{promotion_rate}%，接力情绪好 (+15分)")
            elif promotion_rate >= 15:
                score += 8
                analysis.append(f"晋级率{promotion_rate}%，接力情绪中等 (+8分)")

            # 4. 市场情绪 (0-15分)
            emotion_phase = emotion_data.get('emotion_phase', 'repair')
            phase_scores = {
                'high_tide': 15,      # 高潮期 - 最适合龙头
                'warming': 12,        # 回暖期
                'repair': 8,          # 修复期
                'ebb_tide': 5,        # 退潮期
                'ice_point': 0,       # 冰点期
            }
            phase_score = phase_scores.get(emotion_phase, 0)
            score += phase_score
            if phase_score > 0:
                analysis.append(f"市场{emotion_phase}，龙头热度 (+{phase_score}分)")

            return {
                'total_score': min(score, 100),  # 最多100分
                'level': '★★★★★' if score >= 80 else '★★★★☆' if score >= 65 else '★★★☆☆' if score >= 50 else '★★☆☆☆' if score >= 35 else '★☆☆☆☆',
                'analysis': analysis,
                'recommendation': '强烈关注龙头机会' if score >= 80 else '关注龙头机会' if score >= 60 else '观望为主' if score >= 40 else '等待更好机会',
            }

        except Exception as e:
            logger.error(f"计算龙头评分失败: {e}")
            return {'total_score': 0, 'level': '☆☆☆☆☆', 'analysis': []}

    # ==================== 今日决策综合数据 ====================

    def get_today_decision_data(self, date: str = None) -> Dict[str, Any]:
        """获取今日决策页面的所有数据

        包含：
        - 情绪周期
        - 涨停/跌停数
        - 连板梯队
        - 大幅回撤
        - 龙头评分
        - 情绪走势（近7日）
        - 操作建议
        """

        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        result = {
            'date': date,
            'emotion_cycle': None,           # 情绪周期
            'market_stats': None,            # 涨跌停统计
            'lianban_info': None,            # 连板数据
            'withdrawal_warning': None,      # 大幅回撤
            'leader_score': None,            # 龙头评分
            'emotion_trend': None,           # 情绪走势（7日）
            'operation_advice': None,        # 操作建议
            'key_metrics': None,             # 关键指标
        }

        try:
            # 1. 获取基础情绪数据
            emotion_data = self.crawl_market_emotion(date)
            result['emotion_cycle'] = {
                'score': emotion_data.get('emotion_score', 0),
                'phase': emotion_data.get('emotion_phase', 'repair'),
                'sign': emotion_data.get('emotion_sign', ''),
            }

            # 2. 涨跌停统计
            result['market_stats'] = {
                'limit_up': emotion_data.get('limit_up_count', 0),
                'limit_down': emotion_data.get('limit_down_count', 0),
                'broken': emotion_data.get('broken_count', 0),
                'broken_rate': emotion_data.get('key_metrics', {}).get('broken_rate', 0),
            }

            # 3. 连板梯队
            result['lianban_info'] = emotion_data.get('lianban', {})

            # 4. 大幅回撤
            withdrawal_list = self.get_sharp_withdrawal_detail(date)
            result['withdrawal_warning'] = {
                'count': len(withdrawal_list),
                'top_stocks': withdrawal_list[:5] if withdrawal_list else [],
            }

            # 5. 龙头评分
            result['leader_score'] = self.calculate_leader_score(emotion_data, {})

            # 6. 情绪走势
            result['emotion_trend'] = self.get_market_emotion_trend(date)

            # 7. 关键指标
            result['key_metrics'] = emotion_data.get('key_metrics', {})

            # 8. 操作建议
            result['operation_advice'] = self._generate_advice(emotion_data)

            return result

        except Exception as e:
            logger.error(f"获取今日决策数据失败: {e}")
            return result

    def _generate_advice(self, emotion_data: Dict) -> Dict[str, str]:
        """根据情绪数据生成操作建议"""
        try:
            phase = emotion_data.get('emotion_phase', 'repair')
            score = emotion_data.get('emotion_score', 50)
            lianban = emotion_data.get('lianban', {})
            high_board = lianban.get('high_board', 0)

            advices = {
                'high_tide': {
                    'position': '30-50%',
                    'action': '减仓观望',
                    'focus': '追踪龙头但不追高，关注补涨机会',
                    'risk': '极高 - 注意高位风险'
                },
                'warming': {
                    'position': '50-70%',
                    'action': '积极参与',
                    'focus': '弱转强信号，首板确认，龙头回封',
                    'risk': '中低 - 情绪回暖中'
                },
                'repair': {
                    'position': '40-60%',
                    'action': '高抛低吸',
                    'focus': '技术超跌，金叉信号',
                    'risk': '中等 - 震荡修复中'
                },
                'ebb_tide': {
                    'position': '20-30%',
                    'action': '现金为王',
                    'focus': '等待企稳信号，不抄底',
                    'risk': '高 - 情绪退潮中'
                },
                'ice_point': {
                    'position': '60-80%',
                    'action': '分批抄底',
                    'focus': '超跌反弹，低位首板',
                    'risk': '低 - 恐慌出清后机会大'
                }
            }

            return advices.get(phase, advices['repair'])

        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            return {}

    # ==================== 辅助方法 ====================

    def crawl_market_emotion(self, date: str) -> Dict[str, Any]:
        """爬取市场情绪（来自主爬虫）"""
        # 这个方法应该在主爬虫中实现
        # 这里只是占位符
        return {}
