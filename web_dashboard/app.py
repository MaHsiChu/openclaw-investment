"""OpenClaw Investment Dashboard - Flask Web Application"""
import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.market_data import MarketDataManager
from storage.database import DatabaseManager
from evolution.engine import EvolutionEngine, KnowledgeBase

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Globals & cache
# ---------------------------------------------------------------------------
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 60  # seconds

_start_time = datetime.now()


def _get_cached(key: str):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL:
            return entry["data"]
    return None


def _set_cached(key: str, data):
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}


# ---------------------------------------------------------------------------
# Lazy singletons (created on first request so Flask starts fast)
# ---------------------------------------------------------------------------
_mdm = None
_db = None
_evo = None


def get_mdm() -> MarketDataManager:
    global _mdm
    if _mdm is None:
        _mdm = MarketDataManager(db_path=str(PROJECT_ROOT / "storage" / "market_data.db"))
    return _mdm


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager(db_path=str(PROJECT_ROOT / "storage" / "investment.db"))
    return _db


def get_evo() -> EvolutionEngine:
    global _evo
    if _evo is None:
        _evo = EvolutionEngine(db_path=str(PROJECT_ROOT / "storage" / "evolution.db"))
    return _evo


# ---------------------------------------------------------------------------
# Helper: read sectors.json directly for fast access
# ---------------------------------------------------------------------------
def _load_sectors() -> dict:
    cached = _get_cached("sectors_config")
    if cached:
        return cached
    config_path = PROJECT_ROOT / "config" / "sectors.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)["sectors"]
        _set_cached("sectors_config", data)
        return data
    return {}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API: System
# ---------------------------------------------------------------------------
@app.route("/api/status")
def api_status():
    uptime = datetime.now() - _start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return jsonify({
        "status": "running",
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "started_at": _start_time.isoformat(),
        "version": "1.0.0",
        "sectors_count": len(_load_sectors()),
    })


# ---------------------------------------------------------------------------
# API: Sectors
# ---------------------------------------------------------------------------
@app.route("/api/sectors")
def api_sectors():
    sectors = _load_sectors()
    result = []
    for key, val in sectors.items():
        stock_count = sum(len(stocks) for stocks in val["stocks"].values())
        result.append({
            "id": key,
            "name": val["name"],
            "description": val["description"],
            "stock_count": stock_count,
            "markets": list(val["stocks"].keys()),
        })
    return jsonify(result)


# ---------------------------------------------------------------------------
# API: Stocks per sector
# ---------------------------------------------------------------------------
@app.route("/api/stocks/<sector>")
def api_stocks(sector):
    mdm = get_mdm()
    stocks = mdm.get_sector_stocks(sector)
    if not stocks:
        return jsonify({"error": f"Sector '{sector}' not found"}), 404

    enriched = []
    for s in stocks:
        symbol = s["symbol"]
        price_data = _get_latest_price(symbol)
        enriched.append({**s, **price_data})
    return jsonify(enriched)


