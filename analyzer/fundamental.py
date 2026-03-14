"""
Fundamental Analyzer - 基本面分析模块
财务指标计算、估值模型、财报数据获取
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FundamentalMetrics:
    """基本面指标集合"""
    symbol: str = ""

    # 估值指标
    pe_ratio: Optional[float] = None       # 市盈率
    pe_forward: Optional[float] = None     # 前瞻市盈率
    pb_ratio: Optional[float] = None       # 市净率
    ps_ratio: Optional[float] = None       # 市销率
    peg_ratio: Optional[float] = None      # PEG

    # 盈利指标
    roe: Optional[float] = None            # 净资产收益率 (%)
    roa: Optional[float] = None            # 总资产收益率 (%)
    gross_margin: Optional[float] = None   # 毛利率 (%)
    net_margin: Optional[float] = None     # 净利率 (%)
    operating_margin: Optional[float] = None  # 营业利润率 (%)

    # 成长指标
    revenue_growth: Optional[float] = None    # 营收增长率 (%)
    earnings_growth: Optional[float] = None   # 盈利增长率 (%)

    # 负债指标
    debt_to_equity: Optional[float] = None    # 资产负债率
    current_ratio: Optional[float] = None     # 流动比率

    # 分红指标
    dividend_yield: Optional[float] = None    # 股息率 (%)
    payout_ratio: Optional[float] = None      # 派息比率 (%)

    # 其他
    market_cap: Optional[float] = None        # 市值
    enterprise_value: Optional[float] = None  # 企业价值
    free_cash_flow: Optional[float] = None    # 自由现金流
    eps: Optional[float] = None               # 每股收益
    book_value: Optional[float] = None        # 每股净资产

    # 评分
    score: float = 0.0                        # 综合评分 0-100
    grade: str = ""                           # 评级 A/B/C/D/F


@dataclass
class ValuationResult:
    """估值结果"""
    symbol: str = ""
    current_price: float = 0.0
    dcf_value: Optional[float] = None         # DCF 估值
    peg_fair_value: Optional[float] = None    # PEG 合理估值
    relative_value: Optional[float] = None    # 相对估值
    upside_pct: Optional[float] = None        # 上涨空间 (%)
    verdict: str = ""                          # undervalued / overvalued / fair


class FundamentalAnalyzer:
    """基本面分析器"""

    def __init__(self):
        self._yf = None

    def _get_yf(self):
        if self._yf is None:
            import yfinance as yf
            self._yf = yf
        return self._yf

    # ------------------------------------------------------------------
    # 数据获取
    # ------------------------------------------------------------------

    def fetch_financials(self, symbol: str) -> Dict:
        """通过 yfinance 获取财务数据"""
        yf = self._get_yf()
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return info

    def get_metrics(self, symbol: str) -> FundamentalMetrics:
        """获取并计算基本面指标"""
        info = self.fetch_financials(symbol)
        m = FundamentalMetrics(symbol=symbol)

        # 估值
        m.pe_ratio = info.get("trailingPE")
        m.pe_forward = info.get("forwardPE")
        m.pb_ratio = info.get("priceToBook")
        m.ps_ratio = info.get("priceToSalesTrailing12Months")
        m.peg_ratio = info.get("pegRatio")

        # 盈利
        m.roe = _pct(info.get("returnOnEquity"))
        m.roa = _pct(info.get("returnOnAssets"))
        m.gross_margin = _pct(info.get("grossMargins"))
        m.net_margin = _pct(info.get("profitMargins"))
        m.operating_margin = _pct(info.get("operatingMargins"))

        # 成长
        m.revenue_growth = _pct(info.get("revenueGrowth"))
        m.earnings_growth = _pct(info.get("earningsGrowth"))

        # 负债
        m.debt_to_equity = info.get("debtToEquity")
        m.current_ratio = info.get("currentRatio")

        # 分红
        m.dividend_yield = _pct(info.get("dividendYield"))
        m.payout_ratio = _pct(info.get("payoutRatio"))

        # 其他
        m.market_cap = info.get("marketCap")
        m.enterprise_value = info.get("enterpriseValue")
        m.free_cash_flow = info.get("freeCashflow")
        m.eps = info.get("trailingEps")
        m.book_value = info.get("bookValue")

        # 综合评分
        m.score = self._score_fundamentals(m)
        m.grade = self._grade(m.score)

        return m

    # ------------------------------------------------------------------
    # 估值模型
    # ------------------------------------------------------------------

    def dcf_valuation(self, symbol: str,
                      growth_rate: float = 0.10,
                      discount_rate: float = 0.10,
                      terminal_growth: float = 0.03,
                      projection_years: int = 5) -> Optional[float]:
        """简化 DCF 估值

        Args:
            symbol: 股票代码
            growth_rate: 预期增长率
            discount_rate: 折现率
            terminal_growth: 永续增长率
            projection_years: 预测年数

        Returns:
            每股内在价值，数据不足时返回 None
        """
        info = self.fetch_financials(symbol)
        fcf = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")

        if not fcf or not shares or shares == 0:
            return None

        # 预测未来现金流
        projected_fcf = []
        current_fcf = float(fcf)
        for year in range(1, projection_years + 1):
            current_fcf *= (1 + growth_rate)
            pv = current_fcf / ((1 + discount_rate) ** year)
            projected_fcf.append(pv)

        # 终值
        terminal_fcf = current_fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)

        total_value = sum(projected_fcf) + pv_terminal
        intrinsic_per_share = total_value / float(shares)

        return round(intrinsic_per_share, 2)

    def peg_fair_value(self, symbol: str) -> Optional[float]:
        """基于 PEG=1 的合理估值"""
        info = self.fetch_financials(symbol)
        eps = info.get("trailingEps")
        growth = info.get("earningsGrowth")

        if not eps or not growth or growth <= 0:
            return None

        growth_pct = growth * 100  # 转换为百分比
        fair_pe = growth_pct  # PEG = 1 时 PE = 增长率
        fair_price = eps * fair_pe

        return round(fair_price, 2) if fair_price > 0 else None

    def valuate(self, symbol: str) -> ValuationResult:
        """综合估值"""
        info = self.fetch_financials(symbol)
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)

        result = ValuationResult(symbol=symbol, current_price=current_price)

        # DCF
        result.dcf_value = self.dcf_valuation(symbol)

        # PEG
        result.peg_fair_value = self.peg_fair_value(symbol)

        # 相对估值：取可用估值的均值
        values = [v for v in [result.dcf_value, result.peg_fair_value] if v and v > 0]
        if values:
            result.relative_value = round(sum(values) / len(values), 2)

        # 上涨空间
        if result.relative_value and current_price and current_price > 0:
            result.upside_pct = round(
                (result.relative_value / current_price - 1) * 100, 2
            )
            if result.upside_pct > 15:
                result.verdict = "undervalued"
            elif result.upside_pct < -15:
                result.verdict = "overvalued"
            else:
                result.verdict = "fair"

        return result

    # ------------------------------------------------------------------
    # 评分体系
    # ------------------------------------------------------------------

    def _score_fundamentals(self, m: FundamentalMetrics) -> float:
        """综合评分 (0-100)"""
        scores: List[float] = []

        # PE 评分 (权重: 15)
        if m.pe_ratio is not None and m.pe_ratio > 0:
            if m.pe_ratio < 15:
                scores.append(15)
            elif m.pe_ratio < 25:
                scores.append(10)
            elif m.pe_ratio < 40:
                scores.append(5)
            else:
                scores.append(0)

        # ROE 评分 (权重: 15)
        if m.roe is not None:
            if m.roe > 20:
                scores.append(15)
            elif m.roe > 15:
                scores.append(12)
            elif m.roe > 10:
                scores.append(8)
            else:
                scores.append(3)

        # 净利率 (权重: 10)
        if m.net_margin is not None:
            if m.net_margin > 20:
                scores.append(10)
            elif m.net_margin > 10:
                scores.append(7)
            elif m.net_margin > 5:
                scores.append(4)
            else:
                scores.append(1)

        # 营收增长 (权重: 15)
        if m.revenue_growth is not None:
            if m.revenue_growth > 30:
                scores.append(15)
            elif m.revenue_growth > 15:
                scores.append(12)
            elif m.revenue_growth > 5:
                scores.append(8)
            else:
                scores.append(3)

        # 负债率 (权重: 10)
        if m.debt_to_equity is not None:
            if m.debt_to_equity < 50:
                scores.append(10)
            elif m.debt_to_equity < 100:
                scores.append(7)
            elif m.debt_to_equity < 200:
                scores.append(3)
            else:
                scores.append(0)

        # PEG (权重: 10)
        if m.peg_ratio is not None and m.peg_ratio > 0:
            if m.peg_ratio < 1:
                scores.append(10)
            elif m.peg_ratio < 1.5:
                scores.append(7)
            elif m.peg_ratio < 2:
                scores.append(4)
            else:
                scores.append(1)

        if not scores:
            return 0.0

        # 按满分 75 缩放到 100
        raw = sum(scores)
        max_possible = 75
        return round(min(raw / max_possible * 100, 100), 1)

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 80:
            return "A"
        if score >= 65:
            return "B"
        if score >= 50:
            return "C"
        if score >= 35:
            return "D"
        return "F"

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------

    def format_report(self, metrics: FundamentalMetrics,
                      valuation: Optional[ValuationResult] = None) -> str:
        """格式化基本面报告"""
        grade_emoji = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🟠", "F": "🔴"}

        lines = [
            f"**基本面分析 - {metrics.symbol}**\n",
            f"综合评分: {grade_emoji.get(metrics.grade, '⚪')} {metrics.score:.0f}/100 ({metrics.grade})",
            "",
            "**估值指标**:",
            f"  PE(TTM): {_fmt(metrics.pe_ratio)}    PE(Fwd): {_fmt(metrics.pe_forward)}",
            f"  PB: {_fmt(metrics.pb_ratio)}    PS: {_fmt(metrics.ps_ratio)}    PEG: {_fmt(metrics.peg_ratio)}",
            "",
            "**盈利能力**:",
            f"  ROE: {_fmt_pct(metrics.roe)}    ROA: {_fmt_pct(metrics.roa)}",
            f"  毛利率: {_fmt_pct(metrics.gross_margin)}    净利率: {_fmt_pct(metrics.net_margin)}",
            "",
            "**成长性**:",
            f"  营收增长: {_fmt_pct(metrics.revenue_growth)}    盈利增长: {_fmt_pct(metrics.earnings_growth)}",
            "",
            "**财务健康**:",
            f"  负债率: {_fmt(metrics.debt_to_equity)}    流动比率: {_fmt(metrics.current_ratio)}",
        ]

        if metrics.dividend_yield:
            lines.append(f"  股息率: {_fmt_pct(metrics.dividend_yield)}")

        if valuation:
            lines.extend([
                "",
                "**估值分析**:",
                f"  当前价格: ${valuation.current_price:.2f}",
            ])
            if valuation.dcf_value:
                lines.append(f"  DCF估值: ${valuation.dcf_value:.2f}")
            if valuation.peg_fair_value:
                lines.append(f"  PEG估值: ${valuation.peg_fair_value:.2f}")
            if valuation.upside_pct is not None:
                verdict_cn = {"undervalued": "低估", "overvalued": "高估", "fair": "合理"}
                lines.append(
                    f"  潜在空间: {valuation.upside_pct:+.1f}% "
                    f"({verdict_cn.get(valuation.verdict, valuation.verdict)})"
                )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(value) -> Optional[float]:
    """将小数转为百分比"""
    if value is None:
        return None
    return round(float(value) * 100, 2)


def _fmt(value, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def _fmt_pct(value) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"
