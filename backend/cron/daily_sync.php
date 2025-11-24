<?php
// 每日数据同步脚本
// 建议在收盘后运行：0 16 * * 1-5 php /path/to/daily_sync.php

require_once __DIR__ . '/../services/TushareService.php';
require_once __DIR__ . '/../services/IndicatorService.php';

$date = $argv[1] ?? date('Ymd');

echo "开始同步 {$date} 数据...\n";

$tushare = new TushareService();
$indicator = new IndicatorService();
$db = Database::getInstance();

// 1. 同步日线数据
$count = $tushare->fetchDailyQuotes($date);
echo "同步日线数据: {$count} 条\n";

// 2. 计算技术指标
$stocks = $db->query(
    "SELECT DISTINCT ts_code FROM daily_quotes WHERE trade_date = ?",
    [$date]
);

$calcCount = 0;
foreach ($stocks as $stock) {
    $history = $tushare->getStockHistory($stock['ts_code'], 100);
    if ($indicator->calculate($stock['ts_code'], $history)) {
        $calcCount++;
    }
}
echo "计算指标: {$calcCount} 只\n";

echo "同步完成!\n";
