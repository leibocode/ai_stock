# 快速参考指南

## 🚀 快速启动

### 1. 环境准备
```bash
# Python 3.10+
python --version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/stock_db
REDIS_URL=redis://localhost:6379/0
DEBUG=True
```

### 3. 启动应用
```bash
# 自动启动调度器
python -m uvicorn app.main:app --reload

# 访问 API 文档
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

---

## 📅 定时任务系统

### 自动执行的任务

| 时间 | 任务ID | 功能 | 状态 |
|------|--------|------|------|
| 15:30 | sync_daily | 同步当日日线行情 | ⏳ 待实现 |
| 16:00 | calc_indicators | 计算 RSI/MACD/KDJ 等指标 | ⏳ 待实现 |
| 16:30 | crawl_eastmoney | 爬取龙虎榜、北向资金等 | ⏳ 待实现 |
| 18:00 | cache_warmup | 预热热点数据缓存 | ⏳ 待实现 |

### 管理任务的 API

#### 1️⃣ 查看所有任务
```bash
curl http://localhost:8000/api/v1/scheduler/jobs
```

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "total": 4,
    "jobs": [
      {
        "id": "sync_daily",
        "name": "同步日线行情",
        "next_run_time": "2024-12-24 15:30:00",
        "trigger": "cron[hour='15', minute='30']"
      },
      {
        "id": "calc_indicators",
        "name": "计算技术指标",
        "next_run_time": "2024-12-24 16:00:00",
        "trigger": "cron[hour='16', minute='0']"
      }
    ]
  }
}
```

#### 2️⃣ 查看调度器状态
```bash
curl http://localhost:8000/api/v1/scheduler/status
```

#### 3️⃣ 暂停任务
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/pause/sync_daily
```

#### 4️⃣ 恢复任务
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/resume/sync_daily
```

#### 5️⃣ 立即执行任务（测试用）
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/run-now/sync_daily
```

---

## 📊 API 快速查询

### 行情数据
```bash
# TOP50 成交量
curl "http://localhost:8000/api/v1/volume-top?date=20241223&limit=50"

# RSI 超卖 (RSI < 30)
curl "http://localhost:8000/api/v1/oversold?date=20241223&rsi_threshold=30"

# KDJ 底部 (K<20, D<20)
curl "http://localhost:8000/api/v1/kdj-bottom?date=20241223"

# MACD 金叉
curl "http://localhost:8000/api/v1/macd-golden?date=20241223"

# 市场统计
curl "http://localhost:8000/api/v1/market-stats?date=20241223"
```

### 涨跌停
```bash
# 涨停列表
curl "http://localhost:8000/api/v1/limit-up?date=20241223&limit=100"

# 跌停列表
curl "http://localhost:8000/api/v1/limit-down?date=20241223&limit=100"
```

### 技术形态
```bash
# 突破形态 (突破20日高点)
curl "http://localhost:8000/api/v1/breakout?date=20241223&lookback=20"

# 向上跳空
curl "http://localhost:8000/api/v1/gap-up?date=20241223"

# 向下跳空
curl "http://localhost:8000/api/v1/gap-down?date=20241223"

# 行业跳空
curl "http://localhost:8000/api/v1/industry-gap?date=20241223"
```

### 复盘管理
```bash
# 获取复盘记录
curl "http://localhost:8000/api/v1/review?date=20241223"

# 保存复盘记录 (POST)
curl -X POST "http://localhost:8000/api/v1/review" \
  -H "Content-Type: application/json" \
  -d '{
    "trade_date": "20241223",
    "content": "今日涨停32只，市场热情高涨",
    "emotion_phase": "high"
  }'

# 复盘历史
curl "http://localhost:8000/api/v1/review-history?limit=20"
```

### 数据同步
```bash
# 同步股票列表
curl "http://localhost:8000/api/v1/sync-stocks"

# 同步日线行情
curl "http://localhost:8000/api/v1/sync-daily?date=20241223"

# 计算技术指标
curl "http://localhost:8000/api/v1/calc-indicators?date=20241223"

# 爬取东财数据
curl "http://localhost:8000/api/v1/crawl-eastmoney?date=20241223"
```

---

## 🔧 Python 生态优化实践

### 1. 使用缓存装饰器（已实现）

```python
from app.utils.cache_decorator import cache_with_ttl

# 方式 1: 自动 key 生成
@cache_with_ttl(ttl=3600)
async def get_oversold_stocks(date: str):
    return await db.query(...)

