# -*- coding: utf-8 -*-
"""开盘啦爬虫

数据源：https://www.kaipanla.com/ (网页版)
       longhuvip.com (App API)
提供涨停封单、炸板、连板梯队等核心数据
"""
import re
import json
import uuid
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from loguru import logger

from .base import BaseCrawler


# ==================== App API 封装 ====================

class KaipanlaAppAPI:
    """开盘啦App API封装 (基于抓包分析)

    核心域名:
    - apphis.longhuvip.com - 历史数据/复盘数据
    - apphwshhq.longhuvip.com - 行情数据
    - applhb.longhuvip.com - 主数据
    """

    DOMAINS = {
        'his': 'https://apphis.longhuvip.com',       # 历史/复盘
        'hq': 'https://apphwshhq.longhuvip.com',     # 行情
        'main': 'https://applhb.longhuvip.com',      # 主数据
        'article': 'https://apparticle.longhuvip.com',  # 文章
    }

    API_PATH = '/w1/api/index.php'

    def __init__(self, token: str = '', user_id: str = ''):
        self.token = token
        self.user_id = user_id
        self.device_id = str(uuid.uuid4())
        self.version = '5.22.0.6'
        self.session = requests.Session()
        # 必须使用 Dalvik User-Agent，否则返回空数据
        self.session.headers.update({
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; SM-G9730 Build/PQ3B.190801.12221815)',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept-Encoding': 'gzip',
            'Connection': 'Keep-Alive',
        })

    def _get_base_params(self) -> Dict[str, str]:
        """基础请求参数"""
        return {
            'apiv': 'w43',
            'PhoneOSNew': '1',
            'PhoneOS': '0',
            'VerSion': self.version,
            'Version': self.version,
            'DeviceID': self.device_id,
            'Token': self.token,
            'UserID': self.user_id,
        }

    def _request(self, domain: str, controller: str, action: str,
                 extra_params: Dict = None) -> Optional[Dict]:
        """发送API请求"""
        url = f"{self.DOMAINS.get(domain, self.DOMAINS['his'])}{self.API_PATH}"

        params = self._get_base_params()
        params['c'] = controller
        params['a'] = action
        if extra_params:
            params.update(extra_params)

        try:
            resp = self.session.post(url, data=params, timeout=15)
            resp.raise_for_status()

            try:
                return resp.json()
            except:
                text = resp.text.strip()
                if text.startswith('{') or text.startswith('['):
                    return json.loads(text)
                return None
        except Exception as e:
            logger.error(f"开盘啦API请求失败 [{action}]: {e}")
            return None

    # ========== 市场情绪/复盘核心API ==========

    def get_disk_review(self, date: str = None) -> Optional[Dict]:
        """获取复盘综合数据 (综合强度、趋势判断)

        返回: {"info": {"strong": "65", "sign": "短期大盘趋势偏强..."}, ...}
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'DiskReview', params)

    def get_index_real(self, date: str = None) -> Optional[Dict]:
        """获取指数实时数据 (上证/深证/创业板)

        返回: {"StockList": [{"prod_name": "上证指数", "last_px": "3914.01", ...}]}
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'StockL2History', 'GetZsReal', params)

    def get_market_volume(self, date: str = None) -> Optional[Dict]:
        """获取市场量能数据

        返回: {"info": {"last": "187393782", "yclnstr": "18739亿(18.17%,增量2881亿)", ...}}
        """
        params = {'Date': date} if date else {}  # MarketSCLN uses 'Date'
        return self._request('his', 'HisHomeDingPan', 'MarketSCLN', params)

    def get_rise_fall_detail(self, date: str = None) -> Optional[Dict]:
        """获取涨跌分布详情 (各涨跌幅区间家数)

        返回: {"info": {"-1": "986", "0": "162", "1": "1401", "10": "19", ...}}
        区间: -10到10，代表涨跌幅百分比
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'HisZhangFuDetail', params)

    def get_limit_expression(self, date: str = None) -> Optional[Dict]:
        """获取涨停表现 (一板/二板/三板/高度板数量及连板率)

        返回: {"info": [45, 11, 4, 3, 18.03, 80, 75, 30, ...], ...}
        格式: [一板数, 二板数, 三板数, 高度板数, 二板连板率, 三板连板率, 高度板连板率, ...]
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'ZhangTingExpression', params)

    def get_statistics_num(self, date: str = None) -> Optional[Dict]:
        """获取各类数量统计

        返回: {"nums": {"JJZZ": 76, "ZT": 63, "PB": 27, "DT": 3, ...}}
        JJZZ=竞价涨幅, ZT=涨停, PB=破板, DT=跌停, FYZ=封涨, QB=强板, ...
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'GetNum', params)

    def get_daban_list(self, date: str = None) -> Optional[Dict]:
        """获取打板列表 (涨停股详细信息)

        Args:
            date: 日期 YYYYMMDD 格式

        返回: {"list": [["002792", "通宇通讯", 连板数, "", 10.01, ...], ...]}

        注意: 该接口返回部分涨停股（约10只），如需完整列表需要登录认证
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'HisDaBanList', params)

    def get_weight_performance(self, date: str = None) -> Optional[Dict]:
        """获取权重表现 (板块涨跌)

        返回: {"info": {"XD": [["881156", "保险", -0.765, ...], ...]}}
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'WeightPerformance', params)

    def get_sharp_withdrawal(self, date: str = None) -> Optional[Dict]:
        """获取大幅回撤股票

        返回: {"info": [["688237", "超卓航科", -3.11, -12.54, 49.85], ...]}
        """
        params = {'Day': date} if date else {}
        return self._request('his', 'HisHomeDingPan', 'SharpWithdrawal', params)

    def get_homepage_info(self) -> Optional[Dict]:
        """获取首页综合信息 (排行榜等)

        返回: {"PHBList": [["002202", "金风科技", 0.99, ...], ...], ...}
        """
        return self._request('hq', 'Index', 'GetInfo')


class KaipanlaAppCrawler:
    """开盘啦App数据爬取服务"""

    def __init__(self, token: str = '', user_id: str = ''):
        self.api = KaipanlaAppAPI(token, user_id)

    def crawl_market_emotion(self, date: str = None) -> Dict[str, Any]:
        """爬取完整市场情绪数据

        Returns:
            {
                'date': '2025-12-01',
                'emotion_score': 65,           # 综合强度 (0-100)
                'emotion_sign': '短期大盘趋势偏强',  # 趋势判断
                'limit_up_count': 63,          # 涨停数
                'limit_down_count': 3,         # 跌停数
                'broken_count': 27,            # 破板数
                'rise_count': 3134,            # 上涨家数
                'fall_count': 1853,            # 下跌家数
                'rise_fall_distribution': {...}, # 涨跌分布
                'volume': 18739,               # 成交量(亿)
                'volume_change': '18.17%',     # 量能变化
                'lianban': {                   # 连板数据
                    'first_board': 45,
                    'second_board': 11,
                    'third_board': 4,
                    'high_board': 3,
                    'second_rate': 18.03,
                    'third_rate': 80,
                    'high_rate': 75
                },
                'index': {...}                 # 指数数据
            }
        """
        # 日期格式化：必须是 YYYY-MM-DD (如：2025-12-31)
        if date:
            # 保持 YYYY-MM-DD 格式
            if '-' not in date:
                # 如果是 YYYYMMDD 格式，转换为 YYYY-MM-DD
                date_param = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            else:
                date_param = date
        else:
            # 如果没有日期，使用昨天（因为当天数据可能未完成）
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            date_param = yesterday
            date = yesterday

        result = {
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'emotion_score': 0,
            'emotion_sign': '',
            'limit_up_count': 0,
            'limit_down_count': 0,
            'broken_count': 0,
            'rise_count': 0,
            'fall_count': 0,
            'rise_fall_distribution': {},
            'volume': 0,
            'volume_change': '',
            'lianban': {},
            'index': []
        }

        # 1. 复盘综合数据 (强度、趋势)
        disk_review = self.api.get_disk_review(date_param)
        if disk_review and 'info' in disk_review:
            info = disk_review['info']
            result['emotion_score'] = int(info.get('strong', 0))
            result['emotion_sign'] = info.get('sign', '')

        # 2. 数量统计 (涨停/跌停/破板)
        stats = self.api.get_statistics_num(date_param)
        if stats and 'nums' in stats:
            nums = stats['nums']
            result['limit_up_count'] = nums.get('ZT', 0)
            result['limit_down_count'] = nums.get('DT', 0)
            result['broken_count'] = nums.get('PB', 0)

        # 3. 涨跌分布
        rise_fall = self.api.get_rise_fall_detail(date_param)
        if rise_fall and 'info' in rise_fall:
            info = rise_fall['info']
            distribution = {}
            total_rise = 0
            total_fall = 0
            for k, v in info.items():
                try:
                    pct = int(k)
                    count = int(v)
                    distribution[f"{pct}%"] = count
                    if pct > 0:
                        total_rise += count
                    elif pct < 0:
                        total_fall += count
                except:
                    pass
            result['rise_fall_distribution'] = distribution
            result['rise_count'] = total_rise
            result['fall_count'] = total_fall

        # 4. 市场量能
        volume = self.api.get_market_volume(date_param)
        if volume and 'info' in volume:
            info = volume['info']
            try:
                vol_str = info.get('yclnstr', '')
                # 解析 "18739亿(18.17%,增量2881亿)"
                if '亿' in vol_str:
                    vol_num = float(vol_str.split('亿')[0])
                    result['volume'] = vol_num
                    if '(' in vol_str:
                        change = vol_str.split('(')[1].split(',')[0]
                        result['volume_change'] = change
            except:
                pass

        # 5. 连板数据
        lianban = self.api.get_limit_expression(date_param)
        if lianban and 'info' in lianban:
            info = lianban['info']
            if isinstance(info, list) and len(info) >= 7:
                result['lianban'] = {
                    'first_board': int(info[0]) if info[0] else 0,
                    'second_board': int(info[1]) if info[1] else 0,
                    'third_board': int(info[2]) if info[2] else 0,
                    'high_board': int(info[3]) if info[3] else 0,
                    'second_rate': float(info[4]) if info[4] else 0,
                    'third_rate': float(info[5]) if info[5] else 0,
                    'high_rate': float(info[6]) if info[6] else 0,
                }

        # 6. 指数数据
        index_data = self.api.get_index_real()
        if index_data and 'StockList' in index_data:
            result['index'] = [
                {
                    'name': item.get('prod_name', ''),
                    'price': float(item.get('last_px', 0)),
                    'change': item.get('increase_rate', ''),
                    'amount': float(item.get('increase_amount', 0)),
                }
                for item in index_data['StockList'][:5]
            ]

        return result

    def crawl_limit_up_list(self, date: str = None) -> List[Dict]:
        """爬取涨停股列表

        Returns:
            [
                {
                    'code': '002792',
                    'name': '通宇通讯',
                    'price': 10.01,
                    'continuous': 1,      # 连板数
                    'reason': '商业航天',  # 涨停原因
                    'seal_amount': 7.1,   # 封单(亿)
                    'first_time': '09:31', # 首板时间
                    ...
                }
            ]
        """
        stocks = []

        daban = self.api.get_daban_list(date)
        if daban and 'list' in daban:
            for item in daban['list']:
                try:
                    if isinstance(item, list) and len(item) >= 12:
                        stock = {
                            'code': str(item[0]),
                            'name': str(item[1]),
                            'continuous': int(item[2]) if item[2] else 1,
                            'price': float(item[4]) if item[4] else 0,
                            'reason': str(item[11]) if len(item) > 11 else '',
                            'seal_amount': float(item[12]) / 100000000 if len(item) > 12 and item[12] else 0,
                        }
                        stocks.append(stock)
                except Exception as e:
                    logger.debug(f"解析涨停股数据失败: {e}")
                    continue

        return stocks

    def determine_emotion_phase(self, emotion_data: Dict) -> str:
        """判断情绪阶段

        Returns:
            'high_tide' | 'ebb_tide' | 'ice_point' | 'warming' | 'repair'
        """
        score = emotion_data.get('emotion_score', 0)
        limit_up = emotion_data.get('limit_up_count', 0)
        lianban = emotion_data.get('lianban', {})
        high_board = lianban.get('high_board', 0) + lianban.get('third_board', 0)

        if score >= 80 and limit_up >= 60:
            return 'high_tide'      # 高潮期
        elif score >= 65 and high_board >= 5:
            return 'warming'        # 回暖期
        elif score >= 50:
            return 'repair'         # 修复期
        elif score >= 35:
            return 'ebb_tide'       # 退潮期
        else:
            return 'ice_point'      # 冰点期

    def crawl_sector_flow(self, date: str = None) -> List[Dict]:
        """爬取板块资金流向

        Returns:
            [{'name': '保险', 'pct_chg': -0.765, ...}, ...]
        """
        sectors = []
        weight = self.api.get_weight_performance(date)
        if weight and 'info' in weight:
            info = weight['info']
            # 上涨板块
            for item in info.get('SZ', [])[:10]:
                if isinstance(item, list) and len(item) >= 3:
                    sectors.append({
                        'code': str(item[0]),
                        'name': str(item[1]),
                        'pct_chg': float(item[2]) if item[2] else 0,
                        'type': 'up'
                    })
            # 下跌板块
            for item in info.get('XD', [])[:10]:
                if isinstance(item, list) and len(item) >= 3:
                    sectors.append({
                        'code': str(item[0]),
                        'name': str(item[1]),
                        'pct_chg': float(item[2]) if item[2] else 0,
                        'type': 'down'
                    })
        return sectors

    def crawl_sharp_withdrawal(self, date: str = None) -> List[Dict]:
        """爬取大幅回撤股票（风险预警）

        Returns:
            [{'code': '688237', 'name': '超卓航科', 'high_pct': -3.11, 'close_pct': -12.54, ...}, ...]
        """
        stocks = []
        withdrawal = self.api.get_sharp_withdrawal(date)
        if withdrawal and 'info' in withdrawal:
            for item in withdrawal['info']:
                if isinstance(item, list) and len(item) >= 5:
                    stocks.append({
                        'code': str(item[0]),
                        'name': str(item[1]),
                        'high_pct': float(item[2]) if item[2] else 0,
                        'close_pct': float(item[3]) if item[3] else 0,
                        'amplitude': float(item[4]) if item[4] else 0,
                    })
        return stocks

    def crawl_continuous_ladder(self, date: str = None) -> Dict[str, List[Dict]]:
        """爬取连板梯队详情（按连板数分组）

        Returns:
            {
                '2板': [{'code': 'xxx', 'name': 'xxx', ...}, ...],
                '3板': [...],
                '4板+': [...]
            }
        """
        ladder = {'2板': [], '3板': [], '4板+': []}
        all_stocks = self.crawl_limit_up_list(date)

        for stock in all_stocks:
            continuous = stock.get('continuous', 1)
            if continuous == 2:
                ladder['2板'].append(stock)
            elif continuous == 3:
                ladder['3板'].append(stock)
            elif continuous >= 4:
                ladder['4板+'].append(stock)

        # 按封单金额排序
        for key in ladder:
            ladder[key] = sorted(ladder[key], key=lambda x: x.get('seal_amount', 0), reverse=True)

        return ladder

    def crawl_full_decision_data(self, date: str = None) -> Dict[str, Any]:
        """爬取完整决策数据（一站式）

        整合所有数据，提供全面的决策支持
        """
        # 日期格式化：必须是 YYYYMMDD
        if date:
            date_param = date.replace('-', '') if '-' in date else date
        else:
            # 如果没有日期，使用昨天
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            date_param = yesterday

        # 基础情绪数据
        emotion = self.crawl_market_emotion(date_param)

        # 情绪阶段判断
        phase = self.determine_emotion_phase(emotion)
        emotion['emotion_phase'] = phase

        # 完整涨停股列表
        all_limit_up = self.crawl_limit_up_list(date_param)
        emotion['limit_up_stocks'] = all_limit_up

        # 连板梯队详情
        ladder = self.crawl_continuous_ladder(date_param)
        emotion['continuous_ladder'] = ladder

        # 板块资金流向
        sectors = self.crawl_sector_flow(date_param)
        emotion['sector_flow'] = sectors

        # 大幅回撤预警
        withdrawal = self.crawl_sharp_withdrawal(date_param)
        emotion['sharp_withdrawal'] = withdrawal

        # 计算关键指标
        lianban = emotion.get('lianban', {})
        first_board = lianban.get('first_board', 0)
        second_board = lianban.get('second_board', 0)
        broken = emotion.get('broken_count', 0)

        # 计算晋级率和炸板率
        if first_board > 0:
            promotion_rate = round(second_board / first_board * 100, 1)
        else:
            promotion_rate = 0

        total_attempt = emotion.get('limit_up_count', 0) + broken
        if total_attempt > 0:
            broken_rate = round(broken / total_attempt * 100, 1)
        else:
            broken_rate = 0

        emotion['key_metrics'] = {
            'promotion_rate': promotion_rate,   # 晋级率(一进二)
            'broken_rate': broken_rate,         # 炸板率
            'max_height': len(ladder['4板+']) + 4 if ladder['4板+'] else (3 if ladder['3板'] else 2),
            'up_ratio': round(emotion.get('rise_count', 0) / max(emotion.get('rise_count', 0) + emotion.get('fall_count', 1), 1) * 100, 1),
        }

        # 生成详细策略建议
        emotion['strategy_detail'] = self._generate_strategy(emotion, phase)

        return emotion

    def _generate_strategy(self, data: Dict, phase: str) -> Dict:
        """生成详细策略建议"""
        lianban = data.get('lianban', {})
        metrics = data.get('key_metrics', {})
        score = data.get('emotion_score', 50)

        # 基础策略
        strategies = {
            'high_tide': {
                'position': '30-50%',
                'action': '减仓观望',
                'focus': '追踪龙头但不追高，关注补涨股',
                'risk': '极高，注意高位风险'
            },
            'ebb_tide': {
                'position': '20-30%',
                'action': '现金为王',
                'focus': '等待企稳信号，不抄底',
                'risk': '高，情绪退潮中'
            },
            'ice_point': {
                'position': '60-80%',
                'action': '分批抄底',
                'focus': '超跌反弹+低位首板',
                'risk': '低，恐慌出清后机会大'
            },
            'warming': {
                'position': '50-70%',
                'action': '积极参与',
                'focus': '弱转强+首板确认+龙头回封',
                'risk': '中低，情绪回暖中'
            },
            'repair': {
                'position': '40-60%',
                'action': '高抛低吸',
                'focus': '技术超跌+金叉信号',
                'risk': '中等，震荡修复中'
            }
        }

        base = strategies.get(phase, strategies['repair'])

        # 根据具体数据调整
        adjustments = []

        # 连板高度分析
        high_board = lianban.get('high_board', 0)
        third_board = lianban.get('third_board', 0)
        if high_board >= 3:
            adjustments.append(f"高度板{high_board}只，市场有龙头效应")
        elif high_board == 0 and third_board == 0:
            adjustments.append("无高度板，市场缺乏人气龙头")

        # 晋级率分析
        promotion = metrics.get('promotion_rate', 0)
        if promotion >= 30:
            adjustments.append(f"晋级率{promotion}%较高，接力情绪好")
        elif promotion <= 15:
            adjustments.append(f"晋级率{promotion}%偏低，接力谨慎")

        # 炸板率分析
        broken_rate = metrics.get('broken_rate', 0)
        if broken_rate >= 30:
            adjustments.append(f"炸板率{broken_rate}%较高，追涨需谨慎")
        elif broken_rate <= 15:
            adjustments.append(f"炸板率{broken_rate}%较低，封板质量好")

        # 涨跌比分析
        up_ratio = metrics.get('up_ratio', 50)
        if up_ratio >= 65:
            adjustments.append(f"涨跌比{up_ratio}%，普涨行情")
        elif up_ratio <= 35:
            adjustments.append(f"涨跌比{up_ratio}%，普跌行情")

        # 量能分析
        volume_change = data.get('volume_change', '')
        if volume_change and '%' in volume_change:
            try:
                vol_pct = float(volume_change.replace('%', ''))
                if vol_pct >= 20:
                    adjustments.append(f"量能放大{volume_change}，资金活跃")
                elif vol_pct <= -20:
                    adjustments.append(f"量能萎缩{volume_change}，观望情绪重")
            except:
                pass

        base['adjustments'] = adjustments
        base['score'] = score
        base['phase_name'] = {
            'high_tide': '高潮期',
            'ebb_tide': '退潮期',
            'ice_point': '冰点期',
            'warming': '回暖期',
            'repair': '修复期'
        }.get(phase, '未知')

        return base


# ==================== 网页版爬虫 (原有) ====================

class KaipanlaCrawler(BaseCrawler):
    """开盘啦数据爬虫

    核心数据：
    1. 涨停股列表（含封单额、首次涨停时间、连板数）
    2. 炸板股列表（开板次数、最终状态）
    3. 连板梯队（1板/2板/3板+分布）
    4. 跌停股列表
    5. 昨日涨停今日表现（溢价率）
    """

    # 开盘啦基础URL
    BASE_URL = "https://www.kaipanla.com"
    API_URL = "https://pchq.kaipanla.com"

    # 开盘啦专用请求头
    KAIPANLA_HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.kaipanla.com",
        "Referer": "https://www.kaipanla.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, **kwargs):
        # 开盘啦反爬较弱，可以使用较短延迟
        kwargs.setdefault('delay_range', (1.0, 2.5))
        kwargs.setdefault('retry_count', 3)
        super().__init__(**kwargs)

    def _get_random_headers(self) -> Dict[str, str]:
        """获取开盘啦专用请求头"""
        headers = super()._get_random_headers()
        headers.update(self.KAIPANLA_HEADERS)
        return headers

    async def get_limit_up_list(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取涨停股列表

        Args:
            date: 日期，格式 YYYYMMDD，默认今天

        Returns:
            {
                "date": "20251228",
                "count": 45,
                "stocks": [
                    {
                        "code": "000001",
                        "name": "平安银行",
                        "price": 12.50,
                        "pct_chg": 10.0,
                        "seal_amount": 5.2,  # 封单额(亿)
                        "seal_ratio": 15.3,  # 封单比(%)
                        "first_time": "09:35:20",  # 首次涨停时间
                        "open_times": 0,  # 开板次数
                        "continuous": 2,  # 连板数
                        "reason": "人工智能",  # 涨停原因
                        "is_new": False,  # 是否新股
                    }
                ],
                "statistics": {
                    "total": 45,
                    "first_board": 30,  # 首板数
                    "continuous_board": 15,  # 连板数
                    "avg_seal_amount": 2.3,
                }
            }
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        try:
            # 开盘啦涨停板接口
            url = f"{self.API_URL}/q/stock/soar"
            params = {
                "date": date,
                "type": "zt",  # zt=涨停
                "order": "first_time",
                "desc": 0,
            }

            data = await self.get(url, params=params)

            if not data:
                logger.warning(f"开盘啦涨停数据为空: {date}")
                return self._empty_limit_up_result(date)

            return self._parse_limit_up_data(date, data)

        except Exception as e:
            logger.error(f"获取开盘啦涨停数据失败: {e}")
            return self._empty_limit_up_result(date)

    async def get_broken_board_list(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取炸板股列表

        Args:
            date: 日期，格式 YYYYMMDD

        Returns:
            {
                "date": "20251228",
                "count": 12,
                "broken_rate": 21.0,  # 炸板率(%)
                "stocks": [
                    {
                        "code": "000002",
                        "name": "万科A",
                        "price": 8.50,
                        "pct_chg": 5.2,
                        "open_times": 3,  # 开板次数
                        "first_time": "09:42:15",  # 首次涨停时间
                        "broken_time": "10:15:30",  # 炸板时间
                        "final_status": "red",  # 最终状态: red/green
                        "reason": "房地产",
                    }
                ]
            }
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        try:
            url = f"{self.API_URL}/q/stock/soar"
            params = {
                "date": date,
                "type": "zb",  # zb=炸板
                "order": "open_times",
                "desc": 1,
            }

            data = await self.get(url, params=params)

            if not data:
                logger.warning(f"开盘啦炸板数据为空: {date}")
                return self._empty_broken_board_result(date)

            return self._parse_broken_board_data(date, data)

        except Exception as e:
            logger.error(f"获取开盘啦炸板数据失败: {e}")
            return self._empty_broken_board_result(date)

    async def get_continuous_board_ladder(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取连板梯队

        Args:
            date: 日期，格式 YYYYMMDD

        Returns:
            {
                "date": "20251228",
                "max_height": 8,  # 最高连板
                "ladder": {
                    "8板": [{"code": "xxx", "name": "xxx", ...}],
                    "7板": [...],
                    "6板": [...],
                    ...
                },
                "statistics": {
                    "total_continuous": 25,
                    "height_distribution": {
                        "2板": 12,
                        "3板": 6,
                        "4板": 3,
                        "5板+": 4,
                    }
                }
            }
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        try:
            # 先获取涨停列表，筛选连板股
            limit_up_data = await self.get_limit_up_list(date)

            stocks = limit_up_data.get("stocks", [])
            continuous_stocks = [s for s in stocks if s.get("continuous", 0) >= 2]

            # 按连板数分组
            ladder = {}
            max_height = 0

            for stock in continuous_stocks:
                height = stock.get("continuous", 0)
                max_height = max(max_height, height)
                key = f"{height}板"
                if key not in ladder:
                    ladder[key] = []
                ladder[key].append(stock)

            # 统计
            height_distribution = {}
            for stock in continuous_stocks:
                height = stock.get("continuous", 0)
                if height >= 5:
                    key = "5板+"
                else:
                    key = f"{height}板"
                height_distribution[key] = height_distribution.get(key, 0) + 1

            return {
                "date": date,
                "max_height": max_height,
                "ladder": ladder,
                "statistics": {
                    "total_continuous": len(continuous_stocks),
                    "height_distribution": height_distribution,
                }
            }

        except Exception as e:
            logger.error(f"获取连板梯队失败: {e}")
            return {
                "date": date,
                "max_height": 0,
                "ladder": {},
                "statistics": {"total_continuous": 0, "height_distribution": {}}
            }

    async def get_limit_down_list(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取跌停股列表

        Args:
            date: 日期，格式 YYYYMMDD

        Returns:
            {
                "date": "20251228",
                "count": 8,
                "stocks": [
                    {
                        "code": "000003",
                        "name": "xxx",
                        "price": 5.20,
                        "pct_chg": -10.0,
                        "seal_amount": 1.5,  # 封单额(亿)
                        "first_time": "09:45:00",
                        "reason": "业绩暴雷",
                    }
                ]
            }
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        try:
            url = f"{self.API_URL}/q/stock/soar"
            params = {
                "date": date,
                "type": "dt",  # dt=跌停
                "order": "first_time",
                "desc": 0,
            }

            data = await self.get(url, params=params)

            if not data:
                return {"date": date, "count": 0, "stocks": []}

            return self._parse_limit_down_data(date, data)

        except Exception as e:
            logger.error(f"获取开盘啦跌停数据失败: {e}")
            return {"date": date, "count": 0, "stocks": []}

    async def get_yesterday_limit_up_performance(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取昨日涨停今日表现

        Args:
            date: 日期，格式 YYYYMMDD（查询该日昨涨停的表现）

        Returns:
            {
                "date": "20251228",
                "count": 40,
                "avg_premium": 2.5,  # 平均溢价率(%)
                "statistics": {
                    "up_count": 25,  # 上涨数
                    "down_count": 15,  # 下跌数
                    "limit_up_count": 5,  # 再涨停数
                    "limit_down_count": 2,  # 跌停数
                },
                "stocks": [
                    {
                        "code": "000001",
                        "name": "平安银行",
                        "yesterday_continuous": 2,  # 昨日连板数
                        "today_open": 12.80,  # 今日开盘价
                        "today_close": 13.10,  # 今日收盘价
                        "premium": 5.2,  # 溢价率(%)
                        "today_status": "up",  # up/down/limit_up/limit_down
                    }
                ]
            }
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        try:
            url = f"{self.API_URL}/q/stock/soar"
            params = {
                "date": date,
                "type": "yzzt",  # yzzt=昨日涨停
                "order": "premium",
                "desc": 1,
            }

            data = await self.get(url, params=params)

            if not data:
                return {
                    "date": date,
                    "count": 0,
                    "avg_premium": 0,
                    "statistics": {},
                    "stocks": []
                }

            return self._parse_yesterday_performance_data(date, data)

        except Exception as e:
            logger.error(f"获取昨日涨停今日表现失败: {e}")
            return {
                "date": date,
                "count": 0,
                "avg_premium": 0,
                "statistics": {},
                "stocks": []
            }

    async def get_full_emotion_data(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取完整情绪数据（一站式）

        整合涨停、炸板、连板、跌停、昨日表现等数据

        Returns:
            {
                "date": "20251228",
                "limit_up": {...},
                "broken_board": {...},
                "continuous_ladder": {...},
                "limit_down": {...},
                "yesterday_performance": {...},
                "emotion_score": 65,  # 综合情绪得分
                "emotion_phase": "warming",  # 情绪阶段
            }
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        # 并发获取所有数据
        import asyncio

        results = await asyncio.gather(
            self.get_limit_up_list(date),
            self.get_broken_board_list(date),
            self.get_continuous_board_ladder(date),
            self.get_limit_down_list(date),
            self.get_yesterday_limit_up_performance(date),
            return_exceptions=True
        )

        limit_up = results[0] if not isinstance(results[0], Exception) else self._empty_limit_up_result(date)
        broken_board = results[1] if not isinstance(results[1], Exception) else self._empty_broken_board_result(date)
        continuous_ladder = results[2] if not isinstance(results[2], Exception) else {}
        limit_down = results[3] if not isinstance(results[3], Exception) else {"count": 0}
        yesterday_perf = results[4] if not isinstance(results[4], Exception) else {}

        # 计算综合情绪得分
        emotion_score = self._calculate_emotion_score(
            limit_up, broken_board, continuous_ladder, limit_down, yesterday_perf
        )

        # 判断情绪阶段
        emotion_phase = self._determine_emotion_phase(emotion_score, limit_up, broken_board)

        return {
            "date": date,
            "limit_up": limit_up,
            "broken_board": broken_board,
            "continuous_ladder": continuous_ladder,
            "limit_down": limit_down,
            "yesterday_performance": yesterday_perf,
            "emotion_score": emotion_score,
            "emotion_phase": emotion_phase,
        }

    # ============== 数据解析方法 ==============

    def _parse_limit_up_data(self, date: str, data: Any) -> Dict[str, Any]:
        """解析涨停数据"""
        stocks = []

        items = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        for item in items:
            try:
                stock = {
                    "code": str(item.get("code", "")).zfill(6),
                    "name": item.get("name", ""),
                    "price": float(item.get("price", 0)),
                    "pct_chg": float(item.get("pct_chg", item.get("chg", 0))),
                    "seal_amount": float(item.get("seal_amount", item.get("fde", 0))) / 10000,  # 转为亿
                    "seal_ratio": float(item.get("seal_ratio", item.get("fdn", 0))),
                    "first_time": item.get("first_time", item.get("ft", "")),
                    "open_times": int(item.get("open_times", item.get("oc", 0))),
                    "continuous": int(item.get("continuous", item.get("lbc", 1))),
                    "reason": item.get("reason", item.get("tag", "")),
                    "is_new": item.get("is_new", False),
                }
                stocks.append(stock)
            except Exception as e:
                logger.debug(f"解析涨停股数据失败: {e}")
                continue

        # 统计
        first_board = len([s for s in stocks if s["continuous"] == 1])
        continuous_board = len([s for s in stocks if s["continuous"] >= 2])
        total_seal = sum(s["seal_amount"] for s in stocks)
        avg_seal = total_seal / len(stocks) if stocks else 0

        return {
            "date": date,
            "count": len(stocks),
            "stocks": stocks,
            "statistics": {
                "total": len(stocks),
                "first_board": first_board,
                "continuous_board": continuous_board,
                "avg_seal_amount": round(avg_seal, 2),
            }
        }

    def _parse_broken_board_data(self, date: str, data: Any) -> Dict[str, Any]:
        """解析炸板数据"""
        stocks = []

        items = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        for item in items:
            try:
                pct_chg = float(item.get("pct_chg", item.get("chg", 0)))
                stock = {
                    "code": str(item.get("code", "")).zfill(6),
                    "name": item.get("name", ""),
                    "price": float(item.get("price", 0)),
                    "pct_chg": pct_chg,
                    "open_times": int(item.get("open_times", item.get("oc", 0))),
                    "first_time": item.get("first_time", item.get("ft", "")),
                    "broken_time": item.get("broken_time", item.get("bt", "")),
                    "final_status": "red" if pct_chg > 0 else "green",
                    "reason": item.get("reason", item.get("tag", "")),
                }
                stocks.append(stock)
            except Exception as e:
                logger.debug(f"解析炸板股数据失败: {e}")
                continue

        # 炸板率需要涨停总数，这里返回炸板数
        return {
            "date": date,
            "count": len(stocks),
            "broken_rate": 0,  # 需要外部计算
            "stocks": stocks,
        }

    def _parse_limit_down_data(self, date: str, data: Any) -> Dict[str, Any]:
        """解析跌停数据"""
        stocks = []

        items = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        for item in items:
            try:
                stock = {
                    "code": str(item.get("code", "")).zfill(6),
                    "name": item.get("name", ""),
                    "price": float(item.get("price", 0)),
                    "pct_chg": float(item.get("pct_chg", item.get("chg", 0))),
                    "seal_amount": float(item.get("seal_amount", item.get("fde", 0))) / 10000,
                    "first_time": item.get("first_time", item.get("ft", "")),
                    "reason": item.get("reason", item.get("tag", "")),
                }
                stocks.append(stock)
            except Exception as e:
                logger.debug(f"解析跌停股数据失败: {e}")
                continue

        return {
            "date": date,
            "count": len(stocks),
            "stocks": stocks,
        }

    def _parse_yesterday_performance_data(self, date: str, data: Any) -> Dict[str, Any]:
        """解析昨日涨停今日表现数据"""
        stocks = []

        items = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []

        total_premium = 0
        up_count = 0
        down_count = 0
        limit_up_count = 0
        limit_down_count = 0

        for item in items:
            try:
                pct_chg = float(item.get("pct_chg", item.get("chg", 0)))
                premium = float(item.get("premium", pct_chg))

                # 确定状态
                if pct_chg >= 9.9:
                    status = "limit_up"
                    limit_up_count += 1
                elif pct_chg <= -9.9:
                    status = "limit_down"
                    limit_down_count += 1
                elif pct_chg > 0:
                    status = "up"
                    up_count += 1
                else:
                    status = "down"
                    down_count += 1

                stock = {
                    "code": str(item.get("code", "")).zfill(6),
                    "name": item.get("name", ""),
                    "yesterday_continuous": int(item.get("lbc", 1)),
                    "today_open": float(item.get("open", 0)),
                    "today_close": float(item.get("close", item.get("price", 0))),
                    "premium": premium,
                    "today_status": status,
                }
                stocks.append(stock)
                total_premium += premium

            except Exception as e:
                logger.debug(f"解析昨日涨停数据失败: {e}")
                continue

        avg_premium = total_premium / len(stocks) if stocks else 0

        return {
            "date": date,
            "count": len(stocks),
            "avg_premium": round(avg_premium, 2),
            "statistics": {
                "up_count": up_count + limit_up_count,
                "down_count": down_count + limit_down_count,
                "limit_up_count": limit_up_count,
                "limit_down_count": limit_down_count,
            },
            "stocks": stocks,
        }

    def _calculate_emotion_score(
        self,
        limit_up: Dict,
        broken_board: Dict,
        continuous_ladder: Dict,
        limit_down: Dict,
        yesterday_perf: Dict
    ) -> int:
        """计算综合情绪得分 (0-100)"""
        score = 50  # 基础分

        # 1. 涨停数 (权重40%)
        limit_up_count = limit_up.get("count", 0)
        if limit_up_count >= 80:
            score += 20
        elif limit_up_count >= 50:
            score += 15
        elif limit_up_count >= 30:
            score += 8
        elif limit_up_count < 15:
            score -= 15

        # 2. 连板高度 (权重20%)
        max_height = continuous_ladder.get("max_height", 0)
        if max_height >= 7:
            score += 12
        elif max_height >= 5:
            score += 8
        elif max_height >= 3:
            score += 4
        elif max_height < 2:
            score -= 8

        # 3. 炸板率 (权重20%)
        broken_count = broken_board.get("count", 0)
        if limit_up_count > 0:
            broken_rate = broken_count / limit_up_count * 100
            if broken_rate < 10:
                score += 10
            elif broken_rate < 20:
                score += 5
            elif broken_rate > 40:
                score -= 10

        # 4. 跌停数 (权重10%)
        limit_down_count = limit_down.get("count", 0)
        if limit_down_count < 5:
            score += 5
        elif limit_down_count > 20:
            score -= 10

        # 5. 昨日溢价率 (权重10%)
        avg_premium = yesterday_perf.get("avg_premium", 0)
        if avg_premium > 3:
            score += 5
        elif avg_premium < -2:
            score -= 5

        return max(0, min(100, score))

    def _determine_emotion_phase(
        self,
        score: int,
        limit_up: Dict,
        broken_board: Dict
    ) -> str:
        """判断情绪阶段"""
        limit_up_count = limit_up.get("count", 0)
        broken_count = broken_board.get("count", 0)

        if score >= 80 and limit_up_count >= 60:
            return "high_tide"  # 高潮期
        elif score >= 65:
            return "warming"  # 回暖期
        elif score >= 50:
            return "repair"  # 修复期
        elif score >= 35:
            return "ebb_tide"  # 退潮期
        else:
            return "ice_point"  # 冰点期

    def _empty_limit_up_result(self, date: str) -> Dict:
        """返回空涨停结果"""
        return {
            "date": date,
            "count": 0,
            "stocks": [],
            "statistics": {
                "total": 0,
                "first_board": 0,
                "continuous_board": 0,
                "avg_seal_amount": 0,
            }
        }

    def _empty_broken_board_result(self, date: str) -> Dict:
        """返回空炸板结果"""
        return {
            "date": date,
            "count": 0,
            "broken_rate": 0,
            "stocks": [],
        }
