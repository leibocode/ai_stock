# 数据库连接修复指南

## 📋 问题诊断

### 当前状态
- ✅ **网络连接**: MySQL 服务器端口 (3306) 可访问
- ❌ **认证失败**: `Access denied for user 'root'@'61.169.6.234' (using password: YES)`

### 错误分析
```
(pymysql.err.OperationalError) (1045, "Access denied...")
```

**原因可能**:
1. **密码错误** - 提供的密码 `8pCNX3N3mzsHBLaW` 可能不对
2. **用户不存在** - MySQL中可能没有root用户
3. **权限限制** - 该用户可能不被允许远程连接
4. **新密码已设置** - 密码可能已被修改
5. **URL编码问题** - 特殊字符需要转义

---

## 🔧 修复方案

### 方案 A: 验证并重置数据库密码（推荐）

如果你有 MySQL 管理员权限，执行以下步骤：

#### 步骤 1: 本地连接到 MySQL（在服务器上）

```bash
# 以管理员身份连接
mysql -u root -p

# 输入当前密码（或空密码如果没有设置）
```

#### 步骤 2: 重置 root 用户密码

```sql
-- 修改 root 用户密码并允许远程连接
ALTER USER 'root'@'localhost' IDENTIFIED BY '8pCNX3N3mzsHBLaW';
ALTER USER 'root'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';

-- 或者创建一个新用户用于应用
CREATE USER 'ai_stock'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';

-- 授予权限
GRANT ALL PRIVILEGES ON ai_stock.* TO 'ai_stock'@'%';
GRANT ALL PRIVILEGES ON ai_stock.* TO 'root'@'%';

-- 刷新权限
FLUSH PRIVILEGES;
```

#### 步骤 3: 验证连接

```bash
mysql -h 122.152.213.87 -u root -p ai_stock
```

---

### 方案 B: 使用 URL 编码的密码

如果密码包含特殊字符，需要进行 URL 编码。

**原始密码**: `8pCNX3N3mzsHBLaW`

**对应的 URL 编码**: `8pCNX3N3mzsHBLaW` (这个密码无需编码)

**修改 .env 文件**:

```bash
# 原始格式
DATABASE_URL=mysql+aiomysql://root:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock

# 如果密码中有 @ # % 等特殊字符，需要编码
# 例如: 密码是 "pass@word123"
# 编码后: "pass%40word123"
DATABASE_URL=mysql+aiomysql://root:pass%40word123@122.152.213.87:3306/ai_stock
```

---

### 方案 C: 使用不同的用户名

某些系统可能不允许 root 用户远程连接。

```bash
# 修改 .env 使用 ai_stock 用户
DATABASE_URL=mysql+aiomysql://ai_stock:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock
```

---

### 方案 D: 临时使用 SQLite（快速修复）

如果 MySQL 短期无法修复，可以切换到 SQLite：

#### 步骤 1: 安装 SQLAlchemy SQLite 驱动

```bash
pip install sqlalchemy
```

#### 步骤 2: 修改 .env

```bash
# 使用 SQLite 替代 MySQL
DATABASE_URL=sqlite+aiosqlite:///./ai_stock.db
```

#### 步骤 3: 重启应用

```bash
python -m uvicorn app.main:app --reload
```

**优点**:
- 无需 MySQL 服务器
- 快速测试
- 本地数据库

**缺点**:
- 不适合生产环境
- 只能单机使用
- 并发能力弱

---

## 🔐 密码安全建议

当修复数据库后，建议：

1. **设置强密码**:
```sql
ALTER USER 'root'@'%' IDENTIFIED BY 'SecurePassword2024!@#';
```

2. **创建专用用户**:
```sql
CREATE USER 'app_user'@'%' IDENTIFIED BY 'AppPassword123!@#';
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_stock.* TO 'app_user'@'%';
```

