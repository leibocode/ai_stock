<?php
declare(strict_types=1);

namespace app\service;

class TushareService
{
    protected $token = 'b3c61258053dc770e7873776a4ae9f1b30fc9362f43f46c0f6ddbe08';
    protected $apiUrl = 'http://api.tushare.pro';
    protected $dataPath;

    public function __construct()
    {
        $this->dataPath = __DIR__ . '/../../data/';
        if (!is_dir($this->dataPath)) {
            mkdir($this->dataPath, 0755, true);
        }
    }

    protected function call(string $apiName, array $params = [], string $fields = ''): array
    {
        $postData = [
            'api_name' => $apiName,
            'token' => $this->token,
            'params' => $params,
            'fields' => $fields,
        ];

        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $this->apiUrl,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($postData),
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        ]);
        $result = curl_exec($ch);
        curl_close($ch);

        if (!$result) return [];
        $data = json_decode($result, true);
        if (empty($data['data']['items'])) return [];

        $fields = $data['data']['fields'] ?? [];
        $items = $data['data']['items'] ?? [];
        $result = [];
        foreach ($items as $item) {
            $row = [];
            foreach ($fields as $i => $field) {
                $row[$field] = $item[$i] ?? null;
            }
            $result[] = $row;
        }
        return $result;
    }

    public function crawlDaily(string $date): array
    {
        $result = [
            'date' => $date,
            'crawl_time' => date('Y-m-d H:i:s'),
            'source' => 'tushare',
            'limit_up_down' => $this->getLimitUpDown($date),
            'north_flow' => $this->getNorthFlow($date),
            'dragon_tiger' => $this->getDragonTiger($date),
            'market_emotion' => $this->getMarketEmotion($date),
        ];

        $filename = $this->dataPath . "tushare_{$date}.json";
        file_put_contents($filename, json_encode($result, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        return $result;
    }

    protected function getLimitUpDown(string $date): array
    {
        $limitUp = $this->call('limit_list_d', ['trade_date' => $date, 'limit_type' => 'U'], 
            'ts_code,name,close,pct_chg,fd_amount,first_time,last_time,open_times,limit_times');
        $limitDown = $this->call('limit_list_d', ['trade_date' => $date, 'limit_type' => 'D'], 
            'ts_code,name,close,pct_chg,fd_amount');

        $upList = [];
        foreach ($limitUp as $item) {
            $upList[] = [
                'code' => substr($item['ts_code'] ?? '', 0, 6),
                'name' => $item['name'] ?? '',
                'price' => $item['close'] ?? 0,
                'pct_chg' => $item['pct_chg'] ?? 0,
                'amount' => round(($item['fd_amount'] ?? 0) / 10000, 2),
                'first_time' => $item['first_time'] ?? '',
                'open_times' => $item['open_times'] ?? 0,
                'continuous' => $item['limit_times'] ?? 1,
                'reason' => '',
            ];
        }

        $downList = [];
        foreach ($limitDown as $item) {
            $downList[] = [
                'code' => substr($item['ts_code'] ?? '', 0, 6),
                'name' => $item['name'] ?? '',
                'price' => $item['close'] ?? 0,
                'pct_chg' => $item['pct_chg'] ?? 0,
                'amount' => round(($item['fd_amount'] ?? 0) / 10000, 2),
            ];
        }

        return [
            'limit_up' => $upList, 'limit_up_count' => count($upList),
            'limit_down' => $downList, 'limit_down_count' => count($downList),
        ];
    }

    protected function getNorthFlow(string $date): array
    {
        $data = $this->call('moneyflow_hsgt', ['trade_date' => $date], 'hgt,sgt,north_money');
        $result = ['hk_to_sh' => 0, 'hk_to_sz' => 0, 'total' => 0, 'top_holdings' => []];
        if (!empty($data[0])) {
            $result['hk_to_sh'] = round(($data[0]['hgt'] ?? 0) / 100, 2);
            $result['hk_to_sz'] = round(($data[0]['sgt'] ?? 0) / 100, 2);
            $result['total'] = round(($data[0]['north_money'] ?? 0) / 100, 2);
        }
        return $result;
    }

    protected function getDragonTiger(string $date): array
    {
        $data = $this->call('top_list', ['trade_date' => $date], 
            'ts_code,name,close,pct_change,l_sell,l_buy,net_amount,reason');
        $list = [];
        foreach ($data as $item) {
            $list[] = [
                'code' => substr($item['ts_code'] ?? '', 0, 6),
                'name' => $item['name'] ?? '',
                'pct_chg' => $item['pct_change'] ?? 0,
                'reason' => $item['reason'] ?? '',
                'buy_amount' => round(($item['l_buy'] ?? 0) / 10000, 2),
                'sell_amount' => round(($item['l_sell'] ?? 0) / 10000, 2),
                'net_amount' => round(($item['net_amount'] ?? 0) / 10000, 2),
            ];
        }
        return $list;
    }

    protected function getMarketEmotion(string $date): array
    {
        $data = $this->call('daily', ['trade_date' => $date], 'ts_code,pct_chg');
        $upCount = 0; $downCount = 0; $flatCount = 0;
        foreach ($data as $item) {
            $chg = $item['pct_chg'] ?? 0;
            if ($chg > 0) $upCount++;
            elseif ($chg < 0) $downCount++;
            else $flatCount++;
        }
        $total = $upCount + $downCount;
        $upRatio = $total > 0 ? round($upCount / $total * 100, 1) : 0;
        $level = '中性';
        if ($upRatio >= 70) $level = '极度贪婪';
        elseif ($upRatio >= 55) $level = '贪婪';
        elseif ($upRatio >= 45) $level = '中性';
        elseif ($upRatio >= 30) $level = '恐惧';
        else $level = '极度恐惧';
        
        return ['up_count' => $upCount, 'down_count' => $downCount, 'flat_count' => $flatCount, 
                'up_ratio' => $upRatio, 'emotion_level' => $level];
    }

    public function getData(string $date): ?array
    {
        $filename = $this->dataPath . "tushare_{$date}.json";
        if (file_exists($filename)) {
            return json_decode(file_get_contents($filename), true);
        }
        return null;
    }
}
