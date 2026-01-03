import axios from 'axios'
import {
  mockVolumeTop,
  mockOversold,
  mockKdjBottom,
  mockMacdGolden,
  mockBottomVolume,
  mockIndustryHot,
  mockReview,
} from './mock'

// Mock模式开关
const USE_MOCK = false

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res.data.code === 0 ? res.data.data : Promise.reject(new Error(res.data.msg || '请求失败')),
  (err) => Promise.reject(err)
)

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// 成交量TOP50
export const getVolumeTop = async (date) => {
  if (USE_MOCK) { await delay(200); return mockVolumeTop }
  return api.get('/volume-top', { params: { date } })
}

// RSI超卖
export const getOversold = async (date) => {
  if (USE_MOCK) { await delay(200); return mockOversold }
  return api.get('/oversold', { params: { date } })
}

// KDJ见底
export const getKDJBottom = async (date) => {
  if (USE_MOCK) { await delay(200); return mockKdjBottom }
  return api.get('/kdj-bottom', { params: { date } })
}

// MACD金叉
export const getMACDGolden = async (date) => {
  if (USE_MOCK) { await delay(200); return mockMacdGolden }
  return api.get('/macd-golden', { params: { date } })
}

// 底部放量
export const getBottomVolume = async (date) => {
  if (USE_MOCK) { await delay(200); return mockBottomVolume }
  return api.get('/bottom-volume', { params: { date } })
}

// 行业异动
export const getIndustryHot = async (date) => {
  if (USE_MOCK) { await delay(200); return mockIndustryHot }
  return api.get('/industry-hot', { params: { date } })
}

// 大盘指数
export const getMarketIndex = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '000001.SH', close: 3050.12, pct_chg: -2.35 },
      { ts_code: '399001.SZ', close: 9876.54, pct_chg: -2.89 },
      { ts_code: '399006.SZ', close: 1987.65, pct_chg: -3.12 },
    ]
  }
  return api.get('/market-index', { params: { date } })
}

// 逆势上涨
export const getCounterTrend = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '002049.SZ', name: '紫光国微', industry: '芯片', close: 125.6, pct_chg: 5.23, volume_ratio: 3.2 },
      { ts_code: '300750.SZ', name: '宁德时代', industry: '电池', close: 189.3, pct_chg: 4.87, volume_ratio: 2.8 },
      { ts_code: '002594.SZ', name: '比亚迪', industry: '汽车', close: 256.8, pct_chg: 3.56, volume_ratio: 2.5 },
      { ts_code: '300059.SZ', name: '东方财富', industry: '券商', close: 18.9, pct_chg: 3.21, volume_ratio: 2.1 },
    ]
  }
  return api.get('/counter-trend', { params: { date } })
}

// 市场统计
export const getMarketStats = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return { limitUp: 45, limitDown: 12, northFlow: -28.5 }
  }
  return api.get('/market-stats', { params: { date } })
}

// 涨停列表
export const getLimitUpList = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '002049.SZ', name: '紫光国微', industry: '芯片', first_time: '09:32', open_times: 0, continuous: 3 },
      { ts_code: '300782.SZ', name: '卓胜微', industry: '芯片', first_time: '09:45', open_times: 1, continuous: 2 },
      { ts_code: '688012.SH', name: '中微公司', industry: '半导体', first_time: '10:05', open_times: 0, continuous: 1 },
      { ts_code: '002371.SZ', name: '北方华创', industry: '半导体', first_time: '10:15', open_times: 2, continuous: 1 },
      { ts_code: '603259.SH', name: '药明康德', industry: '医药', first_time: '13:05', open_times: 0, continuous: 1 },
    ]
  }
  return api.get('/limit-up', { params: { date } })
}

