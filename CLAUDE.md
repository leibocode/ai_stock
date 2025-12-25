# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于情绪周期理论的A股复盘分析系统，整合东方财富、同花顺、Tushare数据，提供多维度选股和市场分析。

## 常用命令

### 后端 (ThinkPHP 6)
```bash
cd backend
composer install              # 安装依赖
php think run                 # 启动开发服务器
php -S localhost:8000 -t public  # 备选启动方式
```

### 前端 (Vue 3 + Vite)
```bash
cd frontend
npm install                   # 安装依赖
npm run dev                   # 启动开发服务器
npm run build                 # 构建生产版本
```

### 数据库
```bash
mysql -u root -p < database/schema.sql  # 初始化数据库结构
```

## 架构设计

### 后端核心文件
- `backend/app/controller/Index.php` - API控制器，所有接口入口
- `backend/app/service/EastmoneyCrawler.php` - 东财数据爬虫（龙虎榜、北向资金、板块数据）
- `backend/app/service/IndicatorService.php` - 技术指标计算（RSI、MACD、KDJ、缠论）
- `backend/app/service/TushareService.php` - Tushare API封装
- `backend/services/` - 独立服务模块（Database.php, IndicatorService.php, TushareService.php）
- `backend/route/app.php` - 路由配置
- `backend/api/index.php` - API入口

### 前端核心文件
- `frontend/src/App.vue` - 主组件，包含所有UI和业务逻辑
- `frontend/src/api/` - API接口封装

### 数据库表
- `stocks` - 股票基础信息
- `daily_quotes` - 日线行情
- `technical_indicators` - 技术指标（RSI、MACD、KDJ、布林带）
- `industry_flow` - 行业资金流向
- `review_records` - 复盘记录
- 缠论表：`chan_fractal`(分型)、`chan_bi`(笔)、`chan_segment`(线段)、`chan_hub`(中枢)

## API路由分组

### 行情数据
`/api/volume-top`, `/api/bottom-volume`, `/api/top-volume`, `/api/counter-trend`, `/api/limit-up`, `/api/limit-down`

### 技术指标
`/api/oversold`, `/api/kdj-bottom`, `/api/macd-golden`, `/api/breakout`, `/api/gap-up`, `/api/gap-down`

### 资金流向
`/api/industry-hot`, `/api/north-buy`, `/api/margin-buy`, `/api/dragon-tiger`

### 缠论
`/api/chan-bottom-diverge`, `/api/chan-top-diverge`, `/api/chan-first-buy`, `/api/chan-second-buy`, `/api/chan-third-buy`, `/api/chan-hub-shake`, `/api/calc-chan`

### 复盘与同步
`GET/POST /api/review`, `/api/review-history`, `/api/sync-stocks`, `/api/sync-daily`, `/api/calc-indicators`, `/api/crawl-eastmoney`

## 业务逻辑

### 情绪周期
市场分为五阶段循环：高潮期 → 退潮期 → 冰点期 → 回暖期 → 修复期。判断指标：涨停数(40%)、连板高度(20%)、涨跌比(20%)、炸板率(20%)。

### 多指标共振
跟踪12项指标（涨停、连板、龙头、弱转强、北向、放量、MACD金叉、KDJ底部、突破等），命中≥3个为重点关注。

### 龙头评分
评分维度：连板数(0-50)、封板时间(0-20)、开板次数(0-20)、成交额(0-10)、换手率(0-10)。

## 配置文件

后端需配置 `.env` 文件，包含数据库连接和 Tushare Token。

## 数据来源

- Tushare：股票行情、技术指标
- 东方财富：龙虎榜、北向资金、板块数据
- 同花顺：涨停池、连板数据
