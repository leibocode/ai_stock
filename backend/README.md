# Stock Review Backend (ThinkPHP 6)

## 安装

```bash
cd backend
composer install
```

## 配置

1. 复制 `.env` 文件并配置数据库和Tushare Token
2. 导入数据库结构 `database/schema.sql`

## 运行

```bash
# 开发环境
php think run

# 或使用内置服务器
php -S localhost:8000 -t public
```

## API接口

- `GET /api/volume-top` - 成交量TOP50
- `GET /api/oversold` - RSI超卖
- `GET /api/kdj-bottom` - KDJ见底
- `GET /api/macd-golden` - MACD金叉
- `GET /api/bottom-volume` - 底部放量
- `GET /api/top-volume` - 顶部放量
- `GET /api/gap-up` - 跳空高开
- `GET /api/gap-down` - 跳空低开
- `GET /api/industry-gap` - 行业跳空
- `GET /api/industry-hot` - 行业异动
- `GET /api/market-index` - 大盘指数
- `GET /api/counter-trend` - 逆势上涨
- `GET /api/market-stats` - 市场统计
- `GET /api/limit-up` - 涨停列表
- `GET /api/limit-down` - 跌停列表
- `GET /api/dragon-tiger` - 龙虎榜
- `GET /api/north-buy` - 北向资金
- `GET /api/margin-buy` - 融资买入
- `GET /api/breakout` - 突破形态
- `GET /api/review` - 获取复盘
- `POST /api/review` - 保存复盘
- `GET /api/review-history` - 复盘历史
- `GET /api/sync-daily` - 同步日线
- `GET /api/calc-indicators` - 计算指标
