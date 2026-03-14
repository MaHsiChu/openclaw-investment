"""
Backtest Engine - 回测引擎
历史数据回测、策略绩效计算
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from .portfolio import Portfolio

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str = ""
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 0.0
    final_value: float = 0.0

    # 收益指标
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    benchmark_return_pct: float = 0.0  # 基准收益
    alpha: float = 0.0                 # 超额收益

    # 风险指标
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    volatility_pct: float = 0.0
    calmar_ratio: float = 0.0

    # 交易统计
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    # 每日净值
    equity_curve: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 100000.0,
                 commission_rate: float = 0.001,
                 slippage: float = 0.0005):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage

    def run(self, data: pd.DataFrame, strategy_fn: Callable,
            strategy_name: str = "Strategy",
            benchmark_col: Optional[str] = None) -> BacktestResult:
        """运行回测

        Args:
            data: DataFrame 需包含 date, open, high, low, close, volume 列
                  可包含多只股票时需要 symbol 列
            strategy_fn: 策略函数，签名 (portfolio, row_data, history) -> None
                         函数内部通过 portfolio.buy/sell 发出交易指令
            strategy_name: 策略名称
            benchmark_col: 基准收益列名（如 'close'），用于计算 alpha

        Returns:
            BacktestResult
        """
        portfolio = Portfolio(name=strategy_name, initial_capital=self.initial_capital)
        equity_curve = []
        dates = []

        data = data.sort_values("date").reset_index(drop=True)

        for i in range(len(data)):
            row = data.iloc[i]
            history = data.iloc[:i + 1]
            date_str = str(row["date"])

            # 更新持仓价格
            current_prices = {}
            if "symbol" in data.columns:
                sym = row["symbol"]
                current_prices[sym] = float(row["close"])
            else:
                # 单股票模式
                current_prices["_default"] = float(row["close"])
            portfolio.update_prices(current_prices)

            # 调用策略
            try:
                strategy_fn(portfolio, row, history)
            except Exception as e:
                logger.error("Strategy error at %s: %s", date_str, e)

            # 记录净值
            equity_curve.append(portfolio.total_value())
            dates.append(date_str)

        # 计算绩效指标
        result = self._calculate_metrics(
            equity_curve=equity_curve,
            dates=dates,
            portfolio=portfolio,
            strategy_name=strategy_name,
            data=data,
            benchmark_col=benchmark_col,
        )
        return result

    def _calculate_metrics(self, equity_curve: List[float], dates: List[str],
                           portfolio: Portfolio, strategy_name: str,
                           data: pd.DataFrame,
                           benchmark_col: Optional[str]) -> BacktestResult:
        """计算绩效指标"""
        result = BacktestResult(
            strategy_name=strategy_name,
            start_date=dates[0] if dates else "",
            end_date=dates[-1] if dates else "",
            initial_capital=self.initial_capital,
            final_value=equity_curve[-1] if equity_curve else self.initial_capital,
            equity_curve=equity_curve,
            dates=dates,
        )

        if len(equity_curve) < 2:
            return result

        eq = np.array(equity_curve, dtype=float)

        # 总收益
        result.total_return_pct = round((eq[-1] / eq[0] - 1) * 100, 2)

        # 年化收益 (假设252个交易日)
        n_days = len(equity_curve)
        if n_days > 1:
            years = n_days / 252
            if years > 0 and eq[0] > 0:
                result.annualized_return_pct = round(
                    ((eq[-1] / eq[0]) ** (1 / years) - 1) * 100, 2
                )

        # 日收益率
        daily_returns = np.diff(eq) / eq[:-1]

        # 波动率（年化）
        if len(daily_returns) > 1:
            result.volatility_pct = round(
                float(np.std(daily_returns, ddof=1)) * math.sqrt(252) * 100, 2
            )

        # 夏普比率 (无风险利率假设 2%)
        risk_free_daily = 0.02 / 252
        excess_returns = daily_returns - risk_free_daily
        if len(excess_returns) > 1 and np.std(excess_returns, ddof=1) > 0:
            result.sharpe_ratio = round(
                float(np.mean(excess_returns) / np.std(excess_returns, ddof=1))
                * math.sqrt(252), 2
            )

        # Sortino 比率
        downside = excess_returns[excess_returns < 0]
        if len(downside) > 1 and np.std(downside, ddof=1) > 0:
            result.sortino_ratio = round(
                float(np.mean(excess_returns) / np.std(downside, ddof=1))
                * math.sqrt(252), 2
            )

        # 最大回撤
        peak = np.maximum.accumulate(eq)
        drawdown = (eq - peak) / peak
        result.max_drawdown_pct = round(float(np.min(drawdown)) * 100, 2)
        result.drawdown_curve = drawdown.tolist()

        # Calmar 比率
        if result.max_drawdown_pct != 0:
            result.calmar_ratio = round(
                result.annualized_return_pct / abs(result.max_drawdown_pct), 2
            )

        # 基准收益
        if benchmark_col and benchmark_col in data.columns:
            bm = data[benchmark_col].values
            if len(bm) >= 2 and bm[0] > 0:
                result.benchmark_return_pct = round((bm[-1] / bm[0] - 1) * 100, 2)
                result.alpha = round(
                    result.total_return_pct - result.benchmark_return_pct, 2
                )

        # 交易统计
        result.total_trades = len(portfolio.trade_history)
        self._calculate_trade_stats(portfolio, result)

        return result

    def _calculate_trade_stats(self, portfolio: Portfolio,
                               result: BacktestResult) -> None:
        """计算交易统计"""
        trades = portfolio.trade_history
        if not trades:
            return

        # 按 symbol 配对 buy/sell 计算胜率
        buy_records: Dict[str, List] = {}
        wins = 0
        losses = 0
        total_profit = 0.0
        total_loss = 0.0

        for trade in trades:
            if trade.action == "buy":
                buy_records.setdefault(trade.symbol, []).append(trade)
            elif trade.action == "sell":
                buys = buy_records.get(trade.symbol, [])
                if buys:
                    buy_trade = buys.pop(0)
                    pnl = (trade.price - buy_trade.price) * trade.shares
                    if pnl > 0:
                        wins += 1
                        total_profit += pnl
                    else:
                        losses += 1
                        total_loss += abs(pnl)

        total = wins + losses
        result.win_rate = round(wins / total * 100, 1) if total > 0 else 0.0
        result.avg_win = round(total_profit / wins, 2) if wins > 0 else 0.0
        result.avg_loss = round(total_loss / losses, 2) if losses > 0 else 0.0
        result.profit_factor = (
            round(total_profit / total_loss, 2) if total_loss > 0 else float("inf")
        )

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------

    def format_report(self, result: BacktestResult) -> str:
        """格式化回测报告"""
        lines = [
            f"**回测报告 - {result.strategy_name}**\n",
            f"回测区间: {result.start_date} ~ {result.end_date}",
            f"初始资金: ${result.initial_capital:,.2f}",
            f"期末价值: ${result.final_value:,.2f}",
            "",
            "**收益指标**:",
            f"  总收益: {result.total_return_pct:+.2f}%",
            f"  年化收益: {result.annualized_return_pct:+.2f}%",
        ]

        if result.benchmark_return_pct:
            lines.append(f"  基准收益: {result.benchmark_return_pct:+.2f}%")
            lines.append(f"  Alpha: {result.alpha:+.2f}%")

        lines.extend([
            "",
            "**风险指标**:",
            f"  最大回撤: {result.max_drawdown_pct:.2f}%",
            f"  年化波动率: {result.volatility_pct:.2f}%",
            f"  夏普比率: {result.sharpe_ratio:.2f}",
            f"  Sortino比率: {result.sortino_ratio:.2f}",
            f"  Calmar比率: {result.calmar_ratio:.2f}",
            "",
            "**交易统计**:",
            f"  总交易数: {result.total_trades}",
            f"  胜率: {result.win_rate:.1f}%",
            f"  盈亏比: {result.profit_factor:.2f}",
            f"  平均盈利: ${result.avg_win:.2f}",
            f"  平均亏损: ${result.avg_loss:.2f}",
        ])

        return "\n".join(lines)
