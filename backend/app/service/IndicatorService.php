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

    // MACD计算 - 正确的三线计算
    protected function calculateMACD(array $closes): array
    {
        if (count($closes) < 26) {
            return ['macd' => 0, 'signal' => 0, 'hist' => 0];
        }

        // 计算所有DIF值（为了计算DEA）
        $difs = [];
        $ema12Values = $this->calculateEMAArray($closes, 12);
        $ema26Values = $this->calculateEMAArray($closes, 26);

        for ($i = 0; $i < count($ema12Values); $i++) {
            $difs[] = $ema12Values[$i] - $ema26Values[$i];
        }

        // 最后一个DIF
        $dif = end($difs);

        // DEA是DIF的9日EMA
        $dea = $this->calculateEMA($difs, 9);

        // MACD柱 = DIF - DEA
        $hist = $dif - $dea;

        return [
            'macd' => round($dif, 4),
            'signal' => round($dea, 4),
            'hist' => round($hist, 4),
        ];
    }

    // EMA计算 - 返回完整数组
    protected function calculateEMAArray(array $data, int $period): array
    {
        if (count($data) < $period) {
            return $data;
        }

        $result = [];
        $k = 2 / ($period + 1);

        // 初始EMA = 前period个数据的简单平均
        $ema = array_sum(array_slice($data, 0, $period)) / $period;
        $result[] = $ema;

        // 后续EMA = 当前价格 * k + 前EMA * (1-k)
        for ($i = $period; $i < count($data); $i++) {
            $ema = $data[$i] * $k + $ema * (1 - $k);
            $result[] = $ema;
        }

        return $result;
    }

    // EMA计算 - 返回单个值（兼容旧方法）
    protected function calculateEMA(array $data, int $period): float
    {
        if (count($data) < $period) {
            return end($data);
        }

        $k = 2 / ($period + 1);
        // 初始EMA = 前period个数据的简单平均
        $ema = array_sum(array_slice($data, 0, $period)) / $period;

        // 后续EMA计算
        for ($i = $period; $i < count($data); $i++) {
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
        // 量比>3，价格位置<30% - 使用参数绑定防止注入
        $sql = "SELECT d.ts_code, s.name, s.industry,
                d.vol / avg_vol.avg_vol as volume_ratio,
                ((d.close - price_range.min_price) / (price_range.max_price - price_range.min_price)) * 100 as price_position,
                d.pct_chg
                FROM daily_quotes d
                JOIN stocks s ON s.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, AVG(vol) as avg_vol
                    FROM daily_quotes
                    WHERE trade_date <= ?
                    GROUP BY ts_code
                ) avg_vol ON avg_vol.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, MIN(low) as min_price, MAX(high) as max_price
                    FROM daily_quotes
                    WHERE trade_date <= ?
                    GROUP BY ts_code
                ) price_range ON price_range.ts_code = d.ts_code
                WHERE d.trade_date = ?
                HAVING volume_ratio > 3 AND price_position < 30
                ORDER BY volume_ratio DESC
                LIMIT 50";

        return Db::query($sql, [$date, $date, $date]);
    }

    // 顶部放量股票
    public function getTopVolumeStocks(string $date): array
    {
        // 量比>3，价格位置>70% - 使用参数绑定防止注入
        $sql = "SELECT d.ts_code, s.name, s.industry, d.close,
                d.vol / avg_vol.avg_vol as volume_ratio,
                ((d.close - price_range.min_price) / (price_range.max_price - price_range.min_price)) * 100 as price_position,
                d.pct_chg
                FROM daily_quotes d
                JOIN stocks s ON s.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, AVG(vol) as avg_vol
                    FROM daily_quotes
                    WHERE trade_date <= ?
                    GROUP BY ts_code
                ) avg_vol ON avg_vol.ts_code = d.ts_code
                JOIN (
                    SELECT ts_code, MIN(low) as min_price, MAX(high) as max_price
                    FROM daily_quotes
                    WHERE trade_date <= ?
                    GROUP BY ts_code
                ) price_range ON price_range.ts_code = d.ts_code
                WHERE d.trade_date = ?
                HAVING volume_ratio > 3 AND price_position > 70
                ORDER BY volume_ratio DESC
                LIMIT 50";

        return Db::query($sql, [$date, $date, $date]);
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
        // 收盘价创20日新高
        return Db::table('daily_quotes')
            ->alias('d')
            ->join('stocks s', 's.ts_code = d.ts_code')
            ->where('d.trade_date', $date)
            ->whereRaw('d.close = (SELECT MAX(close) FROM daily_quotes WHERE ts_code = d.ts_code AND trade_date <= ? LIMIT 1)', [$date])
            ->field('d.ts_code, s.name, s.industry, d.pct_chg')
            ->order('d.pct_chg', 'desc')
            ->limit(50)
            ->select()
            ->toArray();
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

    // ==================== 缠论指标计算 ====================

    /**
     * 计算缠论所有指标
     */
    public function calculateChan(string $tsCode, array $history): bool
    {
        if (count($history) < 100) {
            return false;
        }

        // 按日期正序
        $history = array_reverse($history);

        // 1. K线包含处理
        $mergedKlines = $this->mergeKlines($history);

        // 2. 分型识别
        $fractals = $this->calculateChanFractal($tsCode, $mergedKlines);

        // 3. 笔划分
        $bis = $this->calculateChanBi($tsCode, $fractals);

        // 4. 线段划分
        $segments = $this->calculateChanSegment($tsCode, $bis);

        // 5. 中枢识别
        $this->calculateChanHub($tsCode, $segments);

        return true;
    }

    /**
     * K线包含处理
     * 向上时取高高低高，向下时取低低高低
     */
    protected function mergeKlines(array $klines): array
    {
        if (count($klines) < 2) {
            return $klines;
        }

        $merged = [$klines[0]];
        $direction = 0; // 0:未知 1:向上 -1:向下

        for ($i = 1; $i < count($klines); $i++) {
            $prev = end($merged);
            $curr = $klines[$i];

            // 判断包含关系
            $isContain = ($curr['high'] <= $prev['high'] && $curr['low'] >= $prev['low']) ||
                         ($curr['high'] >= $prev['high'] && $curr['low'] <= $prev['low']);

            if ($isContain) {
                // 确定方向
                if ($direction == 0) {
                    $direction = $curr['high'] > $prev['high'] ? 1 : -1;
                }

                // 合并K线
                $mergedKey = count($merged) - 1;
                if ($direction == 1) {
                    // 向上：取高高低高
                    $merged[$mergedKey]['high'] = max($prev['high'], $curr['high']);
                    $merged[$mergedKey]['low'] = max($prev['low'], $curr['low']);
                } else {
                    // 向下：取低低高低
                    $merged[$mergedKey]['high'] = min($prev['high'], $curr['high']);
                    $merged[$mergedKey]['low'] = min($prev['low'], $curr['low']);
                }
            } else {
                // 更新方向
                if ($curr['high'] > $prev['high']) {
                    $direction = 1;
                } elseif ($curr['low'] < $prev['low']) {
                    $direction = -1;
                }
                $merged[] = $curr;
            }
        }

        return $merged;
    }

    /**
     * 分型识别
     * 顶分型：中间K线高点最高
     * 底分型：中间K线低点最低
     */
    protected function calculateChanFractal(string $tsCode, array $klines): array
    {
        $fractals = [];

        for ($i = 1; $i < count($klines) - 1; $i++) {
            $prev = $klines[$i - 1];
            $curr = $klines[$i];
            $next = $klines[$i + 1];

            // 顶分型
            if ($curr['high'] > $prev['high'] && $curr['high'] > $next['high']) {
                $fractals[] = [
                    'trade_date' => $curr['trade_date'],
                    'fractal_type' => 1,
                    'high' => $curr['high'],
                    'low' => $curr['low'],
                ];
            }
            // 底分型
            elseif ($curr['low'] < $prev['low'] && $curr['low'] < $next['low']) {
                $fractals[] = [
                    'trade_date' => $curr['trade_date'],
                    'fractal_type' => -1,
                    'high' => $curr['high'],
                    'low' => $curr['low'],
                ];
            }
        }

        // 保存分型数据
        Db::table('chan_fractal')->where('ts_code', $tsCode)->delete();
        foreach ($fractals as $f) {
            Db::table('chan_fractal')->insert([
                'ts_code' => $tsCode,
                'trade_date' => $f['trade_date'],
                'fractal_type' => $f['fractal_type'],
                'high' => $f['high'],
                'low' => $f['low'],
            ]);
        }

        return $fractals;
    }

    /**
     * 笔划分
     * 连接相邻的顶底分型，至少5根K线
     */
    protected function calculateChanBi(string $tsCode, array $fractals): array
    {
        if (count($fractals) < 2) {
            return [];
        }

        $bis = [];
        $biIndex = 0;
        $lastFractal = null;

        foreach ($fractals as $f) {
            if ($lastFractal === null) {
                $lastFractal = $f;
                continue;
            }

            // 顶底交替
            if ($f['fractal_type'] != $lastFractal['fractal_type']) {
                // 向上笔：从底到顶
                if ($f['fractal_type'] == 1 && $f['high'] > $lastFractal['high']) {
                    $bis[] = [
                        'start_date' => $lastFractal['trade_date'],
                        'end_date' => $f['trade_date'],
                        'direction' => 1,
                        'high' => $f['high'],
                        'low' => $lastFractal['low'],
                        'bi_index' => $biIndex++,
                    ];
                    $lastFractal = $f;
                }
                // 向下笔：从顶到底
                elseif ($f['fractal_type'] == -1 && $f['low'] < $lastFractal['low']) {
                    $bis[] = [
                        'start_date' => $lastFractal['trade_date'],
                        'end_date' => $f['trade_date'],
                        'direction' => -1,
                        'high' => $lastFractal['high'],
                        'low' => $f['low'],
                        'bi_index' => $biIndex++,
                    ];
                    $lastFractal = $f;
                }
            }
            // 同向分型，取极值
            else {
                if ($f['fractal_type'] == 1 && $f['high'] > $lastFractal['high']) {
                    $lastFractal = $f;
                } elseif ($f['fractal_type'] == -1 && $f['low'] < $lastFractal['low']) {
                    $lastFractal = $f;
                }
            }
        }

        // 保存笔数据
        Db::table('chan_bi')->where('ts_code', $tsCode)->delete();
        foreach ($bis as $bi) {
            Db::table('chan_bi')->insert([
                'ts_code' => $tsCode,
                'start_date' => $bi['start_date'],
                'end_date' => $bi['end_date'],
                'direction' => $bi['direction'],
                'high' => $bi['high'],
                'low' => $bi['low'],
                'bi_index' => $bi['bi_index'],
            ]);
        }

        return $bis;
    }

    /**
     * 线段划分
     * 至少3笔构成一个线段
     */
    protected function calculateChanSegment(string $tsCode, array $bis): array
    {
        if (count($bis) < 3) {
            return [];
        }

        $segments = [];
        $segIndex = 0;
        $segStart = 0;

        for ($i = 2; $i < count($bis); $i++) {
            $bi1 = $bis[$i - 2];
            $bi2 = $bis[$i - 1];
            $bi3 = $bis[$i];

            // 向上线段结束条件：向下笔新低
            if ($bi1['direction'] == 1 && $bi3['low'] < $bi2['low']) {
                $segments[] = [
                    'start_date' => $bis[$segStart]['start_date'],
                    'end_date' => $bi2['end_date'],
                    'direction' => 1,
                    'high' => max(array_column(array_slice($bis, $segStart, $i - $segStart), 'high')),
                    'low' => min(array_column(array_slice($bis, $segStart, $i - $segStart), 'low')),
                    'seg_index' => $segIndex++,
                ];
                $segStart = $i - 1;
            }
            // 向下线段结束条件：向上笔新高
            elseif ($bi1['direction'] == -1 && $bi3['high'] > $bi2['high']) {
                $segments[] = [
                    'start_date' => $bis[$segStart]['start_date'],
                    'end_date' => $bi2['end_date'],
                    'direction' => -1,
                    'high' => max(array_column(array_slice($bis, $segStart, $i - $segStart), 'high')),
                    'low' => min(array_column(array_slice($bis, $segStart, $i - $segStart), 'low')),
                    'seg_index' => $segIndex++,
                ];
                $segStart = $i - 1;
            }
        }

        // 处理最后一个线段
        if ($segStart < count($bis) - 1) {
            $lastBis = array_slice($bis, $segStart);
            $segments[] = [
                'start_date' => $lastBis[0]['start_date'],
                'end_date' => end($lastBis)['end_date'],
                'direction' => $lastBis[0]['direction'],
                'high' => max(array_column($lastBis, 'high')),
                'low' => min(array_column($lastBis, 'low')),
                'seg_index' => $segIndex++,
            ];
        }

        // 保存线段数据
        Db::table('chan_segment')->where('ts_code', $tsCode)->delete();
        foreach ($segments as $seg) {
            Db::table('chan_segment')->insert([
                'ts_code' => $tsCode,
                'start_date' => $seg['start_date'],
                'end_date' => $seg['end_date'],
                'direction' => $seg['direction'],
                'high' => $seg['high'],
                'low' => $seg['low'],
                'seg_index' => $seg['seg_index'],
            ]);
        }

        return $segments;
    }

    /**
     * 中枢识别（基于笔）
     * 至少3笔的重叠区间才能形成中枢
     */
    protected function calculateChanHub(string $tsCode, array $segments): array
    {
        // 获取笔数据（从数据库）
        $bis = Db::table('chan_bi')
            ->where('ts_code', $tsCode)
            ->order('bi_index', 'asc')
            ->select()
            ->toArray();

        if (count($bis) < 3) {
            return [];
        }

        $hubs = [];
        $hubIndex = 0;
        $i = 0;

        while ($i <= count($bis) - 3) {
            $bi1 = $bis[$i];
            $bi2 = $bis[$i + 1];
            $bi3 = $bis[$i + 2];

            // 3笔的重叠区间：中枢上沿(zg) = min(3笔高点)，下沿(zd) = max(3笔低点)
            $zg = min($bi1['high'], $bi2['high'], $bi3['high']);
            $zd = max($bi1['low'], $bi2['low'], $bi3['low']);

            // 有效中枢：上沿 > 下沿，且至少跨越1个完整的上升+下降或下降+上升
            if ($zg > $zd) {
                // 从起点到终点的最高/最低（考虑后续笔的扩展）
                $hubStart = $bi1['start_date'];
                $hubEnd = $bi3['end_date'];
                $gg = max($bi1['high'], $bi2['high'], $bi3['high']);
                $dd = min($bi1['low'], $bi2['low'], $bi3['low']);

                $hubs[] = [
                    'start_date' => $hubStart,
                    'end_date' => $hubEnd,
                    'zg' => $zg,
                    'zd' => $zd,
                    'gg' => $gg,
                    'dd' => $dd,
                    'hub_index' => $hubIndex++,
                ];

                $i += 2; // 移动到下一个可能的中枢起点
            } else {
                $i++;
            }
        }

        // 保存中枢数据
        Db::table('chan_hub')->where('ts_code', $tsCode)->delete();
        foreach ($hubs as $hub) {
            Db::table('chan_hub')->insert([
                'ts_code' => $tsCode,
                'start_date' => $hub['start_date'],
                'end_date' => $hub['end_date'],
                'zg' => $hub['zg'],
                'zd' => $hub['zd'],
                'gg' => $hub['gg'],
                'dd' => $hub['dd'],
                'hub_index' => $hub['hub_index'],
                'level' => 1,
            ]);
        }

        return $hubs;
    }

    // ==================== 缠论选股查询 ====================

    /**
     * 底背驰信号
     * 价格创新低但MACD不创新低
     */
    public function getChanBottomDiverge(string $date): array
    {
        $sql = "SELECT b.ts_code, s.name, s.industry,
                b.low as bi_low, t.macd_hist,
                '底背驰' as signal_type
                FROM chan_bi b
                JOIN stocks s ON s.ts_code = b.ts_code
                JOIN technical_indicators t ON t.ts_code = b.ts_code AND t.trade_date = b.end_date
                WHERE b.direction = -1
                AND b.end_date = '{$date}'
                AND b.low < (
                    SELECT MIN(b2.low) FROM chan_bi b2
                    WHERE b2.ts_code = b.ts_code
                    AND b2.direction = -1
                    AND b2.bi_index < b.bi_index
                    AND b2.bi_index >= b.bi_index - 4
                )
                AND t.macd_hist > (
                    SELECT MIN(t2.macd_hist) FROM technical_indicators t2
                    JOIN chan_bi b3 ON b3.ts_code = t2.ts_code AND b3.end_date = t2.trade_date
                    WHERE b3.ts_code = b.ts_code
                    AND b3.direction = -1
                    AND b3.bi_index < b.bi_index
                    AND b3.bi_index >= b.bi_index - 4
                )
                LIMIT 50";

        return Db::query($sql);
    }

    /**
     * 顶背驰信号
     */
    public function getChanTopDiverge(string $date): array
    {
        $sql = "SELECT b.ts_code, s.name, s.industry,
                b.high as bi_high, t.macd_hist,
                '顶背驰' as signal_type
                FROM chan_bi b
                JOIN stocks s ON s.ts_code = b.ts_code
                JOIN technical_indicators t ON t.ts_code = b.ts_code AND t.trade_date = b.end_date
                WHERE b.direction = 1
                AND b.end_date = '{$date}'
                AND b.high > (
                    SELECT MAX(b2.high) FROM chan_bi b2
                    WHERE b2.ts_code = b.ts_code
                    AND b2.direction = 1
                    AND b2.bi_index < b.bi_index
                    AND b2.bi_index >= b.bi_index - 4
                )
                AND t.macd_hist < (
                    SELECT MAX(t2.macd_hist) FROM technical_indicators t2
                    JOIN chan_bi b3 ON b3.ts_code = t2.ts_code AND b3.end_date = t2.trade_date
                    WHERE b3.ts_code = b.ts_code
                    AND b3.direction = 1
                    AND b3.bi_index < b.bi_index
                    AND b3.bi_index >= b.bi_index - 4
                )
                LIMIT 50";

        return Db::query($sql);
    }

    /**
     * 一买信号
     * 下跌趋势中第一个底背驰
     */
    public function getChanFirstBuy(string $date): array
    {
        $sql = "SELECT b.ts_code, s.name, s.industry,
                b.low as price, h.zd as hub_low,
                '一买' as buy_type
                FROM chan_bi b
                JOIN stocks s ON s.ts_code = b.ts_code
                JOIN chan_hub h ON h.ts_code = b.ts_code
                WHERE b.direction = -1
                AND b.end_date = '{$date}'
                AND b.low < h.dd
                AND h.hub_index = (
                    SELECT MAX(hub_index) FROM chan_hub
                    WHERE ts_code = b.ts_code AND end_date < b.end_date
                )
                LIMIT 50";

        return Db::query($sql);
    }

    /**
     * 二买信号
     * 一买后回抽不创新低
     */
    public function getChanSecondBuy(string $date): array
    {
        $sql = "SELECT b.ts_code, s.name, s.industry,
                b.low as price,
                '二买' as buy_type
                FROM chan_bi b
                JOIN stocks s ON s.ts_code = b.ts_code
                WHERE b.direction = -1
                AND b.end_date = '{$date}'
                AND b.bi_index >= 2
                AND b.low > (
                    SELECT low FROM chan_bi
                    WHERE ts_code = b.ts_code AND bi_index = b.bi_index - 2
                )
                LIMIT 50";

        return Db::query($sql);
    }

    /**
     * 三买信号
     * 中枢上方回踩不进中枢
     */
    public function getChanThirdBuy(string $date): array
    {
        $sql = "SELECT b.ts_code, s.name, s.industry,
                b.low as price, h.zg as hub_top,
                '三买' as buy_type
                FROM chan_bi b
                JOIN stocks s ON s.ts_code = b.ts_code
                JOIN chan_hub h ON h.ts_code = b.ts_code
                WHERE b.direction = -1
                AND b.end_date = '{$date}'
                AND b.low > h.zg
                AND h.hub_index = (
                    SELECT MAX(hub_index) FROM chan_hub
                    WHERE ts_code = b.ts_code AND end_date < b.start_date
                )
                LIMIT 50";

        return Db::query($sql);
    }

    /**
     * 中枢震荡
     * 当前价格在中枢区间内
     */
    public function getChanHubShake(string $date): array
    {
        $sql = "SELECT d.ts_code, s.name, s.industry,
                d.close, h.zg, h.zd,
                ROUND((d.close - h.zd) / (h.zg - h.zd) * 100, 2) as position
                FROM daily_quotes d
                JOIN stocks s ON s.ts_code = d.ts_code
                JOIN chan_hub h ON h.ts_code = d.ts_code
                WHERE d.trade_date = '{$date}'
                AND d.close BETWEEN h.zd AND h.zg
                AND h.hub_index = (
                    SELECT MAX(hub_index) FROM chan_hub WHERE ts_code = d.ts_code
                )
                ORDER BY position ASC
                LIMIT 50";

        return Db::query($sql);
    }

    /**
     * 获取单只股票的缠论数据（用于图表绘制）
     */
    public function getChanData(string $tsCode): array
    {
        $fractals = Db::table('chan_fractal')
            ->where('ts_code', $tsCode)
            ->order('trade_date', 'asc')
            ->select()
            ->toArray();

        $bis = Db::table('chan_bi')
            ->where('ts_code', $tsCode)
            ->order('bi_index', 'asc')
            ->select()
            ->toArray();

        $segments = Db::table('chan_segment')
            ->where('ts_code', $tsCode)
            ->order('seg_index', 'asc')
            ->select()
            ->toArray();

        $hubs = Db::table('chan_hub')
            ->where('ts_code', $tsCode)
            ->order('hub_index', 'asc')
            ->select()
            ->toArray();

        return [
            'fractals' => $fractals,
            'bis' => $bis,
            'segments' => $segments,
            'hubs' => $hubs,
        ];
    }
}
