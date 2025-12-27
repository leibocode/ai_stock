#!/usr/bin/env python3
"""缠论背驰信号回测框架

验证背驰信号的准确性：
1. 逐K线扫描，检测一二三买卖点
2. 对每个信号进行"事后验证"
3. 统计胜率、盈亏比、最大回撤等指标

核心思想：
- 一买信号出现后，看后续N根K线是否真的反弹
- 计算"反弹成功率"和"平均收益率"
- 对比不同参数的效果
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json

# 导入核心算法
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
# 数据结构
# ============================================================================

@dataclass
class Trade:
    """交易记录"""
    signal_type: str  # "first_buy", "second_buy", etc.
    signal_date: str
    signal_price: float
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    profit_pct: float  # 收益率 (%)
    profit_points: float  # 绝对收益
    status: str  # "success" / "fail" / "timeout"
    hold_days: int  # 持仓天数
    max_profit: float  # 最大盈利 (%)
    max_loss: float  # 最大亏损 (%)
    notes: str = ""


@dataclass
class BacktestResult:
    """回测结果统计"""
    total_signals: int  # 总信号数
    total_trades: int  # 成交数
    successful_trades: int  # 成功交易数
    failed_trades: int  # 失败交易数
    timeout_trades: int  # 超时交易数（未在窗口内结束）

    win_rate: float  # 胜率 (%)
    avg_profit: float  # 平均收益 (%)
    avg_loss: float  # 平均亏损 (%)
    profit_factor: float  # 盈亏比
    max_consecutive_loss: int  # 最大连续亏损数
    sharpe_ratio: float  # 夏普比
    max_drawdown: float  # 最大回撤 (%)

    trades: List[Trade]  # 所有交易记录


# ============================================================================
# 生成示例数据
# ============================================================================

def generate_sample_data(days=200):
    """生成模拟K线数据"""
    np.random.seed(42)

    base_price = 10.0
    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * np.exp(np.cumsum(returns))

    data = []
    current_date = datetime.now() - timedelta(days=days)

    for i, close in enumerate(prices):
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


# ============================================================================
# 回测引擎
# ============================================================================

class DivergenceBacktester:
    """背驰信号回测引擎"""

    def __init__(self, df: pd.DataFrame, hold_days=10, profit_target=3.0, stop_loss=-2.0):
        """初始化回测器

        Args:
            df: K线数据DataFrame
            hold_days: 持仓最长天数
            profit_target: 目标收益率 (%)
            stop_loss: 止损点 (%)
        """
        self.df = df.reset_index(drop=True)
        self.hold_days = hold_days
        self.profit_target = profit_target
        self.stop_loss = stop_loss

        # 数据准备
        self.closes = self.df['close'].values
        self.highs = self.df['high'].values
        self.lows = self.df['low'].values
        self.dates = self.df['trade_date'].values

    def run(self, strategy='buy') -> BacktestResult:
        """运行回测

        Args:
            strategy: 'buy' 或 'sell'

        Returns:
            BacktestResult 对象
        """
        print(f"\n{'='*80}")
        print(f"  回测开始（策略: {strategy}）")
        print(f"{'='*80}")

        trades = []
        signal_records = {}  # 记录已检测的信号，避免重复

        # 逐K线扫描（保留足够的历史数据用于缠论计算）
        min_bars = 100
        scan_start = min_bars

        for i in range(scan_start, len(self.df)):
            # 获取到当前K线为止的历史数据
            hist_df = self.df.iloc[:i+1]
            hist_closes = hist_df['close'].values
            hist_highs = hist_df['high'].values
            hist_lows = hist_df['low'].values
            current_date = hist_df['trade_date'].iloc[-1]

            # 计算技术指标
            try:
                macd_result = calculate_macd_full(hist_closes)
            except Exception as e:
                print(f"MACD计算失败: {e}")
                continue

            # 计算缠论
            try:
                klines = [
                    {'high': hist_highs[j], 'low': hist_lows[j], 'close': hist_closes[j]}
                    for j in range(len(hist_closes))
                ]
                merged_klines = merge_klines(klines)
                fractals = calculate_fractals(merged_klines)
                bis = calculate_bi(fractals)

                if len(bis) < 3:
                    continue

                segments = calculate_segment(bis)
                hubs = calculate_hub_from_bis(bis)

            except Exception as e:
                print(f"缠论计算失败 [{current_date}]: {e}")
                continue

            # 检测信号
            if strategy == 'buy':
                signals = detect_buy_points_from_bis(bis, hist_closes, macd_result.macd_array, hubs)
            else:
                signals = detect_sell_points_from_bis(bis, hist_closes, macd_result.macd_array, hubs)

            # 处理信号
            for signal_name, signal_data in signals.items():
                if signal_data and signal_name not in signal_records:
                    signal_key = f"{current_date}_{signal_name}"
                    signal_records[signal_key] = True

                    signal_date = current_date
                    signal_price = float(hist_closes[-1])

                    print(f"\n[{signal_date}] {signal_name} 信号出现！价格: {signal_price:.2f}")

                    # 对信号进行事后验证
                    trade = self._verify_signal(
                        signal_type=signal_name,
                        signal_idx=i,
                        signal_price=signal_price,
                        signal_date=signal_date,
                        strategy=strategy
                    )

                    if trade:
                        trades.append(trade)
                        print(f"  → 结果: {trade.status}, 收益: {trade.profit_pct:.2f}%, 持仓: {trade.hold_days}天")

        # 统计结果
        result = self._calculate_statistics(trades, strategy)
        result.trades = trades

        return result

    def _verify_signal(
        self,
        signal_type: str,
        signal_idx: int,
        signal_price: float,
        signal_date: str,
        strategy: str
    ) -> Trade | None:
        """对信号进行事后验证

        Args:
            signal_type: 信号类型
            signal_idx: 信号出现的K线位置
            signal_price: 信号价格
            signal_date: 信号日期
            strategy: 策略方向

        Returns:
            Trade 对象或 None
        """
        # 从信号出现的下一个K线开始检查
        start_idx = signal_idx + 1
        end_idx = min(start_idx + self.hold_days, len(self.df))

        if start_idx >= len(self.df):
            return None

        entry_date = self.df['trade_date'].iloc[start_idx]
        entry_price = self.df['close'].iloc[start_idx]

        # 初始化
        exit_price = entry_price
        exit_date = entry_date
        status = "timeout"
        max_profit = 0.0
        max_loss = 0.0
        exit_bar_idx = end_idx - 1

        # 逐K线检查：是否达到目标收益或止损
        for j in range(start_idx, end_idx):
            current_price = self.df['close'].iloc[j]
            profit_pct = (current_price - entry_price) / entry_price * 100

            # 更新最大盈亏
            max_profit = max(max_profit, profit_pct)
            max_loss = min(max_loss, profit_pct)

            # 检查止损（无论buy还是sell都有)
            if profit_pct <= self.stop_loss:
                exit_price = current_price
                exit_date = self.df['trade_date'].iloc[j]
                status = "fail"
                exit_bar_idx = j
                break

            # 检查目标收益
            if strategy == 'buy' and profit_pct >= self.profit_target:
                exit_price = current_price
                exit_date = self.df['trade_date'].iloc[j]
                status = "success"
                exit_bar_idx = j
                break
            elif strategy == 'sell' and profit_pct >= self.profit_target:
                exit_price = current_price
                exit_date = self.df['trade_date'].iloc[j]
                status = "success"
                exit_bar_idx = j
                break

        # 如果没有达到目标，使用最后一个K线的价格
        if exit_bar_idx == end_idx - 1 and status == "timeout":
            exit_price = self.df['close'].iloc[end_idx - 1]
            exit_date = self.df['trade_date'].iloc[end_idx - 1]

        profit_pct = (exit_price - entry_price) / entry_price * 100
        profit_points = exit_price - entry_price
        hold_days = (exit_bar_idx - start_idx) + 1

        return Trade(
            signal_type=signal_type,
            signal_date=signal_date,
            signal_price=signal_price,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            exit_price=exit_price,
            profit_pct=profit_pct,
            profit_points=profit_points,
            status=status,
            hold_days=hold_days,
            max_profit=max_profit,
            max_loss=max_loss,
        )

    def _calculate_statistics(self, trades: List[Trade], strategy: str) -> BacktestResult:
        """计算回测统计"""
        if not trades:
            return BacktestResult(
                total_signals=0, total_trades=0, successful_trades=0,
                failed_trades=0, timeout_trades=0, win_rate=0, avg_profit=0,
                avg_loss=0, profit_factor=0, max_consecutive_loss=0,
                sharpe_ratio=0, max_drawdown=0, trades=[]
            )

        total_trades = len(trades)
        successful_trades = sum(1 for t in trades if t.status == "success")
        failed_trades = sum(1 for t in trades if t.status == "fail")
        timeout_trades = sum(1 for t in trades if t.status == "timeout")

        win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0

        # 计算平均收益和平均亏损
        profits = [t.profit_pct for t in trades if t.profit_pct > 0]
        losses = [t.profit_pct for t in trades if t.profit_pct <= 0]

        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0

        # 盈亏比 (profit factor)
        total_profit = sum([t.profit_pct for t in trades if t.profit_pct > 0])
        total_loss = abs(sum([t.profit_pct for t in trades if t.profit_pct <= 0]))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

        # 最大连续亏损
        max_consecutive_loss = 0
        current_loss_count = 0
        for t in trades:
            if t.profit_pct <= 0:
                current_loss_count += 1
                max_consecutive_loss = max(max_consecutive_loss, current_loss_count)
            else:
                current_loss_count = 0

        # 夏普比（简化计算）
        returns = [t.profit_pct for t in trades]
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-6) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # 最大回撤
        cumulative_profit = 0
        peak_profit = 0
        max_drawdown = 0
        for t in trades:
            cumulative_profit += t.profit_pct
            if cumulative_profit > peak_profit:
                peak_profit = cumulative_profit
            drawdown = (peak_profit - cumulative_profit)
            max_drawdown = max(max_drawdown, drawdown)

        return BacktestResult(
            total_signals=total_trades,  # 简化：信号数 = 交易数
            total_trades=total_trades,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            timeout_trades=timeout_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_consecutive_loss=max_consecutive_loss,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            trades=[]
        )


# ============================================================================
# 报告生成
# ============================================================================

def print_backtest_report(result: BacktestResult, strategy: str):
    """打印回测报告"""
    print(f"\n{'='*80}")
    print(f"  回测报告 - {strategy.upper()} 策略")
    print(f"{'='*80}")

    print(f"\n【基本统计】")
    print(f"  总信号数:      {result.total_signals}")
    print(f"  成交数:        {result.total_trades}")
    print(f"  成功交易:      {result.successful_trades}")
    print(f"  失败交易:      {result.failed_trades}")
    print(f"  超时交易:      {result.timeout_trades}")

    print(f"\n【收益指标】")
    print(f"  胜率:          {result.win_rate:.2f}%")
    print(f"  平均赢利:      {result.avg_profit:.2f}%")
    print(f"  平均亏损:      {result.avg_loss:.2f}%")
    print(f"  盈亏比:        {result.profit_factor:.2f}x")
    print(f"  最大连续亏损:  {result.max_consecutive_loss} 次")
    print(f"  最大回撤:      {result.max_drawdown:.2f}%")
    print(f"  夏普比:        {result.sharpe_ratio:.2f}")

    # 按信号类型统计
    if result.trades:
        print(f"\n【信号类型统计】")
        signal_stats = {}
        for trade in result.trades:
            if trade.signal_type not in signal_stats:
                signal_stats[trade.signal_type] = {"count": 0, "win": 0, "avg_profit": 0}
            signal_stats[trade.signal_type]["count"] += 1
            if trade.profit_pct > 0:
                signal_stats[trade.signal_type]["win"] += 1
            signal_stats[trade.signal_type]["avg_profit"] += trade.profit_pct

        for signal_type, stats in signal_stats.items():
            win_rate = stats["win"] / stats["count"] * 100 if stats["count"] > 0 else 0
            avg_profit = stats["avg_profit"] / stats["count"]
            print(f"  {signal_type:<15} 次数: {stats['count']:>3}  胜率: {win_rate:>6.2f}%  平均: {avg_profit:>7.2f}%")

    # 交易详情（前20条）
    if result.trades:
        print(f"\n【交易详情（前20条）】")
        print(f"{'日期':<12} {'信号':<12} {'入价':<8} {'出价':<8} {'收益%':<8} {'状态':<10} {'持仓':<6}")
        print(f"{'-'*70}")
        for trade in result.trades[:20]:
            print(f"{trade.signal_date:<12} {trade.signal_type:<12} {trade.entry_price:<8.2f} {trade.exit_price:<8.2f} {trade.profit_pct:<8.2f} {trade.status:<10} {trade.hold_days:<6}")


# ============================================================================
# 主程序
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("  缠论背驰信号 - 回测验证框架")
    print("="*80)

    # 生成数据
    print("\n[1] 生成样本数据...")
    df = generate_sample_data(days=200)
    print(f"✓ 生成{len(df)}根K线")
    print(f"  日期: {df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")
    print(f"  价格: {df['close'].min():.2f} ~ {df['close'].max():.2f}")

    # 回测
    print("\n[2] 运行回测...")
    backtester = DivergenceBacktester(
        df=df,
        hold_days=10,
        profit_target=3.0,  # 目标收益3%
        stop_loss=-2.0,      # 止损-2%
    )

    # 运行BUY策略
    buy_result = backtester.run(strategy='buy')
    print_backtest_report(buy_result, 'buy')

    # 运行SELL策略
    sell_result = backtester.run(strategy='sell')
    print_backtest_report(sell_result, 'sell')

    # 综合评估
    print("\n" + "="*80)
    print("  综合评估")
    print("="*80)

    print(f"\nBUY策略效果:")
    if buy_result.win_rate >= 50:
        print(f"  ✓ 胜率({buy_result.win_rate:.1f}%) >= 50%，可考虑实盘")
    else:
        print(f"  ✗ 胜率({buy_result.win_rate:.1f}%) < 50%，需要优化")

    print(f"\nSELL策略效果:")
    if sell_result.win_rate >= 50:
        print(f"  ✓ 胜率({sell_result.win_rate:.1f}%) >= 50%，可考虑实盘")
    else:
        print(f"  ✗ 胜率({sell_result.win_rate:.1f}%) < 50%，需要优化")

    print("\n" + "="*80)
    print("  回测完毕")
    print("="*80)
    print("\n💡 建议:")
    print("  1. 调整hold_days参数（持仓时间）")
    print("  2. 调整profit_target（目标收益率）")
    print("  3. 调整stop_loss（止损点）")
    print("  4. 用真实历史数据重新验证")
    print("  5. 对比不同信号类型（一买/二买/三买）的效果")
