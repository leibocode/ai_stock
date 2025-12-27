#!/usr/bin/env python3
"""缠论+MACD优化演示脚本

展示：
1. MACD标准计算（修正了*2的问题）
2. 笔级别的中枢识别（标准缠论）
3. 背驰信号检测（一二三买卖点）
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 导入核心模块
from app.core.indicators.macd import calculate_macd_full
from app.core.chan import (
    merge_klines,
    calculate_fractals,
    calculate_bi,
    calculate_segment,
    calculate_hub_from_bis,
    detect_buy_points_from_bis,
    detect_sell_points_from_bis,
)

# ============================================================================
# 1. 生成示例数据（模拟A股日线）
# ============================================================================

def generate_sample_data(days=100):
    """生成模拟K线数据"""
    np.random.seed(42)

    # 生成价格序列（随机游走）
    base_price = 10.0
    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * np.exp(np.cumsum(returns))

    # 生成K线
    data = []
    current_date = datetime.now() - timedelta(days=days)

    for i, close in enumerate(prices):
        # 模拟高低点
        high = close * np.random.uniform(1.0, 1.02)
        low = close * np.random.uniform(0.98, 1.0)
        open_price = (low + high) / 2
        volume = np.random.randint(1000000, 10000000)

        data.append({
            'trade_date': current_date.strftime('%Y-%m-%d'),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        })
        current_date += timedelta(days=1)

    return pd.DataFrame(data)


def print_separator(title):
    """打印分隔符"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


# ============================================================================
# 2. 主程序
# ============================================================================