// 跌停列表
export const getLimitDownList = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '000001.SZ', name: '某股票A', industry: '房地产', reason: '业绩暴雷' },
      { ts_code: '000002.SZ', name: '某股票B', industry: '房地产', reason: '股东减持' },
      { ts_code: '000003.SZ', name: '某股票C', industry: '教育', reason: '政策利空' },
    ]
  }
  return api.get('/limit-down', { params: { date } })
}

// 龙虎榜
export const getDragonTiger = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '002049.SZ', name: '紫光国微', reason: '涨幅偏离7%', buy: 15623, sell: 8956 },
      { ts_code: '300750.SZ', name: '宁德时代', reason: '换手率20%', buy: 28456, sell: 12345 },
      { ts_code: '002594.SZ', name: '比亚迪', reason: '涨幅偏离7%', buy: 18765, sell: 9876 },
      { ts_code: '600519.SH', name: '贵州茅台', reason: '机构专用', buy: 45678, sell: 23456 },
    ]
  }
  return api.get('/dragon-tiger', { params: { date } })
}

// 北向资金买入
export const getNorthBuy = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '600519.SH', name: '贵州茅台', industry: '白酒', net_buy: 56789, hold_ratio: '8.5%' },
      { ts_code: '000858.SZ', name: '五粮液', industry: '白酒', net_buy: 34567, hold_ratio: '6.2%' },
      { ts_code: '601318.SH', name: '中国平安', industry: '保险', net_buy: 23456, hold_ratio: '5.8%' },
      { ts_code: '000333.SZ', name: '美的集团', industry: '家电', net_buy: 18765, hold_ratio: '4.5%' },
    ]
  }
  return api.get('/north-buy', { params: { date } })
}

// 融资买入
export const getMarginBuy = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '600519.SH', name: '贵州茅台', industry: '白酒', rz_buy: 45678, rz_balance: 125.6 },
      { ts_code: '601318.SH', name: '中国平安', industry: '保险', rz_buy: 34567, rz_balance: 98.5 },
      { ts_code: '000858.SZ', name: '五粮液', industry: '白酒', rz_buy: 28765, rz_balance: 76.8 },
      { ts_code: '002594.SZ', name: '比亚迪', industry: '汽车', rz_buy: 23456, rz_balance: 65.4 },
    ]
  }
  return api.get('/margin-buy', { params: { date } })
}

// 突破形态
export const getBreakout = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '002049.SZ', name: '紫光国微', industry: '芯片', type: '突破年线', pct_chg: 5.23 },
      { ts_code: '300750.SZ', name: '宁德时代', industry: '电池', type: '创新高', pct_chg: 4.87 },
      { ts_code: '002594.SZ', name: '比亚迪', industry: '汽车', type: '突破前高', pct_chg: 3.56 },
      { ts_code: '600036.SH', name: '招商银行', industry: '银行', type: '突破半年线', pct_chg: 2.89 },
    ]
  }
  return api.get('/breakout', { params: { date } })
}

// 顶部放量（高位放量，可能出货）
export const getTopVolume = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '600519.SH', name: '贵州茅台', industry: '白酒', close: 1856.0, pct_chg: -3.21, volume_ratio: 4.5, price_position: 85 },
      { ts_code: '000858.SZ', name: '五粮液', industry: '白酒', close: 156.8, pct_chg: -2.89, volume_ratio: 3.8, price_position: 78 },
      { ts_code: '601318.SH', name: '中国平安', industry: '保险', close: 48.5, pct_chg: -1.56, volume_ratio: 3.2, price_position: 82 },
    ]
  }
  return api.get('/top-volume', { params: { date } })
}

// 跳空高开
export const getGapUp = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '002049.SZ', name: '紫光国微', industry: '芯片', open: 128.5, pre_close: 119.6, gap: 7.44, pct_chg: 5.23 },
      { ts_code: '300750.SZ', name: '宁德时代', industry: '电池', open: 195.0, pre_close: 185.3, gap: 5.23, pct_chg: 4.87 },
      { ts_code: '688012.SH', name: '中微公司', industry: '半导体', open: 165.0, pre_close: 158.6, gap: 4.03, pct_chg: 6.12 },
    ]
  }
  return api.get('/gap-up', { params: { date } })
}

