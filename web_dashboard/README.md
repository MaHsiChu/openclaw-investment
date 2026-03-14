# OpenClaw Investment Dashboard

Web-based monitoring dashboard for the OpenClaw Investment Analyst system.

## Quick Start

```bash
# Install dependencies (from project root)
pip install flask flask-cors

# Launch dashboard
python web_dashboard/app.py
```

Open http://localhost:5000 in your browser.

## Features

| Page | Description |
|------|-------------|
| **板块监控** | 6 sector cards with real-time stock prices and change percentages |
| **个股分析** | Interactive price chart (Chart.js) with SMA 20/50, volume bars, time range selector |
| **投资组合** | Portfolio summary, holdings table with P&L |
| **报告中心** | Browse and read daily/weekly/sector analysis reports |
| **模拟投资** | Strategy list, backtest metrics, equity curve |
| **系统进化** | Knowledge base stats, phase progress bars, evolution history |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | System status and uptime |
| `GET /api/sectors` | List all tracked sectors |
| `GET /api/stocks/<sector>` | Stocks in a sector with latest prices |
| `GET /api/chart/<symbol>?days=90` | OHLCV chart data + SMA indicators |
| `GET /api/portfolio` | Portfolio holdings and P&L |
| `GET /api/reports` | Report list |
| `GET /api/reports/<id>` | Single report content |
| `GET /api/simulation/status` | Strategy list and simulation state |
| `GET /api/evolution/status` | Knowledge base, phase progress, evolution log |
| `POST /api/refresh/<symbol>` | Trigger data refresh for a symbol |

## Tech Stack

- **Backend**: Flask + flask-cors, SQLite data access
- **Frontend**: Vanilla JS, Chart.js 4, CSS custom properties
- **Theme**: Dark mode optimized for extended monitoring
- **Responsive**: Mobile-friendly layout with collapsible sidebar
- **Auto-refresh**: 30-second polling cycle, 5-minute cache TTL

## Configuration

The dashboard reads data from the existing project databases:
- `storage/market_data.db` - Stock prices
- `storage/investment.db` - Portfolios, holdings, reports
- `storage/evolution.db` - Evolution logs
- `storage/knowledge.db` - Knowledge base
- `config/sectors.json` - Sector/stock configuration
