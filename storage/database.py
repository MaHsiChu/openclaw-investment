"""Storage Module - 数据存储管理
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "storage/investment.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 股票价格表
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
                    market TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, date)
                )
            """)
            
            # 股票信息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    sector TEXT,
                    industry TEXT,
                    market_cap REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 分析报告表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT,
                    sector TEXT,
                    content TEXT,
                    recommendations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 投资组合表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    initial_capital REAL,
                    current_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 持仓表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER,
                    symbol TEXT,
                    shares INTEGER,
                    avg_cost REAL,
                    current_price REAL,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
                )
            """)
            
            # 交易记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER,
                    symbol TEXT,
                    action TEXT,
                    shares INTEGER,
                    price REAL,
                    date TEXT,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
                )
            """)
            
            # 新闻情绪表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news_sentiment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    title TEXT,
                    source TEXT,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    published_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_stock_price(self, data: Dict[str, Any]) -> bool:
        """保存股票价格"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume, sector, market)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['symbol'], data['date'], data['open'], data['high'],
                    data['low'], data['close'], data['volume'], 
                    data.get('sector'), data.get('market')
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error("Error saving price for %s: %s", data.get('symbol'), e)
            return False
    
    def get_stock_prices(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取股票历史价格"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM stock_prices 
                WHERE symbol = ? 
                AND date >= date('now', '-{} days')
                ORDER BY date ASC
            """.format(days)
            return pd.read_sql_query(query, conn, params=(symbol,))
    
    def save_report(self, report_type: str, sector: str, 
                    content: str, recommendations: Dict) -> int:
        """保存分析报告"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO analysis_reports 
                (report_type, sector, content, recommendations)
                VALUES (?, ?, ?, ?)
            """, (report_type, sector, content, json.dumps(recommendations)))
            conn.commit()
            return cursor.lastrowid
    
    def get_latest_report(self, report_type: str, sector: str) -> Optional[Dict]:
        """获取最新报告"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM analysis_reports
                WHERE report_type = ? AND sector = ?
                ORDER BY created_at DESC, id DESC LIMIT 1
            """, (report_type, sector))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'report_type': row[1],
                    'sector': row[2],
                    'content': row[3],
                    'recommendations': json.loads(row[4]),
                    'created_at': row[5]
                }
            return None
    
    def create_portfolio(self, name: str, initial_capital: float) -> int:
        """创建投资组合"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO portfolios (name, initial_capital, current_value)
                VALUES (?, ?, ?)
            """, (name, initial_capital, initial_capital))
            conn.commit()
            return cursor.lastrowid
    
    def get_portfolio(self, portfolio_id: int) -> Optional[Dict]:
        """获取投资组合详情"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取组合信息
            cursor = conn.execute("""
                SELECT * FROM portfolios WHERE id = ?
            """, (portfolio_id,))
            portfolio_row = cursor.fetchone()
            if not portfolio_row:
                return None
            
            # 获取持仓
            cursor = conn.execute("""
                SELECT * FROM holdings WHERE portfolio_id = ?
            """, (portfolio_id,))
            holdings = []
            for row in cursor.fetchall():
                holdings.append({
                    'id': row[0],
                    'symbol': row[2],
                    'shares': row[3],
                    'avg_cost': row[4],
                    'current_price': row[5]
                })
            
            return {
                'id': portfolio_row[0],
                'name': portfolio_row[1],
                'initial_capital': portfolio_row[2],
                'current_value': portfolio_row[3],
                'created_at': portfolio_row[4],
                'holdings': holdings
            }


if __name__ == "__main__":
    db = DatabaseManager()
    print("Database initialized successfully!")
    
    # 测试创建组合
    portfolio_id = db.create_portfolio("Test Portfolio", 100000.0)
    print(f"Created portfolio: {portfolio_id}")
