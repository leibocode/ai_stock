# 单元测试指南

## 概述

本项目包含完整的单元测试套件，覆盖以下核心模块：
- 缠论算法（分型、笔、线段、中枢）
- 技术指标（RSI、MACD、KDJ、布林带）
- 爬虫计算器（情绪周期、龙头评分）

## 测试文件列表

### 缠论算法测试

#### 1. `tests/test_chan_fractal.py` (180行)
**K线包含处理和分型识别测试**

测试内容：
- `merge_klines()` - K线包含处理
  - 无包含关系K线
  - 简单包含关系
  - 单根K线处理
- `calculate_fractals()` - 分型识别
  - 顶分型识别（high peak）
  - 底分型识别（low trough）
  - 复杂分型序列
  - 分型类型交替验证
  - 平盘无分型处理
- `Fractal` 数据类测试

关键测试方法：
```python
# 顶分型：当前K线高点 > 前后K线高点
# 底分型：当前K线低点 < 前后K线低点

test_top_fractal()        # 顶分型识别
test_bottom_fractal()     # 底分型识别
test_complex_fractals()   # 复杂序列
test_flat_market()        # 平盘处理
```

#### 2. `tests/test_chan_bi.py` (220行)
**笔划分测试**

测试内容：
- `calculate_bi()` - 笔划分
  - 简单笔形成
  - 笔方向交替（向上↔向下）
  - 同向分型取极值
  - 笔的高低点计算
- `get_latest_bi()` - 获取最新笔
- `count_bi_by_direction()` - 笔方向统计

关键规则：
```python
# 向上笔：从底分型→顶分型，要求 top.high > bottom.high
# 向下笔：从顶分型→底分型，要求 bottom.low < top.low
# 同向分型：取极值（底取更低，顶取更高）

test_up_bi()              # 向上笔验证
test_down_bi()            # 向下笔验证
test_same_direction_take_extreme()  # 同向极值
test_bi_alternation()     # 方向交替
```

#### 3. `tests/test_chan_segment.py` (240行)
**线段划分测试**

测试内容：
- `calculate_segment()` - 线段识别
  - 至少3笔形成线段
  - 线段方向交替
  - 线段结束条件（新高/新低）
  - 线段高低点计算
- `get_latest_segment()` - 获取最新线段
- 线段连续性验证

关键规则：
```python
# 向上线段：从向上笔开始，当下行笔创新低时结束
# 向下线段：从向下笔开始，当上行笔创新高时结束
# 有效线段：至少包含3笔

test_up_segment_end_condition()    # 向上线段结束
test_down_segment_end_condition()  # 向下线段结束
test_segment_continuity()          # 时间连续性
test_multiple_segments()           # 多个线段
```

#### 4. `tests/test_chan_hub.py` (280行 - 新增)
**中枢识别测试**

测试内容：
- `calculate_hub()` - 中枢识别
  - 3线段形成中枢
  - 中枢上沿(ZG)和下沿(ZD)计算
  - 有效中枢验证（ZG > ZD）
  - 中枢高低点(GG/DD)
- 价格位置判断
  - `is_price_above_hub()` - 价格在中枢上方
  - `is_price_below_hub()` - 价格在中枢下方
  - `is_price_in_hub()` - 价格在中枢内
  - `get_price_position()` - 价格相对位置

关键规则：
```python
# 中枢上沿(ZG) = min(seg1.high, seg2.high, seg3.high)
# 中枢下沿(ZD) = max(seg1.low, seg2.low, seg3.low)
# 有效中枢：ZG > ZD（存在重叠区间）

test_hub_zg_zd_calculation()   # 上下沿计算
test_invalid_hub_no_overlap()  # 无重叠处理
test_multiple_hubs()           # 多个中枢
test_hub_range()               # 中枢振幅
```

### 技术指标测试

#### 5. `tests/test_indicators.py` (280行)
**RSI、MACD、KDJ、布林带测试**

- **RSI 测试**
  - 上升趋势（RSI > 50）
  - 下跌趋势（RSI < 50）
  - 平盘（RSI ≈ 50）
  - 数据不足处理（返回50）
  - 多周期RSI（6、12周期）