# 方式 2: 自定义 key 生成器
@cache_with_ttl(
    ttl=86400,
    key_builder=lambda fn, *args, **kwargs: f"stocks:{args[0]}"
)
async def get_stocks(date: str):
    return await db.query(...)
```

### 2. Pandas 向量化处理（已应用）

```python
# 获取所有数据后，使用 pandas 批量处理
df = pd.DataFrame(data_list)

# ✅ 优化前：使用 for 循环
results = []
for ts_code, group in df.groupby('ts_code'):
    result = process_group(group)
    results.append(result)

# ✅ 优化后：Pandas 向量化
results = [
    r for r in df.groupby('ts_code').apply(process_group).dropna()
]
```

### 3. AsyncIO 并发处理

```python
import asyncio

# 同步批量获取多只股票数据（10x 性能提升）
stock_codes = ['000001.SZ', '000858.SZ', '000651.SZ', ...]
tasks = [get_daily(code) for code in stock_codes]
results = await asyncio.gather(*tasks)  # 并发执行
```

### 4. 类型提示和 Pydantic（示例）

```python
from pydantic import BaseModel, Field
from typing import List

class StockQuote(BaseModel):
    ts_code: str = Field(..., description="股票代码")
    close: float = Field(gt=0, description="收盘价")
    volume: float = Field(ge=0, description="成交量")

    class Config:
        json_schema_extra = {
            "example": {
                "ts_code": "000001.SZ",
                "close": 10.50,
                "volume": 100000000
            }
        }
```

---

## 🐳 Docker 快速启动（待实现）

```bash
# 启动全栈（MySQL + Redis + FastAPI）
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

---

## 🧪 测试和调试

### 运行单个 API 测试
```bash
# 使用 pytest
pytest tests/test_api/test_market.py -v

# 使用 FastAPI TestClient
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get("/api/v1/volume-top?date=20241223")
assert response.status_code == 200
```

### 监控定时任务执行

查看日志：
```bash
tail -f logs/app.log | grep scheduler
```

或通过 API 查询：
```bash
curl http://localhost:8000/api/v1/scheduler/status
```

---

## 📈 性能监控

### 查看缓存命中率
```bash
# 连接 Redis
redis-cli

# 统计缓存键
DBSIZE

# 监控缓存操作
MONITOR
```

### 检查 API 响应时间
```bash
# 使用 curl -w 显示响应时间
curl -w "@curl-format.txt" \
  -o /dev/null -s \
  "http://localhost:8000/api/v1/volume-top?date=20241223"
```

---

## 🐛 常见问题

### Q: 定时任务没有执行？
**A:** 检查应用是否正确启动（应该看到 "scheduler running"），查看日志：
```bash
grep "scheduler" logs/app.log
curl http://localhost:8000/api/v1/scheduler/status
```

### Q: Redis 连接失败？
**A:** 检查 Redis 服务和连接字符串：
```bash
# 测试 Redis 连接
redis-cli ping
# 应该返回 PONG
```

### Q: API 返回缓存数据，但想要最新数据？
**A:** 目前的 TTL 设置：
- 行情数据：24 小时
- 技术指标：24 小时
- 爬虫数据：6 小时
- 市场统计：1 小时

可以通过修改 API 中的 `ttl` 参数调整。

### Q: 如何手动触发定时任务进行测试？
**A:** 使用立即执行 API：
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/run-now/sync_daily
```

---

## 📚 相关文件速查

| 文件 | 用途 | 修改频率 |
|------|------|---------|
| `app/main.py` | 应用入口，集成调度器 | 低 |
| `app/core/scheduler.py` | 定时任务配置 | 中 |
| `app/api/v1/scheduler.py` | 任务管理 API | 低 |
| `app/utils/cache_decorator.py` | 缓存装饰器 | 低 |
| `requirements.txt` | 依赖管理 | 中 |
| `.env` | 环境配置 | 高（本地） |

---

## 🎯 下一步步骤

### 立即开始
1. ✅ 安装依赖
2. ✅ 配置环境
3. ✅ 启动应用
4. ✅ 测试 API

### 短期（1-2 周）
- 应用缓存装饰器到所有 API
- 添加 Pydantic 响应模型
- 优化爬虫并发

### 中期（2-4 周）
- 实现缺失的服务层
- 编写单元测试
- Docker 部署

### 长期（1-2 月）
- 性能基准测试
- 性能优化
- 监控系统集成

---

**最后更新**: 2024-12-23
**推荐 Python 版本**: 3.10+
**推荐服务器配置**: 2+ CPU 核心，4+ GB RAM
