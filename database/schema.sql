-- 股票复盘数据库结构

CREATE DATABASE IF NOT EXISTS stock_review DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stock_review;

-- 股票基础信息表
CREATE TABLE stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    name VARCHAR(50) NOT NULL COMMENT '股票名称',
    industry VARCHAR(50) COMMENT '所属行业',
    market VARCHAR(20) COMMENT '市场类型',
    list_date DATE COMMENT '上市日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ts_code (ts_code),
    INDEX idx_industry (industry)
) COMMENT '股票基础信息';

-- 日线行情表
CREATE TABLE daily_quotes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(10,2) COMMENT '开盘价',
    high DECIMAL(10,2) COMMENT '最高价',
    low DECIMAL(10,2) COMMENT '最低价',
    close DECIMAL(10,2) COMMENT '收盘价',
    vol BIGINT COMMENT '成交量(手)',
    amount DECIMAL(20,2) COMMENT '成交额(千元)',
    pct_chg DECIMAL(10,2) COMMENT '涨跌幅',
    UNIQUE KEY uk_code_date (ts_code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_vol (trade_date, vol DESC)
) COMMENT '日线行情';

-- 技术指标表
CREATE TABLE technical_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    rsi_6 DECIMAL(10,2) COMMENT 'RSI(6)',
    rsi_12 DECIMAL(10,2) COMMENT 'RSI(12)',
    macd DECIMAL(10,4) COMMENT 'MACD',
    macd_signal DECIMAL(10,4) COMMENT 'MACD信号线',
    macd_hist DECIMAL(10,4) COMMENT 'MACD柱',
    k DECIMAL(10,2) COMMENT 'KDJ-K',
    d DECIMAL(10,2) COMMENT 'KDJ-D',
    j DECIMAL(10,2) COMMENT 'KDJ-J',
    boll_upper DECIMAL(10,2) COMMENT '布林上轨',
    boll_mid DECIMAL(10,2) COMMENT '布林中轨',
    boll_lower DECIMAL(10,2) COMMENT '布林下轨',
    UNIQUE KEY uk_code_date (ts_code, trade_date),
    INDEX idx_rsi (trade_date, rsi_6)
) COMMENT '技术指标';

-- 行业资金流向表
CREATE TABLE industry_flow (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    industry VARCHAR(50) NOT NULL COMMENT '行业名称',
    net_inflow DECIMAL(20,2) COMMENT '净流入(万)',
    buy_amount DECIMAL(20,2) COMMENT '买入金额',
    sell_amount DECIMAL(20,2) COMMENT '卖出金额',
    UNIQUE KEY uk_date_industry (trade_date, industry),
    INDEX idx_inflow (trade_date, net_inflow DESC)
) COMMENT '行业资金流向';

-- 复盘记录表
CREATE TABLE review_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    content TEXT COMMENT '复盘笔记',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trade_date (trade_date)
) COMMENT '复盘记录';
