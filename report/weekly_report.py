"""
Weekly Report Generator - 周报生成器
包含一周回顾、趋势分析、涨跌榜
"""
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.technical import Signal, TechnicalAnalyzer, Trend
from report.generator import ReportConfig, ReportFormat, ReportGenerator
from report.daily_report import _normalize_df, _build_reason, _sector_display_name

logger = logging.getLogger(__name__)


class WeeklyReportGenerator(ReportGenerator):
    """周报生成器"""

    def __init__(
        self,
        sector_data: Dict[str, List[Dict]],
        config: Optional[ReportConfig] = None,
    ):
        """
        Args:
            sector_data: {sector_name: [{"symbol": str, "name": str, "df": pd.DataFrame}]}
                         df 需包含至少过去 5 个交易日数据
            config: 报告配置
        """
        if config is None:
            now = datetime.now()
            monday = now - timedelta(days=now.weekday())
            friday = monday + timedelta(days=4)
            config = ReportConfig(
                title=f"市场周报 {monday.strftime('%Y-%m-%d')} ~ {friday.strftime('%Y-%m-%d')}"
            )
        super().__init__(config)
        self.sector_data = sector_data
        self._week_start, self._week_end = self._calc_week_range()
        self._analyzed: Optional[Dict] = None

    def markdown_template_name(self) -> str:
        return "weekly_report.md"

    def html_template_name(self) -> str:
        return "weekly_report.html"

    def get_template_data(self) -> Dict[str, Any]:
        if self._analyzed is None:
            self._analyzed = self._analyze_all()
        return self._analyzed

    # ------------------------------------------------------------------

    def _calc_week_range(self):
        now = datetime.now()
        monday = now - timedelta(days=now.weekday())
        friday = monday + timedelta(days=4)
        return monday.strftime("%Y-%m-%d"), friday.strftime("%Y-%m-%d")

    def _analyze_all(self) -> Dict[str, Any]:
        sectors_output = []
        all_stocks: List[Dict] = []

        for sector_key, stocks in self.sector_data.items():
            sector_stocks = []
            for item in stocks:
                row = self._analyze_stock(item)
                if row:
                    sector_stocks.append(row)
                    all_stocks.append(row)
            if sector_stocks:
                sectors_output.append({
                    "symbol_key": sector_key,
                    "name": _sector_display_name(sector_key),
                    "stocks": sector_stocks,
                })

        # 排行榜
        sortable = [s for s in all_stocks if s.get("week_change") is not None]
        top_performers = sorted(sortable, key=lambda x: x["week_change"], reverse=True)[:5]
        bottom_performers = sorted(sortable, key=lambda x: x["week_change"])[:5]

        trend_analysis = self._build_trend_analysis(sectors_output)
        outlook = self._build_outlook(all_stocks)

        return {
            "title": self.config.title,
            "week_start": self._week_start,
            "week_end": self._week_end,
            "sectors": sectors_output,
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,
            "trend_analysis": trend_analysis,
            "outlook": outlook,
        }

    def _analyze_stock(self, item: Dict) -> Optional[Dict]:
        symbol = item.get("symbol", "")
        name = item.get("name", symbol)
        df: Optional[pd.DataFrame] = item.get("df")

        if df is None or df.empty:
            return None

        df = _normalize_df(df)
        if "close" not in df.columns:
            return None

        try:
            analyzer = TechnicalAnalyzer(df)
            ind = analyzer.analyze()

            price = df["close"].iloc[-1]

            # 周涨跌幅：取最近5个交易日
            week_change = None
            if len(df) >= 5:
                week_open = df["close"].iloc[-5]
                if week_open and week_open != 0:
                    week_change = (price - week_open) / week_open * 100

            week_high = df["high"].tail(5).max() if "high" in df.columns else None
            week_low = df["low"].tail(5).min() if "low" in df.columns else None

            # 均量变化
            volume_change = None
            if "volume" in df.columns and len(df) >= 10:
                recent_vol = df["volume"].tail(5).mean()
                prev_vol = df["volume"].iloc[-10:-5].mean()
                if prev_vol and prev_vol != 0:
                    volume_change = (recent_vol - prev_vol) / prev_vol * 100

            return {
                "symbol": symbol,
                "name": name,
                "price": price,
                "week_change": week_change,
                "week_high": week_high,
                "week_low": week_low,
                "volume_change": volume_change,
                "trend": ind.trend.value,
                "signal": ind.signal.value,
                "confidence": ind.confidence,
                "rsi": ind.rsi_14,
                "macd_hist": ind.macd_histogram,
                "reason": _build_reason(ind),
            }
        except Exception as e:
            logger.error("Weekly analysis failed for %s: %s", symbol, e)
            return None

    def _build_trend_analysis(self, sectors: List[Dict]) -> Dict:
        strong = []
        weak = []
        for sec in sectors:
            stocks = sec["stocks"]
            bull = sum(1 for s in stocks if s["trend"] == Trend.BULLISH.value)
            bear = sum(1 for s in stocks if s["trend"] == Trend.BEARISH.value)
            total = len(stocks)
            if total == 0:
                continue
            bull_pct = bull / total * 100
            if bull_pct >= 60:
                strong.append({"name": sec["name"], "reason": f"{bull}/{total} 只标的看涨"})
            elif bull_pct <= 40:
                weak.append({"name": sec["name"], "reason": f"{bear}/{total} 只标的看跌"})
        return {"strong_sectors": strong, "weak_sectors": weak}

    def _build_outlook(self, all_stocks: List[Dict]) -> Dict:
        # 选出高置信度买入信号作为下周关注
        watchlist = [
            s for s in all_stocks
            if s.get("signal") == Signal.BUY.value and s.get("confidence", 0) > 50
        ]
        watchlist.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        bull_count = sum(1 for s in all_stocks if s["trend"] == Trend.BULLISH.value)
        total = len(all_stocks)
        bull_pct = bull_count / total * 100 if total else 0

        if bull_pct >= 60:
            summary = "整体市场多头力量较强，下周可关注强势突破个股。"
        elif bull_pct <= 40:
            summary = "整体市场空头压力较大，下周需注意防御，控制仓位。"
        else:
            summary = "市场方向不明，下周建议观望为主，等待方向选择。"

        return {
            "summary": summary,
            "watchlist": [
                {"symbol": s["symbol"], "reason": s.get("reason", "")}
                for s in watchlist[:5]
            ],
        }