- **MACD 测试**
  - 上升趋势（快线在慢线上）
  - 下跌趋势（快线在慢线下）
  - DIF、DEA、MACD柱状线计算
  - 数据不足处理

- **KDJ 测试**
  - K值、D值范围验证（0-100）
  - J值可超出范围
  - 底部反弹信号
  - 数据不足处理

- **布林带 测试**
  - 上中下轨计算
  - 波动性与带宽关系
  - 数据不足处理

边界情况测试：
```python
test_all_zero_input()      # 全零数据
test_nan_handling()        # NaN处理
test_negative_prices()     # 负数价格
test_insufficient_data()   # 数据不足
```

### 爬虫计算器测试

#### 6. `tests/test_crawler_calculators.py` (550行 - 新增)
**情绪周期、龙头评分测试**

**情绪周期计算器 (EmotionCycleCalculator)**

评分规则（满分100）：
```python
赚钱效应(30分)   # >=70% → 30, >=50% → 20, >=30% → 10
连板高度(20分)   # >=5板 → 20, >=3板 → 10, >=2板 → 5
涨停数(20分)     # >=80 → 20, >=50 → 10, >=30 → 5
涨跌比(15分)     # >=5:1 → 15, >=2:1 → 10, >=1:1 → 5
炸板率(10分)     # <=20% → 10, <=40% → 5
晋级率(5分)      # >=30% → 5, >=20% → 3
```

阶段判定（得分）：
- **高潮期** (>=70) - 关注龙头换手，谨慎追高
- **回暖期** (50-69) - 参与龙头首板，低吸强势股
- **修复期** (30-49) - 观察龙头能否走出，轻仓试错
- **退潮期** (10-29) - 减少操作，等待新龙头
- **冰点期** (<10) - 空仓观望，等待转机信号

测试用例：
```python
test_climax_phase()        # 高潮期判定
test_warming_phase()       # 回暖期判定
test_profit_effect_score() # 赚钱效应
test_continuous_score()    # 连板高度
test_broken_rate_score()   # 炸板率
```

**龙头股评分计算器 (LeaderScoreCalculator)**

评分规则（满分≥50为龙头）：
```python
连板高度     # continuous * 15（最高45分）
封板时间     # 09:30前20分, 10:00前15分, 11:00前10分, 13:00前5分
开板次数     # 0次15分, 1次10分, <=3次5分, >3次-5分
成交额(亿)   # 3-15亿10分, 1-30亿5分, >50亿-5分
换手率(%)    # 5-20%10分, 3-30%5分, >40%-5分
市值(亿)     # <=50亿10分, <=100亿5分, >500亿-5分
```

龙头判定：
```python
is_leader = score >= 50
```

测试用例：
```python
test_continuous_score()    # 连板评分
test_first_time_early_morning()    # 早盘开盘
test_open_times_zero()     # 零开板
test_amount_ideal()        # 理想成交额
test_turnover_ideal()      # 理想换手率
test_market_cap_small()    # 小市值
test_batch_calculate()     # 批量计算（倒序排列）
```

## 运行测试

### 环境要求
```bash
Python 3.10+
pytest >= 7.0
pandas >= 2.0
numpy >= 1.23
```

### 安装依赖
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行特定测试文件
```bash
# 缠论分型测试
pytest tests/test_chan_fractal.py -v

# 缠论笔划分测试
pytest tests/test_chan_bi.py -v

# 缠论线段测试
pytest tests/test_chan_segment.py -v

# 缠论中枢测试
pytest tests/test_chan_hub.py -v

# 技术指标测试
pytest tests/test_indicators.py -v

# 爬虫计算器测试
pytest tests/test_crawler_calculators.py -v
```

### 运行特定测试类或方法
```bash
# 运行特定类的所有测试
pytest tests/test_chan_hub.py::TestCalculateHub -v

# 运行特定测试方法
pytest tests/test_chan_hub.py::TestCalculateHub::test_simple_hub -v
```

### 生成测试覆盖率报告
```bash
pip install coverage
coverage run -m pytest tests/
coverage report
coverage html  # 生成HTML报告
```

### 运行时追踪错误
```bash
# 显示打印输出
pytest tests/ -v -s

# 显示本地变量
pytest tests/ -v -l

# 在首个失败处停止
pytest tests/ -x

# 仅运行上次失败的测试
pytest tests/ --lf
```