// 跳空低开
export const getGapDown = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { ts_code: '000001.SZ', name: '某地产A', industry: '房地产', open: 8.5, pre_close: 9.2, gap: -7.61, pct_chg: -9.98 },
      { ts_code: '000002.SZ', name: '某地产B', industry: '房地产', open: 12.3, pre_close: 13.1, gap: -6.11, pct_chg: -8.56 },
      { ts_code: '000003.SZ', name: '某教育C', industry: '教育', open: 5.6, pre_close: 5.9, gap: -5.08, pct_chg: -7.23 },
    ]
  }
  return api.get('/gap-down', { params: { date } })
}

// 行业跳空（行业整体跳空）
export const getIndustryGap = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { industry: '半导体', direction: '高开', avg_gap: 3.56, stock_count: 25, top_stock: '中微公司', top_gap: 7.44 },
      { industry: '光伏', direction: '高开', avg_gap: 2.89, stock_count: 18, top_stock: '隆基绿能', top_gap: 5.23 },
      { industry: '房地产', direction: '低开', avg_gap: -4.12, stock_count: 32, top_stock: '万科A', top_gap: -6.78 },
      { industry: '教育', direction: '低开', avg_gap: -3.56, stock_count: 15, top_stock: '新东方', top_gap: -5.89 },
    ]
  }
  return api.get('/industry-gap', { params: { date } })
}

// 复盘记录
export const getReview = async (date) => {
  if (USE_MOCK) { await delay(200); return mockReview }
  return api.get('/review', { params: { date } })
}

// 复盘历史
export const getReviewHistory = async () => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { trade_date: '2024-11-22', preview: '半导体板块爆发...' },
      { trade_date: '2024-11-21', preview: '市场震荡...' },
      { trade_date: '2024-11-20', preview: '新能源反弹...' },
      { trade_date: '2024-11-19', preview: '银行股护盘...' },
      { trade_date: '2024-11-18', preview: '科技股回调...' },
    ]
  }
  return api.get('/review-history')
}

// 保存复盘
export const saveReview = async (date, content) => {
  if (USE_MOCK) {
    await delay(500)
    mockReview.content = content
    return { success: true }
  }
  return api.post('/review', { date, content })
}

// 同步数据
export const syncDaily = async (date) => {
  if (USE_MOCK) { await delay(1000); return { synced: 5000, date } }
  return api.get('/sync-daily', { params: { date } })
}

// 计算指标
export const calcIndicators = async (date) => {
  if (USE_MOCK) { await delay(1500); return { calculated: 5000 } }
  return api.get('/calc-indicators', { params: { date } })
}

