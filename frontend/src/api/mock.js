// Mock数据

export const mockVolumeTop = [
  { ts_code: '000001.SZ', name: '平安银行', industry: '银行', vol: 1234567, amount: 98765432, pct_chg: 2.35 },
  { ts_code: '000002.SZ', name: '万科A', industry: '房地产', vol: 987654, amount: 76543210, pct_chg: -1.23 },
  { ts_code: '600519.SH', name: '贵州茅台', industry: '白酒', vol: 876543, amount: 65432109, pct_chg: 1.56 },
  { ts_code: '000858.SZ', name: '五粮液', industry: '白酒', vol: 765432, amount: 54321098, pct_chg: 3.21 },
  { ts_code: '601318.SH', name: '中国平安', industry: '保险', vol: 654321, amount: 43210987, pct_chg: -0.89 },
  { ts_code: '000333.SZ', name: '美的集团', industry: '家电', vol: 543210, amount: 32109876, pct_chg: 2.11 },
  { ts_code: '002415.SZ', name: '海康威视', industry: '安防', vol: 432109, amount: 21098765, pct_chg: 4.56 },
  { ts_code: '600036.SH', name: '招商银行', industry: '银行', vol: 321098, amount: 10987654, pct_chg: 1.89 },
]

export const mockOversold = [
  { ts_code: '002230.SZ', name: '科大讯飞', industry: 'AI', rsi_6: 18.5, rsi_12: 22.3, k: 15.2, d: 18.6 },
  { ts_code: '300750.SZ', name: '宁德时代', industry: '电池', rsi_6: 21.3, rsi_12: 25.6, k: 19.8, d: 22.1 },
  { ts_code: '002594.SZ', name: '比亚迪', industry: '汽车', rsi_6: 24.8, rsi_12: 28.9, k: 21.5, d: 25.3 },
  { ts_code: '300059.SZ', name: '东方财富', industry: '券商', rsi_6: 26.1, rsi_12: 30.2, k: 23.4, d: 27.8 },
  { ts_code: '002475.SZ', name: '立讯精密', industry: '电子', rsi_6: 28.5, rsi_12: 32.1, k: 25.6, d: 29.4 },
]

export const mockKdjBottom = [
  { ts_code: '600900.SH', name: '长江电力', industry: '电力', k: 12.5, d: 15.3, j: 6.9 },
  { ts_code: '601899.SH', name: '紫金矿业', industry: '有色', k: 14.2, d: 17.8, j: 7.0 },
  { ts_code: '601857.SH', name: '中国石油', industry: '石油', k: 16.8, d: 19.2, j: 12.0 },
  { ts_code: '600028.SH', name: '中国石化', industry: '石油', k: 18.1, d: 19.5, j: 15.3 },
]

export const mockMacdGolden = [
  { ts_code: '002714.SZ', name: '牧原股份', industry: '养殖', macd: 0.12, macd_signal: 0.10, macd_hist: 0.02 },
  { ts_code: '300274.SZ', name: '阳光电源', industry: '光伏', macd: 0.15, macd_signal: 0.12, macd_hist: 0.03 },
  { ts_code: '002466.SZ', name: '天齐锂业', industry: '锂电', macd: 0.18, macd_signal: 0.14, macd_hist: 0.04 },
  { ts_code: '300124.SZ', name: '汇川技术', industry: '工控', macd: 0.21, macd_signal: 0.16, macd_hist: 0.05 },
]

export const mockBottomVolume = [
  { ts_code: '002049.SZ', name: '紫光国微', industry: '芯片', close: 125.6, pct_chg: 5.23, volume_ratio: 4.5, price_position: 18.5, rsi_6: 35.2 },
  { ts_code: '300782.SZ', name: '卓胜微', industry: '芯片', close: 89.3, pct_chg: 4.87, volume_ratio: 3.8, price_position: 22.1, rsi_6: 38.6 },
  { ts_code: '688012.SH', name: '中微公司', industry: '半导体', close: 156.8, pct_chg: 6.12, volume_ratio: 5.2, price_position: 15.3, rsi_6: 42.1 },
  { ts_code: '002371.SZ', name: '北方华创', industry: '半导体', close: 234.5, pct_chg: 3.56, volume_ratio: 3.2, price_position: 28.6, rsi_6: 45.8 },
]

export const mockIndustryHot = [
  { industry: '半导体', stock_count: 15, avg_pct_chg: 5.67, top_stock: '中微公司', top_pct: 9.98 },
  { industry: '光伏', stock_count: 12, avg_pct_chg: 4.89, top_stock: '隆基绿能', top_pct: 8.56 },
  { industry: '锂电池', stock_count: 10, avg_pct_chg: 4.23, top_stock: '宁德时代', top_pct: 7.89 },
  { industry: '汽车', stock_count: 8, avg_pct_chg: 3.78, top_stock: '比亚迪', top_pct: 6.54 },
  { industry: 'AI', stock_count: 6, avg_pct_chg: 3.45, top_stock: '科大讯飞', top_pct: 5.67 },
]

export const mockReview = {
  content: '今日市场情绪回暖，半导体板块集体爆发，资金明显流入科技股。\n\n关注点：\n1. 中微公司底部放量，量比超5倍\n2. 芯片行业整体上涨，板块效应明显\n3. RSI超卖股票开始反弹\n\n明日策略：继续关注科技板块轮动机会。'
}
