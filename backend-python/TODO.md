# 未完成任务清单

## Phase 3: API 层补全 (37个接口)

### ✅ 已完成 (6个API)
- ✅ `/api/analyze-stock` - 完整股票分析 (analysis.py)
- ✅ `/api/emotion-cycle` - 情绪周期分析 (analysis.py)
- ✅ `/api/multi-indicator-resonance` - 多指标共振选股 (analysis.py)
- ✅ `/api/oversold-stocks` - RSI超卖股票 (analysis.py)
- ✅ `/api/chan-analysis` - 缠论完整分析 (analysis.py)
- ✅ `/api/chan-key-levels` - 缠论关键价格位置 (analysis.py)

### ❌ 未完成的 API 端点 (31个)

#### 行情数据 (market.py) - 9个
- `GET /api/volume-top` - 成交量TOP50 (框架有，需测试)
- `GET /api/oversold` - ❌ RSI超卖 (框架有，逻辑未完)
- `GET /api/kdj-bottom` - ❌ KDJ底部
- `GET /api/macd-golden` - ❌ MACD金叉
- `GET /api/bottom-volume` - ❌ 底部放量
- `GET /api/industry-hot` - ❌ 行业热门
- `GET /api/market-index` - ❌ 市场指数
- `GET /api/counter-trend` - ❌ 反向市场
- `GET /api/market-stats` - ❌ 市场统计

#### 涨跌停 (limit.py) - 2个
- `GET /api/limit-up` - ❌ 涨停池
- `GET /api/limit-down` - ❌ 跌停池

#### 资金流向 (fund_flow.py) - 3个
- `GET /api/dragon-tiger` - ❌ 龙虎榜
- `GET /api/north-buy` - ❌ 北向买入
- `GET /api/margin-buy` - ❌ 融资买入

#### 技术形态 (pattern.py) - 5个
- `GET /api/breakout` - ❌ 技术突破
- `GET /api/top-volume` - ❌ 顶部放量
- `GET /api/gap-up` - ❌ 向上跳空
- `GET /api/gap-down` - ❌ 向下跳空
- `GET /api/industry-gap` - ❌ 行业跳空

#### 复盘管理 (review.py) - 3个
- `GET /api/review` - ❌ 获取复盘
- `POST /api/review` - ❌ 创建复盘
- `GET /api/review-history` - ❌ 复盘历史

#### 数据同步 (sync.py) - 4个
- `GET /api/sync-stocks` - ❌ 同步股票列表 (框架有)
- `GET /api/sync-daily` - ❌ 同步日线行情 (框架有)
- `GET /api/calc-indicators` - ❌ 计算技术指标 (框架有)
- `GET /api/crawl-eastmoney` - ❌ 爬取东财数据 (TODO 注释)

#### 爬虫数据 (crawler.py) - 3个
- `GET /api/eastmoney-data` - ❌ 东财数据
- `GET /api/eastmoney-list` - ❌ 东财列表

#### 缠论 (chan.py) - 8个
- `GET /api/chan-bottom-diverge` - ❌ 底部背离
- `GET /api/chan-top-diverge` - ❌ 顶部背离
- `GET /api/chan-first-buy` - ❌ 第一买点
- `GET /api/chan-second-buy` - ❌ 第二买点
- `GET /api/chan-third-buy` - ❌ 第三买点
- `GET /api/chan-hub-shake` - ❌ 中枢震荡
- `GET /api/chan-momentum` - ❌ 缠论动能
- `GET /api/chan-reversal` - ❌ 缠论反转

---

## Phase 4: 增强功能

### ❌ 定时任务 (APScheduler)
需要实现以下定时任务：
```python
# sync.py 中有 TODO 注释: "# TODO: 实现东财爬虫"

# 待实现的定时任务:
1. 每天 15:30 - 同步当日日线数据
   - 调用 TushareService.get_daily()
   - 保存到数据库

2. 每天 16:00 - 计算技术指标
   - 调用 IndicatorService.calc_all()
   - 计算所有股票的指标

3. 每天 16:30 - 爬取东财数据
   - 涨跌停数据
   - 龙虎榜数据
   - 北向资金
   - 融资买入
   - 情绪周期计算
   - 龙头评分计算

4. (可选) 交易时间每 5 分钟 - 实时数据更新
```

**文件**: `app/core/scheduler.py` (待创建)

### ❌ 缓存预热
需要在以下场景预热缓存：
```python
1. 应用启动时
   - 预热热门股票的技术指标 (top 100)
   - 预热最近 5 个交易日的情绪周期

2. 每日收盘后 (16:30)
   - 预热所有股票的当日指标 (如果列表 < 1000)
   - 预热情绪周期结果

3. 手动预热接口
   - POST /api/cache-warm?symbols=000001,000002
```

**文件**: `app/services/cache_service.py` 中已有 `CacheWarming` 类 (需集成)

---

## Phase 5: 测试部署

### ❌ 单元测试
需要为以下模块编写测试：

