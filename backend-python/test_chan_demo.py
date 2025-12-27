#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chan Theory Algorithm Demo Script

Demonstrates core Chan theory concepts:
1. Fractal identification - high-low-high or low-high-low
2. Bi (brush stroke) - from one fractal to another
3. Segment - at least 5 strokes
4. Hub (center) - overlap of segments
5. Buy/Sell signals
"""

import sys
import pandas as pd
sys.path.insert(0, r'C:\Users\02584\Desktop\新建文件夹\ai_stock\backend-python')

from app.services.chan_service import ChanService
from loguru import logger

# Configure logging
logger.remove()


def generate_demo_klines():
    """Generate demo K-line data (simulated real stock movement)"""

    data = {
        'high': [
            10.0, 10.5, 10.2, 11.0, 10.8,
            12.0, 11.5, 12.5, 13.0, 13.2,
            12.8, 12.0, 11.5, 12.2, 11.8,
            12.5, 12.8, 13.2, 13.5, 13.8,
            13.5, 13.0, 12.5, 12.8, 13.2,
            13.5, 14.0, 14.5, 14.2, 14.8,
            15.0, 14.8, 15.2, 15.5, 15.8,
            15.5, 15.0, 14.8, 15.2, 15.5,
            15.8, 16.0, 16.2, 16.5, 16.8,
            17.0, 16.8, 17.2, 17.5, 17.8,
        ],
        'low': [
            9.5, 9.8, 9.6, 10.2, 10.0,
            10.6, 10.8, 11.2, 12.0, 12.5,
            12.0, 11.2, 10.8, 11.5, 11.0,
            11.8, 12.0, 12.5, 12.8, 13.0,
            13.0, 12.5, 12.0, 12.2, 12.8,
            13.0, 13.5, 14.0, 13.8, 14.2,
            14.5, 14.0, 14.8, 15.0, 15.2,
            15.0, 14.5, 14.2, 14.8, 15.0,
            15.2, 15.5, 15.8, 16.0, 16.2,
            16.5, 16.2, 16.8, 17.0, 17.2,
        ],
        'close': [
            9.8, 10.2, 10.1, 10.8, 10.5,
            11.8, 11.2, 12.3, 12.8, 13.0,
            12.5, 11.8, 11.2, 12.0, 11.5,
            12.2, 12.5, 13.0, 13.2, 13.5,
            13.2, 12.8, 12.2, 12.5, 13.0,
            13.2, 13.8, 14.2, 14.0, 14.5,
            14.8, 14.5, 15.0, 15.2, 15.5,
            15.2, 14.8, 14.5, 15.0, 15.2,
            15.5, 15.8, 16.0, 16.2, 16.5,
            16.8, 16.5, 17.0, 17.2, 17.5,
        ],
    }

    df = pd.DataFrame(data)
    df['trade_date'] = pd.date_range('2025-01-01', periods=len(df))

    return df


def print_section(title):
    """Print section separator"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main():
    """Test Chan algorithm"""

    print_section("Chan Theory Complete Algorithm Demo")

    # 1. Generate demo data
    print("[STEP 1] Generate demo K-line data...")
    df = generate_demo_klines()
    print(f"   Total: {len(df)} K-lines\n")

    print("   First 10 K-lines:")
    print(df.head(10)[['high', 'low', 'close']].to_string())
    print("\n   Last 5 K-lines:")
    print(df.tail(5)[['high', 'low', 'close']].to_string())

    # 2. Run complete Chan analysis
    print_section("Chan Analysis Results")

    result = ChanService.analyze(df)

    print("[ANALYSIS COMPLETE] Key Metrics:")
    print(f"   - Fractals:  {result['fractal_count']}")
    print(f"   - Strokes:   {result['bi_count']}")
    print(f"   - Segments:  {result['segment_count']}")
    print(f"   - Hubs:      {result['hub_count']}")
    print(f"   - Trend:     {result['current_trend']}")

    # 3. Fractal details
    print_section("Step 1: Fractal Identification")

    if result['fractals']:
        print(f"Identified {len(result['fractals'])} fractals:\n")
        for idx, fractal_type in sorted(result['fractals'].items()):
            price = df.iloc[idx]
            ftype = "[TOP]" if fractal_type == 'top' else "[BOT]"
            print(f"  {ftype} K#{idx:2d} | H:{price['high']:6.2f} L:{price['low']:6.2f} C:{price['close']:6.2f}")
    else:
        print("No fractals identified")

    # 4. Bi information
    print_section("Step 2: Bi (Stroke) Identification")

    if result['bis']:
        print(f"Identified {len(result['bis'])} strokes:\n")
        for i, bi in enumerate(result['bis']):
            direction = "[UP]  " if bi['direction'] == 'up' else "[DOWN]"
            print(f"  Stroke#{i+1:2d} {direction} | "
                  f"Range:[#{bi['start_idx']:2d}-#{bi['end_idx']:2d}] | "
                  f"Start:{bi['start_price']:6.2f} End:{bi['end_price']:6.2f} | "
                  f"Len:{bi['length']}")
    else:
        print("No strokes identified")

    # 5. Segment information
    print_section("Step 3: Segment Identification (Min 5 Strokes)")

    if result['segments']:
        print(f"Identified {len(result['segments'])} segments:\n")
        for i, seg in enumerate(result['segments']):
            direction = "[UP]  " if seg['direction'] == 'up' else "[DOWN]"
            print(f"  Segment#{i+1} {direction} | "
                  f"Range:[#{seg['start_idx']:2d}-#{seg['end_idx']:2d}] | "
                  f"High:{seg['high']:6.2f} Low:{seg['low']:6.2f} | "
                  f"Strokes:{seg['bi_count']}")
    else:
        print("No segments identified")

    # 6. Hub information
    print_section("Step 4: Hub (Center) Identification")

    if result['hubs']:
        print(f"Identified {len(result['hubs'])} hubs:\n")
        for i, hub in enumerate(result['hubs']):
            amplitude = hub['amplitude']
            print(f"  Hub#{i+1} | "
                  f"Range:[#{hub['start_idx']:2d}-#{hub['end_idx']:2d}] | "
                  f"Upper:{hub['high']:6.2f} Lower:{hub['low']:6.2f} | "
                  f"Amplitude:{amplitude:6.2f} | Level:{hub['level']}")
    else:
        print("No hubs identified")

    # 7. Breakout points
    print_section("Step 5: Breakout Point Identification")

    breakouts = ChanService.identify_breakout_points(df)
    if breakouts:
        print(f"Identified {len(breakouts)} breakout points:\n")
        for bo in breakouts:
            bo_type = "[UP-BK]  " if bo['type'] == 'up_breakout' else "[DOWN-BK]"
            print(f"  {bo_type} | Price:{bo['close']:6.2f} | Breakpoint:{bo['price']:6.2f}")
    else:
        print("No clear breakout points identified")

    # 8. Key price levels
    print_section("Step 6: Key Price Levels (Support & Resistance)")

    levels = ChanService.get_key_levels(df)

    if levels['resistance']:
        print("RESISTANCE Levels:")
        for res in levels['resistance'][:3]:
            print(f"   {res['level']:6.2f} ({res['strength']})")

    if levels['support']:
        print("\nSUPPORT Levels:")
        for sup in levels['support'][:3]:
            print(f"   {sup['level']:6.2f} ({sup['strength']})")

    # 9. Summary
    print_section("Complete Chan Theory Analysis Summary")

    print("""CORE CONCEPTS DEMONSTRATED:

[1] FRACTAL (Fractal Identification)
    * Top Fractal: High-Low-High K-line combination
    * Bottom Fractal: Low-High-Low K-line combination
    * Purpose: Base pattern for identifying trend reversal points
    * Demo identified {} fractals

[2] BI / STROKE (Brush Stroke Pattern)
    * Definition: Continuous price movement from one fractal to another
    * Up Stroke: Bottom Fractal -> Top Fractal (uptrend)
    * Down Stroke: Top Fractal -> Bottom Fractal (downtrend)
    * Minimum: 3 K-lines per stroke
    * Demo identified {} strokes

[3] SEGMENT (Segment Pattern)
    * Definition: Sequence of at least 5 strokes
    * Direction: Determined by first stroke
    * Represents major trend direction
    * Demo identified {} segments

[4] HUB / CENTER (Center of Oscillation)
    * Definition: Overlapping region of adjacent segments
    * Calculation: max(lower_low) to min(upper_high)
    * Usage: Support/resistance levels, consolidation zones
    * Demo identified {} hubs

[5] TREND ANALYSIS
    * Current Trend: {}
    * Method: Last stroke determines direction
    * Up Trend: Final stroke is upward
    * Down Trend: Final stroke is downward

[PRACTICAL APPLICATIONS]:
1. Support & Resistance: Use hub boundaries
2. Trend Confirmation: Multi-level segment direction alignment
3. Entry Points: Fractal breakouts, segment breaks
4. Risk Management: Hub level stops
5. Position Sizing: Based on segment amplitude

[API ENDPOINTS]:
    GET /api/chan-bottom-diverge?date=YYYYMMDD
        - Identify bottom divergence signals
        - Returns qualified stock list

    GET /api/chan-top-diverge?date=YYYYMMDD
        - Identify top divergence signals
        - Returns qualified stock list

    GET /api/chan-first-buy?date=YYYYMMDD
        - First buy signal (first class buy point)
        - Bottom reversal first signal

    GET /api/chan-second-buy?date=YYYYMMDD
        - Second buy signal (second class buy point)
        - Pullback followed by continuation

    GET /api/chan-third-buy?date=YYYYMMDD
        - Third buy signal (third class buy point)
        - Hub breakout confirmation

    GET /api/chan-hub-shake?date=YYYYMMDD
        - Hub oscillation identification
        - Stocks in hub consolidation zone

    GET /api/chan-data?ts_code=000001.SZ
        - Complete Chan analysis for single stock
        - Returns all fractals, strokes, segments, hubs, signals

    GET /api/calc-chan?date=YYYYMMDD&limit=100
        - Batch calculation of Chan indicators
        - Processes multiple stocks by date

SWAGGER DOCUMENTATION:
    http://127.0.0.1:8000/docs
    """.format(
        result['fractal_count'],
        result['bi_count'],
        result['segment_count'],
        result['hub_count'],
        result['current_trend']
    ))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