def _get_latest_price(symbol: str) -> dict:
    """Get latest price info from cache/db."""
    cache_key = f"price_{symbol}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    mdm = get_mdm()
    df = mdm.get_cached_data(symbol, days=5)
    if df.empty:
        result = {"close": None, "change": None, "change_pct": None, "volume": None}
    else:
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else df.iloc[0]
        close = float(latest.get("close", 0))
        prev_close = float(prev.get("close", close))
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        result = {
            "close": round(close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(latest.get("volume", 0)),
            "date": latest.get("date", ""),
        }
    _set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# API: Chart data for a symbol
# ---------------------------------------------------------------------------
@app.route("/api/chart/<symbol>")
def api_chart(symbol):
    days = request.args.get("days", 90, type=int)
    mdm = get_mdm()
    df = mdm.get_cached_data(symbol, days=days)

    if df.empty:
        # Try fetching fresh data
        try:
            df = mdm.get_us_stock_data(symbol, period="3mo")
            if df.empty:
                return jsonify({"symbol": symbol, "data": [], "indicators": {"sma20": [], "sma50": []}}), 200
            # Normalize columns
            col_map = {"Date": "date", "Open": "open", "High": "high",
                       "Low": "low", "Close": "close", "Volume": "volume"}
            df = df.rename(columns=col_map)
            if "date" in df.columns:
                df["date"] = df["date"].astype(str).str[:10]
        except Exception:
            return jsonify({"symbol": symbol, "data": [], "indicators": {"sma20": [], "sma50": []}}), 200

    records = []
    for _, row in df.iterrows():
        records.append({
            "date": str(row.get("date", ""))[:10],
            "open": round(float(row.get("open", 0)), 2),
            "high": round(float(row.get("high", 0)), 2),
            "low": round(float(row.get("low", 0)), 2),
            "close": round(float(row.get("close", 0)), 2),
            "volume": int(row.get("volume", 0)),
        })

    # Sort by date ascending
    records.sort(key=lambda r: r["date"])

    # Calculate simple technical indicators
    closes = [r["close"] for r in records]
    sma20 = _rolling_avg(closes, 20)
    sma50 = _rolling_avg(closes, 50)

    return jsonify({
        "symbol": symbol,
        "data": records,
        "indicators": {
            "sma20": sma20,
            "sma50": sma50,
        },
    })


def _rolling_avg(values: list, window: int) -> list:
    result = [None] * len(values)
    for i in range(window - 1, len(values)):
        result[i] = round(sum(values[i - window + 1:i + 1]) / window, 2)
    return result


# ---------------------------------------------------------------------------
# API: Portfolio
# ---------------------------------------------------------------------------
@app.route("/api/portfolio")
def api_portfolio():
    db = get_db()
    # Get all portfolios
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute("SELECT * FROM portfolios ORDER BY id DESC")
            rows = cursor.fetchall()
            portfolios = []
            for row in rows:
                portfolio = db.get_portfolio(row[0])
                if portfolio:
                    # Calculate unrealized P&L
                    total_cost = sum(h["shares"] * h["avg_cost"] for h in portfolio["holdings"])
                    total_market = sum(h["shares"] * h["current_price"] for h in portfolio["holdings"])
                    portfolio["total_cost"] = round(total_cost, 2)
                    portfolio["total_market_value"] = round(total_market, 2)
                    portfolio["unrealized_pnl"] = round(total_market - total_cost, 2)
                    portfolios.append(portfolio)
    except Exception:
        portfolios = []

    if not portfolios:
        # Return demo data
        portfolios = [{
            "id": 0,
            "name": "模拟组合",
            "initial_capital": 100000.0,
            "current_value": 100000.0,
            "created_at": datetime.now().isoformat(),
            "holdings": [],
            "total_cost": 0,
            "total_market_value": 0,
            "unrealized_pnl": 0,
        }]

    return jsonify(portfolios)


# ---------------------------------------------------------------------------
# API: Reports
# ---------------------------------------------------------------------------
@app.route("/api/reports")
def api_reports():
    db = get_db()
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, report_type, sector, created_at
                FROM analysis_reports
                ORDER BY created_at DESC
                LIMIT 50
            """)
            reports = []
            for row in cursor.fetchall():
                reports.append({
                    "id": row[0],
                    "type": row[1],
                    "sector": row[2],
                    "created_at": row[3],
                })
    except Exception:
        reports = []
    return jsonify(reports)


@app.route("/api/reports/<int:report_id>")
def api_report_detail(report_id):
    db = get_db()
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_reports WHERE id = ?", (report_id,)
            )
            row = cursor.fetchone()
            if row:
                return jsonify({
                    "id": row[0],
                    "type": row[1],
                    "sector": row[2],
                    "content": row[3],
                    "recommendations": json.loads(row[4]) if row[4] else {},
                    "created_at": row[5],
                })
    except Exception:
        pass
    return jsonify({"error": "Report not found"}), 404


# ---------------------------------------------------------------------------
# API: Simulation status
# ---------------------------------------------------------------------------
@app.route("/api/simulation/status")
def api_simulation_status():
    strategies = [
        {
            "name": "均值回归策略",
            "type": "mean_reversion",
            "status": "active",
            "params": {"lookback": 20, "entry_std": 2.0, "exit_std": 0.5},
        },
        {
            "name": "动量策略",
            "type": "momentum",
            "status": "active",
            "params": {"fast_period": 10, "slow_period": 30, "rsi_threshold": 70},
        },
        {
            "name": "多因子策略",
            "type": "multi_factor",
            "status": "active",
            "params": {"lookback": 20, "buy_threshold": 0.6},
        },
    ]

    # Try loading backtest results from the strategy pool
    try:
        evo = get_evo()
        top = evo.strategy_pool.get_top_strategies(limit=5)
        for s in top:
            strategies.append({
                "name": s.get("name", "Unknown"),
                "type": s.get("type", "custom"),
                "status": "tested",
                "params": json.loads(s.get("params", "{}")),
                "performance_score": s.get("performance_score"),
                "win_rate": s.get("win_rate"),
                "sharpe_ratio": s.get("sharpe_ratio"),
                "generation": s.get("generation"),
            })
    except Exception:
        pass

    return jsonify({
        "strategies": strategies,
        "simulation_running": False,
        "last_backtest": None,
    })


# ---------------------------------------------------------------------------
# API: Evolution status
# ---------------------------------------------------------------------------
@app.route("/api/evolution/status")
def api_evolution_status():
    try:
        evo = get_evo()
        records = evo.get_recent_evolutions(limit=20)
        history = [r.to_dict() for r in records]
    except Exception:
        history = []

    # Knowledge base stats
    try:
        kb = get_evo().knowledge_base
        with sqlite3.connect(kb.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0]
            processed = conn.execute(
                "SELECT COUNT(*) FROM knowledge_items WHERE processed = TRUE"
            ).fetchone()[0]
            unprocessed = total - processed
    except Exception:
        total = processed = unprocessed = 0

    # Completion estimates per evolution type
    type_stats = {}
    for r in history:
        t = r["type"]
        if t not in type_stats:
            type_stats[t] = {"total": 0, "completed": 0, "failed": 0}
        type_stats[t]["total"] += 1
        if r["status"] == "completed":
            type_stats[t]["completed"] += 1
        elif r["status"] == "failed":
            type_stats[t]["failed"] += 1

    return jsonify({
        "knowledge_base": {
            "total_items": total,
            "processed": processed,
            "unprocessed": unprocessed,
        },
        "evolution_history": history,
        "type_stats": type_stats,
        "phase_progress": {
            "phase_0": {"name": "自我进化框架", "progress": 70},
            "phase_1": {"name": "数据获取层", "progress": 100},
            "phase_2": {"name": "技术分析+报告", "progress": 100},
            "phase_3": {"name": "AI分析+基本面", "progress": 100},
            "phase_4": {"name": "投资模拟+回测", "progress": 90},
            "phase_5": {"name": "OpenClaw集成", "progress": 30},
        },
    })


# ---------------------------------------------------------------------------
# API: Refresh data (trigger update for a symbol or sector)
# ---------------------------------------------------------------------------
@app.route("/api/refresh/<symbol>", methods=["POST"])
def api_refresh(symbol):
    mdm = get_mdm()
    sectors = _load_sectors()

    # Find which sector this symbol belongs to
    sector_name = None
    market_type = "US"
    for sname, sdata in sectors.items():
        for mkt, stocks in sdata["stocks"].items():
            for st in stocks:
                if st["symbol"] == symbol:
                    sector_name = sname
                    market_type = mkt
                    break

    if sector_name is None:
        return jsonify({"error": "Symbol not found in config"}), 404

    success = mdm.update_stock_data(symbol, sector_name, market_type)
    # Clear price cache
    with _cache_lock:
        _cache.pop(f"price_{symbol}", None)

    return jsonify({"success": success, "symbol": symbol})


# ---------------------------------------------------------------------------
# API: Alerts - 预警系统
# ---------------------------------------------------------------------------
_alert_manager = None
_alert_engine = None

def get_alert_manager():
    global _alert_manager
    if _alert_manager is None:
        from alerts.manager import AlertManager
        _alert_manager = AlertManager()
    return _alert_manager

def get_alert_engine():
    global _alert_engine
    if _alert_engine is None:
        from alerts.engine import AlertEngine
        _alert_engine = AlertEngine()
    return _alert_engine


@app.route("/api/alerts/rules", methods=["GET"])
def api_alerts_rules():
    """获取预警规则列表"""
    manager = get_alert_manager()
    symbol = request.args.get('symbol')
    status = request.args.get('status')
    
    rules = manager.get_rules(symbol=symbol, status=status)
    return jsonify([rule.to_dict() for rule in rules])


@app.route("/api/alerts/rules", methods=["POST"])
def api_create_alert_rule():
    """创建预警规则"""
    from alerts.models import AlertRule
    
    data = request.json
    rule = AlertRule(
        id=None,
        name=data['name'],
        symbol=data['symbol'],
        alert_type=data['alert_type'],
        condition=data['condition'],
        threshold=float(data['threshold']),
        severity=data.get('severity', 'medium'),
        params=data.get('params', {}),
        cooldown_minutes=int(data.get('cooldown_minutes', 60)),
        notify_discord=data.get('notify_discord', True),
        notify_telegram=data.get('notify_telegram', False),
        description=data.get('description', ''),
    )
    
    manager = get_alert_manager()
    created = manager.create_rule(rule)
    return jsonify(created.to_dict()), 201


@app.route("/api/alerts/rules/<rule_id>", methods=["GET"])
def api_get_alert_rule(rule_id):
    """获取单个规则"""
    manager = get_alert_manager()
    rule = manager.get_rule(rule_id)
    if not rule:
        return jsonify({"error": "Rule not found"}), 404
    return jsonify(rule.to_dict())


@app.route("/api/alerts/rules/<rule_id>", methods=["PUT"])
def api_update_alert_rule(rule_id):
    """更新规则"""
    data = request.json
    manager = get_alert_manager()
    updated = manager.update_rule(rule_id, data)
    if not updated:
        return jsonify({"error": "Rule not found"}), 404
    return jsonify(updated.to_dict())


@app.route("/api/alerts/rules/<rule_id>", methods=["DELETE"])
def api_delete_alert_rule(rule_id):
    """删除规则"""
    manager = get_alert_manager()
    success = manager.delete_rule(rule_id)
    if not success:
        return jsonify({"error": "Rule not found"}), 404
    return jsonify({"success": True})


@app.route("/api/alerts/rules/<rule_id>/toggle", methods=["POST"])
def api_toggle_alert_rule(rule_id):
    """启用/禁用规则"""
    data = request.json
    enabled = data.get('enabled', True)
    
    manager = get_alert_manager()
    if enabled:
        rule = manager.enable_rule(rule_id)
    else:
        rule = manager.disable_rule(rule_id)
    
    if not rule:
        return jsonify({"error": "Rule not found"}), 404
    return jsonify(rule.to_dict())


@app.route("/api/alerts/history", methods=["GET"])
def api_alerts_history():
    """获取预警历史"""
    manager = get_alert_manager()
    symbol = request.args.get('symbol')
    limit = request.args.get('limit', 100, type=int)
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    
    history = manager.get_alert_history(symbol=symbol, limit=limit, unread_only=unread_only)
    return jsonify([h.to_dict() for h in history])


@app.route("/api/alerts/history/<alert_id>/ack", methods=["POST"])
def api_acknowledge_alert(alert_id):
    """确认预警（标记已读）"""
    manager = get_alert_manager()
    success = manager.acknowledge_alert(alert_id)
    if not success:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"success": True})


@app.route("/api/alerts/check", methods=["POST"])
def api_check_alerts():
    """手动触发预警检查"""
    engine = get_alert_engine()
    alerts = engine.check_all_rules()
    return jsonify({
        "checked": True,
        "triggered_count": len(alerts),
        "alerts": [a.to_dict() for a in alerts]
    })


@app.route("/api/alerts/templates", methods=["GET"])
def api_alert_templates():
    """获取预警模板"""
    from alerts.models import ALERT_TEMPLATES
    
    templates = []
    for key, template in ALERT_TEMPLATES.items():
        templates.append({
            "key": key,
            **{k: v.value if hasattr(v, 'value') else v for k, v in template.items()}
        })
    return jsonify(templates)


@app.route("/api/alerts/stats", methods=["GET"])
def api_alerts_stats():
    """获取预警统计"""
    manager = get_alert_manager()
    stats = manager.get_statistics()
    return jsonify(stats)


# ---------------------------------------------------------------------------
# Background data refresh thread
# ---------------------------------------------------------------------------
def _background_refresh():
    """Periodically refresh data cache."""
    while True:
        time.sleep(300)  # every 5 minutes
        with _cache_lock:
            _cache.clear()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Start background refresh thread
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()

    print("=" * 50)
    print("  OpenClaw Investment Dashboard")
    print(f"  http://localhost:8080")
    print("=" * 50)

    app.run(host="0.0.0.0", port=8080, debug=True)
