"""
Daily Report Generator - 日报生成器
包含市场概览、板块分析、个股推荐
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

logger = logging.getLogger(__name__)


class DailyReportGenerator(ReportGenerator):
    """日报生成器"""

    def __init__(
        self,
        sector_data: Dict[str, List[Dict]],
        config: Optional[ReportConfig] = None,
    ):
        """
        Args:
            sector_data: {sector_name: [{"symbol": str, "name": str, "df": pd.DataFrame}]}
            config: 报告配置
        """
        if config is None:
            config = ReportConfig(title=f"市场日报 {datetime.now().strftime('%Y-%m-%d')}")
        super().__init__(config)
        self.sector_data = sector_data
        self._analyzed: Optional[Dict] = None  # lazy cache

    def markdown_template_name(self) -> str:
        return "daily_report.md"

    def html_template_name(self) -> str:
        return "daily_report.html"

    def get_template_data(self) -> Dict[str, Any]:
        if self._analyzed is None:
            self._analyzed = self._analyze_all()
        return self._analyzed

    # ------------------------------------------------------------------
    # Internal analysis
    # ------------------------------------------------------------------

    def _analyze_all(self) -> Dict[str, Any]:
        sectors_output = []
        all_stocks: List[Dict] = []

        for sector_key, stocks in self.sector_data.items():
            sector_stocks = []
            for item in stocks:
                stock_row = self._analyze_stock(item)
                if stock_row:
                    sector_stocks.append(stock_row)
                    all_stocks.append(stock_row)

            if sector_stocks:
                sectors_output.append(
                    self._build_sector_summary(sector_key, sector_stocks)
                )

        market_overview = self._build_market_overview(all_stocks)
        buy_recs = self._build_buy_recommendations(all_stocks)
        sell_recs = self._build_sell_recommendations(all_stocks)

        return {
            "title": self.config.title,
            "market_overview": market_overview,
            "sectors": sectors_output,
            "buy_recommendations": buy_recs,
            "sell_recommendations": sell_recs,
        }

    def _analyze_stock(self, item: Dict) -> Optional[Dict]:
        """分析单只股票，返回展示数据行"""
        symbol = item.get("symbol", "")
        name = item.get("name", symbol)
        df: Optional[pd.DataFrame] = item.get("df")

        if df is None or df.empty:
            logger.warning("No data for %s, skipping", symbol)
            return None

        # 标准化列名
        df = _normalize_df(df)

        try:
            analyzer = TechnicalAnalyzer(df)
            ind = analyzer.analyze()
            sr = analyzer.get_support_resistance()
            patterns = analyzer.detect_patterns()

            price = df["close"].iloc[-1] if "close" in df.columns else None

            return {
                "symbol": symbol,
                "name": name,
                "price": price,
                "rsi": ind.rsi_14,
                "macd": ind.macd,
                "macd_hist": ind.macd_histogram,
                "sma_5": ind.sma_5,
                "sma_20": ind.sma_20,
                "ema_12": ind.ema_12,
                "ema_26": ind.ema_26,
                "bb_position": ind.bb_position * 100 if ind.bb_position is not None else None,
                "k": ind.k,
                "d": ind.d,
                "j": ind.j,
                "atr": ind.atr_14,
                "trend": ind.trend.value,
                "signal": ind.signal.value,
                "confidence": ind.confidence,
                "support": sr["support"],
                "resistance": sr["resistance"],
                "pivot": sr["pivot"],
                "patterns": patterns,
                "reason": _build_reason(ind),
            }
        except Exception as e:
            logger.error("Failed to analyze %s: %s", symbol, e)
            return None

    def _build_sector_summary(self, sector_key: str, stocks: List[Dict]) -> Dict:
        bullish = sum(1 for s in stocks if s["trend"] == Trend.BULLISH.value)
        bearish = sum(1 for s in stocks if s["trend"] == Trend.BEARISH.value)

        if bullish > bearish:
            sentiment = "偏多"
        elif bearish > bullish:
            sentiment = "偏空"
        else:
            sentiment = "震荡"

        # collect any patterns
        patterns = []
        for s in stocks:
            for p in s.get("patterns", []):
                patterns.append({"symbol": s["symbol"], "pattern": p})

        return {
            "symbol_key": sector_key,
            "name": _sector_display_name(sector_key),
            "stock_count": len(stocks),
            "bullish_count": bullish,
            "bearish_count": bearish,
            "sentiment": sentiment,
            "stocks": stocks,
            "patterns": patterns,
        }

    def _build_market_overview(self, all_stocks: List[Dict]) -> Dict:
        if not all_stocks:
            return {
                "total_sectors": 0,
                "total_stocks": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "sentiment": "数据不足",
                "summary": "",
            }

        bullish = sum(1 for s in all_stocks if s["trend"] == Trend.BULLISH.value)
        bearish = sum(1 for s in all_stocks if s["trend"] == Trend.BEARISH.value)
        neutral = len(all_stocks) - bullish - bearish

        total = len(all_stocks)
        bull_pct = bullish / total * 100 if total else 0

        if bull_pct >= 60:
            sentiment = "市场偏多，多数标的处于上升通道"
        elif bull_pct <= 40:
            sentiment = "市场偏空，多数标的承压下行"
        else:
            sentiment = "市场震荡，多空力量相对均衡"

        return {
            "total_sectors": len(self.sector_data),
            "total_stocks": total,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "sentiment": sentiment,
            "summary": f"共分析 {len(self.sector_data)} 个板块 {total} 只股票，"
                       f"看涨 {bullish} 只，看跌 {bearish} 只，中性 {neutral} 只。",
        }

    def _build_buy_recommendations(self, all_stocks: List[Dict]) -> List[Dict]:
        recs = [s for s in all_stocks if s["signal"] == Signal.BUY.value]
        recs.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return recs[:5]

    def _build_sell_recommendations(self, all_stocks: List[Dict]) -> List[Dict]:
        recs = [s for s in all_stocks if s["signal"] == Signal.SELL.value]
        recs.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return recs[:5]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """标准化DataFrame列名为小写"""
    rename = {
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
        "Date": "date",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def _build_reason(ind) -> str:
    parts = []
    if ind.rsi_14 is not None:
        if ind.rsi_14 < 30:
            parts.append(f"RSI({ind.rsi_14:.1f})超卖")
        elif ind.rsi_14 > 70:
            parts.append(f"RSI({ind.rsi_14:.1f})超买")
    if ind.macd_histogram is not None:
        parts.append("MACD金叉" if ind.macd_histogram > 0 else "MACD死叉")
    if ind.bb_position is not None:
        if ind.bb_position < 0.1:
            parts.append("布林带触下轨")
        elif ind.bb_position > 0.9:
            parts.append("布林带触上轨")
    if ind.j is not None:
        if ind.j < 20:
            parts.append("KDJ超卖区")
        elif ind.j > 80:
            parts.append("KDJ超买区")
    return "，".join(parts) if parts else "技术指标综合判断"


def _sector_display_name(key: str) -> str:
    mapping = {
        "internet": "互联网",
        "banking": "银行",
        "finance": "金融",
        "ai": "人工智能",
        "energy": "能源",
        "gaming": "游戏",
    }
    return mapping.get(key, key)
