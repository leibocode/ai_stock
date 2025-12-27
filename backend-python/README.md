# AI Stock Backend - Python/FastAPI

基于情绪周期理论的A股复盘分析系统后端（Python FastAPI版本）

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填入你的配置
# DATABASE_URL=mysql+aiomysql://user:password@localhost/ai_stock
# TUSHARE_TOKEN=your_token_here
```

### 3. 运行

```bash
# 开发模式
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

## 项目结构

```
backend-python/
├── app/
│   ├── main.py                # FastAPI 应用入口
│   ├── config/                # 配置管理
│   ├── models/                # SQLAlchemy 模型
│   ├── schemas/               # Pydantic 数据模型
│   ├── api/v1/                # API 路由层
│   ├── services/              # 业务逻辑层
│   │   ├── tushare_service.py # Tushare API 封装
│   │   ├── indicator_service.py # 技术指标
│   │   └── crawler/           # 爬虫服务
│   ├── core/                  # 核心算法
│   │   ├── indicators/        # RSI, MACD, KDJ, BOLL
│   │   └── chan/              # 缠论算法
│   └── utils/                 # 工具函数
├── requirements.txt           # 依赖
├── .env                       # 环境变量
└── README.md
```

## API 概览

### 行情数据 (9个)
- `GET /api/volume-top` - 成交量TOP50
- `GET /api/oversold` - RSI超卖
- `GET /api/kdj-bottom` - KDJ底部
- `GET /api/macd-golden` - MACD金叉
- `GET /api/bottom-volume` - 底部放量
- `GET /api/top-volume` - 顶部放量
- `GET /api/counter-trend` - 逆势上涨
- `GET /api/market-index` - 大盘指数
- `GET /api/market-stats` - 市场统计

### 涨跌停 (2个)
- `GET /api/limit-up` - 涨停列表
- `GET /api/limit-down` - 跌停列表

### 资金流向 (3个)
- `GET /api/dragon-tiger` - 龙虎榜
- `GET /api/north-buy` - 北向资金
- `GET /api/margin-buy` - 融资买入

### 技术形态 (5个)
- `GET /api/breakout` - 突破形态
- `GET /api/top-volume` - 顶部放量
- `GET /api/gap-up` - 跳空高开
- `GET /api/gap-down` - 跳空低开
- `GET /api/industry-gap` - 行业跳空

### 复盘 (3个)
- `GET /api/review` - 获取复盘记录
- `POST /api/review` - 保存复盘记录
- `GET /api/review-history` - 复盘历史

### 同步 (4个)
- `GET /api/sync-stocks` - 同步股票列表
- `GET /api/sync-daily` - 同步日线行情
- `GET /api/calc-indicators` - 计算指标
- `GET /api/crawl-eastmoney` - 爬取东财数据

### 爬虫 (3个)
- `GET /api/eastmoney-data` - 获取东财缓存
- `GET /api/eastmoney-list` - 东财历史列表

### 缠论 (8个)
- `GET /api/chan-bottom-diverge` - 底背驰
- `GET /api/chan-top-diverge` - 顶背驰
- `GET /api/chan-first-buy` - 一买信号
- `GET /api/chan-second-buy` - 二买信号
- `GET /api/chan-third-buy` - 三买信号
- `GET /api/chan-hub-shake` - 中枢震荡
- `GET /api/chan-data` - 缠论数据
- `GET /api/calc-chan` - 计算缠论

## 核心服务

### TushareService
Tushare API 封装，提供：
- 股票基本信息
- 日线行情数据
- 涨跌停信息
- 北向资金
- 龙虎榜数据

### IndicatorService
技术指标计算，支持：
- RSI (6, 12周期)
- MACD (12, 26, 9)
- KDJ (9周期)
- 布林带 (20周期)

### Crawler 服务
爬虫模块，拆分为：
- `limit_up.py` - 涨跌停数据
- `sector_flow.py` - 板块资金流向
- `north_flow.py` - 北向资金
- `dragon_tiger.py` - 龙虎榜
- `emotion_cycle.py` - 情绪周期计算
- `leader_score.py` - 龙头评分
- `multi_factor.py` - 多因子评分

## 数据库表

- `stocks` - 股票基础信息
- `daily_quotes` - 日线行情
- `technical_indicators` - 技术指标
- `review_records` - 复盘记录
- `chan_fractal` - 缠论分型
- `chan_bi` - 缠论笔
- `chan_segment` - 缠论线段
- `chan_hub` - 缠论中枢

## 开发指南

### 添加新的API接口

1. 在 `app/api/v1/` 中创建或编辑对应模块
2. 定义路由处理函数
3. 在 `router.py` 中注册路由
4. 测试接口

```python
@router.get("/your-endpoint")
async def your_endpoint(db: AsyncSession = Depends(get_db)):
    return success(data)
```

### 添加新的爬虫

1. 在 `app/services/crawler/` 中创建新模块
2. 继承 `BaseCrawler` 类
3. 实现爬虫逻辑
4. 在相应的API中调用

## 响应格式

所有 API 响应遵循统一格式：

```json
{
  "code": 0,
  "data": {...},
  "msg": "success"
}
```

- `code=0`: 成功
- `code!=0`: 失败
- `data`: 具体数据
- `msg`: 错误消息（仅当失败时）

## 性能优化建议

1. 添加 Redis 缓存热点数据
2. 使用 APScheduler 配置定时任务
3. 实现异步并发爬虫
4. 数据库连接池配置
5. 请求超时设置

## 注意事项

- Tushare API 有额度限制，注意调用频率
- 爬虫需要设置合理的延迟和 User-Agent
- 数据库需要提前初始化表结构
- 环境变量必须正确配置

## 后续工作

- [ ] 完整实现所有37个API接口
- [ ] 东财爬虫完整实现
- [ ] 缠论算法完整实现
- [ ] Redis 缓存集成
- [ ] APScheduler 定时任务
- [ ] 单元测试和集成测试
- [ ] Docker 部署
- [ ] 性能优化

## License

MIT
