"""Tests for data/market_data.py"""
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Use a temporary directory for all DB operations
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.market_data import MarketDataManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path):
    """Return a temp DB path inside a temp directory."""
    return str(tmp_path / "test_market.db")


@pytest.fixture()
def sectors_config(tmp_path):
    """Write a minimal sectors.json and return its parent directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    sectors = {
        "sectors": {
            "ai": {
                "name": "人工智能",
                "description": "AI sector",
                "stocks": {
                    "US": [
                        {"symbol": "NVDA", "name": "NVIDIA", "market": "NASDAQ"},
                        {"symbol": "AMD", "name": "AMD", "market": "NASDAQ"},
                    ]
                }
            },
            "banking": {
                "name": "银行",
                "description": "Banking sector",
                "stocks": {
                    "US": [
                        {"symbol": "JPM", "name": "JPMorgan", "market": "NYSE"},
                    ],
                    "CN": [
                        {"symbol": "601398.SS", "name": "工商银行", "market": "SSE"},
                    ]
                }
            }
        }
    }
    (config_dir / "sectors.json").write_text(json.dumps(sectors), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    """MarketDataManager with temp DB and config."""
    # Point config lookup to our temp path
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    sectors = {
        "sectors": {
            "ai": {
                "name": "人工智能",
                "description": "AI sector",
                "stocks": {
                    "US": [
                        {"symbol": "NVDA", "name": "NVIDIA", "market": "NASDAQ"},
                    ]
                }
            }
        }
    }
    (config_dir / "sectors.json").write_text(json.dumps(sectors), encoding="utf-8")
    db_path = str(tmp_path / "storage" / "test.db")
    return MarketDataManager(db_path=db_path)


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------

class TestMarketDataManagerInit:
    def test_db_file_created(self, manager, tmp_path):
        db = tmp_path / "storage" / "test.db"
        assert db.exists()

    def test_tables_created(self, manager, tmp_path):
        db_path = str(tmp_path / "storage" / "test.db")
        with sqlite3.connect(db_path) as conn:
            tables = {row[0] for row in
                      conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "stock_prices" in tables
        assert "stock_info" in tables

    def test_sectors_loaded(self, manager):
        assert "ai" in manager.sectors

    def test_missing_config_returns_empty_sectors(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # no config/sectors.json here
        db_path = str(tmp_path / "storage" / "no_config.db")
        m = MarketDataManager(db_path=db_path)
        assert m.sectors == {}


# ---------------------------------------------------------------------------
# get_sector_stocks tests
# ---------------------------------------------------------------------------

class TestGetSectorStocks:
    def test_valid_sector_returns_stocks(self, manager):
        stocks = manager.get_sector_stocks("ai")
        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "NVDA"

    def test_unknown_sector_returns_empty(self, manager):
        assert manager.get_sector_stocks("nonexistent") == []

    def test_stock_has_required_fields(self, manager):
        stocks = manager.get_sector_stocks("ai")
        assert "symbol" in stocks[0]
        assert "sector" in stocks[0]
        assert "market_type" in stocks[0]

    def test_market_type_set_from_key(self, tmp_path, monkeypatch):
        """Stocks under 'CN' key must have market_type='CN'."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        sectors = {
            "sectors": {
                "banking": {
                    "name": "银行",
                    "description": "Banks",
                    "stocks": {
                        "US": [{"symbol": "JPM", "name": "JPMorgan", "market": "NYSE"}],
                        "CN": [{"symbol": "601398.SS", "name": "工商银行", "market": "SSE"}],
                    }
                }
            }
        }
        (config_dir / "sectors.json").write_text(json.dumps(sectors), encoding="utf-8")
        db_path = str(tmp_path / "storage" / "multi.db")
        m = MarketDataManager(db_path=db_path)
        stocks = m.get_sector_stocks("banking")
        market_types = {s["symbol"]: s["market_type"] for s in stocks}
        assert market_types["JPM"] == "US"
        assert market_types["601398.SS"] == "CN"


# ---------------------------------------------------------------------------
# get_us_stock_data tests (mocked yfinance)
# ---------------------------------------------------------------------------

def _make_us_df():
    """Minimal DataFrame resembling yfinance output."""
    return pd.DataFrame({
        "Date": pd.to_datetime(["2026-03-10", "2026-03-11", "2026-03-12"]),
        "Open": [800.0, 810.0, 790.0],
        "High": [820.0, 830.0, 815.0],
        "Low":  [795.0, 800.0, 780.0],
        "Close":[810.0, 820.0, 800.0],
        "Volume": [10_000_000, 12_000_000, 9_000_000],
    })