// 爬取东方财富数据
export const crawlEastmoney = async (date) => {
  if (USE_MOCK) {
    await delay(2000)
    return {
      date,
      crawl_time: new Date().toISOString(),
      limit_up_down: {
        limit_up_count: 45,
        limit_down_count: 12,
        limit_up: [
          { code: '002049', name: '紫光国微', price: 125.6, pct_chg: 10.0, first_time: '09:32', open_times: 0, continuous: 3, reason: '芯片' },
          { code: '300750', name: '宁德时代', price: 189.3, pct_chg: 10.0, first_time: '09:45', open_times: 1, continuous: 2, reason: '电池' },
          { code: '688012', name: '中微公司', price: 165.0, pct_chg: 10.0, first_time: '09:48', open_times: 0, continuous: 1, reason: '半导体' },
          { code: '002371', name: '北方华创', price: 289.5, pct_chg: 10.0, first_time: '10:05', open_times: 2, continuous: 1, reason: '半导体设备' },
          { code: '300782', name: '卓胜微', price: 98.6, pct_chg: 10.0, first_time: '10:12', open_times: 1, continuous: 2, reason: '芯片' },
          { code: '603259', name: '药明康德', price: 78.5, pct_chg: 10.0, first_time: '10:25', open_times: 0, continuous: 1, reason: 'CXO' },
          { code: '300124', name: '汇川技术', price: 65.8, pct_chg: 10.0, first_time: '10:35', open_times: 0, continuous: 1, reason: '工控' },
          { code: '002594', name: '比亚迪', price: 256.8, pct_chg: 10.0, first_time: '10:45', open_times: 1, continuous: 1, reason: '新能源车' },
          { code: '300059', name: '东方财富', price: 18.9, pct_chg: 10.0, first_time: '11:05', open_times: 0, continuous: 1, reason: '券商' },
          { code: '002475', name: '立讯精密', price: 35.6, pct_chg: 10.0, first_time: '11:15', open_times: 2, continuous: 1, reason: '消费电子' },
          { code: '300496', name: '中科创达', price: 89.5, pct_chg: 10.0, first_time: '13:05', open_times: 0, continuous: 1, reason: '软件' },
          { code: '002415', name: '海康威视', price: 32.5, pct_chg: 10.0, first_time: '13:25', open_times: 1, continuous: 1, reason: '安防' },
          { code: '300033', name: '同花顺', price: 125.8, pct_chg: 10.0, first_time: '13:35', open_times: 0, continuous: 2, reason: '金融IT' },
          { code: '688981', name: '中芯国际', price: 48.9, pct_chg: 10.0, first_time: '13:45', open_times: 0, continuous: 1, reason: '晶圆代工' },
          { code: '002230', name: '科大讯飞', price: 52.3, pct_chg: 10.0, first_time: '14:05', open_times: 1, continuous: 1, reason: 'AI' },
        ],
        limit_down: [
          { code: '000002', name: '万科A', price: 8.5, pct_chg: -10.0 },
          { code: '001979', name: '招商蛇口', price: 12.3, pct_chg: -10.0 },
          { code: '600048', name: '保利发展', price: 9.8, pct_chg: -10.0 },
          { code: '000069', name: '华侨城A', price: 5.6, pct_chg: -10.0 },
          { code: '600383', name: '金地集团', price: 6.2, pct_chg: -10.0 },
        ],
      },
      sector_flow: [
        { name: '半导体', pct_chg: 5.23, main_net: 28.5, main_pct: 15.2 },
        { name: '光伏', pct_chg: 3.89, main_net: 18.3, main_pct: 12.1 },
        { name: '新能源车', pct_chg: 2.56, main_net: 12.8, main_pct: 8.5 },
        { name: '锂电池', pct_chg: 2.35, main_net: 10.5, main_pct: 7.8 },
        { name: '军工', pct_chg: 1.89, main_net: 8.6, main_pct: 6.5 },
        { name: '医药', pct_chg: 1.56, main_net: 6.8, main_pct: 5.2 },
        { name: '白酒', pct_chg: 1.23, main_net: 5.2, main_pct: 4.1 },
        { name: '券商', pct_chg: 0.89, main_net: 3.5, main_pct: 3.2 },
        { name: '银行', pct_chg: 0.56, main_net: 2.1, main_pct: 2.5 },
        { name: '保险', pct_chg: 0.35, main_net: 1.2, main_pct: 1.8 },
        { name: '房地产', pct_chg: -3.56, main_net: -15.6, main_pct: -8.5 },
        { name: '教育', pct_chg: -2.89, main_net: -8.5, main_pct: -6.2 },
      ],
      north_flow: {
        hk_to_sh: 35.6,
        hk_to_sz: 28.9,
        total: 64.5,
        top_holdings: [
          { code: '600519', name: '贵州茅台', hold_market_cap: 1856.5, hold_ratio: 8.5 },
          { code: '000858', name: '五粮液', hold_market_cap: 856.3, hold_ratio: 6.2 },
          { code: '601318', name: '中国平安', hold_market_cap: 625.8, hold_ratio: 5.8 },
          { code: '000333', name: '美的集团', hold_market_cap: 456.2, hold_ratio: 4.5 },
          { code: '600036', name: '招商银行', hold_market_cap: 398.5, hold_ratio: 4.2 },
          { code: '000651', name: '格力电器', hold_market_cap: 356.8, hold_ratio: 3.8 },
          { code: '002415', name: '海康威视', hold_market_cap: 298.5, hold_ratio: 3.5 },
          { code: '600276', name: '恒瑞医药', hold_market_cap: 256.3, hold_ratio: 3.2 },
          { code: '000568', name: '泸州老窖', hold_market_cap: 198.6, hold_ratio: 2.8 },
          { code: '002304', name: '洋河股份', hold_market_cap: 165.8, hold_ratio: 2.5 },
        ],
      },
      dragon_tiger: [
        { code: '002049', name: '紫光国微', pct_chg: 10.0, reason: '涨幅偏离7%', buy_amount: 15623, sell_amount: 8956 },
        { code: '300750', name: '宁德时代', pct_chg: 8.5, reason: '换手率20%', buy_amount: 28456, sell_amount: 12345 },
        { code: '002594', name: '比亚迪', pct_chg: 10.0, reason: '涨幅偏离7%', buy_amount: 18765, sell_amount: 9876 },
        { code: '600519', name: '贵州茅台', pct_chg: 5.2, reason: '机构专用', buy_amount: 45678, sell_amount: 23456 },
        { code: '688012', name: '中微公司', pct_chg: 10.0, reason: '涨幅偏离7%', buy_amount: 12356, sell_amount: 6589 },
        { code: '002371', name: '北方华创', pct_chg: 10.0, reason: '涨幅偏离7%', buy_amount: 9865, sell_amount: 5236 },
        { code: '300782', name: '卓胜微', pct_chg: 10.0, reason: '换手率20%', buy_amount: 8956, sell_amount: 4563 },
        { code: '000002', name: '万科A', pct_chg: -10.0, reason: '跌幅偏离7%', buy_amount: 5236, sell_amount: 18956 },
      ],
      market_emotion: {
        up_count: 3256,
        down_count: 1523,
        flat_count: 221,
        up_ratio: 68.1,
        emotion_level: '贪婪',
      },
      hot_stocks: [
        { code: '002049', name: '紫光国微', rank: 1, rank_change: 5 },
        { code: '300750', name: '宁德时代', rank: 2, rank_change: -1 },
        { code: '002594', name: '比亚迪', rank: 3, rank_change: 2 },
        { code: '600519', name: '贵州茅台', rank: 4, rank_change: 0 },
        { code: '688012', name: '中微公司', rank: 5, rank_change: 8 },
        { code: '002371', name: '北方华创', rank: 6, rank_change: 3 },
        { code: '300782', name: '卓胜微', rank: 7, rank_change: -2 },
        { code: '603259', name: '药明康德', rank: 8, rank_change: 1 },
        { code: '300124', name: '汇川技术', rank: 9, rank_change: 4 },
        { code: '300059', name: '东方财富', rank: 10, rank_change: -3 },
        { code: '002475', name: '立讯精密', rank: 11, rank_change: 2 },
        { code: '300496', name: '中科创达', rank: 12, rank_change: 6 },
        { code: '002415', name: '海康威视', rank: 13, rank_change: -1 },
        { code: '300033', name: '同花顺', rank: 14, rank_change: 5 },
        { code: '688981', name: '中芯国际', rank: 15, rank_change: 3 },
        { code: '002230', name: '科大讯飞', rank: 16, rank_change: 7 },
        { code: '000858', name: '五粮液', rank: 17, rank_change: -4 },
        { code: '601318', name: '中国平安', rank: 18, rank_change: 0 },
        { code: '000333', name: '美的集团', rank: 19, rank_change: 2 },
        { code: '600036', name: '招商银行', rank: 20, rank_change: -2 },
      ],
    }
  }
  return api.get('/crawl-eastmoney', { params: { date } })
}

