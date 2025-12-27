# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**AI Stock** - 基于情绪周期理论的A股量化交易系统（Python FastAPI版本）

- 核心目标：日线复盘分析 + 缠论走势识别 + 情绪周期判断 + 策略回测
- 技术栈：FastAPI + SQLAlchemy 2.0 + numpy/pandas + APScheduler
- 数据源：Tushare（免费版）+ Akshare + 东财爬虫
- 数据库：支持 SQLite（开发）/ MySQL 8.0（生产）

## 快速启动

```bash
# 环境准备
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env.example .env
# 编辑 .env：DATABASE_URL、TUSHARE_TOKEN、REDIS_URL

# 初始化数据库（SQLite自动创建，MySQL需手动执行schema.sql）
python -c "from app.config.database import init_db; init_db()"

# 启动服务
python -m uvicorn app.main:app --reload

# 或使用完整命令
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --reload
```

## 核心架构

### 分层设计

```
app/
├── config/           # 配置层
│   ├── settings.py  # Pydantic-settings，支持 .env 文件
│   └── database.py  # SQLAlchemy 异步连接（支持SQLite/MySQL切换）
├── models/          # 数据模型（ORM）
│   ├── stock.py     # 股票基础信息
│   ├── daily_quote.py # 日线行情
│   ├── technical_indicator.py # 技术指标
│   ├── review_record.py # 复盘记录
│   └── chan.py      # 缠论表（分型/笔/线段/中枢）
├── core/            # 核心算法层
│   ├── indicators/  # 技术指标计算（RSI/MACD/KDJ/BOLL）
│   ├── chan/        # 缠论分析（分型识别→笔→线段→中枢）
│   └── scheduler.py # APScheduler 定时任务配置
├── services/        # 业务服务层
│   ├── tushare_service.py # Tushare API 包装
│   ├── indicator_service.py # 指标计算服务
│   ├── cache_service.py # Redis 缓存服务
│   ├── chan_service.py # 缠论分析服务
│   └── crawler/      # 爬虫模块（东财/同花顺）
│       ├── limit_up.py # 涨跌停（同花顺）
│       ├── sector_flow.py # 板块资金
│       ├── emotion_cycle.py # 情绪周期算法★
│       ├── leader_score.py # 龙头评分★
│       └── multi_factor.py # 多因子评分★
├── api/v1/          # API 路由层（按功能分模块）
│   ├── market.py    # 行情数据API
│   ├── limit.py     # 涨跌停API
│   ├── fund_flow.py # 资金流向API
│   ├── chan.py      # 缠论API
│   └── router.py    # 路由聚合（入口）
└── main.py          # FastAPI 应用入口

tests/               # 测试目录
```

### 关键模块说明

#### 1. 缠论分析 (`core/chan/`)

**核心概念**：分型 → 笔 → 线段 → 中枢 → 买卖点

- `fractal.py` - 分型识别（顶分型：高-低-高，底分型：低-高-低）
- `bi.py` - 笔划分（连接相邻顶底分型）
- `segment.py` - 线段识别（至少5笔的序列）
- `hub.py` - 中枢识别（3个线段的重叠区间）
- `chan_service.py` - 一站式缠论分析（ChanService/ChanAnalyzer）

**关键算法**：

```python
# 完整缠论分析流程
analyzer = ChanAnalyzer(df)
fractals = analyzer.identify_fractals()      # 分型
bis = analyzer.identify_bis(fractals)        # 笔
segments = analyzer.identify_segments(bis)   # 线段
hubs = analyzer.identify_hubs(segments)      # 中枢
buy_points = analyzer.identify_buy_points()  # 一二三买
```

#### 2. 情绪周期分析 (`services/crawler/emotion_cycle.py`)

**5阶段循环**：高潮期 → 退潮期 → 冰点期 → 回暖期 → 修复期

**判断指标**（总分100）：
- 涨停数（40%）：>80=高潮，50-79=回暖/修复，<20=冰点
- 连板高度（20%）：最高连板数
- 涨跌比（20%）：上涨家数/下跌家数
- 炸板率（20%）：开板次数/涨停数

**用法**：

```python
calculator = EmotionCycleCalculator(date)
result = calculator.calculate()
# result.phase: 'high_tide'|'ebb_tide'|'ice_point'|'warming'|'repair'
# result.score: 0-100
# result.strategy: 推荐策略
```

#### 3. 龙头评分 (`services/crawler/leader_score.py`)

