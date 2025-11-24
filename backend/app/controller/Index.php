<?php
declare(strict_types=1);

namespace app\controller;

use think\facade\Db;
use think\Request;
use app\service\TushareService;
use app\service\IndicatorService;
use app\service\EastmoneyCrawler;

class Index
{
    protected $tushare;
    protected $indicator;
    protected $crawler;

    public function __construct()
    {
        $this->tushare = new TushareService();
        $this->indicator = new IndicatorService();
        $this->crawler = new EastmoneyCrawler();
    }

    // 统一响应
    protected function success($data)
    {
        return json(['code' => 0, 'data' => $data]);
    }

    protected function error($msg)
    {
        return json(['code' => 1, 'msg' => $msg]);
    }

    // 成交量TOP50
    public function volumeTop(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->tushare->getVolumeTop50($date);
        return $this->success($data);
    }

    // RSI超卖
    public function oversold(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getOversoldStocks($date);
        return $this->success($data);
    }

    // KDJ见底
    public function kdjBottom(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getKDJBottomStocks($date);
        return $this->success($data);
    }

    // MACD金叉
    public function macdGolden(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getMACDGoldenCross($date);
        return $this->success($data);
    }

    // 底部放量
    public function bottomVolume(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getBottomVolumeStocks($date);
        return $this->success($data);
    }

    // 行业异动
    public function industryHot(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getIndustryHotStocks($date);
        return $this->success($data);
    }

    // 大盘指数
    public function marketIndex(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getMarketIndex($date);
        return $this->success($data);
    }

    // 逆势上涨
    public function counterTrend(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getCounterTrendStocks($date);
        return $this->success($data);
    }

    // 市场统计
    public function marketStats(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getMarketStats($date);
        return $this->success($data);
    }

    // 涨停列表
    public function limitUp(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getLimitUpList($date);
        return $this->success($data);
    }

    // 跌停列表
    public function limitDown(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getLimitDownList($date);
        return $this->success($data);
    }

    // 龙虎榜
    public function dragonTiger(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->tushare->getDragonTiger($date);
        return $this->success($data);
    }

    // 北向资金买入
    public function northBuy(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->tushare->getNorthBuy($date);
        return $this->success($data);
    }

    // 融资买入
    public function marginBuy(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->tushare->getMarginBuy($date);
        return $this->success($data);
    }

    // 突破形态
    public function breakout(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getBreakoutStocks($date);
        return $this->success($data);
    }

    // 顶部放量
    public function topVolume(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getTopVolumeStocks($date);
        return $this->success($data);
    }

    // 跳空高开
    public function gapUp(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getGapUpStocks($date);
        return $this->success($data);
    }

    // 跳空低开
    public function gapDown(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getGapDownStocks($date);
        return $this->success($data);
    }

    // 行业跳空
    public function industryGap(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getIndustryGap($date);
        return $this->success($data);
    }

    // 获取复盘记录
    public function getReview(Request $request)
    {
        $date = $request->get('date', date('Y-m-d'));
        $record = Db::table('review_records')
            ->where('trade_date', $date)
            ->find();
        return $this->success($record);
    }

    // 保存复盘记录
    public function saveReview(Request $request)
    {
        $date = $request->post('date', date('Y-m-d'));
        $content = $request->post('content', '');

        Db::table('review_records')->replace((bool)[
            'trade_date' => $date,
            'content' => $content,
        ]);

        return $this->success(['success' => true]);
    }

    // 复盘历史
    public function reviewHistory()
    {
        $list = Db::table('review_records')
            ->field("trade_date, CONCAT(LEFT(content, 30), '...') as preview")
            ->order('trade_date', 'desc')
            ->limit(20)
            ->select();
        return $this->success($list);
    }

    // 同步股票列表
    public function syncStocks()
    {
        $count = $this->tushare->fetchStockList();
        return $this->success(['synced' => $count]);
    }

    // 同步日线数据
    public function syncDaily(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $count = $this->tushare->fetchDailyQuotes($date);
        return $this->success(['synced' => $count, 'date' => $date]);
    }

    // 计算指标
    public function calcIndicators(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $stocks = Db::table('daily_quotes')
            ->where('trade_date', $date)
            ->distinct(true)
            ->column('ts_code');

        $count = 0;
        foreach ($stocks as $tsCode) {
            $history = $this->tushare->getStockHistory($tsCode, 100);
            if ($this->indicator->calculate($tsCode, $history)) {
                $count++;
            }
        }
        return $this->success(['calculated' => $count]);
    }

    // 爬取东方财富数据
    public function crawlEastmoney(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->crawler->crawlDaily($date);
        return $this->success($data);
    }

    // 获取东方财富数据
    public function getEastmoneyData(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->crawler->getData($date);
        if ($data) {
            return $this->success($data);
        }
        return $this->error('数据不存在，请先爬取');
    }

    // 东方财富数据列表
    public function eastmoneyList()
    {
        $list = $this->crawler->getDataList();
        return $this->success($list);
    }

    // ==================== 缠论选股API ====================

    // 底背驰
    public function chanBottomDiverge(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getChanBottomDiverge($date);
        return $this->success($data);
    }

    // 顶背驰
    public function chanTopDiverge(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getChanTopDiverge($date);
        return $this->success($data);
    }

    // 一买信号
    public function chanFirstBuy(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getChanFirstBuy($date);
        return $this->success($data);
    }

    // 二买信号
    public function chanSecondBuy(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getChanSecondBuy($date);
        return $this->success($data);
    }

    // 三买信号
    public function chanThirdBuy(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getChanThirdBuy($date);
        return $this->success($data);
    }

    // 中枢震荡
    public function chanHubShake(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $data = $this->indicator->getChanHubShake($date);
        return $this->success($data);
    }

    // 获取单只股票缠论数据
    public function chanData(Request $request)
    {
        $tsCode = $request->get('ts_code', '');
        if (empty($tsCode)) {
            return $this->error('缺少股票代码');
        }
        $data = $this->indicator->getChanData($tsCode);
        return $this->success($data);
    }

    // 计算缠论指标
    public function calcChan(Request $request)
    {
        $date = $request->get('date', date('Ymd'));
        $stocks = Db::table('daily_quotes')
            ->where('trade_date', $date)
            ->distinct(true)
            ->column('ts_code');

        $count = 0;
        foreach ($stocks as $tsCode) {
            $history = $this->tushare->getStockHistory($tsCode, 200);
            if ($this->indicator->calculateChan($tsCode, $history)) {
                $count++;
            }
        }
        return $this->success(['calculated' => $count]);
    }
}