if __name__ == '__main__':
    print_separator("缠论+MACD 优化演示")

    # 生成数据
    print("\n[1] 生成示例K线数据...")
    df = generate_sample_data(days=100)
    print(f"✓ 生成{len(df)}根K线")
    print(f"  日期范围: {df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")
    print(f"  价格范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")

    # 提取数据
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    dates = df['trade_date'].values

    # ========================================================================
    # 3. MACD计算（标准版，修正了之前的*2问题）
    # ========================================================================

    print_separator("MACD标准计算")
    print("\n计算MACD指标...")
    macd_result = calculate_macd_full(closes)

    print(f"\n最新MACD值：")
    print(f"  DIF (快线):   {macd_result.dif:>8.4f}")
    print(f"  DEA (慢线):   {macd_result.dea:>8.4f}")
    print(f"  MACD (柱):    {macd_result.macd:>8.4f}")

    # 显示最近5根K线的MACD值
    print(f"\n最近5根K线的MACD值：")
    print(f"{'K线':<6} {'DIF':>8} {'DEA':>8} {'MACD':>8}")
    print(f"{'-'*34}")
    for i in range(-5, 0):
        idx = len(macd_result.dif_array) + i
        if idx >= 0:
            print(f"{dates[i]:<6} {macd_result.dif_array[idx]:>8.4f} {macd_result.dea_array[idx]:>8.4f} {macd_result.macd_array[idx]:>8.4f}")

    # ========================================================================
    # 4. 缠论分析（分型→笔→线段→中枢）
    # ========================================================================

    print_separator("缠论分析流程")

    print("\n[步骤1] K线包含处理...")
    klines = [
        {'high': highs[i], 'low': lows[i], 'close': closes[i]}
        for i in range(len(closes))
    ]
    merged_klines = merge_klines(klines)
    print(f"✓ 包含处理后: {len(klines)} → {len(merged_klines)} 根K线")

    print("\n[步骤2] 分型识别...")
    fractals = calculate_fractals(merged_klines)
    print(f"✓ 识别分型: {len(fractals)} 个")
    if fractals:
        print(f"  最新分型: {fractals[-1]}")

    print("\n[步骤3] 笔划分...")
    bis = calculate_bi(fractals)
    print(f"✓ 笔数: {len(bis)} 个")
    if len(bis) >= 1:
        print(f"  最后一笔: {bis[-1]}")

    print("\n[步骤4] 线段划分...")
    segments = calculate_segment(bis)
    print(f"✓ 线段数: {len(segments)} 个")
    if len(segments) >= 1:
        print(f"  最后一线段: {segments[-1]}")

    print("\n[步骤5] 中枢识别（笔级别）...")
    hubs = calculate_hub_from_bis(bis)
    print(f"✓ 中枢数: {len(hubs)} 个")
    if len(hubs) >= 1:
        latest_hub = hubs[-1]
        print(f"  最新中枢:")
        print(f"    上沿 ZG: {latest_hub.zg:.2f}")
        print(f"    下沿 ZD: {latest_hub.zd:.2f}")
        print(f"    振幅:   {(latest_hub.zg - latest_hub.zd) / latest_hub.zd * 100:.2f}%")

    # ========================================================================
    # 5. 买卖点检测（背驰信号）
    # ========================================================================

    print_separator("买卖点检测（基于背驰）")

    print("\n检测买点信号（底背驰、回踩不破、中枢回踩）...")
    buy_signals = detect_buy_points_from_bis(
        bis=bis,
        closes=closes,
        macd_values=macd_result.macd_array,
        hubs=hubs
    )

    print(f"\n买点信号：")
    for signal_name, signal_data in buy_signals.items():
        if signal_data:
            print(f"  ✓ {signal_name}:")
            for key, value in signal_data.items():
                print(f"     - {key}: {value}")
        else:
            print(f"  ✗ {signal_name}: 暂无信号")

    print(f"\n检测卖点信号（顶背驰、反弹不破、中枢反弹）...")
    sell_signals = detect_sell_points_from_bis(
        bis=bis,
        closes=closes,
        macd_values=macd_result.macd_array,
        hubs=hubs
    )

    print(f"\n卖点信号：")
    for signal_name, signal_data in sell_signals.items():
        if signal_data:
            print(f"  ✓ {signal_name}:")
            for key, value in signal_data.items():
                print(f"     - {key}: {value}")
        else:
            print(f"  ✗ {signal_name}: 暂无信号")

    # ========================================================================
    # 6. 交易策略建议
    # ========================================================================

    print_separator("交易策略建议")

    current_price = closes[-1]
    print(f"\n当前价格: {current_price:.2f}")

    # 根据中枢位置给出建议
    if hubs:
        latest_hub = hubs[-1]
        position = "中枢内"
        if current_price > latest_hub.zg:
            position = "中枢上方"
        elif current_price < latest_hub.zd:
            position = "中枢下方"

        print(f"价格位置: {position} (ZG={latest_hub.zg:.2f}, ZD={latest_hub.zd:.2f})")

        # 根据笔方向给出建议
        if bis:
            last_bi = bis[-1]
            direction = "向上" if last_bi.direction == 1 else "向下"
            print(f"最新笔方向: {direction}")

            if last_bi.direction == 1:
                print(f"\n建议操作:")
                print(f"  1. 如果有买点信号，可考虑做多")
                print(f"  2. 关注中枢上沿 {latest_hub.zg:.2f} 作为压力")
                print(f"  3. 回踩不破中枢下沿 {latest_hub.zd:.2f} 是二买机会")
            else:
                print(f"\n建议操作:")
                print(f"  1. 如果有卖点信号，可考虑做空")
                print(f"  2. 关注中枢下沿 {latest_hub.zd:.2f} 作为支撑")
                print(f"  3. 反弹不破中枢上沿 {latest_hub.zg:.2f} 是二卖机会")

    print_separator("演示完毕")
    print("\n✓ 所有核心算法已成功运行")
    print("\n关键改进总结:")
    print("  1. MACD: 标准计算（DIF = EMA12-EMA26, DEA = EMA(DIF,9), MACD = DIF-DEA）")
    print("  2. 中枢: 从线段级别升级为笔级别（更精确）")
    print("  3. 买卖点: 完整的背驰检测（一二三买卖）")
    print("\n下一步:")
    print("  - 集成WebSocket实时推送")
    print("  - 添加K线图可视化")
    print("  - 优化爬虫数据采集")