**总分100+**：
- 连板数（0-50）：每连板+10分
- 封板时间（0-20）：早盘加分
- 开板次数（0-20）：0次满分，每开-5分
- 成交额/换手率（0-20）：适中最佳
- 题材热度（+10）：热门题材

**筛选标准**：评分 >=50 判定为龙头

#### 4. 技术指标 (`core/indicators/`)

标准计算，支持快速回测：
- **RSI**：6周期、12周期（超卖<30，超买>70）
- **MACD**：DIF(12-26EMA) → DEA(9EMA) → HIST(DIF-DEA)
- **KDJ**：K(RSV平滑) → D(K平滑) → J(3K-2D)（底部<20）
- **BOLL**：中轨(20SMA) ± 2倍标准差

#### 5. 爬虫模块 (`services/crawler/`)

**架构**：异步HTTP客户端（BaseCrawler）+ 具体爬虫

- `limit_up.py` - 同花顺涨停池（分时数据）
- `sector_flow.py` - 东财板块资金流向（JSON爬取）
- `emotion_cycle.py` - 情绪周期计算★（核心）
- `leader_score.py` - 龙头评分★（核心）
- `multi_factor.py` - 多因子选股

**爬虫特点**：
- 异步并发（大幅提升速度）
- 缓存机制（本地文件 + Redis）
- 失败重试（tenacity库）
- User-Agent轮换、随机延迟

## 开发指南

### 常用命令

```bash
# 启动开发服务器（自动重新加载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest tests/ -v -s

# 单个测试文件
pytest tests/test_indicators.py -v

# 快速脚本执行
python analyze_stocks_demo.py  # 缠论演示
python test_chan_demo.py       # 缠论测试

# 数据库操作
python -c "from app.config.database import init_db; init_db()"  # 初始化
python fix_database.py  # 修复数据库

# 数据同步（使用Tushare）
python -c "from app.services.tushare_service import TushareService; TushareService().sync_stocks()"
```

### API 响应格式（统一）

所有API遵循统一的响应格式：

```json
{
  "code": 0,
  "data": {...},
  "msg": "success"
}
```

**错误响应**：
```json
{
  "code": -1,
  "data": null,
  "msg": "error message"
}
```

**使用辅助函数**（在 `app/api/v1/router.py` 中）：
```python
from app.api.v1.router import success, error
return success(data)      # 成功
return error("error msg") # 失败
```

### 添加新 API 接口

#### 第1步：在对应模块添加路由

```python
# app/api/v1/your_module.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db
from app.api.v1.router import success, error

router = APIRouter(prefix="/your-prefix", tags=["your-tag"])

@router.get("/endpoint")
async def your_endpoint(
    date: str = Query(""),
    db: AsyncSession = Depends(get_db)
):
    """endpoint 说明"""
    try:
        # 业务逻辑
        result = await some_service(db, date)
        return success(result)
    except Exception as e:
        return error(str(e))
```

#### 第2步：在 `router.py` 中注册

```python
# app/api/v1/router.py
from .your_module import router as your_router

api_router.include_router(your_router)
```

#### 第3步：定义数据模型（可选）

```python
# app/schemas/your_schema.py
from pydantic import BaseModel

class YourRequest(BaseModel):
    field1: str
    field2: int

class YourResponse(BaseModel):
    code: int
    data: dict
    msg: str
```

### 添加爬虫模块

```python
# app/services/crawler/your_crawler.py
from .base import BaseCrawler

class YourCrawler(BaseCrawler):
    async def crawl(self, date: str) -> dict:
        """爬虫主逻辑"""
        url = "..."
        data = await self.get(url, params={"date": date})
        return self._parse_data(data)

    def _parse_data(self, raw: dict) -> dict:
        """数据解析"""
        return {
            "ts_code": raw.get("code"),
            "name": raw.get("name"),
            # ...
        }
```

### 数据库操作（SQLAlchemy 2.0）

**查询**：
```python
from sqlalchemy import select
from app.models import Stock

stmt = select(Stock).where(Stock.ts_code == "000001.SZ")
result = await db.execute(stmt)
stock = result.scalar_one_or_none()
```

**插入**：
```python
from app.models import DailyQuote

quote = DailyQuote(
    ts_code="000001.SZ",
    trade_date="2024-01-01",
    close=10.0,
    # ...
)
db.add(quote)
await db.commit()
```

**批量操作**：
```python
from sqlalchemy import insert

stmt = insert(Stock).values([
    {"ts_code": "000001.SZ", "name": "平安银行"},
    {"ts_code": "000002.SZ", "name": "万科A"},
])
await db.execute(stmt)
await db.commit()
```

### 缓存使用（Redis）

