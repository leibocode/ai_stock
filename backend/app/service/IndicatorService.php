<?php
declare(strict_types=1);

namespace app\service;

use think\facade\Db;

class IndicatorService
{
    // 计算并保存指标
    public function calculate(string $tsCode, array $history): bool
    {
        if (count($history) < 30) {
            return false;
        }

        // 按日期正序
        $history = array_reverse($history);
        $closes = array_column($history, 'close');
        $highs = array_column($history, 'high');
        $lows = array_column($history, 'low');
        $volumes = array_column($history, 'vol');

        $lastDate = end($history)['trade_date'];

        // 计算各项指标
        $rsi = $this->calculateRSI($closes);
        $macd = $this->calculateMACD($closes);
        $kdj = $this->calculateKDJ($highs, $lows, $closes);
        $boll = $this->calculateBOLL($closes);

        // 保存
        Db::table('technical_indicators')->replace([
            'ts_code' => $tsCode,
            'trade_date' => $lastDate,
            'rsi_6' => $rsi['rsi6'],
            'rsi_12' => $rsi['rsi12'],
            'macd' => $macd['macd'],
            'macd_signal' => $macd['signal'],
            'macd_hist' => $macd['hist'],
            'k' => $kdj['k'],
            'd' => $kdj['d'],
            'j' => $kdj['j'],
            'boll_upper' => $boll['upper'],
            'boll_mid' => $boll['mid'],
            'boll_lower' => $boll['lower'],
        ]);

        return true;
    }

    // RSI计算
    protected function calculateRSI(array $closes, int $period6 = 6, int $period12 = 12): array
    {
        $gains6 = $losses6 = $gains12 = $losses12 = [];

        for ($i = 1; $i < count($closes); $i++) {
            $change = $closes[$i] - $closes[$i - 1];
            if ($i <= $period6) {
                $gains6[] = max($change, 0);
                $losses6[] = max(-$change, 0);
            }
            if ($i <= $period12) {
                $gains12[] = max($change, 0);
                $losses12[] = max(-$change, 0);
            }
        }

        $avgGain6 = array_sum($gains6) / $period6;
        $avgLoss6 = array_sum($losses6) / $period6;
        $avgGain12 = array_sum($gains12) / $period12;
        $avgLoss12 = array_sum($losses12) / $period12;

        $rsi6 = $avgLoss6 == 0 ? 100 : round(100 - (100 / (1 + $avgGain6 / $avgLoss6)), 2);
        $rsi12 = $avgLoss12 == 0 ? 100 : round(100 - (100 / (1 + $avgGain12 / $avgLoss12)), 2);

        return ['rsi6' => $rsi6, 'rsi12' => $rsi12];
    }

    // MACD计算
    protected function calculateMACD(array $closes): array
    {
        $ema12 = $this->calculateEMA($closes, 12);
        $ema26 = $this->calculateEMA($closes, 26);
        $dif = $ema12 - $ema26;

        // 简化处理
        $signal = $dif * 0.8;
        $hist = $dif - $signal;

        return [
            'macd' => round($dif, 4),
            'signal' => round($signal, 4),
            'hist' => round($hist, 4),
        ];
    }

    // EMA计算
    protected function calculateEMA(array $data, int $period): float
    {
        $k = 2 / ($period + 1);
        $ema = $data[0];
        for ($i = 1; $i < count($data); $i++) {
            $ema = $data[$i] * $k + $ema * (1 - $k);
        }
        return $ema;
    }

    // KDJ计算
    protected function calculateKDJ(array $highs, array $lows, array $closes): array
    {
        $period = 9;
        $n = count($closes);
        if ($n < $period) {
            return ['k' => 50, 'd' => 50, 'j' => 50];
        }

        $highMax = max(array_slice($highs, -$period));
        $lowMin = min(array_slice($lows, -$period));
        $close = end($closes);

        $rsv = $highMax == $lowMin ? 50 : (($close - $lowMin) / ($highMax - $lowMin)) * 100;
        $k = round($rsv * 0.67 + 50 * 0.33, 2);
        $d = round($k * 0.67 + 50 * 0.33, 2);
        $j = round(3 * $k - 2 * $d, 2);

        return ['k' => $k, 'd' => $d, 'j' => $j];
    }

