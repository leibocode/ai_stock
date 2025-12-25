# 快速开始指南

## 项目启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量 (.env)
DATABASE_URL=mysql+aiomysql://root:password@localhost/ai_stock
TUSHARE_TOKEN=your_token
REDIS_URL=redis://localhost:6379/0
DEBUG=False

# 3. 启动应用
uvicorn app.main:app --reload

# 4. 访问 API 文档
# 自动文档: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

---

## 核心 API 示例

### 1. 完整股票分析 (所有技术指标)
```bash
# 请求
GET /api/analyze-stock?symbol=000001

# 响应 (示例)
{
  "code": 0,
  "data": {
    "symbol": "000001",
    "date": "2023-12-15",
    "ohlc": {
      "open": 10.5,
      "high": 10.8,
      "low": 10.3,
      "close": 10.7
    },
    "indicators": {
      "rsi_6": 35,
      "rsi_12": 42,
      "macd": 0.15,
      "macd_hist": 0.05,
      "k": 28,
      "d": 32,
      "j": 20,
      "boll_upper": 11.2,
      "boll_mid": 10.8,
      "boll_lower": 10.4,
      "atr": 0.35
    },
    "signals": {
      "rsi_oversold": true,
      "macd_golden_cross": true,
      "kdj_bottom": true
    },
    "history_count": 250,
    "from_cache": false
  },
  "msg": "success"
}
```

### 2. 情绪周期分析
```bash
# 请求
GET /api/emotion-cycle?trade_date=20231215

# 响应 (示例)
{
  "code": 0,
  "data": {
    "trade_date": "20231215",
    "emotion_cycle": {
      "phase": "高潮期",
      "score": 75,
      "limit_up_count": 95,
      "limit_down_count": 8,
      "profit_effect": 72.5,
      "strategy": "追踪龙头，谨慎追高"
    },
    "top_leaders": [
      {"symbol": "000001", "score": 85, "continuous": 3},
      ...
    ],
    "recommendation": "当前处于高潮期，龙头战法机会大"
  },
  "msg": "success"
}
```

### 3. 多指标共振选股
```bash
# 请求
GET /api/multi-indicator-resonance?symbols=000001,000002,000003&trade_date=20231215

# 响应 (示例)
{
  "code": 0,
  "data": {
    "trade_date": "20231215",
    "total_analyzed": 3,
    "resonance_count": 2,
    "resonance_stocks": [
      {
        "symbol": "000001",
        "hit_count": 5,
        "indicators": ["rsi_6 < 30", "macd_hist > 0", "k < 20", ...],
        "close": 10.7,
        "rsi_6": 28
      },
      {
        "symbol": "000002",
        "hit_count": 4,
        "indicators": ["macd_hist > 0", "close > ma_20", ...]
      }
    ],
    "recommendation": "命中 >= 3 个指标的股票为重点关注"
  },
  "msg": "success"
}
```

### 4. RSI 超卖股票
```bash
# 请求
GET /api/oversold-stocks?symbols=000001,000002,000003&rsi_threshold=30

# 响应 (示例)
{
  "code": 0,
  "data": [
    {"symbol": "000001", "rsi_6": 22, "rsi_12": 28, "close": 10.7},
    {"symbol": "000002", "rsi_6": 25, "rsi_12": 35, "close": 15.3}
  ],
  "msg": "success"
}
```

### 5. 缠论完整分析
```bash
# 请求
GET /api/chan-analysis?symbol=000001

# 响应 (示例)
{
  "code": 0,
  "data": {
    "symbol": "000001",
    "date": "2023-12-15",
    "close": 10.7,
    "chan": {
      "current_trend": "up",
      "fractal_count": 28,
      "bi_count": 14,
      "segment_count": 3,
      "hub_count": 2
    },
    "latest_bis": [
      {
        "start_idx": 240,
        "end_idx": 250,
        "direction": "up",
        "start_price": 10.2,
        "end_price": 10.8
      }
    ],
    "latest_hub": {
      "start_idx": 230,
      "end_idx": 250,
      "high": 11.0,
      "low": 10.3,
      "amplitude": 0.7
    },
    "breakouts": [],
    "key_levels": {
      "resistance": [
        {"level": 11.0, "strength": "medium"},
        {"level": 10.9, "strength": "weak"}
      ],
      "support": [
        {"level": 10.3, "strength": "medium"},
        {"level": 10.1, "strength": "weak"}
      ]
    }
  },
  "msg": "success"
}
```

### 6. 缠论关键价格位置
```bash
# 请求
GET /api/chan-key-levels?symbol=000001

# 响应 (示例)
{
  "code": 0,
  "data": {
    "symbol": "000001",
    "date": "2023-12-15",
    "close": 10.7,
    "resistance": [
      {"level": 11.0, "strength": "medium"},
      {"level": 10.9, "strength": "weak"}
    ],
    "support": [
      {"level": 10.3, "strength": "medium"},
      {"level": 10.1, "strength": "weak"}
    ],
    "recommendation": "价格接近阻力位时减仓，接近支撑位时加仓"
  },
  "msg": "success"
}
```