// 获取东方财富数据
export const getEastmoneyData = async (date) => {
  if (USE_MOCK) {
    await delay(200)
    return null // 模拟未爬取
  }
  return api.get('/eastmoney-data', { params: { date } })
}

// 东方财富数据列表
export const getEastmoneyList = async () => {
  if (USE_MOCK) {
    await delay(200)
    return [
      { date: '20241122', time: '2024-11-22 18:30:00' },
      { date: '20241121', time: '2024-11-21 18:25:00' },
    ]
  }
  return api.get('/eastmoney-list')
}

// 爬取Tushare数据
export const crawlTushare = async (date) => {
  return api.get('/crawl-tushare', { params: { date } })
}

// 获取Tushare数据
export const getTushareData = async (date) => {
  return api.get('/tushare-data', { params: { date } })
}

// ==================== 缠论API ====================

// 底背驰
export const getChanBottomDiverge = async (date) => {
  return api.get('/chan-bottom-diverge', { params: { date } })
}

// 顶背驰
export const getChanTopDiverge = async (date) => {
  return api.get('/chan-top-diverge', { params: { date } })
}

// 一买信号
export const getChanFirstBuy = async (date) => {
  return api.get('/chan-first-buy', { params: { date } })
}

// 二买信号
export const getChanSecondBuy = async (date) => {
  return api.get('/chan-second-buy', { params: { date } })
}

