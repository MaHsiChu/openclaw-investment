"""Market Data Module - 股票数据获取
支持美股(yfinance)和A股(akshare)
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)

# 延迟导入，避免启动时加载
def _get_yf():
    import yfinance as yf
    return yf

def _get_ak():
    import akshare as ak
    return ak


class MarketDataManager:
    """市场数据管理器"""
    
    def __init__(self, db_path: str = "storage/market_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_sectors()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    sector TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    sector TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def _load_sectors(self):
        """加载板块配置"""
        config_path = Path("config/sectors.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.sectors = json.load(f)["sectors"]
        else:
            self.sectors = {}
    
    def get_us_stock_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """获取美股数据"""
        yf = _get_yf()
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        df.reset_index(inplace=True)
        df['symbol'] = symbol
        return df
    
    def get_cn_stock_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """获取A股数据"""
        ak = _get_ak()
        # 转换symbol格式
        if '.' in symbol:
            code = symbol.split('.')[0]
        else:
            code = symbol
        
        # 获取日K数据
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                                end_date=datetime.now().strftime("%Y%m%d"))
        df['symbol'] = symbol
        return df
    
    def get_sector_stocks(self, sector_name: str) -> List[Dict]:
        """获取板块股票列表"""
        if sector_name not in self.sectors:
            return []
        
        stocks = []
        sector = self.sectors[sector_name]
        for market, market_stocks in sector["stocks"].items():
            for stock in market_stocks:
                stocks.append({
                    **stock,
                    "sector": sector_name,
                    "market_type": market
                })
        return stocks
    
    def update_stock_data(self, symbol: str, sector: str, market_type: str = "US") -> bool:
        """更新股票数据到数据库"""
        try:
            if market_type == "US":
                df = self.get_us_stock_data(symbol)
            else:
                df = self.get_cn_stock_data(symbol)
            
            # 转换日期格式
            if 'Date' in df.columns:
                df['date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            elif '日期' in df.columns:
                df['date'] = df['日期']
            
            # 标准化列名
            column_mapping = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 
                'Close': 'close', 'Volume': 'volume',
                '开盘': 'open', '最高': 'high', '最低': 'low',
                '收盘': 'close', '成交量': 'volume'
            }
            df = df.rename(columns=column_mapping)
            
            # 写入数据库
            with sqlite3.connect(self.db_path) as conn:
                for _, row in df.iterrows():
                    conn.execute("""
                        INSERT OR REPLACE INTO stock_prices 
                        (symbol, date, open, high, low, close, volume, sector)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, row.get('date'), 
                        float(row.get('open', 0)), float(row.get('high', 0)),
                        float(row.get('low', 0)), float(row.get('close', 0)),
                        int(row.get('volume', 0)), sector
                    ))
                conn.commit()
            return True
        except Exception as e:
            logger.error("Error updating %s: %s", symbol, e)
            return False
    
    def get_cached_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """从缓存获取数据"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM stock_prices 
                WHERE symbol = ? 
                AND date >= date('now', '-{} days')
                ORDER BY date DESC
            """.format(days)
            df = pd.read_sql_query(query, conn, params=(symbol,))
        return df
    
    def update_all_sectors(self):
        """更新所有板块数据"""
        for sector_name in self.sectors:
            logger.info("Updating sector: %s", sector_name)
            stocks = self.get_sector_stocks(sector_name)
            for stock in stocks:
                success = self.update_stock_data(
                    stock["symbol"],
                    sector_name,
                    stock.get("market_type", "US")
                )
                if success:
                    logger.debug("Updated %s successfully", stock["symbol"])
                else:
                    logger.warning("Failed to update %s", stock["symbol"])


if __name__ == "__main__":
    # 测试
    mdm = MarketDataManager()
    print("Loading sectors...")
    print(f"Available sectors: {list(mdm.sectors.keys())}")
    
    # 测试获取数据
    print("\nTesting NVDA data fetch...")
    df = mdm.get_us_stock_data("NVDA", period="5d")
    print(df.head())
    
    # 测试更新
    print("\nUpdating NVDA data to database...")
    mdm.update_stock_data("NVDA", "ai", "US")
    
    print("\nDone!")
