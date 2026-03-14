"""
OpenClaw Integration - OpenClaw命令集成模块
实现投资系统的命令接口和定时任务
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# 延迟导入避免循环依赖
_DATA_MANAGER = None
_DB_MANAGER = None


def _get_data_manager():
    global _DATA_MANAGER
    if _DATA_MANAGER is None:
        from data.market_data import MarketDataManager
        _DATA_MANAGER = MarketDataManager()
    return _DATA_MANAGER


def _get_db_manager():
    global _DB_MANAGER
    if _DB_MANAGER is None:
        from storage.database import DatabaseManager
        _DB_MANAGER = DatabaseManager()
    return _DB_MANAGER


class OpenClawCommands:
    """OpenClaw命令处理器"""
    
    COMMANDS = {
        "invest sectors": "查看监控板块",
        "invest stocks <sector>": "查看板块股票",
        "invest update [sector]": "更新股票数据",
        "invest chart <symbol>": "查看股票图表",
        "invest report [daily|weekly]": "生成分析报告",
        "invest portfolio": "查看投资组合",
        "invest simulate": "运行投资模拟",
        "invest evolve status": "查看进化状态",
        "invest evolve learn": "执行知识学习",
        "invest evolve upgrade": "执行系统升级",
        "invest status": "查看系统状态",
    }
    
    @classmethod
    def help(cls) -> str:
        """帮助信息"""
        return "\n".join([f"  `{cmd}` - {desc}" for cmd, desc in cls.COMMANDS.items()])
    
    @classmethod
    def handle(cls, command: str, args: List[str] = None) -> str:
        """处理命令"""
        args = args or []
        parts = command.lower().strip().split()
        
        if len(parts) < 2 or parts[0] != "invest":
            return f"未知命令。可用命令:\n{cls.help()}"
        
        action = parts[1] if len(parts) > 1 else None
        sub_action = parts[2] if len(parts) > 2 else None
        
        # 路由命令
        if action == "sectors":
            return cls._cmd_sectors()
        
        elif action == "stocks" and args:
            return cls._cmd_stocks(args[0])
        
        elif action == "update":
            return cls._cmd_update(args[0] if args else None)
        
        elif action == "chart" and args:
            return cls._cmd_chart(args[0])
        
        elif action == "report":
            return cls._cmd_report(args[0] if args else "daily")
        
        elif action == "portfolio":
            return cls._cmd_portfolio()
        
        elif action == "simulate":
            return cls._cmd_simulate()
        
        elif action == "evolve":
            if sub_action == "status":
                return cls._cmd_evolve_status()
            elif sub_action == "learn":
                return cls._cmd_evolve_learn()
            elif sub_action == "upgrade":
                return cls._cmd_evolve_upgrade()
            else:
                return "进化命令: status, learn, upgrade"
        
        elif action == "status":
            return cls._cmd_status()
        
        else:
            return f"未知命令 '{action}'。\n可用命令:\n{cls.help()}"
    
    @classmethod
    def _cmd_sectors(cls) -> str:
        """查看板块命令"""
        dm = _get_data_manager()
        
        lines = ["📊 **监控板块**\n"]
        for code, info in dm.sectors.items():
            count = sum(len(stocks) for stocks in info["stocks"].values())
            lines.append(f"• **{info['name']}** (`{code}`) - {count}只股票")
            lines.append(f"  {info['description']}\n")
        
        return "\n".join(lines)
    
    @classmethod
    def _cmd_stocks(cls, sector: str) -> str:
        """查看板块股票"""
        dm = _get_data_manager()
        
        if sector not in dm.sectors:
            return f"❌ 未知板块: {sector}\n可用: {', '.join(dm.sectors.keys())}"
        
        info = dm.sectors[sector]
        stocks = dm.get_sector_stocks(sector)
        
        lines = [f"📈 **{info['name']}板块股票**\n"]
        
        # 按市场分组
        by_market = {}
        for s in stocks:
            mt = s.get("market_type", "US")
            by_market.setdefault(mt, []).append(s)
        
        for market, market_stocks in by_market.items():
            lines.append(f"\n**{market}市场:**")
            for s in market_stocks:
                lines.append(f"  • {s['symbol']} - {s['name']}")
        
        return "\n".join(lines)
    
    @classmethod
    def _cmd_update(cls, sector: Optional[str]) -> str:
        """更新数据"""
        dm = _get_data_manager()
        
        if sector:
            if sector not in dm.sectors:
                return f"❌ 未知板块: {sector}"
            
            sectors = [sector]
        else:
            sectors = list(dm.sectors.keys())
        
        results = []
        for s in sectors:
            stocks = dm.get_sector_stocks(s)
            success_count = 0
            for stock in stocks:
                success = dm.update_stock_data(
                    stock["symbol"], s, stock.get("market_type", "US")
                )
                if success:
                    success_count += 1
            results.append(f"{dm.sectors[s]['name']}: {success_count}/{len(stocks)} 成功")
        
        return "🔄 **数据更新完成**\n\n" + "\n".join(f"• {r}" for r in results)
    
    @classmethod
    def _cmd_chart(cls, symbol: str) -> str:
        """查看股票图表"""
        dm = _get_data_manager()
        
        df = dm.get_cached_data(symbol, days=10)
        if df.empty:
            return f"⏳ 正在获取 {symbol} 数据...\n请稍后再试。"
        
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else latest
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close']) * 100 if prev['close'] > 0 else 0
        
        emoji = "🟢" if change >= 0 else "🔴"
        
        lines = [
            f"📈 **{symbol}** 最新数据\n",
            f"收盘价: ${latest['close']:.2f}",
            f"涨跌: {emoji} {change:+.2f} ({change_pct:+.2f}%)",
            f"成交量: {latest['volume']:,.0f}",
            f"\n最近5日:",
        ]
        
        for _, row in df.head(5).iterrows():
            lines.append(f"  {row['date'][:10]}: ${row['close']:.2f}")
        
        return "\n".join(lines)
    
    @classmethod
    def _cmd_report(cls, report_type: str) -> str:
        """生成报告"""
        if report_type not in ["daily", "weekly"]:
            return "❌ 报告类型: daily 或 weekly"
        
        return f"⏳ {report_type}报告生成功能开发中...\n预计Phase 2完成。"
    
    @classmethod
    def _cmd_portfolio(cls) -> str:
        """查看组合"""
        return "💼 投资组合管理功能开发中...\n预计Phase 4完成。"
    
    @classmethod
    def _cmd_simulate(cls) -> str:
        """运行模拟"""
        return "🎮 投资模拟功能开发中...\n预计Phase 4完成。"
    
    @classmethod
    def _cmd_evolve_status(cls) -> str:
        """查看进化状态"""
        from evolution.auto_upgrade import AutoUpgrader
        
        upgrader = AutoUpgrader()
        status = upgrader.get_status()
        
        lines = [
            "🧬 **系统进化状态**\n",
            f"✅ 已完成升级: {status['completed_upgrades']}",
            f"❌ 失败升级: {status['failed_upgrades']}",
            f"⏳ 待处理任务: {status['pending_tasks']}",
            "\n**系统能力:**",
        ]
        
        for cap, available in status['capabilities'].items():
            icon = "✅" if available else "❌"
            lines.append(f"  {icon} {cap}")
        
        return "\n".join(lines)
    
    @classmethod
    def _cmd_evolve_learn(cls) -> str:
        """执行知识学习"""
        from evolution.auto_upgrade import AutoUpgrader, UpgradeType, UpgradePriority
        
        upgrader = AutoUpgrader()
        task_id = upgrader.schedule_upgrade(
            UpgradeType.KNOWLEDGE,
            priority=UpgradePriority.HIGH,
            description="Auto-learn from arXiv and GitHub",
            auto_execute=True
        )
        
        return f"🧠 **知识学习已启动**\n任务ID: {task_id}\n正在扫描arXiv论文和GitHub项目..."
    
    @classmethod
    def _cmd_evolve_upgrade(cls) -> str:
        """执行系统升级"""
        from evolution.auto_upgrade import AutoUpgrader, UpgradeType, UpgradePriority
        
        upgrader = AutoUpgrader()
        
        # 发现可升级项
        tasks = upgrader.auto_discover_upgrades()
        
        if not tasks:
            return "✅ 系统已是最新状态，未发现需要升级的项目。"
        
        lines = [f"🔧 **发现 {len(tasks)} 个升级机会**\n"]
        
        for i, task in enumerate(tasks, 1):
            lines.append(f"{i}. [{task.type.value}] {task.description}")
            # 自动执行高优先级
            if task.priority.value <= 2:
                result = upgrader.execute_upgrade(task.id)
                status = "✅" if result.get("success") else "❌"
                lines.append(f"   {status} 已自动执行")
        
        return "\n".join(lines)
    
    @classmethod
    def _cmd_status(cls) -> str:
        """查看系统状态"""
        dm = _get_data_manager()
        db = _get_db_manager()
        
        lines = [
            "📊 **系统状态**\n",
            f"监控板块: {len(dm.sectors)} 个",
            f"股票总数: {sum(sum(len(s) for s in sec['stocks'].values()) for sec in dm.sectors.values())} 只",
            f"工作目录: {Path('.').resolve()}",
            f"\n可用命令: `invest help`",
        ]
        
        return "\n".join(lines)


# ============== 定时任务调度 ==============

class Scheduler:
    """定时任务调度器"""
    
    SCHEDULES = {
        "market_open": {
            "time": "09:30",
            "timezone": "US/Eastern",
            "action": "update_all",
        },
        "market_close": {
            "time": "16:00",
            "timezone": "US/Eastern",
            "action": "daily_report",
        },
        "evening_learning": {
            "time": "21:00",
            "timezone": "Asia/Shanghai",
            "action": "auto_learn",
        },
        "weekly_report": {
            "day": "fri",
            "time": "18:00",
            "timezone": "Asia/Shanghai",
            "action": "weekly_report",
        },
    }
    
    @classmethod
    def get_schedule(cls) -> str:
        """获取定时任务安排"""
        lines = ["⏰ **定时任务安排**\n"]
        
        for name, config in cls.SCHEDULES.items():
            time_str = config.get("time", "")
            day_str = f"每周{config['day'].upper()} " if "day" in config else "每日 "
            lines.append(f"• **{name}**: {day_str}{time_str} ({config['timezone']})")
            lines.append(f"  动作: {config['action']}\n")
        
        return "\n".join(lines)


# ============== 消息推送 ==============

class Notifier:
    """消息推送器"""
    
    @staticmethod
    def push_daily_report(report: str, channel: str = "feishu"):
        """推送日报"""
        # TODO: 集成OpenClaw message工具
        print(f"[Notifier] Daily report would be sent to {channel}")
        print(report[:500] + "...")
    
    @staticmethod
    def push_alert(message: str, priority: str = "normal"):
        """推送预警"""
        print(f"[Notifier] Alert ({priority}): {message}")


# ============== 入口点 ==============

def main():
    """测试入口"""
    import sys
    
    if len(sys.argv) < 2:
        print(OpenClawCommands.help())
        return
    
    command = " ".join(sys.argv[1:])
    result = OpenClawCommands.handle(command)
    print(result)


if __name__ == "__main__":
    main()