// 三买信号
export const getChanThirdBuy = async (date) => {
  return api.get('/chan-third-buy', { params: { date } })
}

// 中枢震荡
export const getChanHubShake = async (date) => {
  return api.get('/chan-hub-shake', { params: { date } })
}

// 获取单只股票缠论数据
export const getChanData = async (tsCode) => {
  return api.get('/chan-data', { params: { ts_code: tsCode } })
}

// 计算缠论指标
export const calcChan = async (date) => {
  return api.get('/calc-chan', { params: { date } })
}

// 趋势分析
export const getTrendAnalysis = async (tsCode) => {
  return api.get('/trend/analyze', { params: { ts_code: tsCode } })
}

// 多周期分析
export const getMultiPeriodAnalysis = async (tsCode) => {
  return api.get('/trend/multi-period-analysis', { params: { ts_code: tsCode } })
}

// 全市场扫描
export const scanMarket = async (date) => {
  return api.get('/trend-scan', { params: { date } })
}

// ==================== v2.5 策略分析 API ====================

/**
 * 完整策略分析（一站式决策）
 * @param {Object} emotionData - 市场情绪数据
 * @param {Object} marketData - 市场数据
 * @param {Array} holdings - 持仓列表（可选）
 * @returns {Promise} 完整分析结果
 */
export const getFullAnalysis = async (emotionData, marketData, holdings = []) => {
  return api.post('/strategy/full-analysis', {
    emotion_data: emotionData,
    market_data: marketData,
    holdings: holdings
  })
}

/**
 * 分析单只持仓反馈信号
 * @param {Object} holding - 持仓信息
 * @param {Object} market - 市场数据
 * @returns {Promise} 反馈分析结果
 */
export const analyzeHoldingFeedback = async (holding, market) => {
  return api.post('/strategy/feedback/analyze-holding', {
    holding,
    market
  })
}

/**
 * 批量分析所有持仓反馈信号
 * @param {Array} holdings - 持仓列表
 * @param {Object} market - 市场数据
 * @returns {Promise} 批量反馈分析结果
 */
export const batchAnalyzeHoldings = async (holdings, market) => {
  return api.post('/strategy/feedback/batch-analyze', {
    holdings,
    market
  })
}

/**
 * 获取市场情绪周期
 * @param {Object} emotionData - 情绪数据
 * @returns {Promise} 情绪周期分析
 */
