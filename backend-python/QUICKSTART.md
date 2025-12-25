# 快速启动指南

## 前置要求

### 1. 系统依赖
- Python 3.10+
- MySQL 8.0+
- Redis 6.0+

### 2. 可选（推荐）
- Docker / Docker Compose

---

## 方式1：本地运行（推荐开发）

### 第1步：环境配置

```bash
cd backend-python

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，修改以下内容：
# DATABASE_URL=mysql+aiomysql://root:password@localhost/ai_stock
# TUSHARE_TOKEN=你的tushare_token
# REDIS_URL=redis://localhost:6379/0
# DEBUG=True  # 开发环境启用热重载
```

### 第2步：创建数据库

```bash
# MySQL 中执行
mysql -u root -p

# SQL:
CREATE DATABASE ai_stock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 第3步：安装依赖

```bash
# 方法A：pip (推荐)
pip install -r requirements.txt

# 方法B：conda
conda create -n ai_stock python=3.10
conda activate ai_stock
pip install -r requirements.txt
```

### 第4步：初始化数据库

```bash
# 运行Alembic迁移（如果有）
alembic upgrade head

# 或导入 SQL 脚本（如果有）
mysql -u root -p ai_stock < database/schema.sql
```

### 第5步：启动应用

```bash
# 开发模式 (带热重载)
python app/main.py

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式 (4 worker)
python app/main.py  # 会用requirements.txt中的配置
```

访问：
- API: http://localhost:8000/api/docs
- 健康检查: http://localhost:8000/health

---

## 方式2：Docker 运行（推荐生产）

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

---

## 常见问题

### Q: 数据库连接失败
**A:** 检查以下内容：
```bash
# 1. 验证 MySQL 运行
mysql -u root -p -e "SELECT 1"

# 2. 验证数据库存在
mysql -u root -p -e "SHOW DATABASES;"

# 3. 检查 .env 中的 DATABASE_URL 格式
DATABASE_URL=mysql+aiomysql://user:password@host:port/database
```

### Q: Redis 连接失败
**A:**
```bash
# 1. 确保 Redis 在运行
redis-cli ping  # 应返回 PONG

# 2. 如果用 Docker
docker run -d -p 6379:6379 redis:latest

# 3. 检查 REDIS_URL 格式
REDIS_URL=redis://localhost:6379/0
```

### Q: Tushare API 限额
**A:**
- 去 https://tushare.pro 注册账号
- 获取免费 Token
- 填入 .env: `TUSHARE_TOKEN=your_token`

### Q: ta-lib 安装失败
**A:** 这个库需要编译，如果失败可以跳过：
```bash
# 移除 ta-lib，使用 pandas_ta 代替
pip install pandas-ta

# 或用 conda (更稳定)
conda install -c conda-forge ta-lib
```

---

## API 示例

### 1. 健康检查
```bash
curl http://localhost:8000/health
```

### 2. 缠论分析
```bash
curl "http://localhost:8000/api/chan-data?ts_code=000001.SZ"
```

### 3. 爬虫数据
```bash
curl "http://localhost:8000/api/crawl-eastmoney?date=20240101"
```

### 4. 技术指标
```bash
curl "http://localhost:8000/api/oversold?date=20240101"
```

查看完整 API 文档：http://localhost:8000/api/docs

---

## 性能优化

### 1. 数据库优化
```sql
-- 创建必要索引
CREATE INDEX idx_stock_code ON daily_quotes(ts_code);
CREATE INDEX idx_trade_date ON daily_quotes(trade_date);
CREATE INDEX idx_stock_date ON daily_quotes(ts_code, trade_date);
```

### 2. Redis 优化
```bash
# 启用持久化
redis-cli CONFIG SET save "900 1 300 10 60 10000"
redis-cli CONFIG REWRITE
```

### 3. 应用优化
编辑 .env:
```
DEBUG=False        # 关闭调试
WORKERS=8         # 增加worker数（根据CPU核数）
```

---

## 目录结构

```
backend-python/
├── app/
│   ├── main.py                 # 应用入口
│   ├── api/v1/                 # API 路由
│   ├── models/                 # ORM 模型
│   ├── schemas/                # Pydantic 模型
│   ├── services/               # 业务逻辑
│   │   ├── tushare_service.py
│   │   ├── indicator_service.py
│   │   └── crawler/            # 爬虫模块
│   ├── core/                   # 核心算法
│   │   ├── indicators/         # 技术指标
│   │   └── chan/               # 缠论算法
│   ├── config/                 # 配置管理
│   └── utils/                  # 工具函数
├── requirements.txt            # 依赖
├── .env.example               # 环境变量模板
├── docker-compose.yml         # Docker配置
└── README.md
```

---

## 开发命令

```bash
# 运行测试
pytest tests/ -v

# 代码检查
mypy app/

# 类型检查
python -m mypy app/

# 格式化代码
black app/

# 性能分析
python -m cProfile -s cumtime app/main.py
```

---

## 生产部署

### 使用 Gunicorn
```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Nginx 反向代理
```nginx
upstream app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 日志和监控

应用使用 `loguru` 记录日志，配置：
```python
# app/main.py 中修改日志级别
logger.enable("app")  # 启用日志
logger.add("logs/app.log", rotation="100 MB")  # 日志轮转
```

---

## 常用命令速查

```bash
# 启动
python app/main.py

# 热重载开发
uvicorn app.main:app --reload

# 数据库初始化
alembic upgrade head

# 同步股票数据
curl http://localhost:8000/api/sync-stocks

# 同步日线数据
curl "http://localhost:8000/api/sync-daily?date=20240101"

# 计算技术指标
curl "http://localhost:8000/api/calc-indicators?date=20240101"

# 爬取东财数据
curl "http://localhost:8000/api/crawl-eastmoney?date=20240101"
```

---

需要帮助？查看完整文档或提交 Issue！
