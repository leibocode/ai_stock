#!/usr/bin/env python3
"""用真实A股历史数据验证缠论算法

支持两种数据源：
1. 本地SQLite数据库（如果已有历史数据）
2. Tushare API（需要TOKEN）

用法：
  python validate_with_real_data.py --stock 000001.SZ --start-date 2024-01-01 --days 100
"""

import sys
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# 导入验证框架
from backtest_chan_divergence import DivergenceBacktester, print_backtest_report


# ============================================================================
# 数据加载器
# ============================================================================

class DataLoader:
    """数据加载器 - 支持SQLite和Tushare"""

    @staticmethod
    def load_from_db(
        ts_code: str,
        start_date: str,
        end_date: str,
        db_path: str = "./ai_stock.db"
    ) -> Optional[pd.DataFrame]:
        """从SQLite数据库加载数据

        Args:
            ts_code: 股票代码 (如 '000001.SZ')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            db_path: 数据库文件路径

        Returns:
            DataFrame 或 None
        """
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            query = f"""
                SELECT trade_date, open, high, low, close, vol as volume
                FROM daily_quotes
                WHERE ts_code = '{ts_code}'
                  AND trade_date >= '{start_date}'
                  AND trade_date <= '{end_date}'
                ORDER BY trade_date ASC
            """
            df = pd.read_sql(query, conn)
            conn.close()

            if df.empty:
                print(f"❌ 数据库中未找到 {ts_code} 的数据")
                return None

            print(f"✓ 从SQLite加载: {len(df)} 条记录")
            return df

        except Exception as e:
            print(f"❌ 从数据库加载失败: {e}")
            return None

    @staticmethod
    def load_from_tushare(
        ts_code: str,
        start_date: str,
        end_date: str,
        token: str = ""
    ) -> Optional[pd.DataFrame]:
        """从Tushare API加载数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            token: Tushare Token

        Returns:
            DataFrame 或 None
        """
        try:
            import tushare as ts

            if not token:
                # 从环境变量读取
                import os
                token = os.getenv('TUSHARE_TOKEN', '')
                if not token:
                    print("❌ 请设置TUSHARE_TOKEN或传入token参数")
                    return None

            pro = ts.pro_api(token)
            df = pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                print(f"❌ Tushare中未找到 {ts_code} 的数据")
                return None

            # 数据清理
            df = df[['trade_date', 'open', 'high', 'low', 'close', 'vol']]
            df = df.rename(columns={'vol': 'volume'})
            df = df.sort_values('trade_date').reset_index(drop=True)

            print(f"✓ 从Tushare加载: {len(df)} 条记录")
            return df

        except Exception as e:
            print(f"❌ 从Tushare加载失败: {e}")
            return None

    @staticmethod
    def load_data(
        ts_code: str,
        days: int = 100,
        end_date: Optional[str] = None,
        prefer_source: str = "db"  # "db" 或 "tushare"
    ) -> Optional[pd.DataFrame]:
        """加载数据（自动选择最佳源）

        Args:
            ts_code: 股票代码
            days: 天数
            end_date: 结束日期，默认为今天
            prefer_source: 优先数据源

        Returns:
            DataFrame 或 None
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 计算开始日期（往前推days天）
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=days)
        start_date = start_dt.strftime('%Y-%m-%d')

        print(f"\n📊 加载数据: {ts_code}")
        print(f"  日期范围: {start_date} ~ {end_date}")

        # 尝试从数据库加载
        if prefer_source == "db":
            df = DataLoader.load_from_db(ts_code, start_date, end_date)
            if df is not None:
                return df

            # 降级到Tushare
            print("  数据库无数据，尝试Tushare...")
            start_date_ts = start_date.replace('-', '')
            end_date_ts = end_date.replace('-', '')
            df = DataLoader.load_from_tushare(ts_code, start_date_ts, end_date_ts)
            return df

        else:
            # 优先Tushare
            start_date_ts = start_date.replace('-', '')
            end_date_ts = end_date.replace('-', '')
            df = DataLoader.load_from_tushare(ts_code, start_date_ts, end_date_ts)
            if df is not None:
                return df

            # 降级到数据库
            print("  Tushare无数据，尝试数据库...")
            df = DataLoader.load_from_db(ts_code, start_date, end_date)
            return df


# ============================================================================
# 验证框架
# ============================================================================

def validate_stock(
    ts_code: str,
    days: int = 100,
    hold_days: int = 10,
    profit_target: float = 3.0,
    stop_loss: float = -2.0,
):
    """验证单只股票

    Args:
        ts_code: 股票代码
        days: 历史数据天数
        hold_days: 持仓天数
        profit_target: 目标收益率 (%)
        stop_loss: 止损点 (%)
    """
    print("="*80)
    print(f"  单只股票验证: {ts_code}")
    print("="*80)

    # 加载数据
    df = DataLoader.load_data(ts_code, days=days, prefer_source="db")
    if df is None:
        print("❌ 无法加载数据，跳过")
        return

    # 检查数据足够性
    if len(df) < 100:
        print(f"❌ 数据不足（{len(df)}条），需要至少100条")
        return

    print(f"✓ 数据加载成功: {len(df)} 条K线")
    print(f"  日期: {df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")
    print(f"  价格: {df['close'].min():.2f} ~ {df['close'].max():.2f}")

    # 运行回测
    try:
        backtester = DivergenceBacktester(
            df=df,
            hold_days=hold_days,
            profit_target=profit_target,
            stop_loss=stop_loss,
        )

        buy_result = backtester.run(strategy='buy')
        print_backtest_report(buy_result, 'buy')

        # 简单评估
        if buy_result.total_trades > 0:
            if buy_result.win_rate >= 50:
                print(f"\n✓ {ts_code}: 胜率{buy_result.win_rate:.1f}%, 可考虑实盘")
            else:
                print(f"\n✗ {ts_code}: 胜率{buy_result.win_rate:.1f}%, 需优化")
        else:
            print(f"\n⚠ {ts_code}: 未检测到信号")

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()


def validate_batch(stock_list: list, days: int = 100):
    """批量验证多只股票

    Args:
        stock_list: 股票代码列表
        days: 历史数据天数
    """
    print("\n" + "="*80)
    print("  批量股票验证")
    print("="*80)

    results = []

    for ts_code in stock_list:
        try:
            # 加载数据
            df = DataLoader.load_data(ts_code, days=days, prefer_source="db")
            if df is None or len(df) < 100:
                results.append({
                    'stock': ts_code,
                    'status': '数据不足',
                    'win_rate': 0,
                    'avg_profit': 0,
                    'trades': 0,
                })
                continue

            # 运行回测（静默模式，不打印详细日志）
            backtester = DivergenceBacktester(df, hold_days=10, profit_target=3.0, stop_loss=-2.0)

            # 临时重定向stdout以抑制输出
            import io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            buy_result = backtester.run(strategy='buy')

            sys.stdout = old_stdout

            results.append({
                'stock': ts_code,
                'status': 'OK' if buy_result.total_trades > 0 else '无信号',
                'win_rate': buy_result.win_rate,
                'avg_profit': buy_result.avg_profit,
                'trades': buy_result.total_trades,
            })

        except Exception as e:
            results.append({
                'stock': ts_code,
                'status': f'失败: {str(e)[:30]}',
                'win_rate': 0,
                'avg_profit': 0,
                'trades': 0,
            })

    # 输出结果表格
    print("\n【批量验证结果】")
    print(f"{'股票':<15} {'状态':<20} {'胜率':<10} {'平均':<10} {'交易':<5}")
    print(f"{'-'*60}")
    for r in results:
        print(f"{r['stock']:<15} {r['status']:<20} {r['win_rate']:<10.2f}% {r['avg_profit']:<10.2f}% {r['trades']:<5}")

    # 统计
    ok_count = sum(1 for r in results if r['status'] == 'OK')
    avg_win_rate = np.mean([r['win_rate'] for r in results if r['win_rate'] > 0]) if ok_count > 0 else 0

    print(f"\n【统计】")
    print(f"  总验证数: {len(results)}")
    print(f"  有信号: {ok_count}")
    print(f"  平均胜率: {avg_win_rate:.2f}%")


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='验证缠论背驰信号算法',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 验证单只股票
  python validate_with_real_data.py --stock 000001.SZ --days 100

  # 批量验证
  python validate_with_real_data.py --batch 000001.SZ 000858.SZ 000858.SZ --days 60

  # 自定义参数
  python validate_with_real_data.py --stock 600000.SH --hold-days 15 --profit-target 5.0
        """
    )

    parser.add_argument('--stock', type=str, help='单只股票代码 (如 000001.SZ)')
    parser.add_argument('--batch', nargs='+', help='批量股票代码列表')
    parser.add_argument('--days', type=int, default=100, help='历史数据天数 (默认100)')
    parser.add_argument('--hold-days', type=int, default=10, help='持仓天数 (默认10)')
    parser.add_argument('--profit-target', type=float, default=3.0, help='目标收益率% (默认3.0)')
    parser.add_argument('--stop-loss', type=float, default=-2.0, help='止损点% (默认-2.0)')

    args = parser.parse_args()

    if args.stock:
        validate_stock(
            ts_code=args.stock,
            days=args.days,
            hold_days=args.hold_days,
            profit_target=args.profit_target,
            stop_loss=args.stop_loss,
        )
    elif args.batch:
        validate_batch(args.batch, days=args.days)
    else:
        print("❌ 请指定 --stock 或 --batch")
        parser.print_help()


if __name__ == '__main__':
    main()
