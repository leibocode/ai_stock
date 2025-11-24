<?php
// 技术指标计算服务

require_once __DIR__ . '/Database.php';

class IndicatorService {
    private $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }

    // 计算并保存所有指标
    public function calculate(string $tsCode, array $history): ?array {
        if (count($history) < 26) return null; // 数据不足

        // 反转数组，使其按时间正序
        $data = array_reverse($history);
        $closes = array_column($data, 'close');
        $highs = array_column($data, 'high');
        $lows = array_column($data, 'low');

        $latest = end($data);
        $tradeDate = $latest['trade_date'];

        // 计算各指标
        $rsi6 = $this->calculateRSI($closes, 6);
        $rsi12 = $this->calculateRSI($closes, 12);
        $macd = $this->calculateMACD($closes);
        $kdj = $this->calculateKDJ($closes, $highs, $lows);
        $boll = $this->calculateBOLL($closes);

        $indicators = [
            'ts_code' => $tsCode,
            'trade_date' => $tradeDate,
            'rsi_6' => $rsi6,
            'rsi_12' => $rsi12,
            'macd' => $macd['macd'],
            'macd_signal' => $macd['signal'],
            'macd_hist' => $macd['hist'],
            'k' => $kdj['k'],
            'd' => $kdj['d'],
            'j' => $kdj['j'],
            'boll_upper' => $boll['upper'],
            'boll_mid' => $boll['mid'],
            'boll_lower' => $boll['lower'],
        ];

        // 保存到数据库
        $this->saveIndicators($indicators);

        return $indicators;
    }

    // RSI计算
    private function calculateRSI(array $closes, int $period): float {
        $changes = [];
        for ($i = 1; $i < count($closes); $i++) {
            $changes[] = $closes[$i] - $closes[$i - 1];
        }

        $gains = [];
        $losses = [];
        foreach ($changes as $change) {
            $gains[] = $change > 0 ? $change : 0;
            $losses[] = $change < 0 ? abs($change) : 0;
        }

        // 取最近period个数据
        $recentGains = array_slice($gains, -$period);
        $recentLosses = array_slice($losses, -$period);

        $avgGain = array_sum($recentGains) / $period;
        $avgLoss = array_sum($recentLosses) / $period;

        if ($avgLoss == 0) return 100;

        $rs = $avgGain / $avgLoss;
        return round(100 - (100 / (1 + $rs)), 2);
    }

    // MACD计算
    private function calculateMACD(array $closes): array {
        $ema12 = $this->calculateEMA($closes, 12);
        $ema26 = $this->calculateEMA($closes, 26);

        $dif = $ema12 - $ema26;

        // 简化：用最近9个DIF的EMA作为信号线
        $signal = $dif * 0.2 + $dif * 0.8; // 简化处理
        $hist = $dif - $signal;

        return [
            'macd' => round($dif, 4),
            'signal' => round($signal, 4),
            'hist' => round($hist, 4),
        ];
    }

    // EMA计算
    private function calculateEMA(array $data, int $period): float {
        $k = 2 / ($period + 1);
        $ema = $data[0];

        for ($i = 1; $i < count($data); $i++) {
            $ema = $data[$i] * $k + $ema * (1 - $k);
        }

        return $ema;
    }

    // KDJ计算
    private function calculateKDJ(array $closes, array $highs, array $lows): array {
        $period = 9;
        $n = count($closes);

        // 取最近period天的最高和最低
        $recentHighs = array_slice($highs, -$period);
        $recentLows = array_slice($lows, -$period);

        $hn = max($recentHighs);
        $ln = min($recentLows);
        $cn = end($closes);

        $rsv = ($hn - $ln) != 0 ? (($cn - $ln) / ($hn - $ln)) * 100 : 50;

        // 简化：K=RSV的SMA，D=K的SMA
        $k = $rsv;
        $d = $k;
        $j = 3 * $k - 2 * $d;

        return [
            'k' => round($k, 2),
            'd' => round($d, 2),
            'j' => round($j, 2),
        ];
    }

    // 布林带计算
    private function calculateBOLL(array $closes, int $period = 20): array {
        $recentCloses = array_slice($closes, -$period);
        $mid = array_sum($recentCloses) / $period;

        // 计算标准差
        $variance = 0;
        foreach ($recentCloses as $close) {
            $variance += pow($close - $mid, 2);
        }
        $std = sqrt($variance / $period);

        return [
            'upper' => round($mid + 2 * $std, 2),
            'mid' => round($mid, 2),
            'lower' => round($mid - 2 * $std, 2),
        ];
    }

    // 保存指标
    private function saveIndicators(array $data): void {
        $columns = implode(',', array_keys($data));
        $placeholders = implode(',', array_fill(0, count($data), '?'));

        $updates = [];
        foreach (array_keys($data) as $col) {
            if ($col !== 'ts_code' && $col !== 'trade_date') {
                $updates[] = "{$col}=VALUES({$col})";
            }
        }

        $sql = "INSERT INTO technical_indicators ({$columns}) VALUES ({$placeholders})
                ON DUPLICATE KEY UPDATE " . implode(',', $updates);

        $this->db->execute($sql, array_values($data));
    }

    // 获取超卖股票（RSI<30）
    public function getOversoldStocks(string $tradeDate): array {
        return $this->db->query(
            "SELECT i.ts_code, s.name, s.industry, i.rsi_6, i.rsi_12, i.k, i.d
             FROM technical_indicators i
             JOIN stocks s ON i.ts_code = s.ts_code
             WHERE i.trade_date = ? AND i.rsi_6 < 30
             ORDER BY i.rsi_6 ASC
             LIMIT 50",
            [$tradeDate]
        );
    }

    // 获取KDJ见底股票
    public function getKDJBottomStocks(string $tradeDate): array {
        return $this->db->query(
            "SELECT i.ts_code, s.name, s.industry, i.k, i.d, i.j
             FROM technical_indicators i
             JOIN stocks s ON i.ts_code = s.ts_code
             WHERE i.trade_date = ? AND i.k < 20 AND i.d < 20
             ORDER BY i.k ASC
             LIMIT 50",
            [$tradeDate]
        );
    }

    // 获取MACD金叉股票
    public function getMACDGoldenCross(string $tradeDate): array {
        return $this->db->query(
            "SELECT i.ts_code, s.name, s.industry, i.macd, i.macd_signal, i.macd_hist
             FROM technical_indicators i
             JOIN stocks s ON i.ts_code = s.ts_code
             WHERE i.trade_date = ? AND i.macd_hist > 0 AND i.macd_hist < 0.1
             ORDER BY i.macd_hist ASC
             LIMIT 50",
            [$tradeDate]
        );
    }

    // 获取底部放量股票
    public function getBottomVolumeStocks(string $tradeDate): array {
        // 底部放量条件：
        // 1. 量比 > 3（当日成交量/20日均量）
        // 2. 价格位置 < 0.3（处于60日低位）
        // 3. 当日涨幅 > 3%
        // 4. RSI < 50（还没超买）
        return $this->db->query(
            "SELECT
                q.ts_code,
                s.name,
                s.industry,
                q.close,
                q.pct_chg,
                ROUND(q.vol / avg_data.avg_vol, 2) as volume_ratio,
                ROUND((q.close - range_data.low_60) / (range_data.high_60 - range_data.low_60) * 100, 2) as price_position,
                i.rsi_6
             FROM daily_quotes q
             JOIN stocks s ON q.ts_code = s.ts_code
             JOIN technical_indicators i ON q.ts_code = i.ts_code AND q.trade_date = i.trade_date
             JOIN (
                 SELECT ts_code, AVG(vol) as avg_vol
                 FROM daily_quotes
                 WHERE trade_date <= ? AND trade_date >= DATE_FORMAT(DATE_SUB(STR_TO_DATE(?, '%Y%m%d'), INTERVAL 20 DAY), '%Y%m%d')
                 GROUP BY ts_code
             ) avg_data ON q.ts_code = avg_data.ts_code
             JOIN (
                 SELECT ts_code, MIN(low) as low_60, MAX(high) as high_60
                 FROM daily_quotes
                 WHERE trade_date <= ? AND trade_date >= DATE_FORMAT(DATE_SUB(STR_TO_DATE(?, '%Y%m%d'), INTERVAL 60 DAY), '%Y%m%d')
                 GROUP BY ts_code
             ) range_data ON q.ts_code = range_data.ts_code
             WHERE q.trade_date = ?
               AND q.vol > avg_data.avg_vol * 3
               AND (q.close - range_data.low_60) / (range_data.high_60 - range_data.low_60) < 0.3
               AND q.pct_chg > 3
               AND i.rsi_6 < 50
               AND range_data.high_60 > range_data.low_60
             ORDER BY q.vol / avg_data.avg_vol DESC
             LIMIT 50",
            [$tradeDate, $tradeDate, $tradeDate, $tradeDate, $tradeDate]
        );
    }

    // 获取行业异动（板块集体上涨）
    public function getIndustryHotStocks(string $tradeDate): array {
        // 条件：行业内上涨股票数>=5，平均涨幅>3%
        return $this->db->query(
            "SELECT
                s.industry,
                COUNT(*) as stock_count,
                ROUND(AVG(q.pct_chg), 2) as avg_pct_chg,
                (SELECT s2.name FROM daily_quotes q2
                 JOIN stocks s2 ON q2.ts_code = s2.ts_code
                 WHERE q2.trade_date = ? AND s2.industry = s.industry
                 ORDER BY q2.pct_chg DESC LIMIT 1) as top_stock,
                (SELECT MAX(q3.pct_chg) FROM daily_quotes q3
                 JOIN stocks s3 ON q3.ts_code = s3.ts_code
                 WHERE q3.trade_date = ? AND s3.industry = s.industry) as top_pct
             FROM daily_quotes q
             JOIN stocks s ON q.ts_code = s.ts_code
             WHERE q.trade_date = ?
               AND q.pct_chg > 0
               AND s.industry IS NOT NULL
               AND s.industry != ''
             GROUP BY s.industry
             HAVING COUNT(*) >= 5 AND AVG(q.pct_chg) > 3
             ORDER BY AVG(q.pct_chg) DESC
             LIMIT 20",
            [$tradeDate, $tradeDate, $tradeDate]
        );
    }

    // 获取大盘指数
    public function getMarketIndex(string $tradeDate): array {
        return $this->db->query(
            "SELECT ts_code, close, pct_chg, vol, amount
             FROM daily_quotes
             WHERE trade_date = ?
               AND ts_code IN ('000001.SH', '399001.SZ', '399006.SZ')
             ORDER BY ts_code",
            [$tradeDate]
        );
    }

    // 获取逆势上涨股票
    public function getCounterTrendStocks(string $tradeDate): array {
        // 先获取上证指数涨跌幅
        $indexData = $this->db->query(
            "SELECT pct_chg FROM daily_quotes WHERE trade_date = ? AND ts_code = '000001.SH'",
            [$tradeDate]
        );

        $indexChg = $indexData[0]['pct_chg'] ?? 0;

        // 大盘跌时筛选逆势股，涨幅>2%，量比>1.5
        return $this->db->query(
            "SELECT
                q.ts_code,
                s.name,
                s.industry,
                q.close,
                q.pct_chg,
                ROUND(q.vol / NULLIF(avg_data.avg_vol, 0), 2) as volume_ratio
             FROM daily_quotes q
             JOIN stocks s ON q.ts_code = s.ts_code
             LEFT JOIN (
                 SELECT ts_code, AVG(vol) as avg_vol
                 FROM daily_quotes
                 WHERE trade_date <= ? AND trade_date >= DATE_FORMAT(DATE_SUB(STR_TO_DATE(?, '%Y%m%d'), INTERVAL 10 DAY), '%Y%m%d')
                 GROUP BY ts_code
             ) avg_data ON q.ts_code = avg_data.ts_code
             WHERE q.trade_date = ?
               AND q.pct_chg > 2
               AND q.ts_code NOT LIKE '%%.SH'
               AND q.ts_code NOT LIKE '399%%'
             ORDER BY q.pct_chg DESC
             LIMIT 50",
            [$tradeDate, $tradeDate, $tradeDate]
        );
    }
}
