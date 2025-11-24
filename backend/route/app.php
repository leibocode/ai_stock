<?php
// 路由配置
use think\facade\Route;

// API路由组
Route::group('api', function () {
    // 行情数据
    Route::get('volume-top', 'Index/volumeTop');
    Route::get('oversold', 'Index/oversold');
    Route::get('kdj-bottom', 'Index/kdjBottom');
    Route::get('macd-golden', 'Index/macdGolden');
    Route::get('bottom-volume', 'Index/bottomVolume');
    Route::get('industry-hot', 'Index/industryHot');
    Route::get('market-index', 'Index/marketIndex');
    Route::get('counter-trend', 'Index/counterTrend');
    Route::get('market-stats', 'Index/marketStats');
    Route::get('limit-up', 'Index/limitUp');
    Route::get('limit-down', 'Index/limitDown');
    Route::get('dragon-tiger', 'Index/dragonTiger');
    Route::get('north-buy', 'Index/northBuy');
    Route::get('margin-buy', 'Index/marginBuy');
    Route::get('breakout', 'Index/breakout');
    Route::get('top-volume', 'Index/topVolume');
    Route::get('gap-up', 'Index/gapUp');
    Route::get('gap-down', 'Index/gapDown');
    Route::get('industry-gap', 'Index/industryGap');

    // 复盘
    Route::get('review', 'Index/getReview');
    Route::post('review', 'Index/saveReview');
    Route::get('review-history', 'Index/reviewHistory');

    // 同步
    Route::get('sync-stocks', 'Index/syncStocks');
    Route::get('sync-daily', 'Index/syncDaily');
    Route::get('calc-indicators', 'Index/calcIndicators');

    // 东方财富爬虫
    Route::get('crawl-eastmoney', 'Index/crawlEastmoney');
    Route::get('eastmoney-data', 'Index/getEastmoneyData');
    Route::get('eastmoney-list', 'Index/eastmoneyList');

    // 缠论
    Route::get('chan-bottom-diverge', 'Index/chanBottomDiverge');
    Route::get('chan-top-diverge', 'Index/chanTopDiverge');
    Route::get('chan-first-buy', 'Index/chanFirstBuy');
    Route::get('chan-second-buy', 'Index/chanSecondBuy');
    Route::get('chan-third-buy', 'Index/chanThirdBuy');
    Route::get('chan-hub-shake', 'Index/chanHubShake');
    Route::get('chan-data', 'Index/chanData');
    Route::get('calc-chan', 'Index/calcChan');
});
