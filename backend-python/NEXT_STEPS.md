# 下一步行动计划

## 📊 当前完成度

```
基础框架:         ████████████████████ 100%  ✅
数据服务:         ████████████████████ 100%  ✅
缠论算法:         ████████████████████ 100%  ✅
缓存系统:         ████████████████████ 100%  ✅
高级 API:         ████████░░░░░░░░░░░░  16%  (6/37)
定时任务:         ░░░░░░░░░░░░░░░░░░░░   0%  ❌
单元测试:         ░░░░░░░░░░░░░░░░░░░░   0%  ❌
Docker 部署:      ░░░░░░░░░░░░░░░░░░░░   0%  ❌
─────────────────────────────────────────────
整体完成度:       ████████░░░░░░░░░░░░  40%
```

---

## 🎯 核心缺陷

### 1. **API 端点不完整** (31个待完成)
- 行情数据: 9个
- 涨跌停: 2个
- 资金流向: 3个
- 技术形态: 5个
- 复盘管理: 3个
- 数据同步: 4个
- 爬虫数据: 3个
- 缠论特殊形态: 8个

**影响**: 前端无法访问大部分功能

### 2. **没有定时任务**
- 日线数据无法自动同步 (需手动调用 API)
- 技术指标无法自动计算
- 情绪周期无法自动更新

**影响**: 无法实现自动化流程

### 3. **没有 Docker 配置**
- 无法快速部署到服务器
- 依赖管理混乱

**影响**: 部署困难

### 4. **没有测试用例**
- 算法正确性无法保证
- 无法进行 PHP vs Python 对标

**影响**: 不敢放心上线

---

## ✅ 优先顺序 (推荐)

### Week 1: 快速补全基础 (18-20 小时)

#### Day 1-2: API 端点 (10 小时) 🔴 最高优先级
```bash
# 先做简单的 (每个 1-2 小时)
1. /api/volume-top           # 成交量排序
2. /api/oversold             # RSI 过滤
3. /api/kdj-bottom           # KDJ 过滤
4. /api/macd-golden          # MACD 过滤

# 再做复杂的 (每个 2-3 小时)
5. /api/industry-hot         # 行业分析
6. /api/limit-up/limit-down  # 涨跌停池
7. /api/dragon-tiger         # 龙虎榜
```

**关键**: 使用新的 DataService + pandas 逻辑，不要复制 PHP

#### Day 3: APScheduler (5 小时) 🔴 最高优先级
```python
# app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 15:30 同步数据
scheduler.add_job(sync_daily, 'cron', hour=15, minute=30)

# 16:00 计算指标
scheduler.add_job(calc_indicators, 'cron', hour=16, minute=0)

# 16:30 情绪周期 + 龙头评分
scheduler.add_job(update_emotion_cycle, 'cron', hour=16, minute=30)
```

#### Day 4: Docker (3-4 小时) 🔴 最高优先级
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

**成果**: 完整可运行的系统 ✅

---

### Week 2: 保障质量 (12-14 小时)

#### Day 1-2: 单元测试 (8 小时) 🟡 高优先级
```bash
# tests/test_services/
pytest test_data_service.py          # ta-lib 计算精度
pytest test_chan_service.py           # 缠论算法正确性
pytest test_cache_service.py          # 缓存功能

# tests/test_api/
pytest test_analysis_api.py           # API 集成测试
```

**成果**: 代码有保障 ✅

#### Day 3: 错误处理 (3-4 小时) 🟡 中优先级
```python
# app/core/exceptions.py
- 自定义异常类 (DataSourceError, CacheError, etc)
- 全局异常处理器
- 重试机制 (exponential backoff)
```

#### Day 4: 性能测试 (2-3 小时) 🟡 中优先级
```python
# tests/benchmark/
- 对标 PHP vs Python
- 生成性能报告
- 验证优化成果
```

---

### Week 3: 可选优化 (5-10 小时)

