"""CLI Main - 命令行界面
"""
import sys
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.market_data import MarketDataManager
from storage.database import DatabaseManager


console = Console()


class InvestmentCLI:
    """投资分析CLI"""
    
    def __init__(self):
        self.market = MarketDataManager()
        self.db = DatabaseManager()
    
    def show_banner(self):
        """显示欢迎信息"""
        console.print(Panel.fit(
            "[bold cyan]OpenClaw Investment Analyst[/bold cyan]\n"
            "[dim]AI驱动的专业投资分析系统[/dim]",
            box=box.DOUBLE
        ))
    
    def show_sectors(self):
        """显示所有板块"""
        table = Table(title="监控板块", box=box.ROUNDED)
        table.add_column("板块代码", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("描述", style="dim")
        table.add_column("股票数量", justify="right")
        
        for code, info in self.market.sectors.items():
            count = sum(len(stocks) for stocks in info["stocks"].values())
            table.add_row(code, info["name"], info["description"], str(count))
        
        console.print(table)
    
    def show_sector_stocks(self, sector_name: str):
        """显示板块股票"""
        if sector_name not in self.market.sectors:
            console.print(f"[red]Unknown sector: {sector_name}[/red]")
            return
        
        sector = self.market.sectors[sector_name]
        table = Table(title=f"{sector['name']}板块股票", box=box.ROUNDED)
        table.add_column("代码", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("市场", style="yellow")
        table.add_column("类型", style="dim")
        
        for market_type, stocks in sector["stocks"].items():
            for stock in stocks:
                table.add_row(
                    stock["symbol"], 
                    stock["name"], 
                    stock["market"],
                    market_type
                )
        
        console.print(table)
    
    def update_sector(self, sector_name: Optional[str] = None):
        """更新板块数据"""
        if sector_name:
            if sector_name not in self.market.sectors:
                console.print(f"[red]Unknown sector: {sector_name}[/red]")
                return
            sectors = [sector_name]
        else:
            sectors = list(self.market.sectors.keys())
        
        for s in sectors:
            console.print(f"[cyan]Updating {s}...[/cyan]")
            stocks = self.market.get_sector_stocks(s)
            for stock in stocks:
                success = self.market.update_stock_data(
                    stock["symbol"], s, stock.get("market_type", "US")
                )
                status = "[green]✓[/green]" if success else "[red]✗[/red]"
                console.print(f"  {status} {stock['symbol']}")
        
        console.print("[green]Update complete![/green]")
    
    def show_stock_chart(self, symbol: str):
        """显示股票数据（文本形式）"""
        df = self.market.get_cached_data(symbol, days=30)
        
        if df.empty:
            console.print(f"[yellow]No cached data for {symbol}, fetching...[/yellow]")
            # Try to fetch
            df = self.market.get_us_stock_data(symbol, period="1mo")
        
        if df.empty:
            console.print(f"[red]Could not fetch data for {symbol}[/red]")
            return
        
        table = Table(title=f"{symbol} - Last 10 Days", box=box.ROUNDED)
        table.add_column("Date", style="cyan")
        table.add_column("Open", justify="right")
        table.add_column("High", justify="right")
        table.add_column("Low", justify="right")
        table.add_column("Close", justify="right")
        table.add_column("Volume", justify="right")
        
        for _, row in df.head(10).iterrows():
            table.add_row(
                str(row['date'])[:10],
                f"{row['open']:.2f}",
                f"{row['high']:.2f}",
                f"{row['low']:.2f}",
                f"{row['close']:.2f}",
                f"{row['volume']:,.0f}"
            )
        
        console.print(table)
        
        # Show simple stats
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else latest
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close']) * 100 if prev['close'] > 0 else 0
        
        color = "green" if change >= 0 else "red"
        console.print(f"\n[bold]Latest Close:[/bold] ${latest['close']:.2f} "
                      f"[{color}]{change:+.2f} ({change_pct:+.2f}%)[/{color}]")
    
    def run(self):
        """运行交互式CLI"""
        self.show_banner()
        
        while True:
            try:
                console.print("\n[dim]Commands: sectors, stocks <sector>, update [sector], chart <symbol>, quit[/dim]")
                cmd = console.input("[bold cyan]> [/bold cyan]").strip().split()
                
                if not cmd:
                    continue
                
                action = cmd[0].lower()
                
                if action == "quit" or action == "q":
                    console.print("[dim]Goodbye![/dim]")
                    break
                
                elif action == "sectors":
                    self.show_sectors()
                
                elif action == "stocks" and len(cmd) > 1:
                    self.show_sector_stocks(cmd[1])
                
                elif action == "update":
                    self.update_sector(cmd[1] if len(cmd) > 1 else None)
                
                elif action == "chart" and len(cmd) > 1:
                    self.show_stock_chart(cmd[1])
                
                else:
                    console.print("[red]Unknown command[/red]")
                    
            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye![/dim]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


def main():
    cli = InvestmentCLI()
    cli.run()


if __name__ == "__main__":
    main()
