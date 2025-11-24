<?php
// 简化版API入口 - 不依赖ThinkPHP框架

error_reporting(E_ALL);
ini_set('display_errors', 0);

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// 加载服务类
require_once __DIR__ . '/../app/service/EastmoneyCrawler.php';
require_once __DIR__ . '/../app/service/TushareService.php';

// 简单路由
$uri = $_SERVER['REQUEST_URI'];
$path = parse_url($uri, PHP_URL_PATH);
$path = str_replace('/api/', '', $path);
$path = trim($path, '/');

try {
    $result = handleRequest($path);
    echo json_encode(['code' => 0, 'data' => $result], JSON_UNESCAPED_UNICODE);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['code' => 1, 'msg' => $e->getMessage()], JSON_UNESCAPED_UNICODE);
}

function handleRequest(string $action) {
    $date = $_GET['date'] ?? date('Ymd');

    // 东方财富/同花顺数据接口
    if (in_array($action, ['crawl-eastmoney', 'eastmoney-data', 'eastmoney-list'])) {
        $crawler = new \app\service\EastmoneyCrawler();

        switch ($action) {
            case 'crawl-eastmoney':
                return $crawler->crawlDaily($date);
            case 'eastmoney-data':
                $data = $crawler->getData($date);
                if (!$data) {
                    throw new Exception('数据不存在，请先爬取');
                }
                return $data;
            case 'eastmoney-list':
                return $crawler->getDataList();
        }
    }

    // Tushare数据接口
    if (in_array($action, ['crawl-tushare', 'tushare-data'])) {
        $tushare = new \app\service\TushareService();

        switch ($action) {
            case 'crawl-tushare':
                return $tushare->crawlDaily($date);
            case 'tushare-data':
                $data = $tushare->getData($date);
                if (!$data) {
                    throw new Exception('数据不存在，请先爬取');
                }
                return $data;
        }
    }

    // 其他接口返回空数据（需要数据库支持）
    switch ($action) {
        case 'volume-top':
        case 'oversold':
        case 'kdj-bottom':
        case 'macd-golden':
        case 'bottom-volume':
        case 'industry-hot':
        case 'counter-trend':
        case 'limit-up':
        case 'limit-down':
        case 'dragon-tiger':
        case 'north-buy':
        case 'margin-buy':
        case 'breakout':
        case 'top-volume':
        case 'gap-up':
        case 'gap-down':
        case 'industry-gap':
            return []; // 需要数据库，暂返回空

        case 'market-index':
            return [
                ['ts_code' => '000001.SH', 'close' => 0, 'pct_chg' => 0],
                ['ts_code' => '399001.SZ', 'close' => 0, 'pct_chg' => 0],
                ['ts_code' => '399006.SZ', 'close' => 0, 'pct_chg' => 0],
            ];

        case 'market-stats':
            return ['limitUp' => 0, 'limitDown' => 0, 'northFlow' => 0];

        case 'review':
            if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                return ['success' => true];
            }
            return null;

        case 'review-history':
            return [];

        case 'sync-daily':
            return ['synced' => 0, 'date' => $date];

        case 'calc-indicators':
            return ['calculated' => 0];

        default:
            throw new Exception("未知接口: {$action}");
    }
}