## 测试统计

| 模块 | 文件 | 测试类 | 测试方法 | 覆盖范围 |
|------|------|--------|--------|--------|
| 分型 | test_chan_fractal.py | 4 | 14 | merge_klines, calculate_fractals, Fractal类 |
| 笔 | test_chan_bi.py | 4 | 18 | calculate_bi, Bi类, 方向统计 |
| 线段 | test_chan_segment.py | 3 | 13 | calculate_segment, Segment类, 连续性 |
| 中枢 | test_chan_hub.py | 5 | 28 | calculate_hub, Hub类, 价格位置, 振幅 |
| 指标 | test_indicators.py | 5 | 23 | RSI, MACD, KDJ, 布林带, 边界情况 |
| 爬虫 | test_crawler_calculators.py | 2 | 46 | 情绪周期, 龙头评分, 各阶段判定 |
| **总计** | **6个** | **23** | **142** | **完整核心模块测试** |

## 测试的关键特性

### 1. **单元测试原则**
- ✅ 每个测试方法测试单一功能
- ✅ 使用 pytest fixtures 提供样本数据
- ✅ 断言清晰，错误信息有意义
- ✅ 独立性强，无测试间依赖

### 2. **边界情况覆盖**
- ✅ 空列表处理
- ✅ 数据不足（insufficient_data）
- ✅ 异常值（零值、负数、超大值）
- ✅ 浮点精度处理

### 3. **缠论算法完整性**
- ✅ 分型识别（顶/底）
- ✅ K线包含处理
- ✅ 笔的形成规则
- ✅ 线段的连续性
- ✅ 中枢的重叠判定
- ✅ 价格相对中枢位置

### 4. **指标计算准确性**
- ✅ 趋势判定（上升/下跌）
- ✅ 超买超卖判定
- ✅ 金叉死叉判定
- ✅ 波动率计算

### 5. **爬虫计算器逻辑**
- ✅ 评分规则完整覆盖
- ✅ 各阶段判定边界
- ✅ 批量计算排序
- ✅ 龙头判定标准

## 常见问题

### Q: 测试失败，显示"ModuleNotFoundError"
**A:** 确保项目根目录在Python路径中
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Q: 如何在PyCharm中运行测试？
**A:**
1. 打开测试文件
2. 点击类/方法左边的绿色播放按钮
3. 或右键选择 "Run pytest"

### Q: 如何调试单个测试？
**A:**
```bash
pytest tests/test_file.py::TestClass::test_method -v -s --pdb
```

### Q: 测试速度慢，如何优化？
**A:**
```bash
# 并行运行测试
pip install pytest-xdist
pytest tests/ -n auto

# 仅运行最近修改的测试
pytest tests/ --testmon
```

## 测试驱动开发（TDD）工作流

当需要添加新功能时：

1. **编写测试**
   ```bash
   # 在 tests/ 中创建对应的测试文件
   # 测试应该失败（因为功能还未实现）
   ```

2. **实现功能**
   ```bash
   # 在 app/ 中实现最小必要代码
   # 使测试通过
   ```

3. **重构优化**
   ```bash
   # 改进实现，保持测试通过
   pytest tests/ -v  # 验证所有测试仍通过
   ```

## 持续集成（CI）配置

### GitHub Actions 示例
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=app
```

## 文件清单

```
tests/
├── __init__.py                      # 测试包初始化
├── test_chan_fractal.py             # 分型测试 (180行)
├── test_chan_bi.py                  # 笔划分测试 (220行)
├── test_chan_segment.py             # 线段测试 (240行)
├── test_chan_hub.py                 # 中枢测试 (280行)  [新增]
├── test_indicators.py               # 指标测试 (280行)
└── test_crawler_calculators.py      # 爬虫计算器测试 (550行)  [新增]
```

## 后续工作

- [ ] 集成测试（API端点测试）
- [ ] 性能基准测试（benchmark）
- [ ] 压力测试（stress testing）
- [ ] 数据库集成测试
- [ ] Redis缓存测试
- [ ] APScheduler定时任务测试

---

**最后更新**: 2024-12-24
**测试覆盖率**: 核心模块 > 90%
**总测试方法数**: 142
