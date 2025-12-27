# 快速开始

## 5分钟上手

### 1. 配置数据库和API Token

编辑 `.env`：
```env
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_stock
TUSHARE_TOKEN=your_tushare_token_here
```

### 2. 一键初始化所有数据

```bash
python data_init.py --step all
```

**这会自动：**
- ✓ 创建数据库表
- ✓ 同步4000+ 只股票信息
- ✓ 同步 500 天的日线数据
- ✓ 计算 RSI、MACD、KDJ、布林带
- ✓ 计算缠论指标（分型、走势、拐点）

**耗时：** 60-90 分钟

### 3. 查询单只股票

```bash
# 基本信息
python query_stock.py 000001.SZ

# 完整分析（包括缠论）
python query_stock.py 000001.SZ --all

# 多周期分析
python query_stock.py 000001.SZ --multi-period
```

### 4. 启动 API 服务

```bash
python -m uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看所有 API

### 5. 设置定时更新（可选）

```bash
# 每天收盘后自动更新数据和指标
python schedule_sync.py
```

---

## 常用命令

| 需求 | 命令 |
|------|------|
| 完整初始化 | `python data_init.py --step all` |
| 仅测试（100只股票） | `python data_init.py --step all --limit 100` |
| 查询单股 | `python query_stock.py 000001.SZ --all` |
| 重新计算指标 | `python data_init.py --step indicators` |
| 重新计算缠论 | `python data_init.py --step chan` |
| 启动定时服务 | `python schedule_sync.py` |
| 测试定时任务 | `python schedule_sync.py --test` |

---

## 主要 API 端点

```bash
# 单股票完整分析
GET /api/v1/trend/analyze?ts_code=000001.SZ

# 多周期分析（日线+30分钟+5分钟）
GET /api/v1/trend/multi-period?ts_code=000001.SZ

# 全市场趋势扫描
GET /api/v1/trend/scan-market?limit=100

# 买入信号扫描
GET /api/v1/trend/scan-buy-signals?limit=50

# 卖出信号扫描
GET /api/v1/trend/scan-sell-signals?limit=50
```

---

## 故障排查

| 问题 | 解决方案 |
|------|--------|
| 数据库连接失败 | 检查 `.env` 中的 `DATABASE_URL` 和数据库是否启动 |
| Tushare 超时 | 检查 Token 有效性，增加超时时间 |
| K线数据不足 | 运行 `python data_init.py --step sync-klines` |
| 缠论计算失败 | 数据不足(<50条)，忽略即可 |
| 分钟K线超时 | 东财 API 不稳定，多试几次 |

---

## 新增工具

| 文件 | 用途 |
|------|------|
| `data_init.py` | 完整数据初始化 |
| `query_stock.py` | 单股票查询 |
| `schedule_sync.py` | 定时更新服务 |

详见：`DATA_INITIALIZATION.md`

---

**祝你使用愉快！🚀**
