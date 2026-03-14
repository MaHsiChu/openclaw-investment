"""
Strategy Library - 策略库
提供多种投资策略供回测引擎使用
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .portfolio import Portfolio

logger = logging.getLogger(__name__)


class Strategy(ABC):
    """策略基类"""

    def __init__(self, name: str = "BaseStrategy"):
        self.name = name

    @abstractmethod
    def execute(self, portfolio: Portfolio, row: pd.Series,
                history: pd.DataFrame) -> None:
        """策略执行函数，由回测引擎每日调用

        Args:
            portfolio: 投资组合
            row: 当日行情数据
            history: 截至当日的历史数据
        """

    def __call__(self, portfolio: Portfolio, row: pd.Series,
                 history: pd.DataFrame) -> None:
        self.execute(portfolio, row, history)


class MeanReversionStrategy(Strategy):
    """均值回归策略

    当价格偏离均线超过阈值时反向交易：
    - 价格低于均线 N 个标准差 → 买入
    - 价格高于均线 N 个标准差 → 卖出
    """

    def __init__(self, lookback: int = 20, entry_std: float = 2.0,
                 exit_std: float = 0.5, position_pct: float = 0.2):
        """
        Args:
            lookback: 均线周期
            entry_std: 入场标准差倍数
            exit_std: 出场标准差倍数
            position_pct: 单次交易占总资产比例
        """
        super().__init__(name="MeanReversion")
        self.lookback = lookback
        self.entry_std = entry_std
        self.exit_std = exit_std
        self.position_pct = position_pct

    def execute(self, portfolio: Portfolio, row: pd.Series,
                history: pd.DataFrame) -> None:
        if len(history) < self.lookback:
            return

        close = float(row["close"])
        symbol = str(row.get("symbol", "_default"))
        recent = history["close"].tail(self.lookback)
        mean = float(recent.mean())
        std = float(recent.std())

        if std == 0:
            return

        z_score = (close - mean) / std

        # 买入信号：价格显著低于均线
        if z_score < -self.entry_std:
            if symbol not in portfolio.positions:
                budget = portfolio.total_value() * self.position_pct
                shares = int(budget / close)
                if shares > 0:
                    portfolio.buy(symbol, shares, close)

        # 卖出信号：价格回归均线或高于均线
        elif z_score > self.exit_std:
            if symbol in portfolio.positions:
                shares = portfolio.positions[symbol].shares
                portfolio.sell(symbol, shares, close)


class MomentumStrategy(Strategy):
    """动量策略

    追踪价格动量：
    - 短期均线上穿长期均线（金叉）→ 买入
    - 短期均线下穿长期均线（死叉）→ 卖出
    结合 RSI 过滤假信号
    """

    def __init__(self, fast_period: int = 10, slow_period: int = 30,
                 rsi_period: int = 14, rsi_oversold: float = 30,
                 rsi_overbought: float = 70, position_pct: float = 0.3):
        super().__init__(name="Momentum")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.position_pct = position_pct

    def execute(self, portfolio: Portfolio, row: pd.Series,
                history: pd.DataFrame) -> None:
        if len(history) < self.slow_period + 2:
            return

        close = float(row["close"])
        symbol = str(row.get("symbol", "_default"))
        closes = history["close"]

        fast_ma = float(closes.tail(self.fast_period).mean())
        slow_ma = float(closes.tail(self.slow_period).mean())

        prev_fast = float(closes.iloc[-(self.fast_period + 1):-1].mean())
        prev_slow = float(closes.iloc[-(self.slow_period + 1):-1].mean())

        # 计算 RSI
        rsi = self._calc_rsi(closes, self.rsi_period)

        # 金叉 + RSI 未超买
        if fast_ma > slow_ma and prev_fast <= prev_slow:
            if rsi < self.rsi_overbought:
                if symbol not in portfolio.positions:
                    budget = portfolio.total_value() * self.position_pct
                    shares = int(budget / close)
                    if shares > 0:
                        portfolio.buy(symbol, shares, close)

        # 死叉 + RSI 未超卖
        elif fast_ma < slow_ma and prev_fast >= prev_slow:
            if rsi > self.rsi_oversold:
                if symbol in portfolio.positions:
                    shares = portfolio.positions[symbol].shares
                    portfolio.sell(symbol, shares, close)

        # RSI 极端值强制止损/止盈
        if rsi > 85 and symbol in portfolio.positions:
            shares = portfolio.positions[symbol].shares
            portfolio.sell(symbol, shares, close)

    @staticmethod
    def _calc_rsi(series: pd.Series, period: int) -> float:
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return 50.0 if pd.isna(val) else float(val)


class MultiFactorStrategy(Strategy):
    """多因子策略

    综合多个因子打分：
    - 价值因子：PE 分位数
    - 动量因子：近期涨幅
    - 波动因子：波动率
    - 均值回归因子：偏离度

    总分高于阈值买入，低于阈值卖出
    """

    def __init__(self, lookback: int = 20, buy_threshold: float = 0.6,
                 sell_threshold: float = 0.3, position_pct: float = 0.25):
        super().__init__(name="MultiFactor")
        self.lookback = lookback
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.position_pct = position_pct

    def execute(self, portfolio: Portfolio, row: pd.Series,
                history: pd.DataFrame) -> None:
        if len(history) < self.lookback + 5:
            return

        close = float(row["close"])
        symbol = str(row.get("symbol", "_default"))
        closes = history["close"].values

        score = self._compute_score(closes)

        if score > self.buy_threshold:
            if symbol not in portfolio.positions:
                budget = portfolio.total_value() * self.position_pct
                shares = int(budget / close)
                if shares > 0:
                    portfolio.buy(symbol, shares, close)
        elif score < self.sell_threshold:
            if symbol in portfolio.positions:
                shares = portfolio.positions[symbol].shares
                portfolio.sell(symbol, shares, close)

    def _compute_score(self, closes: np.ndarray) -> float:
        """计算多因子综合得分 (0-1)"""
        scores = []

        # 动量因子：近 N 日收益率的排名
        recent = closes[-self.lookback:]
        momentum = (recent[-1] / recent[0] - 1) if recent[0] != 0 else 0
        # 归一化到 0-1
        mom_score = min(max((momentum + 0.2) / 0.4, 0), 1)
        scores.append(mom_score)

        # 波动因子：低波动得分高
        returns = np.diff(recent) / recent[:-1]
        vol = float(np.std(returns)) if len(returns) > 1 else 0
        vol_score = max(1 - vol * 10, 0)  # 波动越小分越高
        scores.append(vol_score)

        # 均值回归因子：偏离均线程度
        mean = float(np.mean(recent))
        if mean > 0:
            deviation = (recent[-1] - mean) / mean
            # 低于均线得分高（反转机会）
            rev_score = min(max(0.5 - deviation * 5, 0), 1)
        else:
            rev_score = 0.5
        scores.append(rev_score)

        # 趋势因子：均线斜率
        if len(recent) >= 5:
            slope = (float(np.mean(recent[-5:])) - float(np.mean(recent[:5]))) / float(np.mean(recent[:5]))
            trend_score = min(max((slope + 0.1) / 0.2, 0), 1)
        else:
            trend_score = 0.5
        scores.append(trend_score)

        # 等权平均
        return sum(scores) / len(scores)

    def get_factor_breakdown(self, closes: np.ndarray) -> Dict[str, float]:
        """获取因子分解（用于分析）"""
        recent = closes[-self.lookback:]
        momentum = (recent[-1] / recent[0] - 1) if recent[0] != 0 else 0
        returns = np.diff(recent) / recent[:-1]
        vol = float(np.std(returns)) if len(returns) > 1 else 0
        mean = float(np.mean(recent))
        deviation = (recent[-1] - mean) / mean if mean > 0 else 0

        return {
            "momentum": round(momentum * 100, 2),
            "volatility": round(vol * 100, 2),
            "deviation_from_mean": round(deviation * 100, 2),
            "composite_score": round(self._compute_score(closes), 3),
        }