```python
from app.services.cache_service import CacheService

cache_service = CacheService(redis_url="redis://localhost", ttl=3600)

# 存储
await cache_service.set("key", value)

# 获取
value = await cache_service.get("key")

# 删除
await cache_service.delete("key")
```

### 定时任务配置（APScheduler）

```python
# app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=15, minute=30)
async def sync_daily_data():
    """每天15:30同步日线数据"""
    # 业务逻辑

scheduler.start()
```

## 性能优化

### 1. 异步优先

所有 IO 操作必须异步：
```python
# ❌ 错误
result = requests.get(url)

# ✅ 正确
result = await httpx.AsyncClient().get(url)
```

### 2. 向量化计算

使用 numpy 替代 Python 循环：
```python
# ❌ 慢
for i in range(len(closes)):
    rsi = calculate(closes[i])

# ✅ 快
rsi = calculate_rsi_vectorized(closes)  # numpy实现
```

### 3. 缓存热点数据

```python
# 缓存不经常变化的数据（股票列表、板块等）
cache_key = f"stocks:{date}"
cached = await cache_service.get(cache_key)
if not cached:
    data = await fetch_stocks(date)
    await cache_service.set(cache_key, data, ttl=86400)
```

## 重点文件清单

| 文件 | 职责 | 优先级 |
|------|------|--------|
| `core/chan/chan_service.py` | 缠论一站式分析 | ★★★ |
| `services/crawler/emotion_cycle.py` | 情绪周期算法 | ★★★ |
| `services/crawler/leader_score.py` | 龙头评分算法 | ★★★ |
| `core/indicators/*.py` | 技术指标计算 | ★★ |
| `api/v1/router.py` | API 路由聚合 | ★★ |
| `config/database.py` | 数据库连接配置 | ★★ |

## 常见问题

### 1. SQLite vs MySQL

**开发环境**：使用 SQLite（零配置，自动创建）
```env
DATABASE_URL=sqlite+aiosqlite:///./ai_stock.db
```

**生产环境**：使用 MySQL 8.0
```env
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_stock
```

### 2. Tushare API 限制

- 免费版本：每分钟 200 次请求
- 添加延迟：`await asyncio.sleep(0.5)`
- 使用 tenacity 重试机制

### 3. 爬虫被封 IP

- 添加随机延迟（1-3秒）
- 轮换 User-Agent
- 使用代理池（可选）

### 4. 数据库连接超时

```python
# 调整连接池配置（database.py）
create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,           # 连接池大小
    max_overflow=40,        # 最大溢出连接
    pool_pre_ping=True,     # 连接前检查
    pool_recycle=3600,      # 连接回收时间
)
```

## 下一步任务

- [ ] **缠论完整实现**：补全分型、笔、线段、中枢的所有算法
- [ ] **API补全**：实现37个核心接口（优先：情绪周期、龙头评分、多因子选股）
- [ ] **爬虫优化**：异步并发爬取，增强容错能力
- [ ] **回测引擎**：集成 backtrader/vnpy，支持策略回测
- [ ] **实时盯盘**：WebSocket 推送实时数据和信号
- [ ] **测试覆盖**：单元测试、集成测试、性能测试
- [ ] **Docker部署**：生产环境 Docker Compose 配置

## 环境变量模板

```env
# .env.example
DATABASE_URL=sqlite+aiosqlite:///./ai_stock.db
# DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_stock

TUSHARE_TOKEN=your_token_here
TUSHARE_API_URL=http://api.tushare.pro

REDIS_URL=redis://localhost:6379/0

DEBUG=True
API_V1_PREFIX=/api
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

## 关键概念

### 情绪周期五阶段

| 阶段 | 涨停数 | 连板数 | 策略 |
|------|-------|-------|------|
| 🔥高潮期 | >80 | >5 | 追踪龙头，关注补涨 |
| 📉退潮期 | 50-80 | 3-5 | 现金为王，等待信号 |
| ❄️冰点期 | <20 | <2 | 等待企稳，分批建仓 |
| 🌱回暖期 | 30-50 | 2-3 | 关注弱转强，首板确认 |
| 🔧修复期 | 50-80 | 3-4 | 超跌反弹，技术金叉 |

### 缠论买点判断

- **一买**：下跌趋势中第一个底背驰（价格创新低但指标不创新低）
- **二买**：一买后回调不破前低
- **三买**：中枢上方回踩不进中枢

---

**最后提醒**：Python 的优势在于**库生态强大**和**计算速度快**。充分利用 numpy 矢量化、pandas 数据处理、asyncio 并发，可以大幅提升性能。