export const getEmotionCycle = async (emotionData) => {
  return api.post('/strategy/emotion-phase', emotionData)
}

/**
 * 检测市场共振信号
 * @param {Object} resonanceInput - 共振检测输入
 * @returns {Promise} 共振检测结果
 */
export const detectResonance = async (resonanceInput) => {
  return api.post('/strategy/resonance-detect', resonanceInput)
}

/**
 * 生成买卖信号
 * @param {Object} marketData - 市场数据
 * @returns {Promise} 信号生成结果
 */
export const generateSignals = async (marketData) => {
  return api.post('/strategy/generate-signals', marketData)
}

/**
 * 计算仓位建议
 * @param {Object} positionInput - 仓位输入数据
 * @returns {Promise} 仓位建议
 */
export const getPositionAdvice = async (positionInput) => {
  return api.post('/strategy/position-advice', positionInput)
}

// ==================== 开盘啦 API (App版) ====================

/**
 * 获取实时市场情绪数据 (开盘啦App API)
 * @param {String} date - 日期 YYYY-MM-DD，默认最近交易日
 * @returns {Promise} 完整情绪数据，包括综合强度、涨跌分布、连板数据等
 */
export const getRealtimeEmotion = async (date) => {
  return api.get('/emotion/realtime', { params: { date } })
}

/**
 * 获取涨停股列表 (开盘啦App API)
 * @param {String} date - 日期 YYYY-MM-DD
 * @returns {Promise} 涨停股列表
 */
export const getEmotionLimitUpList = async (date) => {
  return api.get('/emotion/limit-up-list', { params: { date } })
}

/**
 * 获取情绪历史数据
 * @param {Number} days - 获取最近N天数据
 * @returns {Promise} 历史情绪数据
 */
export const getEmotionHistory = async (days = 7) => {
  return api.get('/emotion/history', { params: { days } })
}

/**
 * 获取最新情绪数据
 * @returns {Promise} 最新情绪数据
 */
export const getLatestEmotion = async () => {
  return api.get('/emotion/latest')
}

// ==================== 开盘啦 API (网页版 - 保留兼容) ====================

/**
 * 获取开盘啦涨停股列表
 * @param {String} date - 交易日期 YYYYMMDD
 * @returns {Promise} 涨停股数据
 */
export const getKaipanlaLimitUp = async (date) => {
  return api.get('/kaipanla/limit-up', { params: { date } })
}

/**
 * 获取开盘啦炸板股列表
 * @param {String} date - 交易日期 YYYYMMDD
 * @returns {Promise} 炸板股数据
 */
export const getKaipanlaBrokenBoard = async (date) => {
  return api.get('/kaipanla/broken-board', { params: { date } })
}

/**
 * 获取连板梯队
 * @param {String} date - 交易日期 YYYYMMDD
 * @returns {Promise} 连板梯队数据
 */
export const getKaipanlaContinuousLadder = async (date) => {
  return api.get('/kaipanla/continuous-ladder', { params: { date } })
}

/**
 * 获取开盘啦跌停股列表
 * @param {String} date - 交易日期 YYYYMMDD
 * @returns {Promise} 跌停股数据
 */
export const getKaipanlaLimitDown = async (date) => {
  return api.get('/kaipanla/limit-down', { params: { date } })
}

/**
 * 获取昨日涨停今日表现
 * @param {String} date - 交易日期 YYYYMMDD
 * @returns {Promise} 昨日涨停表现数据
 */
export const getKaipanlaYesterdayPerformance = async (date) => {
  return api.get('/kaipanla/yesterday-performance', { params: { date } })
}

/**
 * 获取开盘啦完整情绪数据（一站式）
 * @param {String} date - 交易日期 YYYYMMDD
 * @returns {Promise} 完整情绪数据
 */
export const getKaipanlaFullEmotion = async (date) => {
  return api.get('/kaipanla/full-emotion', { params: { date } })
}
