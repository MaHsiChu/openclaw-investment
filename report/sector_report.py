"""
Sector Report Generator - 板块深度分析报告
对单一板块内所有标的进行技术分析并输出深度报告
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.technical import Signal, TechnicalAnalyzer, Trend
from report.generator import ReportConfig, ReportFormat, ReportGenerator
from report.daily_report import _normalize_df, _build_reason, _sector_display_name

logger = logging.getLogger(__name__)


class SectorReportGenerator(ReportGenerator):
    """板块深度分析报告生成器"""

    def __init__(
        self,
        sector_key: str,
        stocks: List[Dict],
        config: Optional[ReportConfig] = None,
    ):
        """
        Args:
            sector_key: 板块标识，例如 "ai"
            stocks: [{"symbol": str, "name": str, "df": pd.DataFrame}, ...]
            config: 报告配置
        """
        sector_name = _sector_display_name(sector_key)
        if config is None:
            config = ReportConfig(
                title=f"{sector_name} 板块深度分析报告 {datetime.now().strftime('%Y-%m-%d')}"
            )
        super().__init__(config)
        self.sector_key = sector_key
        self.sector_name = sector_name
        self.stocks_input = stocks
        self._analyzed: Optional[Dict] = None

    def markdown_template_name(self) -> str:
        return "sector_report.md"

    def html_template_name(self) -> str:
        return "sector_report.html"

    def get_template_data(self) -> Dict[str, Any]:
        if self._analyzed is None:
            self._analyzed = self._analyze_all()
        return self._analyzed

    def _report_filename(self) -> str:
        return f"sector_{self.sector_key}"

    # ------------------------------------------------------------------

    def _analyze_all(self) -> Dict[str, Any]:
        stocks_output = []
        for item in self.stocks_input:
            row = self._analyze_stock(item)
            if row:
                stocks_output.append(row)

        overview = self._build_overview(stocks_output)
        correlation = self._build_correlation(stocks_output)

        return {
            "title": self.config.title,
            "sector_name": self.sector_name,
            "overview": overview,
            "stocks": stocks_output,
            "correlation": correlation,
        }

    def _analyze_stock(self, item: Dict) -> Optional[Dict]:
        symbol = item.get("symbol", "")
        name = item.get("name", symbol)
        df: Optional[pd.DataFrame] = item.get("df")

        if df is None or df.empty:
            logger.warning("No data for %s", symbol)
            return None

        df = _normalize_df(df)

        try:
            analyzer = TechnicalAnalyzer(df)
            ind = analyzer.analyze()
            sr = analyzer.get_support_resistance()
            patterns = analyzer.detect_patterns()

            price = df["close"].iloc[-1] if "close" in df.columns else None

            # bb_position转百分比
            bb_pct = ind.bb_position * 100 if ind.bb_position is not None else None

            summary = self._build_stock_summary(symbol, ind, sr, patterns)

            return {
                "symbol": symbol,
                "name": name,
                "price": price,
                "trend": ind.trend.value,
                "signal": ind.signal.value,
                "confidence": ind.confidence,
                "sma_5": ind.sma_5,
                "sma_10": ind.sma_10,
                "sma_20": ind.sma_20,
                "sma_50": ind.sma_50,
                "ema_12": ind.ema_12,
                "ema_26": ind.ema_26,
                "rsi": ind.rsi_14,
                "macd": ind.macd,
                "macd_signal": ind.macd_signal,
                "macd_hist": ind.macd_histogram,
                "bb_upper": ind.bb_upper,
                "bb_middle": ind.bb_middle,
                "bb_lower": ind.bb_lower,
                "bb_width": ind.bb_width,
                "bb_position": bb_pct,
                "k": ind.k,
                "d": ind.d,
                "j": ind.j,
                "atr": ind.atr_14,
                "volume_sma": ind.volume_sma,
                "support": sr.get("support"),
                "resistance": sr.get("resistance"),
                "pivot": sr.get("pivot"),
                "patterns": patterns,
                "summary": summary,
            }
        except Exception as e:
            logger.error("Sector analysis failed for %s: %s", symbol, e)
            return None

    def _build_overview(self, stocks: List[Dict]) -> Dict:
        bullish = sum(1 for s in stocks if s["trend"] == Trend.BULLISH.value)
        bearish = sum(1 for s in stocks if s["trend"] == Trend.BEARISH.value)
        neutral = len(stocks) - bullish - bearish

        total = len(stocks)
        if total == 0:
            return {"stock_count": 0, "bullish_count": 0, "bearish_count": 0,
                    "neutral_count": 0, "rating": "N/A", "description": ""}

        bull_pct = bullish / total * 100
        if bull_pct >= 70:
            rating = "强烈看多"
            desc = f"{self.sector_name}板块整体多头强势，{bullish}/{total} 只标的看涨。"
        elif bull_pct >= 50:
            rating = "温和看多"
            desc = f"{self.sector_name}板块多头略占优势，建议关注强势个股。"
        elif bull_pct <= 30:
            rating = "看空"
            desc = f"{self.sector_name}板块空头压力较大，建议谨慎操作。"
        else:
            rating = "中性震荡"
            desc = f"{self.sector_name}板块多空力量均衡，建议等待方向选择。"

        return {
            "stock_count": total,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "rating": rating,
            "description": desc,
        }

    def _build_correlation(self, stocks: List[Dict]) -> Dict:
        if not stocks:
            return {"consistency": 0, "leaders": [], "laggards": []}

        # 趋势一致性
        trends = [s["trend"] for s in stocks]
        most_common = max(set(trends), key=trends.count)
        consistency = trends.count(most_common) / len(trends) * 100

        # 领涨：BUY信号，高置信度
        leaders = [
            s["symbol"] for s in sorted(
                [s for s in stocks if s["signal"] == Signal.BUY.value],
                key=lambda x: x.get("confidence", 0), reverse=True
            )[:3]
        ]

        # 落后：SELL信号或最低置信度
        laggards = [
            s["symbol"] for s in sorted(
                [s for s in stocks if s["signal"] == Signal.SELL.value],
                key=lambda x: x.get("confidence", 0), reverse=True
            )[:3]
        ]

        return {
            "consistency": round(consistency, 1),
            "leaders": leaders,
            "laggards": laggards,
        }

    def _build_stock_summary(self, symbol: str, ind, sr: Dict, patterns: List[str]) -> str:
        parts = []

        # 趋势
        if ind.trend == Trend.BULLISH:
            parts.append("当前处于上升趋势")
        elif ind.trend == Trend.BEARISH:
            parts.append("当前处于下降趋势")
        else:
            parts.append("当前处于震荡区间")

        # RSI
        if ind.rsi_14 is not None:
            if ind.rsi_14 < 30:
                parts.append(f"RSI({ind.rsi_14:.1f})已进入超卖区域，关注反弹机会")
            elif ind.rsi_14 > 70:
                parts.append(f"RSI({ind.rsi_14:.1f})已进入超买区域，注意获利了结风险")

        # MACD
        if ind.macd_histogram is not None:
            if ind.macd_histogram > 0:
                parts.append("MACD金叉，动能偏多")
            else:
                parts.append("MACD死叉，动能偏空")

        # 布林带
        if ind.bb_position is not None:
            if ind.bb_position < 0.1:
                parts.append("价格触及布林带下轨，超卖信号")
            elif ind.bb_position > 0.9:
                parts.append("价格触及布林带上轨，超买信号")

        # 支撑阻力
        if sr.get("support") and sr.get("resistance"):
            parts.append(
                f"关键支撑 ${sr['support']:.2f}，阻力 ${sr['resistance']:.2f}"
            )

        # K线形态
        if patterns:
            parts.append(f"K线形态: {', '.join(patterns)}")

        return "；".join(parts) + "。" if parts else ""
