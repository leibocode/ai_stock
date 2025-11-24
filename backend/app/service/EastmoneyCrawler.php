<?php
declare(strict_types=1);

namespace app\service;

class EastmoneyCrawler
{
    protected $dataPath;

    public function __construct()
    {
        $this->dataPath = __DIR__ . '/../../data/';
        if (!is_dir($this->dataPath)) {
            mkdir($this->dataPath, 0755, true);
        }
    }

    // HTTP请求 - 使用原生curl
    protected function httpGet(string $url): string
    {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_HTTPHEADER => [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer: https://data.eastmoney.com/',
            ],
        ]);
        $result = curl_exec($ch);
        curl_close($ch);
        return $result ?: '';
    }

    protected function httpPost(string $url, array $data): string
    {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 30,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            ],
        ]);
        $result = curl_exec($ch);
        curl_close($ch);
        return $result ?: '';
    }

    // 爬取当日所有数据
    public function crawlDaily(string $date): array
    {
        $limitUpDown = $this->crawlLimitUpDown();

        $result = [
            'date' => $date,
            'crawl_time' => date('Y-m-d H:i:s'),
            'limit_up_down' => $limitUpDown,
            'sector_flow' => $this->crawlSectorFlow(),
            'north_flow' => $this->crawlNorthFlow(),
            'dragon_tiger' => $this->crawlDragonTiger($date),
            'market_emotion' => $this->crawlMarketEmotion(),
            'hot_stocks' => $this->crawlHotStocks(),
            'relative_strength' => $this->crawlRelativeStrength(),
            'emotion_cycle' => $this->crawlEmotionCycle($limitUpDown),
            'leader_stocks' => $this->identifyLeaderStocks($limitUpDown),
            'strength_change' => $this->crawlStrengthChange(),
            'volume_analysis' => $this->crawlVolumeAnalysis(),
            'multi_factor' => $this->crawlMultiFactor(),
            'technical' => $this->crawlTechnicalIndicators(),
            'sector_strength' => $this->crawlSectorStrength(),
        ];

        // 计算综合选股（需要所有数据）
        $result['composite'] = $this->calcCompositeSelection($result);

        return $result;
    }

    // 综合选股 - 多指标命中
    protected function calcCompositeSelection(array $allData): array
    {
        $stocks = [];

        // 收集各指标命中的股票
        $indicators = [
            '涨停' => [],
            '连板' => [],
            '龙头' => [],
            '弱转强' => [],
            '分时强' => [],
            '北向' => [],
            '放量' => [],
            'MACD金叉' => [],
            'KDJ底部' => [],
            '突破' => [],
            '多因子' => [],
            '板块龙' => [],
        ];

        // 1. 涨停股
        foreach ($allData['limit_up_down']['limit_up'] ?? [] as $item) {
            $code = $item['code'];
            $indicators['涨停'][$code] = $item;
            if (($item['continuous'] ?? 1) >= 2) {
                $indicators['连板'][$code] = $item;
            }
        }

        // 2. 龙头股 (得分>60)
        foreach ($allData['leader_stocks']['leaders'] ?? [] as $item) {
            if (($item['score'] ?? 0) >= 60) {
                $indicators['龙头'][$item['code']] = $item;
            }
        }

        // 3. 弱转强
        foreach ($allData['strength_change']['weak_to_strong'] ?? [] as $item) {
            $indicators['弱转强'][$item['code']] = $item;
        }

        // 4. 分时强度 (前30)
        $strengthStocks = array_slice($allData['relative_strength']['stocks'] ?? [], 0, 30);
        foreach ($strengthStocks as $item) {
            $indicators['分时强'][$item['code']] = $item;
        }

        // 5. 北向持仓
        foreach ($allData['north_flow']['top_holdings'] ?? [] as $item) {
            $indicators['北向'][$item['code']] = $item;
        }

        // 6. 底部放量
        foreach ($allData['volume_analysis']['bottom_volume'] ?? [] as $item) {
            $indicators['放量'][$item['code']] = $item;
        }

        // 7. 技术指标
        foreach ($allData['technical']['macd_golden'] ?? [] as $item) {
            $indicators['MACD金叉'][$item['code']] = $item;
        }
        foreach ($allData['technical']['kdj_bottom'] ?? [] as $item) {
            $indicators['KDJ底部'][$item['code']] = $item;
        }
        foreach ($allData['technical']['breakout'] ?? [] as $item) {
            $indicators['突破'][$item['code']] = $item;
        }

        // 8. 多因子高分 (>50)
        foreach ($allData['multi_factor']['stocks'] ?? [] as $item) {
            if (($item['score'] ?? 0) >= 50) {
                $indicators['多因子'][$item['code']] = $item;
            }
        }

        // 9. 板块资金流入龙头
        $topSectors = array_slice($allData['sector_flow'] ?? [], 0, 5);
        $topSectorNames = array_column($topSectors, 'name');

        // 汇总所有股票的指标命中情况
        $allCodes = [];
        foreach ($indicators as $name => $list) {
            foreach ($list as $code => $item) {
                if (!isset($allCodes[$code])) {
                    $allCodes[$code] = [
                        'code' => $code,
                        'name' => $item['name'] ?? '',
                        'price' => $item['price'] ?? 0,
                        'pct_chg' => $item['pct_chg'] ?? 0,
                        'amount' => $item['amount'] ?? 0,
                        'hit_count' => 0,
                        'hit_indicators' => [],
                        'details' => [],
                    ];
                }
                $allCodes[$code]['hit_count']++;
                $allCodes[$code]['hit_indicators'][] = $name;

                // 保存详细信息
                if ($name === '涨停' || $name === '连板') {
                    $allCodes[$code]['continuous'] = $item['continuous'] ?? 1;
                    $allCodes[$code]['first_time'] = $item['first_time'] ?? '';
                }
                if ($name === '龙头') {
                    $allCodes[$code]['leader_score'] = $item['score'] ?? 0;
                }
                if ($name === '多因子') {
                    $allCodes[$code]['factor_score'] = $item['score'] ?? 0;
                }
            }
        }

        // 按命中数排序
        $stockList = array_values($allCodes);
        usort($stockList, function($a, $b) {
            if ($b['hit_count'] !== $a['hit_count']) {
                return $b['hit_count'] - $a['hit_count'];
            }
            return $b['pct_chg'] <=> $a['pct_chg'];
        });

        // 获取情绪周期阶段
        $cyclePhase = $allData['emotion_cycle']['cycle_phase'] ?? '中性';
        $cycleScore = $allData['emotion_cycle']['cycle_score'] ?? 50;

        // 根据情绪周期生成策略
        $strategy = $this->generateCycleStrategy($cyclePhase, $cycleScore, $stockList, $indicators);

        return [
            'multi_hit' => array_filter($stockList, fn($s) => $s['hit_count'] >= 2),
            'top_hit' => array_slice(array_filter($stockList, fn($s) => $s['hit_count'] >= 3), 0, 20),
            'indicator_stats' => array_map(fn($list) => count($list), $indicators),
            'strategy' => $strategy,
        ];
    }

    // 根据情绪周期生成策略
    protected function generateCycleStrategy(string $phase, int $score, array $stocks, array $indicators): array
    {
        $strategy = [
            'phase' => $phase,
            'score' => $score,
            'focus' => [],
            'avoid' => [],
            'stocks' => [],
        ];

        switch ($phase) {
            case '高潮期':
                $strategy['desc'] = '市场情绪高涨，龙头股强势，但需警惕高位风险';
                $strategy['focus'] = [
                    ['text' => '追踪龙头连板', 'reason' => '高潮期龙头效应明显，连板股溢价高'],
                    ['text' => '关注补涨机会', 'reason' => '同板块滞涨股有补涨预期'],
                    ['text' => '控制仓位', 'reason' => '高潮期后易出现分歧，需预留资金']
                ];
                $strategy['avoid'] = [
                    ['text' => '追高接力', 'reason' => '高位股获利盘多，容易被砸'],
                    ['text' => '满仓操作', 'reason' => '情绪顶点风险大，需保留灵活性']
                ];
                // 推荐：龙头+连板
                foreach ($stocks as $s) {
                    if (in_array('龙头', $s['hit_indicators']) || in_array('连板', $s['hit_indicators'])) {
                        $s['reason'] = '龙头/连板';
                        $strategy['stocks'][] = $s;
                    }
                    if (count($strategy['stocks']) >= 10) break;
                }
                break;

            case '回暖期':
                $strategy['desc'] = '市场开始回暖，重点关注弱转强和首板';
                $strategy['focus'] = [
                    ['text' => '弱转强个股', 'reason' => '前一日弱势今日转强，说明资金开始介入'],
                    ['text' => '首板确认', 'reason' => '回暖期首板成功率高，关注封板质量'],
                    ['text' => '板块轮动', 'reason' => '资金开始活跃，注意板块切换节奏']
                ];
                $strategy['avoid'] = [
                    ['text' => '高位股', 'reason' => '前期强势股可能补跌，风险大于机会'],
                    ['text' => '前期妖股', 'reason' => '妖股炒作结束后容易持续阴跌']
                ];
                // 推荐：弱转强+首板
                foreach ($stocks as $s) {
                    if (in_array('弱转强', $s['hit_indicators'])) {
                        $s['reason'] = '弱转强';
                        $strategy['stocks'][] = $s;
                    }
                    if (count($strategy['stocks']) >= 10) break;
                }
                break;

            case '修复期':
                $strategy['desc'] = '市场修复中，关注超跌反弹和技术信号';
                $strategy['focus'] = [
                    ['text' => '超跌反弹', 'reason' => '超跌股技术性反弹需求强，弹性大'],
                    ['text' => '技术金叉', 'reason' => 'MACD/KDJ金叉确认底部，可靠性高'],
                    ['text' => '底部放量', 'reason' => '放量说明资金开始进场，关注持续性']
                ];
                $strategy['avoid'] = [
                    ['text' => '追涨', 'reason' => '修复期反弹高度有限，追涨容易被套'],
                    ['text' => '重仓', 'reason' => '市场方向不明，保持仓位灵活']
                ];
                // 推荐：技术信号+放量
                foreach ($stocks as $s) {
                    if (in_array('MACD金叉', $s['hit_indicators']) ||
                        in_array('KDJ底部', $s['hit_indicators']) ||
                        in_array('放量', $s['hit_indicators'])) {
                        $s['reason'] = '技术信号';
                        $strategy['stocks'][] = $s;
                    }
                    if (count($strategy['stocks']) >= 10) break;
                }
                break;

            case '退潮期':
                $strategy['desc'] = '市场退潮，以防守为主，降低仓位';
                $strategy['focus'] = [
                    ['text' => '现金为王', 'reason' => '退潮期亏钱效应强，保住本金最重要'],
                    ['text' => '等待信号', 'reason' => '等待市场企稳信号，不急于抄底'],
                    ['text' => '小仓试错', 'reason' => '可用小仓位试探市场温度']
                ];
                $strategy['avoid'] = [
                    ['text' => '追涨停', 'reason' => '退潮期涨停次日大概率低开，接力风险大'],
                    ['text' => '重仓操作', 'reason' => '市场赚钱效应差，重仓亏损扩大'],
                    ['text' => '连板接力', 'reason' => '连板高度受限，接力大概率被埋']
                ];
                // 推荐：多因子高分+北向
                foreach ($stocks as $s) {
                    if (in_array('北向', $s['hit_indicators']) || in_array('多因子', $s['hit_indicators'])) {
                        $s['reason'] = '防守配置';
                        $strategy['stocks'][] = $s;
                    }
                    if (count($strategy['stocks']) >= 10) break;
                }
                break;

            case '冰点期':
                $strategy['desc'] = '市场冰点，耐心等待转机，可小仓布局';
                $strategy['focus'] = [
                    ['text' => '等待企稳', 'reason' => '冰点期需等待止跌信号，不要盲目抄底'],
                    ['text' => '超跌优质股', 'reason' => '优质股超跌后安全边际高，可分批布局'],
                    ['text' => '分批建仓', 'reason' => '底部不确定，分批买入降低风险']
                ];
                $strategy['avoid'] = [
                    ['text' => '恐慌杀跌', 'reason' => '冰点期往往是底部区域，杀跌容易卖在最低'],
                    ['text' => '重仓抄底', 'reason' => '底部可能反复磨，重仓抄底容易被套']
                ];
                // 推荐：突破+放量
                foreach ($stocks as $s) {
                    if (in_array('突破', $s['hit_indicators']) || in_array('放量', $s['hit_indicators'])) {
                        $s['reason'] = '企稳信号';
                        $strategy['stocks'][] = $s;
                    }
                    if (count($strategy['stocks']) >= 10) break;
                }
                break;

            default:
                $strategy['desc'] = '市场中性，均衡配置';
                $strategy['focus'] = ['多指标共振', '控制风险'];
                $strategy['avoid'] = ['单一押注'];
                // 推荐：多指标命中
                $strategy['stocks'] = array_slice(array_filter($stocks, fn($s) => $s['hit_count'] >= 3), 0, 10);
        }

        return $strategy;
    }

    // 板块强度分析 - 逆势上涨和共振板块
    protected function crawlSectorStrength(): array
    {
        try {
            // 获取大盘涨幅
            $marketUrl = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f3&secids=1.000001';
            $marketResp = $this->httpGet($marketUrl);
            $marketData = json_decode($marketResp, true);
            $marketChg = (float)($marketData['data']['diff'][0]['f3'] ?? 0);

            // 获取板块数据
            $sectorUrl = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=100&pn=1&np=1&fltt=2&invt=2&fs=m:90+t:2&fields=f12,f14,f3,f8,f104,f105,f128,f136,f140';
            $sectorResp = $this->httpGet($sectorUrl);
            $sectorData = json_decode($sectorResp, true);

            $sectors = [];
            $resonanceSectors = []; // 共振板块
            $counterSectors = [];   // 逆势板块

            if (!empty($sectorData['data']['diff'])) {
                foreach ($sectorData['data']['diff'] as $item) {
                    $sectorCode = $item['f12'] ?? '';
                    $sectorName = $item['f14'] ?? '';
                    $sectorChg = (float)($item['f3'] ?? 0);
                    $upCount = (int)($item['f104'] ?? 0);
                    $downCount = (int)($item['f105'] ?? 0);

                    $sectors[$sectorName] = [
                        'code' => $sectorCode,
                        'name' => $sectorName,
                        'pct_chg' => $sectorChg,
                        'up_count' => $upCount,
                        'down_count' => $downCount,
                        'strength' => round($sectorChg - $marketChg, 2),
                    ];

                    // 共振板块：与大盘同向且强度高
                    if ($marketChg >= 0 && $sectorChg > $marketChg + 0.5) {
                        $resonanceSectors[] = $sectors[$sectorName];
                    } elseif ($marketChg < 0 && $sectorChg < $marketChg - 0.5) {
                        $resonanceSectors[] = $sectors[$sectorName];
                    }

                    // 逆势板块：大盘跌但板块涨
                    if ($marketChg < 0 && $sectorChg > 0) {
                        $counterSectors[] = $sectors[$sectorName];
                    }
                }
            }

            // 获取个股数据
            $stockUrl = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=500&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f6,f8,f10,f12,f14,f100';
            $stockResp = $this->httpGet($stockUrl);
            $stockData = json_decode($stockResp, true);

            $counterTrend = [];  // 逆势上涨个股
            $sectorLeaders = []; // 板块龙头

            if (!empty($stockData['data']['diff'])) {
                // 按板块分组
                $stocksBySector = [];
                foreach ($stockData['data']['diff'] as $item) {
                    $code = $item['f12'] ?? '';
                    $name = $item['f14'] ?? '';
                    $price = (float)($item['f2'] ?? 0);
                    $pctChg = (float)($item['f3'] ?? 0);
                    $amount = round((float)($item['f6'] ?? 0) / 100000000, 2);
                    $turnover = (float)($item['f8'] ?? 0);
                    $volumeRatio = (float)($item['f10'] ?? 0);
                    $sector = $item['f100'] ?? '';

                    if ($price <= 0) continue;

                    // 查找板块涨幅 - 精确匹配或模糊匹配
                    $sectorChg = 0;
                    if (isset($sectors[$sector])) {
                        $sectorChg = $sectors[$sector]['pct_chg'];
                    } else {
                        // 模糊匹配板块名
                        foreach ($sectors as $sName => $sData) {
                            if (strpos($sector, $sName) !== false || strpos($sName, $sector) !== false) {
                                $sectorChg = $sData['pct_chg'];
                                break;
                            }
                        }
                    }

                    $strength = round($pctChg - $marketChg, 2);

                    $stockInfo = [
                        'code' => $code,
                        'name' => $name,
                        'price' => $price,
                        'pct_chg' => $pctChg,
                        'amount' => $amount,
                        'turnover' => $turnover,
                        'volume_ratio' => $volumeRatio,
                        'sector' => $sector,
                        'sector_chg' => $sectorChg,
                        'strength' => $strength,
                    ];

                    // 逆势上涨：板块强于大盘，个股强于板块，个股上涨
                    if ($sectorChg > $marketChg && $pctChg > $sectorChg && $pctChg > 0) {
                        $counterTrend[] = $stockInfo;
                    }

                    // 按板块分组
                    if (!isset($stocksBySector[$sector])) {
                        $stocksBySector[$sector] = [];
                    }
                    $stocksBySector[$sector][] = $stockInfo;
                }

                // 找出共振板块的龙头股
                usort($resonanceSectors, fn($a, $b) => abs($b['strength']) <=> abs($a['strength']));
                $topResonance = array_slice($resonanceSectors, 0, 10);

                foreach ($topResonance as &$sector) {
                    $sectorStocks = $stocksBySector[$sector['name']] ?? [];
                    usort($sectorStocks, fn($a, $b) => $b['pct_chg'] <=> $a['pct_chg']);
                    $sector['leaders'] = array_slice($sectorStocks, 0, 3);

                    // 添加到板块龙头列表
                    if (!empty($sector['leaders'])) {
                        foreach ($sector['leaders'] as $leader) {
                            $leader['is_sector_leader'] = true;
                            $sectorLeaders[] = $leader;
                        }
                    }
                }
            }

            // 排序
            usort($counterTrend, fn($a, $b) => $b['strength'] <=> $a['strength']);
            usort($sectorLeaders, fn($a, $b) => $b['pct_chg'] <=> $a['pct_chg']);

            return [
                'market_chg' => $marketChg,
                'counter_trend' => array_slice($counterTrend, 0, 30),
                'resonance_sectors' => $topResonance ?? [],
                'sector_leaders' => array_slice($sectorLeaders, 0, 30),
                'counter_sectors' => array_slice($counterSectors, 0, 10),
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'counter_trend' => [], 'resonance_sectors' => [], 'sector_leaders' => []];
        }
    }

    // 涨跌停统计 (使用同花顺接口)
    protected function crawlLimitUpDown(): array
    {
        try {
            // 涨停统计 - 同花顺接口
            $url = 'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=200&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004&filter=HS,GEM2STAR&order_field=330324&order_type=0';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $limitUp = [];
            if (!empty($data['data']['info'])) {
                foreach ($data['data']['info'] as $item) {
                    // 解析连板数
                    $highDays = $item['high_days'] ?? '首板';
                    $continuous = 1;
                    if (preg_match('/(\d+)天(\d+)板/', $highDays, $matches)) {
                        $continuous = (int)$matches[2];
                    } elseif (preg_match('/(\d+)板/', $highDays, $matches)) {
                        $continuous = (int)$matches[1];
                    }

                    // 转换首封时间戳为时间字符串
                    $firstTime = '';
                    if (!empty($item['first_limit_up_time'])) {
                        $ts = (int)$item['first_limit_up_time'];
                        if ($ts > 1000000000) {
                            $firstTime = date('H:i', $ts);
                        }
                    }

                    $limitUp[] = [
                        'code' => $item['code'] ?? '',
                        'name' => $item['name'] ?? '',
                        'price' => $item['latest'] ?? 0,
                        'pct_chg' => $item['change_rate'] ?? 0,
                        'amount' => isset($item['currency_value']) ? round($item['currency_value'] / 100000000, 2) : 0,
                        'first_time' => $firstTime,
                        'last_time' => '',
                        'open_times' => $item['open_num'] ?? 0,
                        'continuous' => $continuous,
                        'reason' => $item['reason_type'] ?? '',
                        'turnover' => $item['turnover_rate'] ?? 0,
                    ];
                }
            }

            // 跌停统计 - 同花顺接口
            $url2 = 'https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool?page=1&limit=200&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914&filter=HS,GEM2STAR&order_field=330324&order_type=0';
            $response2 = $this->httpGet($url2);
            $data2 = json_decode($response2, true);

            $limitDown = [];
            if (!empty($data2['data']['info'])) {
                foreach ($data2['data']['info'] as $item) {
                    $limitDown[] = [
                        'code' => $item['code'] ?? '',
                        'name' => $item['name'] ?? '',
                        'price' => $item['latest'] ?? 0,
                        'pct_chg' => $item['change_rate'] ?? 0,
                        'amount' => isset($item['currency_value']) ? round($item['currency_value'] / 100000000, 2) : 0,
                        'reason' => $item['reason_type'] ?? '',
                    ];
                }
            }

            return [
                'limit_up' => $limitUp,
                'limit_up_count' => count($limitUp),
                'limit_down' => $limitDown,
                'limit_down_count' => count($limitDown),
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'limit_up' => [], 'limit_down' => [], 'limit_up_count' => 0, 'limit_down_count' => 0];
        }
    }

    // 板块资金流向
    protected function crawlSectorFlow(): array
    {
        try {
            $url = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=100&pn=1&np=1&fltt=2&invt=2&fs=m:90+t:2&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $sectors = [];
            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    $sectors[] = [
                        'code' => $item['f12'] ?? '',
                        'name' => $item['f14'] ?? '',
                        'pct_chg' => $item['f3'] ?? 0,
                        'main_net' => isset($item['f62']) ? round($item['f62'] / 100000000, 2) : 0,
                        'main_pct' => $item['f184'] ?? 0,
                        'super_net' => isset($item['f66']) ? round($item['f66'] / 100000000, 2) : 0,
                        'big_net' => isset($item['f72']) ? round($item['f72'] / 100000000, 2) : 0,
                        'mid_net' => isset($item['f78']) ? round($item['f78'] / 100000000, 2) : 0,
                        'small_net' => isset($item['f84']) ? round($item['f84'] / 100000000, 2) : 0,
                    ];
                }
            }

            return $sectors;
        } catch (\Exception $e) {
            return ['error' => $e->getMessage()];
        }
    }

    // 北向资金
    protected function crawlNorthFlow(): array
    {
        try {
            $url = 'https://push2.eastmoney.com/api/qt/kamt.rtmin/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55,f56';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $result = [
                'hk_to_sh' => 0,
                'hk_to_sz' => 0,
                'total' => 0,
                'top_holdings' => [],
            ];

            if (!empty($data['data'])) {
                // f1=沪股通净流入(万), f3=深股通净流入(万)
                $hkToSh = (float)($data['data']['f1'] ?? 0);
                $hkToSz = (float)($data['data']['f3'] ?? 0);
                $result['hk_to_sh'] = round($hkToSh / 10000, 2);
                $result['hk_to_sz'] = round($hkToSz / 10000, 2);
                $result['total'] = round($result['hk_to_sh'] + $result['hk_to_sz'], 2);
            }

            // 北向资金持股TOP
            $url2 = 'https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=ADD_MARKET_CAP&sortTypes=-1&pageSize=20&pageNumber=1&columns=ALL&reportName=RPT_MUTUAL_STOCK_NORTHSTA';
            $response2 = $this->httpGet($url2);
            $data2 = json_decode($response2, true);

            if (!empty($data2['result']['data'])) {
                foreach ($data2['result']['data'] as $item) {
                    $result['top_holdings'][] = [
                        'code' => $item['SECURITY_CODE'] ?? '',
                        'name' => $item['SECURITY_NAME_ABBR'] ?? '',
                        'hold_shares' => isset($item['HOLD_SHARES']) ? round($item['HOLD_SHARES'] / 10000, 2) : 0,
                        'hold_market_cap' => isset($item['HOLD_MARKET_CAP']) ? round($item['HOLD_MARKET_CAP'] / 100000000, 2) : 0,
                        'hold_ratio' => $item['FREECAP_RATIO'] ?? 0,
                        'change_shares' => isset($item['ADD_SHARES']) ? round($item['ADD_SHARES'] / 10000, 2) : 0,
                    ];
                }
            }

            return $result;
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'hk_to_sh' => 0, 'hk_to_sz' => 0, 'total' => 0, 'top_holdings' => []];
        }
    }

    // 龙虎榜
    protected function crawlDragonTiger(string $date): array
    {
        try {
            $formatDate = substr($date, 0, 4) . '-' . substr($date, 4, 2) . '-' . substr($date, 6, 2);
            $url = "https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=SECURITY_CODE&sortTypes=1&pageSize=100&pageNumber=1&columns=ALL&reportName=RPT_DAILYBILLBOARD_DETAILSNEW&filter=(TRADE_DATE='{$formatDate}')";
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $list = [];
            if (!empty($data['result']['data'])) {
                foreach ($data['result']['data'] as $item) {
                    $list[] = [
                        'code' => $item['SECURITY_CODE'] ?? '',
                        'name' => $item['SECURITY_NAME_ABBR'] ?? '',
                        'close' => $item['CLOSE_PRICE'] ?? 0,
                        'pct_chg' => $item['CHANGE_RATE'] ?? 0,
                        'reason' => $item['EXPLAIN'] ?? '',
                        'buy_amount' => isset($item['BILLBOARD_BUY_AMT']) ? round($item['BILLBOARD_BUY_AMT'] / 10000, 2) : 0,
                        'sell_amount' => isset($item['BILLBOARD_SELL_AMT']) ? round($item['BILLBOARD_SELL_AMT'] / 10000, 2) : 0,
                        'net_amount' => isset($item['BILLBOARD_NET_AMT']) ? round($item['BILLBOARD_NET_AMT'] / 10000, 2) : 0,
                        'turnover' => $item['TURNOVERRATE'] ?? 0,
                    ];
                }
            }

            return $list;
        } catch (\Exception $e) {
            return [];
        }
    }

    // 市场情绪
    protected function crawlMarketEmotion(): array
    {
        try {
            $url = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f1,f2,f3,f4,f6,f12,f13,f104,f105,f106&secids=1.000001,0.399001,0.399006';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $result = [
                'up_count' => 0,
                'down_count' => 0,
                'flat_count' => 0,
                'up_ratio' => 0,
                'emotion_level' => '中性',
            ];

            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    if (($item['f12'] ?? '') === '000001') {
                        $result['up_count'] = $item['f104'] ?? 0;
                        $result['down_count'] = $item['f105'] ?? 0;
                        $result['flat_count'] = $item['f106'] ?? 0;
                    }
                }
            }

            $total = $result['up_count'] + $result['down_count'];
            $result['up_ratio'] = $total > 0 ? round($result['up_count'] / $total * 100, 1) : 0;
            $result['emotion_level'] = $this->getEmotionLevel($result['up_ratio']);

            return $result;
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'up_count' => 0, 'down_count' => 0, 'flat_count' => 0, 'up_ratio' => 0, 'emotion_level' => '未知'];
        }
    }

    // 热门股票 - 按换手率排序
    protected function crawlHotStocks(): array
    {
        try {
            // 按换手率排序获取人气股
            $url = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f8&po=1&pz=50&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f6,f8,f10,f12,f14';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $list = [];
            if (!empty($data['data']['diff'])) {
                $rank = 1;
                foreach ($data['data']['diff'] as $item) {
                    $code = $item['f12'] ?? '';
                    $name = $item['f14'] ?? '';
                    $pctChg = (float)($item['f3'] ?? 0);
                    $amount = round((float)($item['f6'] ?? 0) / 100000000, 2);
                    $turnover = (float)($item['f8'] ?? 0);

                    if (empty($name)) continue;

                    // 人气指数 = 换手率 + 涨幅 + 成交额/10
                    $hotIndex = round($turnover + abs($pctChg) + $amount / 10, 1);

                    $list[] = [
                        'code' => $code,
                        'name' => $name,
                        'rank' => $rank,
                        'rank_change' => 0,
                        'pct_chg' => $pctChg,
                        'amount' => $amount,
                        'turnover' => $turnover,
                        'hot_index' => $hotIndex,
                    ];
                    $rank++;
                }
            }

            return $list;
        } catch (\Exception $e) {
            return [];
        }
    }

    // 分时相对强度 (个股 > 板块 > 大盘)
    protected function crawlRelativeStrength(): array
    {
        try {
            // 1. 获取大盘涨跌幅
            $marketUrl = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f12,f14&secids=1.000001';
            $marketResp = $this->httpGet($marketUrl);
            $marketData = json_decode($marketResp, true);
            $marketChg = 0;
            if (!empty($marketData['data']['diff'])) {
                $marketChg = (float)($marketData['data']['diff'][0]['f3'] ?? 0);
            }

            // 2. 获取板块涨跌幅
            $sectorUrl = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=100&pn=1&np=1&fltt=2&invt=2&fs=m:90+t:2&fields=f12,f14,f3';
            $sectorResp = $this->httpGet($sectorUrl);
            $sectorData = json_decode($sectorResp, true);
            $sectors = [];
            if (!empty($sectorData['data']['diff'])) {
                foreach ($sectorData['data']['diff'] as $item) {
                    $sectors[$item['f14']] = (float)($item['f3'] ?? 0);
                }
            }

            // 3. 获取个股数据(涨幅>0,带板块信息,成交额,换手率,量比等)
            $stockUrl = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=500&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f6,f8,f10,f12,f14,f15,f16,f17,f18,f22,f100';
            $stockResp = $this->httpGet($stockUrl);
            $stockData = json_decode($stockResp, true);

            $result = [];
            if (!empty($stockData['data']['diff'])) {
                foreach ($stockData['data']['diff'] as $item) {
                    $stockChg = (float)($item['f3'] ?? 0);
                    $stockCode = $item['f12'] ?? '';
                    $stockName = $item['f14'] ?? '';
                    $sectorName = $item['f100'] ?? '';

                    // 获取板块涨跌幅
                    $sectorChg = $sectors[$sectorName] ?? 0;

                    // 筛选: 个股 > 板块 > 大盘 且 个股涨幅 > 0
                    if ($stockChg > $sectorChg && $sectorChg > $marketChg && $stockChg > 0) {
                        // 计算强度得分
                        $stockExcess = $stockChg - $sectorChg;
                        $sectorExcess = $sectorChg - $marketChg;
                        $strength = $stockExcess + $sectorExcess;

                        $result[] = [
                            'code' => $stockCode,
                            'name' => $stockName,
                            'sector' => $sectorName,
                            'price' => (float)($item['f2'] ?? 0),
                            'stock_chg' => $stockChg,
                            'sector_chg' => $sectorChg,
                            'market_chg' => $marketChg,
                            'stock_excess' => round($stockExcess, 2),
                            'sector_excess' => round($sectorExcess, 2),
                            'strength' => round($strength, 2),
                            'volume' => (float)($item['f5'] ?? 0), // 成交量(手)
                            'amount' => round((float)($item['f6'] ?? 0) / 100000000, 2), // 成交额(亿)
                            'turnover' => (float)($item['f8'] ?? 0), // 换手率
                            'volume_ratio' => (float)($item['f10'] ?? 0), // 量比
                            'high' => (float)($item['f15'] ?? 0), // 最高
                            'low' => (float)($item['f16'] ?? 0), // 最低
                            'open' => (float)($item['f17'] ?? 0), // 开盘
                            'pre_close' => (float)($item['f18'] ?? 0), // 昨收
                            'speed' => (float)($item['f22'] ?? 0), // 涨速
                        ];
                    }
                }
            }

            // 按强度排序
            usort($result, function($a, $b) {
                return $b['strength'] <=> $a['strength'];
            });

            return [
                'market_chg' => $marketChg,
                'stocks' => array_slice($result, 0, 50), // 取前50
                'count' => count($result),
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'market_chg' => 0, 'stocks' => [], 'count' => 0];
        }
    }

    // 情绪等级
    protected function getEmotionLevel(float $upRatio): string
    {
        if ($upRatio >= 70) return '极度贪婪';
        if ($upRatio >= 55) return '贪婪';
        if ($upRatio >= 45) return '中性';
        if ($upRatio >= 30) return '恐惧';
        return '极度恐惧';
    }

    // 情绪周期判断 (炒股养家心法量化)
    protected function crawlEmotionCycle(array $limitUpDown): array
    {
        try {
            $result = [
                'cycle_phase' => '未知',
                'cycle_score' => 0,
                'indicators' => [],
                'yesterday_limit_up_performance' => [], // 昨日涨停今日表现
                'profit_effect' => 0, // 赚钱效应
                'loss_effect' => 0, // 亏钱效应
                'max_continuous' => 0, // 最高连板
                'limit_up_count' => 0,
                'limit_down_count' => 0,
                'broken_rate' => 0, // 炸板率
                'promotion_rate' => 0, // 首板晋级率
            ];

            // 1. 从同花顺获取昨日涨停统计数据
            $url = 'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=1&field=199112&filter=HS,GEM2STAR&order_field=330324&order_type=0';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $yesterdayNum = 0;
            $yesterdayOpenNum = 0;
            $avgYesterdayChg = 0;

            if (!empty($data['data']['limit_up_count']['yesterday'])) {
                $yesterday = $data['data']['limit_up_count']['yesterday'];
                $yesterdayNum = (int)($yesterday['num'] ?? 0);
                $yesterdayOpenNum = (int)($yesterday['open_num'] ?? 0);
            }

            // 获取昨日涨停今日表现详情（从今日连板股中筛选）
            $url2 = 'https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_pool?page=1&limit=100&field=199112,10,9001,330323,330324,330325,9002&filter=HS,GEM2STAR&order_field=330324&order_type=0';
            $response2 = $this->httpGet($url2);
            $data2 = json_decode($response2, true);

            $yesterdayList = [];
            $profitCount = 0;
            $lossCount = 0;
            $totalChg = 0;

            // 连板股是昨日涨停今日继续涨停的
            if (!empty($data2['data']['info'])) {
                foreach ($data2['data']['info'] as $item) {
                    $chg = (float)($item['change_rate'] ?? 0);
                    $yesterdayList[] = [
                        'code' => $item['code'] ?? '',
                        'name' => $item['name'] ?? '',
                        'price' => $item['latest'] ?? 0,
                        'pct_chg' => $chg,
                        'amount' => 0,
                        'status' => '连板',
                    ];
                    $totalChg += $chg;
                    $profitCount++;
                }
            }

            // 昨日涨停今日开板的估算为亏损
            $openBoardCount = $yesterdayOpenNum;
            $lossCount = $openBoardCount;

            // 计算赚钱效应
            $totalYesterday = $yesterdayNum > 0 ? $yesterdayNum : ($profitCount + $lossCount);
            if ($totalYesterday > 0) {
                // 继续涨停的占比作为赚钱效应
                $result['profit_effect'] = round($profitCount / $totalYesterday * 100, 1);
                $result['loss_effect'] = round($lossCount / $totalYesterday * 100, 1);
                $avgYesterdayChg = $profitCount > 0 ? round($totalChg / $profitCount, 2) : 0;
            }

            $result['yesterday_limit_up_performance'] = $yesterdayList;
            $result['yesterday_total'] = $yesterdayNum;
            $result['yesterday_continue'] = $profitCount;
            $result['yesterday_open'] = $lossCount;

            // 2. 获取连板数据
            $limitUpList = $limitUpDown['limit_up'] ?? [];
            $result['limit_up_count'] = count($limitUpList);
            $result['limit_down_count'] = $limitUpDown['limit_down_count'] ?? 0;

            // 统计连板高度分布
            $continuousStats = [1 => 0, 2 => 0, 3 => 0, 4 => 0, 5 => 0];
            $maxContinuous = 0;
            foreach ($limitUpList as $stock) {
                $continuous = (int)($stock['continuous'] ?? 1);
                if ($continuous > $maxContinuous) $maxContinuous = $continuous;
                if ($continuous >= 5) {
                    $continuousStats[5]++;
                } else {
                    $continuousStats[$continuous]++;
                }
            }
            $result['max_continuous'] = $maxContinuous;
            $result['continuous_stats'] = $continuousStats;

            // 3. 炸板率 (开板次数/涨停数)
            $totalOpenTimes = 0;
            foreach ($limitUpList as $stock) {
                $totalOpenTimes += (int)($stock['open_times'] ?? 0);
            }
            $result['broken_rate'] = $result['limit_up_count'] > 0
                ? round($totalOpenTimes / $result['limit_up_count'] * 100, 1)
                : 0;

            // 4. 首板晋级率 (2连板/首板)
            $firstBoard = $continuousStats[1] ?? 0;
            $secondBoard = $continuousStats[2] ?? 0;
            $result['promotion_rate'] = $firstBoard > 0
                ? round($secondBoard / $firstBoard * 100, 1)
                : 0;

            // 5. 计算情绪周期得分和判断
            $score = 0;

            // 赚钱效应权重最高
            if ($result['profit_effect'] >= 70) $score += 30;
            elseif ($result['profit_effect'] >= 50) $score += 20;
            elseif ($result['profit_effect'] >= 30) $score += 10;
            else $score -= 10;

            // 连板高度
            if ($maxContinuous >= 5) $score += 20;
            elseif ($maxContinuous >= 3) $score += 10;
            elseif ($maxContinuous >= 2) $score += 5;

            // 涨停数量
            if ($result['limit_up_count'] >= 80) $score += 20;
            elseif ($result['limit_up_count'] >= 50) $score += 10;
            elseif ($result['limit_up_count'] >= 30) $score += 5;
            else $score -= 5;

            // 涨跌停比
            $upDownRatio = $result['limit_down_count'] > 0
                ? $result['limit_up_count'] / $result['limit_down_count']
                : $result['limit_up_count'];
            if ($upDownRatio >= 5) $score += 15;
            elseif ($upDownRatio >= 2) $score += 10;
            elseif ($upDownRatio >= 1) $score += 5;
            else $score -= 10;

            // 炸板率
            if ($result['broken_rate'] <= 20) $score += 10;
            elseif ($result['broken_rate'] <= 40) $score += 5;
            else $score -= 5;

            // 首板晋级率
            if ($result['promotion_rate'] >= 30) $score += 5;
            elseif ($result['promotion_rate'] >= 20) $score += 3;

            $result['cycle_score'] = $score;

            // 判断周期阶段
            if ($score >= 70) {
                $result['cycle_phase'] = '高潮期';
                $result['phase_desc'] = '情绪亢奋，注意高位风险';
                $result['strategy'] = '龙头换手接力，谨慎追高';
            } elseif ($score >= 50) {
                $result['cycle_phase'] = '回暖期';
                $result['phase_desc'] = '赚钱效应显现，可积极参与';
                $result['strategy'] = '参与龙头首板，低吸强势股';
            } elseif ($score >= 30) {
                $result['cycle_phase'] = '修复期';
                $result['phase_desc'] = '市场企稳，等待龙头确认';
                $result['strategy'] = '观察龙头能否走出，轻仓试错';
            } elseif ($score >= 10) {
                $result['cycle_phase'] = '退潮期';
                $result['phase_desc'] = '高位股分歧，亏钱效应增加';
                $result['strategy'] = '减少操作，等待新龙头';
            } else {
                $result['cycle_phase'] = '冰点期';
                $result['phase_desc'] = '亏钱效应强，大面多';
                $result['strategy'] = '空仓观望，等待转机信号';
            }

            // 指标明细
            $result['indicators'] = [
                ['name' => '昨涨停平均', 'value' => $avgYesterdayChg . '%', 'score' => $avgYesterdayChg >= 2 ? '好' : ($avgYesterdayChg >= 0 ? '中' : '差')],
                ['name' => '赚钱效应', 'value' => $result['profit_effect'] . '%', 'score' => $result['profit_effect'] >= 60 ? '好' : ($result['profit_effect'] >= 40 ? '中' : '差')],
                ['name' => '连板高度', 'value' => $maxContinuous . '板', 'score' => $maxContinuous >= 4 ? '好' : ($maxContinuous >= 2 ? '中' : '差')],
                ['name' => '涨停家数', 'value' => $result['limit_up_count'], 'score' => $result['limit_up_count'] >= 60 ? '好' : ($result['limit_up_count'] >= 30 ? '中' : '差')],
                ['name' => '跌停家数', 'value' => $result['limit_down_count'], 'score' => $result['limit_down_count'] <= 10 ? '好' : ($result['limit_down_count'] <= 30 ? '中' : '差')],
                ['name' => '炸板率', 'value' => $result['broken_rate'] . '%', 'score' => $result['broken_rate'] <= 30 ? '好' : ($result['broken_rate'] <= 50 ? '中' : '差')],
                ['name' => '晋级率', 'value' => $result['promotion_rate'] . '%', 'score' => $result['promotion_rate'] >= 25 ? '好' : ($result['promotion_rate'] >= 15 ? '中' : '差')],
            ];

            return $result;
        } catch (\Exception $e) {
            return [
                'error' => $e->getMessage(),
                'cycle_phase' => '未知',
                'cycle_score' => 0,
                'indicators' => [],
            ];
        }
    }

    // 弱转强/强转弱识别
    protected function crawlStrengthChange(): array
    {
        try {
            // 获取个股数据 (开盘、最高、最低、现价、涨跌幅)
            $url = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=500&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f6,f8,f12,f14,f15,f16,f17,f18,f22';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $weakToStrong = []; // 弱转强
            $strongToWeak = []; // 强转弱

            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    $open = (float)($item['f17'] ?? 0);
                    $high = (float)($item['f15'] ?? 0);
                    $low = (float)($item['f16'] ?? 0);
                    $close = (float)($item['f2'] ?? 0);
                    $preClose = (float)($item['f18'] ?? 0);
                    $pctChg = (float)($item['f3'] ?? 0);

                    if ($preClose <= 0 || $open <= 0 || $close <= 0) continue;

                    $openChg = round(($open - $preClose) / $preClose * 100, 2);
                    $amplitude = $high > 0 && $low > 0 ? round(($high - $low) / $preClose * 100, 2) : 0;

                    // 弱转强: 低开高走 (开盘跌>1%, 收盘涨>2%)
                    // 或: 盘中最低跌>3%, 收盘涨>0%
                    $lowChg = round(($low - $preClose) / $preClose * 100, 2);
                    if (($openChg <= -1 && $pctChg >= 2) || ($lowChg <= -3 && $pctChg >= 0)) {
                        $weakToStrong[] = [
                            'code' => $item['f12'] ?? '',
                            'name' => $item['f14'] ?? '',
                            'open_chg' => $openChg,
                            'low_chg' => $lowChg,
                            'pct_chg' => $pctChg,
                            'amplitude' => $amplitude,
                            'amount' => isset($item['f6']) ? round($item['f6'] / 100000000, 2) : 0,
                            'turnover' => $item['f8'] ?? 0,
                            'strength' => round($pctChg - $openChg, 2), // 转强幅度
                        ];
                    }

                    // 强转弱: 高开低走 (开盘涨>2%, 收盘跌或涨幅<开盘涨幅的一半)
                    // 或: 盘中最高涨>5%, 收盘涨幅<最高涨幅的一半
                    $highChg = round(($high - $preClose) / $preClose * 100, 2);
                    if (($openChg >= 2 && $pctChg < $openChg * 0.5) || ($highChg >= 5 && $pctChg < $highChg * 0.5)) {
                        $strongToWeak[] = [
                            'code' => $item['f12'] ?? '',
                            'name' => $item['f14'] ?? '',
                            'open_chg' => $openChg,
                            'high_chg' => $highChg,
                            'pct_chg' => $pctChg,
                            'amplitude' => $amplitude,
                            'amount' => isset($item['f6']) ? round($item['f6'] / 100000000, 2) : 0,
                            'turnover' => $item['f8'] ?? 0,
                            'weakness' => round($highChg - $pctChg, 2), // 转弱幅度
                        ];
                    }
                }
            }

            // 按转强/转弱幅度排序
            usort($weakToStrong, fn($a, $b) => $b['strength'] <=> $a['strength']);
            usort($strongToWeak, fn($a, $b) => $b['weakness'] <=> $a['weakness']);

            return [
                'weak_to_strong' => array_slice($weakToStrong, 0, 30),
                'strong_to_weak' => array_slice($strongToWeak, 0, 30),
                'weak_to_strong_count' => count($weakToStrong),
                'strong_to_weak_count' => count($strongToWeak),
            ];
        } catch (\Exception $e) {
            return [
                'error' => $e->getMessage(),
                'weak_to_strong' => [],
                'strong_to_weak' => [],
            ];
        }
    }

    // 龙头股识别 (根据炒股养家心法)
    protected function identifyLeaderStocks(array $limitUpDown): array
    {
        try {
            $limitUpList = $limitUpDown['limit_up'] ?? [];
            if (empty($limitUpList)) {
                return ['leaders' => [], 'by_continuous' => []];
            }

            // 获取详细数据 (成交额、换手率、流通市值)
            $codes = array_column($limitUpList, 'code');
            $codeStr = implode(',', array_map(fn($c) => (strpos($c, '6') === 0 ? '1.' : '0.') . $c, $codes));

            $url = "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f5,f6,f8,f12,f14,f20,f21&secids={$codeStr}";
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $stockDetails = [];
            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    $stockDetails[$item['f12']] = [
                        'amount' => isset($item['f6']) ? round($item['f6'] / 100000000, 2) : 0, // 成交额(亿)
                        'turnover' => $item['f8'] ?? 0, // 换手率
                        'market_cap' => isset($item['f21']) ? round($item['f21'] / 100000000, 2) : 0, // 流通市值(亿)
                    ];
                }
            }

            // 计算龙头得分
            $leaders = [];
            foreach ($limitUpList as $stock) {
                $code = $stock['code'];
                $continuous = (int)($stock['continuous'] ?? 1);
                $openTimes = (int)($stock['open_times'] ?? 0);
                $firstTime = $stock['first_time'] ?? '15:00';
                $detail = $stockDetails[$code] ?? ['amount' => 0, 'turnover' => 0, 'market_cap' => 0];

                $score = 0;

                // 连板高度 (权重最高)
                $score += $continuous * 15;

                // 封板时间 (越早越好)
                $timeParts = explode(':', $firstTime);
                $minutes = (int)$timeParts[0] * 60 + (int)($timeParts[1] ?? 0);
                if ($minutes <= 570) $score += 20; // 9:30前
                elseif ($minutes <= 600) $score += 15; // 10:00前
                elseif ($minutes <= 660) $score += 10; // 11:00前
                elseif ($minutes <= 780) $score += 5; // 13:00前

                // 开板次数 (越少越好)
                if ($openTimes == 0) $score += 15;
                elseif ($openTimes <= 1) $score += 10;
                elseif ($openTimes <= 3) $score += 5;
                else $score -= 5;

                // 成交额 (适中最好，太大说明分歧大)
                $amount = $detail['amount'];
                if ($amount >= 3 && $amount <= 15) $score += 10;
                elseif ($amount >= 1 && $amount <= 30) $score += 5;
                elseif ($amount > 50) $score -= 5;

                // 换手率 (适中最好)
                $turnover = $detail['turnover'];
                if ($turnover >= 5 && $turnover <= 20) $score += 10;
                elseif ($turnover >= 3 && $turnover <= 30) $score += 5;
                elseif ($turnover > 40) $score -= 5;

                // 市值 (小市值加分)
                $marketCap = $detail['market_cap'];
                if ($marketCap > 0 && $marketCap <= 50) $score += 10;
                elseif ($marketCap <= 100) $score += 5;
                elseif ($marketCap > 500) $score -= 5;

                $leaders[] = [
                    'code' => $code,
                    'name' => $stock['name'],
                    'continuous' => $continuous,
                    'first_time' => $firstTime,
                    'open_times' => $openTimes,
                    'amount' => $amount,
                    'turnover' => $turnover,
                    'market_cap' => $marketCap,
                    'reason' => $stock['reason'] ?? '',
                    'score' => $score,
                    'is_leader' => $score >= 50, // 得分>=50判定为龙头
                ];
            }

            // 按得分排序
            usort($leaders, fn($a, $b) => $b['score'] <=> $a['score']);

            // 按连板数分组
            $byContinuous = [];
            foreach ($leaders as $leader) {
                $c = $leader['continuous'];
                $key = $c >= 5 ? '5+板' : $c . '板';
                if (!isset($byContinuous[$key])) {
                    $byContinuous[$key] = [];
                }
                $byContinuous[$key][] = $leader;
            }

            return [
                'leaders' => array_slice($leaders, 0, 30), // 取前30
                'by_continuous' => $byContinuous,
                'top_leader' => !empty($leaders) ? $leaders[0] : null,
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'leaders' => [], 'by_continuous' => []];
        }
    }

    // 读取已保存的数据
    // 量价分析 (成交额TOP、底部放量、顶部放量)
    protected function crawlVolumeAnalysis(): array
    {
        try {
            // 获取个股数据
            $url = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f6&po=1&pz=200&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f6,f8,f10,f12,f14,f15,f16,f17,f18,f22,f100';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $volumeTop = [];
            $bottomVolume = [];
            $topVolume = [];

            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    $code = $item['f12'] ?? '';
                    $name = $item['f14'] ?? '';
                    $price = (float)($item['f2'] ?? 0);
                    $pctChg = (float)($item['f3'] ?? 0);
                    $amount = round((float)($item['f6'] ?? 0) / 100000000, 2);
                    $turnover = (float)($item['f8'] ?? 0);
                    $volumeRatio = (float)($item['f10'] ?? 0);
                    $high = (float)($item['f15'] ?? 0);
                    $low = (float)($item['f16'] ?? 0);
                    $preClose = (float)($item['f18'] ?? 0);

                    // 成交额TOP
                    $volumeTop[] = [
                        'code' => $code,
                        'name' => $name,
                        'price' => $price,
                        'pct_chg' => $pctChg,
                        'amount' => $amount,
                        'turnover' => $turnover,
                        'volume_ratio' => $volumeRatio,
                    ];

                    // 计算价格位置 (简化版)
                    $pricePosition = 50; // 默认中位
                    if ($high > 0 && $low > 0 && $preClose > 0) {
                        $range = $high - $low;
                        if ($range > 0) {
                            $pricePosition = round(($price - $low) / $range * 100);
                        }
                    }

                    // 底部放量: 量比>2, 涨幅>0, 换手>3%
                    if ($volumeRatio > 2 && $pctChg > 0 && $turnover > 3) {
                        $bottomVolume[] = [
                            'code' => $code,
                            'name' => $name,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'turnover' => $turnover,
                            'volume_ratio' => $volumeRatio,
                            'score' => round($volumeRatio * $pctChg, 2),
                        ];
                    }

                    // 顶部放量: 量比>2, 跌幅, 高换手
                    if ($volumeRatio > 2 && $pctChg < 0 && $turnover > 5) {
                        $topVolume[] = [
                            'code' => $code,
                            'name' => $name,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'turnover' => $turnover,
                            'volume_ratio' => $volumeRatio,
                        ];
                    }
                }
            }

            // 排序
            usort($bottomVolume, fn($a, $b) => $b['score'] <=> $a['score']);
            usort($topVolume, fn($a, $b) => $b['volume_ratio'] <=> $a['volume_ratio']);

            return [
                'volume_top' => array_slice($volumeTop, 0, 50),
                'bottom_volume' => array_slice($bottomVolume, 0, 30),
                'top_volume' => array_slice($topVolume, 0, 30),
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'volume_top' => [], 'bottom_volume' => [], 'top_volume' => []];
        }
    }

    // 多因子叠加选股
    protected function crawlMultiFactor(): array
    {
        try {
            // 获取个股完整数据
            $url = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=500&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f6,f8,f10,f12,f14,f15,f16,f17,f18,f22,f100';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            // 获取大盘涨幅
            $marketUrl = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f3&secids=1.000001';
            $marketResp = $this->httpGet($marketUrl);
            $marketData = json_decode($marketResp, true);
            $marketChg = (float)($marketData['data']['diff'][0]['f3'] ?? 0);

            // 获取板块涨幅
            $sectorUrl = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=100&pn=1&np=1&fltt=2&invt=2&fs=m:90+t:2&fields=f12,f14,f3';
            $sectorResp = $this->httpGet($sectorUrl);
            $sectorData = json_decode($sectorResp, true);
            $sectors = [];
            if (!empty($sectorData['data']['diff'])) {
                foreach ($sectorData['data']['diff'] as $item) {
                    $sectors[$item['f14']] = (float)($item['f3'] ?? 0);
                }
            }

            $stocks = [];
            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    $code = $item['f12'] ?? '';
                    $name = $item['f14'] ?? '';
                    $price = (float)($item['f2'] ?? 0);
                    $pctChg = (float)($item['f3'] ?? 0);
                    $amount = round((float)($item['f6'] ?? 0) / 100000000, 2);
                    $turnover = (float)($item['f8'] ?? 0);
                    $volumeRatio = (float)($item['f10'] ?? 0);
                    $high = (float)($item['f15'] ?? 0);
                    $low = (float)($item['f16'] ?? 0);
                    $open = (float)($item['f17'] ?? 0);
                    $preClose = (float)($item['f18'] ?? 0);
                    $speed = (float)($item['f22'] ?? 0);
                    $sector = $item['f100'] ?? '';
                    $sectorChg = $sectors[$sector] ?? 0;

                    if ($price <= 0 || $preClose <= 0) continue;

                    // 计算各项因子得分
                    $score = 0;
                    $factors = [];

                    // 1. 涨幅因子 (0-20分)
                    $chgScore = min(20, max(0, $pctChg * 2));
                    $score += $chgScore;
                    $factors['涨幅'] = round($chgScore);

                    // 2. 相对强度因子 (0-20分)
                    $relStrength = $pctChg - $marketChg;
                    $relScore = min(20, max(0, $relStrength * 2));
                    $score += $relScore;
                    $factors['相对强度'] = round($relScore);

                    // 3. 板块强度因子 (0-15分)
                    $sectorScore = min(15, max(0, $sectorChg * 1.5));
                    $score += $sectorScore;
                    $factors['板块'] = round($sectorScore);

                    // 4. 量比因子 (0-15分)
                    $volScore = 0;
                    if ($volumeRatio >= 3) $volScore = 15;
                    elseif ($volumeRatio >= 2) $volScore = 10;
                    elseif ($volumeRatio >= 1.5) $volScore = 5;
                    $score += $volScore;
                    $factors['量比'] = $volScore;

                    // 5. 弱转强因子 (0-15分)
                    $openChg = round(($open - $preClose) / $preClose * 100, 2);
                    $wtScore = 0;
                    if ($openChg < 0 && $pctChg > 2) {
                        $wtScore = min(15, ($pctChg - $openChg) * 1.5);
                    }
                    $score += $wtScore;
                    $factors['弱转强'] = round($wtScore);

                    // 6. 涨速因子 (0-15分)
                    $speedScore = min(15, max(0, abs($speed) * 3));
                    $score += $speedScore;
                    $factors['涨速'] = round($speedScore);

                    // 只保留得分>30的股票
                    if ($score > 30) {
                        $stocks[] = [
                            'code' => $code,
                            'name' => $name,
                            'sector' => $sector,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'turnover' => $turnover,
                            'volume_ratio' => $volumeRatio,
                            'speed' => $speed,
                            'score' => round($score),
                            'factors' => $factors,
                            'sector_chg' => $sectorChg,
                            'market_chg' => $marketChg,
                        ];
                    }
                }
            }

            // 按得分排序
            usort($stocks, fn($a, $b) => $b['score'] <=> $a['score']);

            return [
                'stocks' => array_slice($stocks, 0, 50),
                'count' => count($stocks),
                'market_chg' => $marketChg,
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'stocks' => [], 'count' => 0];
        }
    }

    // 技术指标选股
    protected function crawlTechnicalIndicators(): array
    {
        try {
            // 获取个股数据用于技术分析
            $url = 'https://push2.eastmoney.com/api/qt/clist/get?fid=f3&po=1&pz=500&pn=1&np=1&fltt=2&invt=2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f6,f8,f10,f12,f14,f15,f16,f17,f18,f22,f100';
            $response = $this->httpGet($url);
            $data = json_decode($response, true);

            $macdGolden = [];
            $kdjBottom = [];
            $rsiOversold = [];
            $breakout = [];

            if (!empty($data['data']['diff'])) {
                foreach ($data['data']['diff'] as $item) {
                    $code = $item['f12'] ?? '';
                    $name = $item['f14'] ?? '';
                    $price = (float)($item['f2'] ?? 0);
                    $pctChg = (float)($item['f3'] ?? 0);
                    $amount = round((float)($item['f6'] ?? 0) / 100000000, 2);
                    $turnover = (float)($item['f8'] ?? 0);
                    $volumeRatio = (float)($item['f10'] ?? 0);
                    $high = (float)($item['f15'] ?? 0);
                    $low = (float)($item['f16'] ?? 0);
                    $open = (float)($item['f17'] ?? 0);
                    $preClose = (float)($item['f18'] ?? 0);

                    if ($price <= 0 || $preClose <= 0) continue;

                    // 简化的技术形态判断 (基于价格行为)
                    $priceRange = $high - $low;
                    $bodySize = abs($price - $open);
                    $upperShadow = $high - max($price, $open);
                    $lowerShadow = min($price, $open) - $low;

                    // MACD金叉信号: 涨幅1-8%, 量比>1, 收阳
                    if ($pctChg >= 1 && $pctChg <= 8 && $volumeRatio > 1 && $price > $open) {
                        $macdGolden[] = [
                            'code' => $code,
                            'name' => $name,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'volume_ratio' => $volumeRatio,
                            'signal' => '金叉放量',
                        ];
                    }

                    // KDJ底部信号: 反弹+下影线
                    if ($pctChg > 0 && $priceRange > 0 && $lowerShadow / $priceRange > 0.2) {
                        $kdjBottom[] = [
                            'code' => $code,
                            'name' => $name,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'lower_shadow' => round($lowerShadow / $priceRange * 100, 1),
                            'signal' => '底部反转',
                        ];
                    }

                    // RSI超卖反弹: 反弹+放量
                    if ($pctChg >= 2 && $volumeRatio > 1.5 && $turnover > 2) {
                        $rsiOversold[] = [
                            'code' => $code,
                            'name' => $name,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'turnover' => $turnover,
                            'signal' => '超卖反弹',
                        ];
                    }

                    // 突破形态: 涨幅>3%, 放量
                    if ($pctChg >= 3 && $volumeRatio > 1.5) {
                        $breakout[] = [
                            'code' => $code,
                            'name' => $name,
                            'price' => $price,
                            'pct_chg' => $pctChg,
                            'amount' => $amount,
                            'volume_ratio' => $volumeRatio,
                            'type' => '放量突破',
                        ];
                    }
                }
            }

            // 排序
            usort($macdGolden, fn($a, $b) => $b['pct_chg'] <=> $a['pct_chg']);
            usort($kdjBottom, fn($a, $b) => $b['lower_shadow'] <=> $a['lower_shadow']);
            usort($rsiOversold, fn($a, $b) => $b['pct_chg'] <=> $a['pct_chg']);
            usort($breakout, fn($a, $b) => $b['pct_chg'] <=> $a['pct_chg']);

            return [
                'macd_golden' => array_slice($macdGolden, 0, 30),
                'kdj_bottom' => array_slice($kdjBottom, 0, 30),
                'rsi_oversold' => array_slice($rsiOversold, 0, 30),
                'breakout' => array_slice($breakout, 0, 30),
            ];
        } catch (\Exception $e) {
            return ['error' => $e->getMessage(), 'macd_golden' => [], 'kdj_bottom' => [], 'rsi_oversold' => [], 'breakout' => []];
        }
    }

    public function getData(string $date): ?array
    {
        $filename = $this->dataPath . "eastmoney_{$date}.json";
        if (file_exists($filename)) {
            return json_decode(file_get_contents($filename), true);
        }
        return null;
    }

    // 获取历史数据列表
    public function getDataList(): array
    {
        $files = glob($this->dataPath . 'eastmoney_*.json');
        $list = [];
        foreach ($files as $file) {
            preg_match('/eastmoney_(\d{8})\.json/', $file, $matches);
            if (!empty($matches[1])) {
                $list[] = [
                    'date' => $matches[1],
                    'file' => basename($file),
                    'size' => filesize($file),
                    'time' => date('Y-m-d H:i:s', filemtime($file)),
                ];
            }
        }
        usort($list, fn($a, $b) => $b['date'] <=> $a['date']);
        return $list;
    }
}
