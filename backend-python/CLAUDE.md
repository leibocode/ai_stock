# AI Stock Backend - 开发指南

## 项目信息

- **名称**: AI Stock - 股票复盘系统 (Python FastAPI 版本)
- **框架**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0 + aiomysql
- **数据库**: MySQL 8.0

## 快速开始

```bash
# 环境配置
cp .env.example .env
# 编辑 .env，填入数据库和 Tushare Token

# 安装依赖
pip install -r requirements.txt

# 运行
python -m uvicorn app.main:app --reload
```

## 核心模块

### 1. 配置层 (`app/config/`)
- `settings.py` - pydantic-settings 配置管理
- `database.py` - SQLAlchemy 异步连接

### 2. 数据模型 (`app/models/`)
复用原有数据库表结构:
- `stock.py` - 股票基础信息
- `daily_quote.py` - 日线行情
- `technical_indicator.py` - 技术指标
- `review_record.py` - 复盘记录
- `chan.py` - 缠论表 (ChanFractal/Bi/Segment/Hub)

### 3. 业务服务层 (`app/services/`)

#### TushareService (`tushare_service.py`)
Tushare API 包装，提供:
- `get_stock_list()` - 股票列表 (排除ST和科创板)
- `get_daily()` - 日线数据
- `get_limit_list()` - 涨跌停
- `get_money_flow()` - 北向资金
- `get_top_list()` - 龙虎榜
- `sync_stocks()` - 批量同步到数据库

#### IndicatorService (`indicator_service.py`)
技术指标计算，支持:
- RSI (6, 12周期)
- MACD (12, 26, 9)
- KDJ (9周期)
- 布林带 (20周期)

**关键方法**:
- `calculate_indicators()` - 计算单只股票指标
- `calc_all()` - 批量计算所有股票
- `get_oversold_stocks()` - 获取RSI<30的股票
- `get_kdj_bottom_stocks()` - 获取KDJ底部股票
- `get_macd_golden_stocks()` - 获取MACD金叉股票

#### Crawler 爬虫服务 (`services/crawler/`)
拆分为8个模块:

| 模块 | 职责 |
|------|------|
| `base.py` | HTTP 基类 |
| `limit_up.py` | 涨跌停数据（同花顺）|
| `sector_flow.py` | 板块资金流向 |
| `north_flow.py` | 北向资金 |
| `dragon_tiger.py` | 龙虎榜 |
| `emotion_cycle.py` | 情绪周期计算（核心） |
| `leader_score.py` | 龙头评分算法 |
| `multi_factor.py` | 多因子评分 |

**EmotionCycleCalculator 核心算法**:
- 满分100分，评分规则详见源码
- 5个阶段: 冰点→修复→回暖→高潮→退潮
- 返回 EmotionCycleResult(phase, score, strategy)

**LeaderScoreCalculator**:
- 综合评分 >=50 判定为龙头
- 考虑因素: 连板数、封板时间、开板次数、成交额、换手率、市值

### 4. 核心算法 (`app/core/`)

#### 技术指标 (`core/indicators/`)
- `rsi.py` - RSI 计算
- `macd.py` - MACD 和 EMA
- `kdj.py` - KDJ 指标
- `boll.py` - 布林带

#### 缠论 (`core/chan/`)
- 待完整实现: 分型、笔、线段、中枢

### 5. API 层 (`app/api/v1/`)

按功能分模块:
- `market.py` - 行情数据 (9个)
- `limit.py` - 涨跌停 (2个)
- `fund_flow.py` - 资金流向 (3个)
- `pattern.py` - 技术形态 (5个)
- `review.py` - 复盘管理 (3个)
- `sync.py` - 数据同步 (4个)
- `crawler.py` - 爬虫数据 (3个)
- `chan.py` - 缠论 (8个)
- `router.py` - 路由聚合

## API 响应格式

所有 API 统一响应:
```json
{
  "code": 0,
  "data": {...},
  "msg": "success"
}
```

使用 `success(data)` 和 `error(msg)` 辅助函数

## 数据流向

1. **同步数据**: Tushare → MySQL
   ```
   TushareService.sync_stocks() → stocks 表
   TushareService.get_daily() → daily_quotes 表
   ```

