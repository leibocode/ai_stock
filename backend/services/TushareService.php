<?php
// Tushare API服务

require_once __DIR__ . '/Database.php';

class TushareService {
    private $token;
    private $apiUrl;
    private $db;

    public function __construct() {
        $config = require __DIR__ . '/../config/tushare.php';
        $this->token = $config['token'];
        $this->apiUrl = $config['api_url'];
        $this->db = Database::getInstance();
    }

    // 调用Tushare API
    private function call(string $apiName, array $params = [], string $fields = ''): array {
        $data = [
            'api_name' => $apiName,
            'token' => $this->token,
            'params' => $params,
            'fields' => $fields,
        ];

        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $this->apiUrl,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_TIMEOUT => 30,
        ]);

        $response = curl_exec($ch);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new Exception("Tushare API错误: {$error}");
        }

        $result = json_decode($response, true);
        if (!isset($result['data'])) {
            throw new Exception("Tushare返回数据异常: " . ($result['msg'] ?? '未知错误'));
        }

        // 转换为关联数组
        $items = [];
        $fields = $result['data']['fields'];
        foreach ($result['data']['items'] as $item) {
            $items[] = array_combine($fields, $item);
        }

        return $items;
    }

    // 获取股票列表
    public function fetchStockList(): int {
        $data = $this->call('stock_basic', [
            'exchange' => '',
            'list_status' => 'L',
        ], 'ts_code,name,industry,market,list_date');

        $rows = [];
        foreach ($data as $item) {
            $rows[] = [
                'ts_code' => $item['ts_code'],
                'name' => $item['name'],
                'industry' => $item['industry'] ?? '',
                'market' => $item['market'] ?? '',
                'list_date' => $item['list_date'],
            ];
        }

        return $this->db->insertBatch('stocks', $rows);
    }

    // 获取日线行情
    public function fetchDailyQuotes(string $tradeDate): int {
        $data = $this->call('daily', [
            'trade_date' => $tradeDate,
        ], 'ts_code,trade_date,open,high,low,close,vol,amount,pct_chg');

        $rows = [];
        foreach ($data as $item) {
            $rows[] = [
                'ts_code' => $item['ts_code'],
                'trade_date' => $item['trade_date'],
                'open' => $item['open'],
                'high' => $item['high'],
                'low' => $item['low'],
                'close' => $item['close'],
                'vol' => $item['vol'],
                'amount' => $item['amount'],
                'pct_chg' => $item['pct_chg'],
            ];
        }

        $table = 'daily_quotes';
        $columns = implode(',', array_keys($rows[0]));
        $placeholders = '(' . implode(',', array_fill(0, count($rows[0]), '?')) . ')';
        $allPlaceholders = implode(',', array_fill(0, count($rows), $placeholders));

        $values = [];
        foreach ($rows as $row) {
            $values = array_merge($values, array_values($row));
        }

        $sql = "INSERT INTO {$table} ({$columns}) VALUES {$allPlaceholders}
                ON DUPLICATE KEY UPDATE
                open=VALUES(open),high=VALUES(high),low=VALUES(low),
                close=VALUES(close),vol=VALUES(vol),amount=VALUES(amount),pct_chg=VALUES(pct_chg)";

        return $this->db->execute($sql, $values);
    }

    // 获取成交量TOP50
    public function getVolumeTop50(string $tradeDate): array {
        return $this->db->query(
            "SELECT q.ts_code, s.name, s.industry, q.close, q.vol, q.amount, q.pct_chg
             FROM daily_quotes q
             JOIN stocks s ON q.ts_code = s.ts_code
             WHERE q.trade_date = ?
             ORDER BY q.vol DESC
             LIMIT 50",
            [$tradeDate]
        );
    }

    // 获取个股历史数据（用于计算指标）
    public function getStockHistory(string $tsCode, int $limit = 100): array {
        return $this->db->query(
            "SELECT trade_date, open, high, low, close, vol
             FROM daily_quotes
             WHERE ts_code = ?
             ORDER BY trade_date DESC
             LIMIT ?",
            [$tsCode, $limit]
        );
    }
}