3. **限制访问 IP**:
```sql
-- 只允许特定 IP 访问
CREATE USER 'app_user'@'192.168.1.100' IDENTIFIED BY 'password';
```

---

## 📝 完整的修复步骤清单

- [ ] **第一步**: 确认 MySQL 服务器运行正常
- [ ] **第二步**: 验证 root 用户是否存在
- [ ] **第三步**: 确认 root 用户密码
- [ ] **第四步**: 检查 root 用户是否有 '%' (远程) 权限
- [ ] **第五步**: 修改 .env 文件中的 DATABASE_URL
- [ ] **第六步**: 重启 FastAPI 应用
- [ ] **第七步**: 测试数据库连接

---

## 🧪 测试数据库连接

### 方法 1: Python 脚本测试

```python
import pymysql

conn = pymysql.connect(
    host="122.152.213.87",
    user="root",
    password="8pCNX3N3mzsHBLaW",
    database="ai_stock"
)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM stocks")
count = cursor.fetchone()[0]
print(f"Stock count: {count}")

conn.close()
```

### 方法 2: 命令行测试

```bash
mysql -h 122.152.213.87 -u root -p8pCNX3N3mzsHBLaW ai_stock -e "SELECT COUNT(*) FROM stocks;"
```

### 方法 3: 通过 Python 检查表结构

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import inspect

async def check_db():
    engine = create_async_engine("mysql+aiomysql://root:8pCNX3N3mzsHBLaW@122.152.213.87:3306/ai_stock")

    async with engine.connect() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        print(f"Tables: {tables}")

asyncio.run(check_db())
```

---

## 🚨 常见问题

### Q1: "Access denied for user 'root'"
**A**: 密码错误或用户不存在。检查：
- 密码是否正确输入
- 用户是否在 MySQL 中存在
- 用户是否有远程访问权限

### Q2: "Can't connect to MySQL server"
**A**: 网络或端口问题。检查：
- MySQL 服务是否运行
- 防火墙是否允许 3306 端口
- IP 地址和端口是否正确

### Q3: "Unknown database 'ai_stock'"
**A**: 数据库不存在。执行：
```sql
CREATE DATABASE ai_stock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Q4: "Table doesn't exist"
**A**: 初始化数据库表。执行 schema.sql：
```bash
mysql -h 122.152.213.87 -u root -p < database/schema.sql
```

---

## 🔄 快速修复命令

如果你有 SSH 访问权限，可以在服务器上执行：

```bash
# 进入 MySQL
mysql -u root -p

# 执行这些命令
mysql> ALTER USER 'root'@'%' IDENTIFIED BY '8pCNX3N3mzsHBLaW';
mysql> GRANT ALL PRIVILEGES ON ai_stock.* TO 'root'@'%';
mysql> FLUSH PRIVILEGES;
mysql> QUIT;

# 重启 MySQL 服务
service mysql restart
```

---

## 📞 获取更多帮助

如果以上方案都不工作，请检查：

1. **MySQL 错误日志**:
```bash
tail -f /var/log/mysql/error.log
```

2. **MySQL 状态**:
```bash
mysql> SHOW GRANTS FOR 'root'@'%';
mysql> SELECT user, host FROM mysql.user;
```

3. **网络连接**:
```bash
telnet 122.152.213.87 3306
ping 122.152.213.87
```

---

## ✅ 验证修复成功

修复后，执行以下命令验证：

```bash
# 1. 查看数据库内容
curl http://127.0.0.1:8000/api/oversold?date=20251224

# 2. 查看单只股票缠论分析
curl http://127.0.0.1:8000/api/chan-data?ts_code=000001.SZ

# 3. 运行批量分析
python analyze_all_stocks.py
```

预期结果：
- ✅ 返回实际数据（不再报 "数据库连接失败"）
- ✅ 股票列表正常显示
- ✅ 缠论分析正常执行

---

**最后更新**: 2025-12-24
**状态**: 需要用户操作修复