2. **计算指标**: 历史数据 → 技术指标
   ```
   IndicatorService.calc_all() → 逐个股票计算
   → technical_indicators 表
   ```

3. **爬虫数据**: 东财/同花顺 → JSON 缓存/数据库
   ```
   各爬虫模块 → 文件缓存或数据库
   EmotionCycleCalculator → 情绪周期结果
   LeaderScoreCalculator → 龙头评分结果
   ```

## 开发规范

### 1. 添加新 API
1. 在 `app/api/v1/` 中的对应模块添加路由
2. 依赖注入数据库: `db: AsyncSession = Depends(get_db)`
3. 返回统一格式: `success(data)` 或 `error(msg)`

```python
@router.get("/your-endpoint")
async def your_endpoint(date: str = Query(None), db: AsyncSession = Depends(get_db)):
    service = YourService(db)
    data = await service.some_method()
    return success(data)
```

### 2. 添加新爬虫
1. 在 `app/services/crawler/` 创建新文件
2. 继承 `BaseCrawler` (异步 HTTP 客户端)
3. 实现爬虫方法

```python
class NewCrawler(BaseCrawler):
    async def crawl(self, date: str):
        data = await self.get(url, params)
        return self._parse_data(data)
```

### 3. 数据库操作
使用 SQLAlchemy ORM:
```python
# 查询
stmt = select(Stock).where(Stock.ts_code == "000001.SZ")
result = await db.execute(stmt)
stock = result.scalar_one_or_none()

# 插入/更新
db.add(new_stock)
await db.commit()
```

## 常见任务

### 补全 API 接口
大部分 API 只有框架，需要实现核心逻辑。关键接口:
- `/api/volume-top` - 需要查询 daily_quotes 按成交额排序
- `/api/bottom-volume` - 需要量比>3 且 price_position<30%
- `/api/breakout` - 需要技术形态识别
- `/api/crawl-eastmoney` - 需要调用各爬虫模块

### 缠论算法完整实现
`core/chan/` 目录需要实现:
1. K线包含处理
2. 分型识别 (顶/底)
3. 笔划分
4. 线段划分
5. 中枢识别

参考原 PHP 代码: `backend/app/service/IndicatorService.php` (426-961行)

### 集成缓存和定时任务
1. Redis 缓存热点数据 (涨停、情绪周期等)
2. APScheduler 配置:
   - 15:30 同步日线数据
   - 16:00 计算指标
   - 交易时间每5分钟爬取实时数据

## 性能注意事项

- **数据库**: 连接池配置在 `database.py` (pool_size=10, max_overflow=20)
- **异步**: 所有 IO 操作都是异步，充分利用 asyncio
- **爬虫延迟**: 设置合理的延迟避免被封IP
- **缓存策略**: 使用 Redis 缓存不经常变化的数据

## 测试

待实现:
- `tests/test_services/` - 服务层测试
- `tests/test_api/` - API 接口测试
- `tests/test_core/` - 核心算法测试

运行测试:
```bash
pytest tests/ -v
```

## 部署

### Docker
```bash
docker-compose up -d
```

### 生产环境
```bash
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

## 常见问题

1. **Tushare API 超时**
   - 检查 TOKEN 是否正确
   - 增加超时时间: `TushareService.timeout = 60`

2. **数据库连接失败**
   - 检查 DATABASE_URL 格式和数据库是否启动
   - 确保表结构已初始化: `database/schema.sql`

3. **爬虫被封IP**
   - 添加随机延迟
   - 轮换 User-Agent
   - 使用代理池

## 关键文件路径

- 配置: `app/config/settings.py`
- 数据库: `app/config/database.py`
- 主入口: `app/main.py`
- API 路由: `app/api/v1/router.py`
- 环境变量: `.env`
- 依赖: `requirements.txt`

## 下一步

- [ ] 补全所有 37 个 API 接口
- [ ] 实现完整的爬虫和数据处理
- [ ] 集成 Redis 缓存
- [ ] 配置 APScheduler 定时任务
- [ ] 编写单元测试
- [ ] Docker 生产部署
- [ ] 性能优化和监控