class TestGetUsStockData:
    @patch("data.market_data._get_yf")
    def test_returns_dataframe(self, mock_get_yf, manager):
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value.history.return_value = _make_us_df()
        mock_get_yf.return_value = mock_yf

        df = manager.get_us_stock_data("NVDA", period="5d")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    @patch("data.market_data._get_yf")
    def test_symbol_column_added(self, mock_get_yf, manager):
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value.history.return_value = _make_us_df()
        mock_get_yf.return_value = mock_yf

        df = manager.get_us_stock_data("NVDA", period="5d")
        assert "symbol" in df.columns
        assert (df["symbol"] == "NVDA").all()

    @patch("data.market_data._get_yf")
    def test_correct_ticker_called(self, mock_get_yf, manager):
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value.history.return_value = _make_us_df()
        mock_get_yf.return_value = mock_yf

        manager.get_us_stock_data("AMD", period="1mo")
        mock_yf.Ticker.assert_called_once_with("AMD")


# ---------------------------------------------------------------------------
# get_cn_stock_data tests (mocked akshare)
# ---------------------------------------------------------------------------

def _make_cn_df():
    return pd.DataFrame({
        "日期": ["2026-03-10", "2026-03-11"],
        "开盘": [5.10, 5.20],
        "最高": [5.30, 5.40],
        "最低": [5.05, 5.15],
        "收盘": [5.25, 5.35],
        "成交量": [100_000_000, 120_000_000],
    })


class TestGetCnStockData:
    @patch("data.market_data._get_ak")
    def test_returns_dataframe(self, mock_get_ak, manager):
        mock_ak = MagicMock()
        mock_ak.stock_zh_a_hist.return_value = _make_cn_df()
        mock_get_ak.return_value = mock_ak

        df = manager.get_cn_stock_data("601398.SS")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    @patch("data.market_data._get_ak")
    def test_symbol_with_dot_stripped(self, mock_get_ak, manager):
        """Code '601398.SS' should call akshare with '601398'."""
        mock_ak = MagicMock()
        mock_ak.stock_zh_a_hist.return_value = _make_cn_df()
        mock_get_ak.return_value = mock_ak

        manager.get_cn_stock_data("601398.SS")
        call_kwargs = mock_ak.stock_zh_a_hist.call_args
        assert call_kwargs.kwargs.get("symbol") == "601398" or \
               call_kwargs[1].get("symbol") == "601398"

    @patch("data.market_data._get_ak")
    def test_symbol_column_added(self, mock_get_ak, manager):
        mock_ak = MagicMock()
        mock_ak.stock_zh_a_hist.return_value = _make_cn_df()
        mock_get_ak.return_value = mock_ak

        df = manager.get_cn_stock_data("601398.SS")
        assert "symbol" in df.columns


# ---------------------------------------------------------------------------
# update_stock_data tests
# ---------------------------------------------------------------------------

class TestUpdateStockData:
    @patch("data.market_data._get_yf")
    def test_us_stock_returns_true_on_success(self, mock_get_yf, manager):
        mock_yf = MagicMock()
        df = _make_us_df()
        df.reset_index(drop=True, inplace=True)
        mock_yf.Ticker.return_value.history.return_value = df
        mock_get_yf.return_value = mock_yf

        result = manager.update_stock_data("NVDA", "ai", "US")
        assert result is True

    @patch("data.market_data._get_yf")
    def test_data_persisted_in_db(self, mock_get_yf, manager, tmp_path):
        mock_yf = MagicMock()
        df = _make_us_df()
        df.reset_index(drop=True, inplace=True)
        mock_yf.Ticker.return_value.history.return_value = df
        mock_get_yf.return_value = mock_yf

        manager.update_stock_data("NVDA", "ai", "US")
        cached = manager.get_cached_data("NVDA", days=365)
        assert not cached.empty

    @patch("data.market_data._get_yf")
    def test_returns_false_on_exception(self, mock_get_yf, manager):
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value.history.side_effect = RuntimeError("network error")
        mock_get_yf.return_value = mock_yf

        result = manager.update_stock_data("NVDA", "ai", "US")
        assert result is False


# ---------------------------------------------------------------------------
# get_cached_data tests
# ---------------------------------------------------------------------------

class TestGetCachedData:
    def _insert_row(self, manager, symbol="NVDA", date="2026-03-12"):
        with sqlite3.connect(manager.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO stock_prices "
                "(symbol, date, open, high, low, close, volume, sector) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (symbol, date, 800.0, 820.0, 790.0, 810.0, 10_000_000, "ai")
            )
            conn.commit()

    def test_returns_dataframe(self, manager):
        self._insert_row(manager)
        df = manager.get_cached_data("NVDA", days=30)
        assert isinstance(df, pd.DataFrame)

    def test_correct_symbol_returned(self, manager):
        self._insert_row(manager, symbol="NVDA")
        self._insert_row(manager, symbol="AMD", date="2026-03-11")
        df = manager.get_cached_data("NVDA", days=30)
        assert (df["symbol"] == "NVDA").all()

    def test_empty_for_unknown_symbol(self, manager):
        df = manager.get_cached_data("ZZZZZ", days=30)
        assert df.empty