    // BOLL计算
    protected function calculateBOLL(array $closes, int $period = 20): array
    {
        $slice = array_slice($closes, -$period);
        $mid = array_sum($slice) / count($slice);

        $variance = 0;
        foreach ($slice as $val) {
            $variance += pow($val - $mid, 2);
        }
        $std = sqrt($variance / count($slice));

        return [
            'upper' => round($mid + 2 * $std, 2),
            'mid' => round($mid, 2),
            'lower' => round($mid - 2 * $std, 2),
        ];
    }

    // RSI超卖股票
    public function getOversoldStocks(string $date): array
    {
        return Db::table('technical_indicators')
            ->alias('t')
            ->join('stocks s', 's.ts_code = t.ts_code')
            ->where('t.trade_date', $date)
            ->where('t.rsi_6', '<', 30)
            ->field('t.ts_code, s.name, s.industry, t.rsi_6, t.rsi_12')
            ->order('t.rsi_6', 'asc')
            ->limit(50)
            ->select()
            ->toArray();
    }

    // KDJ见底股票
    public function getKDJBottomStocks(string $date): array
    {
        return Db::table('technical_indicators')
            ->alias('t')
            ->join('stocks s', 's.ts_code = t.ts_code')
            ->where('t.trade_date', $date)
            ->where('t.k', '<', 20)
            ->where('t.d', '<', 20)
            ->field('t.ts_code, s.name, s.industry, t.k, t.d, t.j')
            ->order('t.k', 'asc')
            ->limit(50)
            ->select()
            ->toArray();
    }

    // MACD金叉
    public function getMACDGoldenCross(string $date): array
    {
        return Db::table('technical_indicators')
            ->alias('t')
            ->join('stocks s', 's.ts_code = t.ts_code')
            ->where('t.trade_date', $date)
            ->where('t.macd_hist', '>', 0)
            ->field('t.ts_code, s.name, s.industry, t.macd, t.macd_hist')
            ->order('t.macd_hist', 'desc')
            ->limit(50)
            ->select()
            ->toArray();
    }