#### 监控系统 (3-5 小时)
```python
# app/core/logging.py
# app/core/monitoring.py
- 日志聚合
- API 响应时间监控
- 缓存命中率监控
```

#### 缓存预热 (2-3 小时)
```python
# 在 scheduler 中调用
await CacheWarming(cache).warm_stock_data(top_100_symbols)
```

---

## 📝 具体命令

### 立即可执行
```bash
# 查看当前 API 完成度
grep -r "@router.get" app/api/v1/ | wc -l

# 查看测试覆盖率
pytest --cov=app tests/

# 查看数据库状态
mysql -u root -p ai_stock -e "SELECT COUNT(*) FROM stocks;"
```

### 第一周结束应该达成
```bash
# ✅ 所有 API 都可以访问
curl http://localhost:8000/api/volume-top
curl http://localhost:8000/api/oversold

# ✅ 定时任务正在运行
python -c "from app.core.scheduler import scheduler; print(scheduler.get_jobs())"

# ✅ Docker 可以启动
docker-compose up -d
curl http://localhost:8000/health
```

### 第二周结束应该达成
```bash
# ✅ 所有测试通过
pytest tests/ -v --tb=short

# ✅ 代码覆盖率 > 80%
pytest --cov=app tests/ --cov-report=html

# ✅ 性能对标完成
python tests/benchmark/benchmark_indicators.py
```

---

## 🚨 风险和预防

### 风险 1: API 逻辑不清晰
**预防**:
- 参考 PHP 源码理解业务逻辑
- 用 Python 最优方式重新实现（不是直译）
- 每个 API 必须有清晰的文档

### 风险 2: 并发问题
**预防**:
- 所有异步调用都用 `await`
- 使用线程池处理阻塞 IO
- 测试并发场景

### 风险 3: 数据源失败
**预防**:
- 所有 API 调用都要有异常处理
- 实现重试机制
- 缓存作为降级方案

### 风险 4: 性能不达预期
**预防**:
- 及时进行性能测试
- 监控 API 响应时间
- 优化慢查询

---

## 📊 里程碑

```
Week 1 结束:  40% → 70%  (基础功能可用)
Week 2 结束:  70% → 85%  (质量有保障)
Week 3 结束:  85% → 95%  (优化完成)
Week 4:       95% → 100% (修复边界情况)
```

---

## 🎬 立即开始

### 选项 A: 快速补全 API (推荐)
```bash
# 现在开始，估计 10-12 小时
# 为每个简单 API 创建实现（参考 analysis.py 的模式）

# 1. 复制 analysis.py 的结构
# 2. 使用 DataService 的向量化方法
# 3. 集成缓存
# 4. 文档齐全

→ 快速让系统可用
```

### 选项 B: 先做定时任务 (备选)
```bash
# 创建 app/core/scheduler.py
# 配置 APScheduler
# 测试定时触发

→ 系统自动化
```

### 选项 C: 先做 Docker (备选)
```bash
# 创建 Dockerfile + docker-compose.yml
# 测试完整启动流程

→ 快速部署
```

**建议**: **选项 A + B 并行** (一个开发者 API，一个开发者 Scheduler)

---

## ❓ 常见问题

**Q: 必须按顺序来吗？**
A: 不必。API 和 Scheduler 可以并行做，但 Docker 建议在 API 和 Scheduler 都完成后再做。

**Q: 可以借用 PHP 代码吗？**
A: 可以参考业务逻辑，但要用 Python 优化方式重写。直接翻译会失去性能优势。

**Q: 需要的测试覆盖率是多少？**
A: 最少 70%。关键逻辑（缠论、指标计算）必须 100%。

**Q: 前端需要改动吗？**
A: 不需要。API 路由完全兼容，请求和响应格式一致。

---

## 📞 需要帮助？

检查以下文件：
- **OPTIMIZATION_GUIDE.md** - 优化原理
- **QUICK_START.md** - API 使用
- **TODO.md** - 详细任务清单
- **CLAUDE.md** - 项目规范