---

## 代码使用示例

### 在你的代码中使用服务

```python
from app.services.data_service import DataService
from app.services.chan_service import ChanService
from app.services.cache_service import CacheService, CacheKeys

# 1. 获取数据并计算指标
df = DataService.get_market_data_akshare('000001')
df = DataService.calculate_indicators(df)

# 2. 识别超卖信号
oversold_df = DataService.identify_oversold(df, rsi_threshold=30)

# 3. 缠论分析
chan_result = ChanService.analyze(df)
print(f"当前趋势: {chan_result['current_trend']}")
print(f"分型数: {chan_result['fractal_count']}")

# 4. 获取关键价格位置
key_levels = ChanService.get_key_levels(df)
print(f"阻力位: {key_levels['resistance']}")
print(f"支撑位: {key_levels['support']}")

# 5. 使用缓存
cache = CacheService()
key = CacheKeys.stock_indicators('000001')

# 尝试从缓存获取
cached = await cache.get(key)
if not cached:
    # 计算并保存
    data = await expensive_calculation()
    await cache.set(key, data, ttl=3600)
```

### 批量处理

```python
import asyncio

async def analyze_portfolio(symbols: List[str]):
    # 并发分析多只股票
    stocks_data = await DataService.batch_analyze_stocks(symbols)

    # 多指标共振
    resonance = DataService.get_multi_indicator_resonance(
        stocks_data,
        date='20231215'
    )

    # 按命中指标数排序
    resonance.sort(key=lambda x: x['hit_count'], reverse=True)

    return resonance

# 运行
asyncio.run(analyze_portfolio(['000001', '000002', '000003']))
```

---

## 缓存使用

```python
from app.services.cache_service import CacheService, CacheKeys

async def get_stock_with_cache(symbol: str):
    cache = CacheService()
    key = CacheKeys.stock_indicators(symbol)

    # 先查缓存
    cached = await cache.get(key)
    if cached:
        return cached  # 1ms 返回

    # 缓存未命中，计算
    df = DataService.get_market_data_akshare(symbol)
    df = DataService.calculate_indicators(df)

    # 保存到缓存
    data = df.to_dict(orient='records')
    await cache.set(key, data, ttl=86400)  # 24 小时

    return data
```

---

## 性能测试

```python
import time

# 测试技术指标计算性能
df = DataService.get_market_data_akshare('000001')

start = time.time()
df = DataService.calculate_indicators(df)
elapsed = time.time() - start

print(f"指标计算耗时: {elapsed*1000:.1f}ms")  # 通常 < 50ms

# 测试并发处理
symbols = ['000001', '000002', '000003', '000004', '000005']

start = time.time()
results = asyncio.run(DataService.batch_analyze_stocks(symbols))
elapsed = time.time() - start

print(f"5只股票并发分析耗时: {elapsed*1000:.1f}ms")  # 通常 150-200ms
```

---

## 常见问题

### Q: 数据来源是什么？
A: 使用 `akshare` 作为主数据源，提供完整的中国股票数据。

### Q: 如何添加新的技术指标？
A: 直接在 `DataService.calculate_indicators()` 中添加 ta-lib 计算：
```python
df['custom_indicator'] = talib.SOME_FUNCTION(close, **params)
```

### Q: 如何清除缓存？
A:
```python
cache = CacheService()
await cache.delete(CacheKeys.stock_indicators('000001'))
await cache.delete_pattern('stock:*')  # 清除所有股票缓存
```

### Q: 支持多少只股票的并发分析？
A: 取决于服务器性能和网络带宽。通常可以并发 50-100 只股票而不会过载。

### Q: 缠论分析的时间复杂度是多少？
A: O(n)，其中 n 是 K 线数量。分析 5000 条 K 线通常 < 100ms。

---

## 下一步

1. **部署到生产环境**
   ```bash
   docker-compose up -d
   ```

2. **配置定时任务** (APScheduler)
   - 15:30 同步日线数据
   - 16:00 计算技术指标
   - 每日更新缠论数据

3. **监控和日志**
   - 使用 loguru 记录重要操作
   - 监控 Redis 内存使用
   - 监控 API 响应时间

4. **性能优化**
   - 根据实际情况调整缓存 TTL
   - 监控慢查询日志
   - 优化数据库索引

---

## 相关文件

- 详细优化指南: `OPTIMIZATION_GUIDE.md`
- 项目规划: `../plans/elegant-leaping-horizon.md`
- API 文档: http://localhost:8000/docs (自动生成)