    // 底部放量股票
    public function getBottomVolumeStocks(string $date): array
    {
        // 量比>3，价格位置<30%
        $sql = "SELECT d.ts_code, s.name, s.industry,
                d.vol / avg_vol.avg_vol as volume_ratio,
                ((d.close - price_range.min_price) / (price_range.max_price - price_range.min_price)) * 100 as price_position,
                d.pct_chg
                FROM daily_quotes d
                JOIN stocks s ON s.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, AVG(vol) as avg_vol
                    FROM daily_quotes
                    WHERE trade_date <= '{$date}'
                    GROUP BY ts_code
                ) avg_vol ON avg_vol.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, MIN(low) as min_price, MAX(high) as max_price
                    FROM daily_quotes
                    WHERE trade_date <= '{$date}'
                    GROUP BY ts_code
                ) price_range ON price_range.ts_code = d.ts_code
                WHERE d.trade_date = '{$date}'
                HAVING volume_ratio > 3 AND price_position < 30
                ORDER BY volume_ratio DESC
                LIMIT 50";

        return Db::query($sql);
    }

    // 顶部放量股票
    public function getTopVolumeStocks(string $date): array
    {
        // 量比>3，价格位置>70%
        $sql = "SELECT d.ts_code, s.name, s.industry, d.close,
                d.vol / avg_vol.avg_vol as volume_ratio,
                ((d.close - price_range.min_price) / (price_range.max_price - price_range.min_price)) * 100 as price_position,
                d.pct_chg
                FROM daily_quotes d
                JOIN stocks s ON s.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, AVG(vol) as avg_vol
                    FROM daily_quotes
                    WHERE trade_date <= '{$date}'
                    GROUP BY ts_code
                ) avg_vol ON avg_vol.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, MIN(low) as min_price, MAX(high) as max_price
                    FROM daily_quotes
                    WHERE trade_date <= '{$date}'
                    GROUP BY ts_code
                ) price_range ON price_range.ts_code = d.ts_code
                WHERE d.trade_date = '{$date}'
                HAVING volume_ratio > 3 AND price_position > 70
                ORDER BY volume_ratio DESC
                LIMIT 50";

        return Db::query($sql);
    }

    // 行业异动
    public function getIndustryHotStocks(string $date): array
    {
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->where('d.pct_chg', '>', 0)
            ->group('s.industry')
            ->having('COUNT(*) >= 5')
            ->field('s.industry, COUNT(*) as stock_count, ROUND(AVG(d.pct_chg), 2) as avg_pct_chg')
            ->order('avg_pct_chg', 'desc')
            ->limit(20)
            ->select()
            ->toArray();
    }

    // 大盘指数
    public function getMarketIndex(string $date): array
    {
        $codes = ['000001.SH', '399001.SZ', '399006.SZ'];
        return Db::table('daily_quotes')
            ->whereIn('ts_code', $codes)
            ->where('trade_date', $date)
            ->field('ts_code, close, pct_chg')
            ->select()
            ->toArray();
    }

    // 逆势上涨
    public function getCounterTrendStocks(string $date): array
    {
        // 获取大盘涨跌
        $index = Db::table('daily_quotes')
            ->where('ts_code', '000001.SH')
            ->where('trade_date', $date)
            ->value('pct_chg');

        if ($index >= 0) {
            return [];
        }

        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->where('d.pct_chg', '>', 2)
            ->field('d.ts_code, s.name, s.industry, d.close, d.pct_chg, 1 as volume_ratio')
            ->order('d.pct_chg', 'desc')
            ->limit(50)
            ->select()
            ->toArray();
    }

    // 市场统计
    public function getMarketStats(string $date): array
    {
        $limitUp = Db::table('daily_quotes')
            ->where('trade_date', $date)
            ->where('pct_chg', '>=', 9.9)
            ->count();

        $limitDown = Db::table('daily_quotes')
            ->where('trade_date', $date)
            ->where('pct_chg', '<=', -9.9)
            ->count();

        return [
            'limitUp' => $limitUp,
            'limitDown' => $limitDown,
            'northFlow' => 0, // 需要单独获取
        ];
    }

    // 涨停列表
    public function getLimitUpList(string $date): array
    {
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->where('d.pct_chg', '>=', 9.9)
            ->field('d.ts_code, s.name, s.industry, "09:30" as first_time, 0 as open_times, 1 as continuous')
            ->order('d.pct_chg', 'desc')
            ->select()
            ->toArray();
    }

    // 跌停列表
    public function getLimitDownList(string $date): array
    {
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->where('d.pct_chg', '<=', -9.9)
            ->field('d.ts_code, s.name, s.industry, "-" as reason')
            ->order('d.pct_chg', 'asc')
            ->select()
            ->toArray();
    }

    // 突破形态
    public function getBreakoutStocks(string $date): array
    {
        // 简化实现：收盘价创20日新高
        $sql = "SELECT d.ts_code, s.name, s.industry, '创新高' as type, d.pct_chg
                FROM daily_quotes d
                JOIN stocks s ON s.ts_code = d.ts_code
                WHERE d.trade_date = '{$date}'
                AND d.close = (
                    SELECT MAX(close) FROM daily_quotes
                    WHERE ts_code = d.ts_code AND trade_date <= '{$date}'
                    ORDER BY trade_date DESC LIMIT 20
                )
                ORDER BY d.pct_chg DESC
                LIMIT 50";

        return Db::query($sql);
    }

    // 跳空高开
    public function getGapUpStocks(string $date): array
    {
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->whereRaw('d.open > d.pre_close * 1.03')
            ->field('d.ts_code, s.name, s.industry, d.open, d.pre_close,
                    ROUND((d.open - d.pre_close) / d.pre_close * 100, 2) as gap, d.pct_chg')
            ->order('gap', 'desc')
            ->limit(50)
            ->select()
            ->toArray();
    }

    // 跳空低开
    public function getGapDownStocks(string $date): array
    {
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->whereRaw('d.open < d.pre_close * 0.97')
            ->field('d.ts_code, s.name, s.industry, d.open, d.pre_close,
                    ROUND((d.open - d.pre_close) / d.pre_close * 100, 2) as gap, d.pct_chg')
            ->order('gap', 'asc')
            ->limit(50)
            ->select()
            ->toArray();
    }

    // 行业跳空
    public function getIndustryGap(string $date): array
    {
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->group('s.industry')
            ->field('s.industry,
                    IF(AVG((d.open - d.pre_close) / d.pre_close) > 0, "高开", "低开") as direction,
                    ROUND(AVG((d.open - d.pre_close) / d.pre_close * 100), 2) as avg_gap,
                    COUNT(*) as stock_count')
            ->having('ABS(avg_gap) > 1')
            ->order('avg_gap', 'desc')
            ->select()
            ->toArray();
    }
}
