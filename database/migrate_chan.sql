-- 缠论指标表迁移脚本
-- 执行命令: mysql -u root -p stock_review < database/migrate_chan.sql

USE stock_review;

-- 分型表（顶分型/底分型）
CREATE TABLE IF NOT EXISTS chan_fractal (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL COMMENT '分型中间K线日期',
    fractal_type TINYINT NOT NULL COMMENT '1:顶分型 -1:底分型',
    high DECIMAL(10,2) NOT NULL COMMENT '分型最高价',
    low DECIMAL(10,2) NOT NULL COMMENT '分型最低价',
    UNIQUE KEY uk_code_date (ts_code, trade_date),
    INDEX idx_type (ts_code, fractal_type, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '缠论分型';

-- 笔表
CREATE TABLE IF NOT EXISTS chan_bi (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL COMMENT '笔起点日期',
    end_date DATE NOT NULL COMMENT '笔终点日期',
    direction TINYINT NOT NULL COMMENT '1:向上笔 -1:向下笔',
    high DECIMAL(10,2) NOT NULL COMMENT '笔最高价',
    low DECIMAL(10,2) NOT NULL COMMENT '笔最低价',
    bi_index INT NOT NULL COMMENT '笔序号',
    UNIQUE KEY uk_code_index (ts_code, bi_index),
    INDEX idx_date (ts_code, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '缠论笔';

-- 线段表
CREATE TABLE IF NOT EXISTS chan_segment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL COMMENT '线段起点日期',
    end_date DATE NOT NULL COMMENT '线段终点日期',
    direction TINYINT NOT NULL COMMENT '1:向上线段 -1:向下线段',
    high DECIMAL(10,2) NOT NULL COMMENT '线段最高价',
    low DECIMAL(10,2) NOT NULL COMMENT '线段最低价',
    seg_index INT NOT NULL COMMENT '线段序号',
    UNIQUE KEY uk_code_index (ts_code, seg_index),
    INDEX idx_date (ts_code, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '缠论线段';

-- 中枢表
CREATE TABLE IF NOT EXISTS chan_hub (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL COMMENT '中枢起始日期',
    end_date DATE NOT NULL COMMENT '中枢结束日期',
    zg DECIMAL(10,2) NOT NULL COMMENT '中枢上沿(最低高点)',
    zd DECIMAL(10,2) NOT NULL COMMENT '中枢下沿(最高低点)',
    gg DECIMAL(10,2) NOT NULL COMMENT '中枢最高点',
    dd DECIMAL(10,2) NOT NULL COMMENT '中枢最低点',
    hub_index INT NOT NULL COMMENT '中枢序号',
    level TINYINT DEFAULT 1 COMMENT '中枢级别',
    UNIQUE KEY uk_code_index (ts_code, hub_index),
    INDEX idx_date (ts_code, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '缠论中枢';

SELECT '缠论表创建完成' AS result;
