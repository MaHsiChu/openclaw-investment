"""Tests for report generation module"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from report.generator import ReportConfig, ReportFormat, ReportGenerator
from report.daily_report import DailyReportGenerator, _normalize_df, _build_reason, _sector_display_name
from report.weekly_report import WeeklyReportGenerator
from report.sector_report import SectorReportGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 60, base_price: float = 100.0, seed: int = 42) -> pd.DataFrame:
    """生成模拟OHLCV数据"""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="B")
    closes = base_price + np.cumsum(rng.normal(0, 1, n))
    opens = closes + rng.normal(0, 0.5, n)
    highs = np.maximum(closes, opens) + np.abs(rng.normal(0, 0.3, n))
    lows = np.minimum(closes, opens) - np.abs(rng.normal(0, 0.3, n))
    volumes = rng.integers(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }, index=dates)


def _make_sector_data(symbols=("NVDA", "AMD"), sector="ai"):
    return {
        sector: [
            {"symbol": sym, "name": sym, "df": _make_ohlcv(seed=i)}
            for i, sym in enumerate(symbols)
        ]
    }


@pytest.fixture
def daily_config(tmp_path):
    return ReportConfig(
        title="测试日报",
        output_dir=str(tmp_path / "reports"),
    )


@pytest.fixture
def sector_data():
    return _make_sector_data()


# ---------------------------------------------------------------------------
# ReportConfig / ReportFormat
# ---------------------------------------------------------------------------

class TestReportConfig:
    def test_defaults(self):
        cfg = ReportConfig()
        assert cfg.format == ReportFormat.MARKDOWN
        assert cfg.output_dir is None

    def test_custom_values(self):
        cfg = ReportConfig(title="Test", format=ReportFormat.HTML)
        assert cfg.title == "Test"
        assert cfg.format == ReportFormat.HTML


# ---------------------------------------------------------------------------
# DailyReportGenerator
# ---------------------------------------------------------------------------

class TestDailyReportGenerator:
    def test_generate_markdown(self, sector_data):
        gen = DailyReportGenerator(sector_data)
        result = gen.generate(ReportFormat.MARKDOWN)
        assert result.format == ReportFormat.MARKDOWN
        assert len(result.content) > 0
        assert "市场概览" in result.content
        assert "板块分析" in result.content
        assert "个股推荐" in result.content

    def test_generate_html(self, sector_data):
        gen = DailyReportGenerator(sector_data)
        result = gen.generate(ReportFormat.HTML)
        assert result.format == ReportFormat.HTML
        assert "<!DOCTYPE html>" in result.content
        assert "市场概览" in result.content

    def test_symbols_appear_in_report(self, sector_data):
        gen = DailyReportGenerator(sector_data)
        result = gen.generate(ReportFormat.MARKDOWN)
        assert "NVDA" in result.content
        assert "AMD" in result.content

    def test_saves_to_file(self, sector_data, tmp_path):
        cfg = ReportConfig(output_dir=str(tmp_path / "out"))
        gen = DailyReportGenerator(sector_data, config=cfg)
        result = gen.generate()
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.read_text(encoding="utf-8") == result.content

    def test_empty_sector_data(self):
        gen = DailyReportGenerator({})
        result = gen.generate()
        assert "0" in result.content  # stock counts zero

    def test_stock_missing_df_skipped(self):
        data = {"ai": [{"symbol": "NVDA", "name": "NVIDIA", "df": None}]}
        gen = DailyReportGenerator(data)
        result = gen.generate()
        assert result.content  # doesn't crash

    def test_stock_empty_df_skipped(self):
        data = {"ai": [{"symbol": "NVDA", "name": "NVIDIA", "df": pd.DataFrame()}]}
        gen = DailyReportGenerator(data)
        result = gen.generate()
        assert result.content

    def test_market_overview_counts(self, sector_data):
        gen = DailyReportGenerator(sector_data)
        data = gen.get_template_data()
        ov = data["market_overview"]
        assert ov["total_stocks"] == 2
        assert ov["bullish_count"] + ov["bearish_count"] + ov["neutral_count"] == 2

    def test_buy_recommendations_max_5(self):
        # Create many stocks that should all get buy signals
        many = {
            "ai": [{"symbol": f"S{i}", "name": f"Stock{i}", "df": _make_ohlcv(seed=i * 7 + 1)}
                   for i in range(10)]
        }
        gen = DailyReportGenerator(many)
        data = gen.get_template_data()
        assert len(data["buy_recommendations"]) <= 5
        assert len(data["sell_recommendations"]) <= 5

    def test_multiple_sectors(self):
        data = {
            "ai": [{"symbol": "NVDA", "name": "NVIDIA", "df": _make_ohlcv(seed=1)}],
            "banking": [{"symbol": "JPM", "name": "JPMorgan", "df": _make_ohlcv(seed=2)}],
        }
        gen = DailyReportGenerator(data)
        result = gen.generate()
        assert "NVDA" in result.content
        assert "JPM" in result.content


# ---------------------------------------------------------------------------
# WeeklyReportGenerator
# ---------------------------------------------------------------------------

class TestWeeklyReportGenerator:
    def test_generate_markdown(self, sector_data):
        gen = WeeklyReportGenerator(sector_data)
        result = gen.generate(ReportFormat.MARKDOWN)
        assert "一周回顾" in result.content
        assert "趋势分析" in result.content
        assert "涨幅榜" in result.content

    def test_generate_html(self, sector_data):
        gen = WeeklyReportGenerator(sector_data)
        result = gen.generate(ReportFormat.HTML)
        assert "<!DOCTYPE html>" in result.content

    def test_week_range_in_output(self, sector_data):
        gen = WeeklyReportGenerator(sector_data)
        result = gen.generate()
        assert gen._week_start in result.content
        assert gen._week_end in result.content

    def test_performers_capped_at_5(self):
        many = {
            "ai": [{"symbol": f"T{i}", "name": f"T{i}", "df": _make_ohlcv(seed=i + 100)}
                   for i in range(10)]
        }
        gen = WeeklyReportGenerator(many)
        data = gen.get_template_data()
        assert len(data["top_performers"]) <= 5
        assert len(data["bottom_performers"]) <= 5

    def test_outlook_present(self, sector_data):
        gen = WeeklyReportGenerator(sector_data)
        data = gen.get_template_data()
        assert "summary" in data["outlook"]
        assert "watchlist" in data["outlook"]

    def test_symbols_in_output(self, sector_data):
        gen = WeeklyReportGenerator(sector_data)
        result = gen.generate()
        assert "NVDA" in result.content or "AMD" in result.content

    def test_saves_html_to_file(self, sector_data, tmp_path):
        cfg = ReportConfig(output_dir=str(tmp_path / "weekly"))
        gen = WeeklyReportGenerator(sector_data, config=cfg)
        result = gen.generate(ReportFormat.HTML)
        assert result.output_path is not None
        assert result.output_path.suffix == ".html"


# ---------------------------------------------------------------------------
# SectorReportGenerator
# ---------------------------------------------------------------------------

class TestSectorReportGenerator:
    def test_generate_markdown(self):
        stocks = [
            {"symbol": "NVDA", "name": "NVIDIA", "df": _make_ohlcv(seed=1)},
            {"symbol": "AMD", "name": "AMD", "df": _make_ohlcv(seed=2)},
        ]
        gen = SectorReportGenerator("ai", stocks)
        result = gen.generate(ReportFormat.MARKDOWN)
        assert "板块概览" in result.content
        assert "个股深度分析" in result.content
        assert "NVDA" in result.content
        assert "AMD" in result.content

    def test_generate_html(self):
        stocks = [{"symbol": "NVDA", "name": "NVIDIA", "df": _make_ohlcv(seed=1)}]
        gen = SectorReportGenerator("ai", stocks)
        result = gen.generate(ReportFormat.HTML)
        assert "<!DOCTYPE html>" in result.content
        assert "NVDA" in result.content

    def test_sector_name_in_report(self):
        stocks = [{"symbol": "JPM", "name": "JPMorgan", "df": _make_ohlcv(seed=3)}]
        gen = SectorReportGenerator("banking", stocks)
        result = gen.generate()
        assert "银行" in result.content

    def test_overview_rating_present(self):
        stocks = [{"symbol": "NVDA", "name": "NVIDIA", "df": _make_ohlcv(seed=1)}]
        gen = SectorReportGenerator("ai", stocks)
        data = gen.get_template_data()
        assert data["overview"]["rating"] in ("强烈看多", "温和看多", "中性震荡", "看空")

    def test_correlation_structure(self):
        stocks = [
            {"symbol": "NVDA", "name": "NVIDIA", "df": _make_ohlcv(seed=1)},
            {"symbol": "AMD", "name": "AMD", "df": _make_ohlcv(seed=2)},
        ]
        gen = SectorReportGenerator("ai", stocks)
        data = gen.get_template_data()
        corr = data["correlation"]
        assert "consistency" in corr
        assert 0 <= corr["consistency"] <= 100

    def test_empty_stocks(self):
        gen = SectorReportGenerator("ai", [])
        result = gen.generate()
        assert result.content

    def test_saves_to_file(self, tmp_path):
        stocks = [{"symbol": "NVDA", "name": "NVIDIA", "df": _make_ohlcv(seed=1)}]
        cfg = ReportConfig(output_dir=str(tmp_path / "sector"))
        gen = SectorReportGenerator("ai", stocks, config=cfg)
        result = gen.generate()
        assert result.output_path is not None
        assert "sector_ai" in result.output_path.name

    def test_insufficient_data_graceful(self):
        """少量数据不应崩溃（analyze()返回空指标）"""
        short_df = _make_ohlcv(n=10)  # < 50 rows, analyze() returns empty TechnicalIndicators
        stocks = [{"symbol": "NVDA", "name": "NVIDIA", "df": short_df}]
        gen = SectorReportGenerator("ai", stocks)
        result = gen.generate()
        assert result.content


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_normalize_df_uppercase(self):
        df = pd.DataFrame({"Open": [1], "High": [2], "Low": [0.5], "Close": [1.5], "Volume": [100]})
        out = _normalize_df(df)
        assert "close" in out.columns
        assert "Open" not in out.columns

    def test_normalize_df_already_lowercase(self):
        df = pd.DataFrame({"open": [1], "close": [1.5]})
        out = _normalize_df(df)
        assert "open" in out.columns

    def test_sector_display_name_known(self):
        assert _sector_display_name("ai") == "人工智能"
        assert _sector_display_name("banking") == "银行"

    def test_sector_display_name_unknown(self):
        assert _sector_display_name("unknown_sector") == "unknown_sector"
