"""
Portfolio Manager - 投资组合管理
支持买入、卖出、调仓、实时估值
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """单个持仓"""
    symbol: str
    shares: float
    avg_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "shares": self.shares,
            "avg_cost": round(self.avg_cost, 4),
            "current_price": round(self.current_price, 4),
            "market_value": round(self.market_value, 2),
            "cost_basis": round(self.cost_basis, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2),
        }


@dataclass
class TradeRecord:
    """交易记录"""
    symbol: str
    action: str           # buy / sell
    shares: float
    price: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    commission: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.shares * self.price + self.commission


class Portfolio:
    """投资组合管理器"""

    def __init__(self, name: str = "default", initial_capital: float = 100000.0):
        self.name = name
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeRecord] = []
        self.created_at = datetime.now().isoformat()

    # ------------------------------------------------------------------
    # 交易操作
    # ------------------------------------------------------------------

    def buy(self, symbol: str, shares: float, price: float,
            commission: float = 0.0) -> bool:
        """买入股票

        Returns:
            True if trade executed, False if insufficient cash
        """
        total_cost = shares * price + commission
        if total_cost > self.cash:
            logger.warning(
                "Insufficient cash for %s: need %.2f, have %.2f",
                symbol, total_cost, self.cash,
            )
            return False

        self.cash -= total_cost

        if symbol in self.positions:
            pos = self.positions[symbol]
            total_shares = pos.shares + shares
            pos.avg_cost = (pos.cost_basis + shares * price) / total_shares
            pos.shares = total_shares
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=shares,
                avg_cost=price,
                current_price=price,
            )

        self.trade_history.append(TradeRecord(
            symbol=symbol, action="buy", shares=shares,
            price=price, commission=commission,
        ))
        logger.info("BUY %s x%.2f @ $%.2f", symbol, shares, price)
        return True

    def sell(self, symbol: str, shares: float, price: float,
             commission: float = 0.0) -> bool:
        """卖出股票

        Returns:
            True if trade executed, False if insufficient shares
        """
        if symbol not in self.positions:
            logger.warning("No position in %s", symbol)
            return False

        pos = self.positions[symbol]
        if shares > pos.shares:
            logger.warning(
                "Insufficient shares for %s: want %.2f, have %.2f",
                symbol, shares, pos.shares,
            )
            return False

        proceeds = shares * price - commission
        self.cash += proceeds
        pos.shares -= shares

        if pos.shares <= 0:
            del self.positions[symbol]

        self.trade_history.append(TradeRecord(
            symbol=symbol, action="sell", shares=shares,
            price=price, commission=commission,
        ))
        logger.info("SELL %s x%.2f @ $%.2f", symbol, shares, price)
        return True

    def rebalance(self, target_weights: Dict[str, float],
                  prices: Dict[str, float]) -> List[TradeRecord]:
        """根据目标权重调仓

        Args:
            target_weights: {symbol: weight} 总和应为 1.0
            prices: {symbol: current_price}

        Returns:
            执行的交易列表
        """
        total_value = self.total_value(prices)
        trades_executed = []

        # 先卖出需要减仓/清仓的
        for symbol in list(self.positions.keys()):
            target_w = target_weights.get(symbol, 0.0)
            target_value = total_value * target_w
            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            current_value = self.positions[symbol].shares * price
            diff = current_value - target_value

            if diff > price:  # 需要卖出
                shares_to_sell = int(diff / price)
                if shares_to_sell > 0:
                    if self.sell(symbol, shares_to_sell, price):
                        trades_executed.append(self.trade_history[-1])

        # 再买入需要加仓的
        for symbol, target_w in target_weights.items():
            if target_w <= 0:
                continue
            target_value = total_value * target_w
            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            current_value = 0
            if symbol in self.positions:
                current_value = self.positions[symbol].shares * price

            diff = target_value - current_value
            if diff > price:
                shares_to_buy = int(diff / price)
                if shares_to_buy > 0:
                    if self.buy(symbol, shares_to_buy, price):
                        trades_executed.append(self.trade_history[-1])

        return trades_executed

    # ------------------------------------------------------------------
    # 估值
    # ------------------------------------------------------------------

    def update_prices(self, prices: Dict[str, float]) -> None:
        """更新持仓的当前价格"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price

    def total_value(self, prices: Optional[Dict[str, float]] = None) -> float:
        """计算组合总价值"""
        if prices:
            self.update_prices(prices)
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + market_value

    def total_return(self, prices: Optional[Dict[str, float]] = None) -> float:
        """总收益率 (%)"""
        if self.initial_capital == 0:
            return 0.0
        return (self.total_value(prices) / self.initial_capital - 1) * 100

    def position_weights(self, prices: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """各持仓权重"""
        total = self.total_value(prices)
        if total == 0:
            return {}
        weights = {}
        for symbol, pos in self.positions.items():
            weights[symbol] = pos.market_value / total
        weights["_cash"] = self.cash / total
        return weights

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------

    def summary(self, prices: Optional[Dict[str, float]] = None) -> Dict:
        """组合摘要"""
        if prices:
            self.update_prices(prices)

        return {
            "name": self.name,
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "total_value": round(self.total_value(), 2),
            "total_return_pct": round(self.total_return(), 2),
            "position_count": len(self.positions),
            "trade_count": len(self.trade_history),
            "positions": [pos.to_dict() for pos in self.positions.values()],
        }

    def format_report(self, prices: Optional[Dict[str, float]] = None) -> str:
        """格式化组合报告"""
        s = self.summary(prices)
        lines = [
            f"**投资组合 - {s['name']}**\n",
            f"总资产: ${s['total_value']:,.2f}",
            f"可用现金: ${s['cash']:,.2f}",
            f"总收益: {s['total_return_pct']:+.2f}%",
            f"持仓数: {s['position_count']}  |  交易数: {s['trade_count']}",
        ]

        if s["positions"]:
            lines.extend(["", "**持仓明细**:"])
            for p in s["positions"]:
                lines.append(
                    f"  {p['symbol']}: {p['shares']}股 @ ${p['avg_cost']:.2f} "
                    f"-> ${p['current_price']:.2f} "
                    f"({p['unrealized_pnl_pct']:+.1f}%)"
                )

        return "\n".join(lines)
