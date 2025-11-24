<?php
// API入口

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once __DIR__ . '/../services/Database.php';
require_once __DIR__ . '/../services/TushareService.php';
require_once __DIR__ . '/../services/IndicatorService.php';

$path = $_GET['action'] ?? '';
$method = $_SERVER['REQUEST_METHOD'];

try {
    $result = handleRequest($path, $method);
    echo json_encode(['code' => 0, 'data' => $result]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['code' => 1, 'msg' => $e->getMessage()]);
}

function handleRequest(string $action, string $method) {
    $tushare = new TushareService();
    $indicator = new IndicatorService();
    $db = Database::getInstance();

    switch ($action) {
        // 获取成交量TOP50
        case 'volume-top':
            $date = $_GET['date'] ?? date('Ymd');
            return $tushare->getVolumeTop50($date);

        // 获取RSI超卖股票
        case 'oversold':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getOversoldStocks($date);

        // 获取KDJ见底股票
        case 'kdj-bottom':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getKDJBottomStocks($date);

        // 获取MACD金叉股票
        case 'macd-golden':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getMACDGoldenCross($date);

        // 获取底部放量股票
        case 'bottom-volume':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getBottomVolumeStocks($date);

        // 获取行业异动
        case 'industry-hot':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getIndustryHotStocks($date);

        // 获取大盘指数
        case 'market-index':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getMarketIndex($date);

        // 获取逆势上涨
        case 'counter-trend':
            $date = $_GET['date'] ?? date('Ymd');
            return $indicator->getCounterTrendStocks($date);

        // 获取复盘记录
        case 'review':
            if ($method === 'GET') {
                $date = $_GET['date'] ?? date('Y-m-d');
                $records = $db->query(
                    "SELECT * FROM review_records WHERE trade_date = ?",
                    [$date]
                );
                return $records[0] ?? null;
            } else {
                $input = json_decode(file_get_contents('php://input'), true);
                $date = $input['date'] ?? date('Y-m-d');
                $content = $input['content'] ?? '';

                $db->execute(
                    "INSERT INTO review_records (trade_date, content) VALUES (?, ?)
                     ON DUPLICATE KEY UPDATE content = VALUES(content)",
                    [$date, $content]
                );
                return ['success' => true];
            }

        // 获取复盘历史列表
        case 'review-history':
            return $db->query(
                "SELECT trade_date, CONCAT(LEFT(content, 30), '...') as preview
                 FROM review_records
                 ORDER BY trade_date DESC
                 LIMIT 20"
            );

        // 同步股票列表
        case 'sync-stocks':
            $count = $tushare->fetchStockList();
            return ['synced' => $count];

        // 同步日线数据
        case 'sync-daily':
            $date = $_GET['date'] ?? date('Ymd');
            $count = $tushare->fetchDailyQuotes($date);
            return ['synced' => $count, 'date' => $date];

        // 计算指标
        case 'calc-indicators':
            $date = $_GET['date'] ?? date('Ymd');
            // 获取当日有行情的股票
            $stocks = $db->query(
                "SELECT DISTINCT ts_code FROM daily_quotes WHERE trade_date = ?",
                [$date]
            );

            $count = 0;
            foreach ($stocks as $stock) {
                $history = $tushare->getStockHistory($stock['ts_code'], 100);
                if ($indicator->calculate($stock['ts_code'], $history)) {
                    $count++;
                }
            }
            return ['calculated' => $count];

        default:
            throw new Exception("未知接口: {$action}");
    }
}