```
tests/
├── test_services/
│   ├── test_data_service.py
│   │   ├── test_calculate_indicators()      # ta-lib 精度测试
│   │   ├── test_identify_oversold()         # 向量化过滤
│   │   ├── test_batch_analyze_stocks()      # asyncio 并发
│   │   └── test_multi_indicator_resonance() # 共振逻辑
│   ├── test_chan_service.py
│   │   ├── test_identify_fractals()         # 分型识别
│   │   ├── test_identify_bis()              # 笔识别
│   │   ├── test_identify_segments()         # 线段识别
│   │   ├── test_identify_hubs()             # 中枢识别
│   │   └── test_key_levels()                # 支撑阻力
│   ├── test_cache_service.py
│   │   ├── test_redis_set_get()
│   │   ├── test_cache_ttl()
│   │   └── test_cache_delete_pattern()
│   └── test_crawler/
│       ├── test_market_crawler.py
│       ├── test_limit_crawler.py
│       └── test_tushare_service.py
├── test_api/
│   ├── test_analysis_api.py
│   ├── test_market_api.py
│   ├── test_chan_api.py
│   └── test_integration.py  # 完整流程测试
└── conftest.py  # pytest 配置和 fixtures
```

### ❌ 性能对标测试
对比 PHP vs Python 的性能差异：
```python
# tests/benchmark/
├── benchmark_indicators.py      # 技术指标计算
├── benchmark_filtering.py        # 数据过滤
├── benchmark_concurrent.py       # 并发处理
├── benchmark_chan.py             # 缠论分析
└── benchmark_cache.py            # 缓存性能
```

### ❌ Docker 部署配置
```
# 待创建的文件:
- Dockerfile                      # Python 应用镜像
- docker-compose.yml              # MySQL + Redis + 应用
- .dockerignore
- docker/entrypoint.sh           # 启动脚本 (初始化DB)
```

**Dockerfile 示例内容**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Phase 6: 运维和监控

### ❌ 日志系统配置
```python
# app/core/logging.py (待创建)
# 配置 loguru:
# 1. 日志级别: DEBUG, INFO, WARNING, ERROR
# 2. 日志输出:
#    - 控制台 (开发)
#    - 文件 (生产，自动轮转)
#    - 结构化日志 (JSON)
# 3. 性能日志:
#    - API 响应时间
#    - 数据库查询时间
#    - 缓存命中率
```

### ❌ 性能监控
```python
# app/core/monitoring.py (待创建)
# 1. 中间件: 记录每个 API 的响应时间
# 2. 缓存监控: 命中率、未命中率
# 3. 数据库监控: 慢查询
# 4. Redis 监控: 内存使用、命令延迟
```

### ❌ 错误处理和重试机制
```python
# app/core/exceptions.py (待创建)
# 1. 自定义异常类
# 2. 全局异常处理器
# 3. 数据源失败时的重试逻辑 (exponential backoff)
# 4. 限流控制
```

---

## 优先级排序

### 高优先级 (必做)
1. **API 端点补全** (7-10 小时)
   - 先完成简单的 (volume-top, oversold 等)
   - 再完成复杂的 (缠论变体)

2. **定时任务** (3-5 小时)
   - APScheduler 配置
   - 15:30 同步、16:00 计算任务

3. **Docker 部署** (2-3 小时)
   - Dockerfile + docker-compose
   - 一键启动完整环境

### 中优先级 (重要)
4. **单元测试** (5-8 小时)
   - 关键算法测试
   - API 集成测试

5. **错误处理** (3-4 小时)
   - 异常处理器
   - 重试机制

### 低优先级 (可选)
6. **性能对标** (4-6 小时)
   - PHP vs Python 对比
   - 基准测试

7. **监控告警** (3-5 小时)
   - 日志系统
   - 性能监控

---

## 工作量估算

| 项目 | 工作量 | 优先级 |
|------|--------|--------|
| API 端点补全 | 10h | 🔴 高 |
| APScheduler | 5h | 🔴 高 |
| Docker 部署 | 3h | 🔴 高 |
| 单元测试 | 8h | 🟡 中 |
| 错误处理 | 4h | 🟡 中 |
| 性能对标 | 6h | 🟢 低 |
| 监控系统 | 5h | 🟢 低 |
| **总计** | **41h** | - |

---

## 建议执行顺序

### 第一周 (高优先级，18h)
1. 完成 API 端点补全 (10h)
   - 先用 Python 优化思路 (asyncio + pandas + ta-lib)
   - 不要简单搬运 PHP 逻辑

2. 实现 APScheduler 定时任务 (5h)
   - 15:30 同步任务
   - 16:00 计算任务
   - 缓存预热

3. Docker 部署配置 (3h)
   - 一键启动

### 第二周 (中优先级，12h)
4. 单元测试 (8h)
   - 优先测试关键算法 (缠论、技术指标)
   - 再测试 API 端点

5. 错误处理和重试 (4h)
   - 异常捕获
   - 数据源失败处理

### 第三周 (可选，10h)
6. 性能对标和监控
   - 生成 PHP vs Python 对比报告
   - 监控系统集成

---

## 快速检查清单

- [ ] 所有 37 个 API 端点都有实现
- [ ] 定时任务正常运行 (15:30, 16:00)
- [ ] Redis 缓存正常工作
- [ ] 所有测试通过 (pytest)
- [ ] Docker 可以一键启动
- [ ] 性能数据符合预期
- [ ] 前端无需修改即可访问新 API

---

## 相关文件位置

| 功能 | 文件 | 状态 |
|------|------|------|
| API 路由 | `app/api/v1/` | ⚠️ 部分完成 |
| 数据服务 | `app/services/` | ✅ 完成 |
| 定时任务 | `app/core/scheduler.py` | ❌ 待创建 |
| 测试 | `tests/` | ❌ 待创建 |
| Docker | `Dockerfile` | ❌ 待创建 |
| 日志监控 | `app/core/logging.py` | ❌ 待创建 |
