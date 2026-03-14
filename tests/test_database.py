"""Tests for storage/database.py"""
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import DatabaseManager


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """DatabaseManager backed by a temp SQLite file."""
    return DatabaseManager(db_path=str(tmp_path / "test_investment.db"))


def _price_record(**overrides):
    base = {
        "symbol": "NVDA",
        "date": "2026-03-12",
        "open": 800.0,
        "high": 820.0,
        "low": 790.0,
        "close": 810.0,
        "volume": 10_000_000,
        "sector": "ai",
        "market": "US",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestDatabaseManagerInit:
    def test_db_file_created(self, tmp_path):
        db_path = str(tmp_path / "sub" / "inv.db")
        DatabaseManager(db_path=db_path)
        assert Path(db_path).exists()

    def test_all_tables_created(self, db, tmp_path):
        with sqlite3.connect(db.db_path) as conn:
            tables = {row[0] for row in
                      conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {
            "stock_prices", "stock_info", "analysis_reports",
            "portfolios", "holdings", "trades", "news_sentiment"
        }
        assert expected.issubset(tables)


# ---------------------------------------------------------------------------
# save_stock_price / get_stock_prices
# ---------------------------------------------------------------------------

class TestStockPrice:
    def test_save_returns_true(self, db):
        assert db.save_stock_price(_price_record()) is True

    def test_save_and_retrieve(self, db):
        db.save_stock_price(_price_record())
        df = db.get_stock_prices("NVDA", days=365)
        assert len(df) == 1
        assert df.iloc[0]["symbol"] == "NVDA"
        assert df.iloc[0]["close"] == pytest.approx(810.0)

    def test_upsert_replaces_existing(self, db):
        db.save_stock_price(_price_record(close=810.0))
        db.save_stock_price(_price_record(close=999.0))
        df = db.get_stock_prices("NVDA", days=365)
        assert len(df) == 1
        assert df.iloc[0]["close"] == pytest.approx(999.0)

    def test_save_multiple_dates(self, db):
        for day in ["2026-03-10", "2026-03-11", "2026-03-12"]:
            db.save_stock_price(_price_record(date=day))
        df = db.get_stock_prices("NVDA", days=365)
        assert len(df) == 3

    def test_returns_dataframe(self, db):
        df = db.get_stock_prices("NVDA", days=30)
        assert isinstance(df, pd.DataFrame)

    def test_empty_for_unknown_symbol(self, db):
        df = db.get_stock_prices("ZZZZZ", days=30)
        assert df.empty

    def test_save_missing_optional_fields(self, db):
        record = _price_record()
        del record["sector"]
        del record["market"]
        assert db.save_stock_price(record) is True

    def test_save_invalid_record_returns_false(self, db):
        # Missing required 'symbol' key should not raise, just return False
        result = db.save_stock_price({})
        assert result is False


# ---------------------------------------------------------------------------
# save_report / get_latest_report
# ---------------------------------------------------------------------------

class TestReports:
    def test_save_report_returns_id(self, db):
        report_id = db.save_report("daily", "ai", "Content here", {"buy": ["NVDA"]})
        assert isinstance(report_id, int)
        assert report_id > 0

    def test_get_latest_report_returns_dict(self, db):
        db.save_report("daily", "ai", "Report content", {"buy": ["NVDA"]})
        result = db.get_latest_report("daily", "ai")
        assert result is not None
        assert result["report_type"] == "daily"
        assert result["sector"] == "ai"
        assert result["content"] == "Report content"

    def test_recommendations_deserialized(self, db):
        recs = {"buy": ["NVDA", "AMD"], "sell": ["INTC"]}
        db.save_report("weekly", "ai", "Weekly report", recs)
        result = db.get_latest_report("weekly", "ai")
        assert result["recommendations"] == recs

    def test_get_latest_returns_most_recent(self, db):
        db.save_report("daily", "ai", "Old report", {})
        db.save_report("daily", "ai", "New report", {})
        result = db.get_latest_report("daily", "ai")
        assert result["content"] == "New report"

    def test_get_latest_returns_none_when_missing(self, db):
        result = db.get_latest_report("daily", "nonexistent_sector")
        assert result is None

    def test_report_type_and_sector_isolated(self, db):
        db.save_report("daily", "ai", "AI daily", {})
        db.save_report("weekly", "banking", "Bank weekly", {})
        assert db.get_latest_report("weekly", "ai") is None
        assert db.get_latest_report("daily", "banking") is None


# ---------------------------------------------------------------------------
# create_portfolio / get_portfolio
# ---------------------------------------------------------------------------

class TestPortfolio:
    def test_create_portfolio_returns_id(self, db):
        portfolio_id = db.create_portfolio("Test Fund", 100_000.0)
        assert isinstance(portfolio_id, int)
        assert portfolio_id > 0

    def test_get_portfolio_returns_dict(self, db):
        pid = db.create_portfolio("My Fund", 50_000.0)
        result = db.get_portfolio(pid)
        assert result is not None
        assert result["name"] == "My Fund"
        assert result["initial_capital"] == pytest.approx(50_000.0)

    def test_current_value_equals_initial_on_creation(self, db):
        pid = db.create_portfolio("Fund", 200_000.0)
        result = db.get_portfolio(pid)
        assert result["current_value"] == pytest.approx(200_000.0)

    def test_get_portfolio_has_holdings_list(self, db):
        pid = db.create_portfolio("Fund", 100_000.0)
        result = db.get_portfolio(pid)
        assert "holdings" in result
        assert result["holdings"] == []

    def test_get_nonexistent_portfolio_returns_none(self, db):
        assert db.get_portfolio(99999) is None

    def test_multiple_portfolios_independent(self, db):
        pid1 = db.create_portfolio("Fund A", 100_000.0)
        pid2 = db.create_portfolio("Fund B", 200_000.0)
        r1 = db.get_portfolio(pid1)
        r2 = db.get_portfolio(pid2)
        assert r1["name"] == "Fund A"
        assert r2["name"] == "Fund B"
        assert r1["initial_capital"] != r2["initial_capital"]
