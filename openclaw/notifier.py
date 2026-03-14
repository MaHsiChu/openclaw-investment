"""
Notifier - 消息推送模块
支持 Discord 和 Telegram 推送
"""
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class ChannelType(Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"


@dataclass
class NotificationConfig:
    """推送配置"""
    channel: ChannelType
    target: str  # Discord channel ID 或 Telegram chat ID
    account_id: Optional[str] = None
    
    # Discord 特有
    webhook_url: Optional[str] = None
    
    # Telegram 特有
    bot_token: Optional[str] = None


class MessageFormatter:
    """消息格式化器"""
    
    @staticmethod
    def format_daily_report(report_data: Dict) -> str:
        """格式化日报为Discord/Telegram友好格式"""
        lines = [
            "📊 **每日投资报告**",
            f"📅 {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}",
            "",
        ]
        
        # 市场概览
        market = report_data.get('market_overview', {})
        lines.extend([
            "**📈 市场概览**",
        ])
        
        for index, data in market.items():
            emoji = "🟢" if data.get('change', 0) >= 0 else "🔴"
            lines.append(f"{emoji} {index}: {data.get('change_pct', 0):+.2f}%")
        
        lines.append("")
        
        # 板块表现
        sectors = report_data.get('sector_performance', [])
        if sectors:
            lines.append("**🏆 板块表现 TOP3**")
            for i, sector in enumerate(sectors[:3], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                lines.append(f"{emoji} {sector['name']}: {sector['change_pct']:+.2f}%")
            lines.append("")
        
        # 个股推荐
        picks = report_data.get('stock_picks', [])
        if picks:
            lines.append("**⭐ 今日推荐**")
            for pick in picks[:3]:
                signal_emoji = "💚" if pick.get('signal') == 'buy' else "❤️" if pick.get('signal') == 'sell' else "💛"
                lines.append(f"{signal_emoji} {pick['symbol']} - {pick['name']} (置信度: {pick.get('confidence', 0):.0f}%)")
            lines.append("")
        
        # AI洞察
        insights = report_data.get('ai_insights', [])
        if insights:
            lines.append("**🤖 AI洞察**")
            for insight in insights[:2]:
                lines.append(f"• {insight}")
            lines.append("")
        
        lines.append("—")
        lines.append("🤖 由 OpenClaw Investment Analyst 自动生成")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_weekly_report(report_data: Dict) -> str:
        """格式化周报"""
        lines = [
            "📊 **每周投资报告**",
            f"📅 {report_data.get('week_start', '')} - {report_data.get('week_end', '')}",
            "",
            "**📈 本周回顾**",
        ]
        
        # 本周表现
        weekly = report_data.get('weekly_performance', {})
        for sector, data in weekly.items():
            emoji = "🟢" if data.get('change', 0) >= 0 else "🔴"
            lines.append(f"{emoji} {sector}: {data.get('change_pct', 0):+.2f}%")
        
        lines.append("")
        
        # 趋势分析
        trends = report_data.get('trends', [])
        if trends:
            lines.append("**📊 趋势分析**")
            for trend in trends:
                emoji = "📈" if trend.get('direction') == 'up' else "📉"
                lines.append(f"{emoji} {trend['name']}: {trend['description']}")
            lines.append("")
        
        # 下周展望
        outlook = report_data.get('outlook', [])
        if outlook:
            lines.append("**🔮 下周展望**")
            for item in outlook:
                lines.append(f"• {item}")
            lines.append("")
        
        lines.append("—")
        lines.append("🤖 由 OpenClaw Investment Analyst 自动生成")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_alert(alert_type: str, message: str, data: Dict = None) -> str:
        """格式化预警消息"""
        emoji_map = {
            "price_spike": "🚀",
            "price_drop": "📉",
            "volume_spike": "📊",
            "news": "📰",
            "earnings": "💰",
            "technical_signal": "📈",
        }
        
        emoji = emoji_map.get(alert_type, "⚠️")
        
        lines = [
            f"{emoji} **投资预警**",
            "",
            message,
        ]
        
        if data:
            lines.append("")
            if 'symbol' in data:
                lines.append(f"股票: {data['symbol']}")
            if 'price' in data:
                lines.append(f"价格: ${data['price']:.2f}")
            if 'change_pct' in data:
                emoji = "🟢" if data['change_pct'] >= 0 else "🔴"
                lines.append(f"涨跌: {emoji} {data['change_pct']:+.2f}%")
        
        return "\n".join(lines)


class Notifier:
    """消息推送器 - 支持Discord/Telegram"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.formatter = MessageFormatter()
    
    async def send_message(self, message: str) -> bool:
        """发送消息"""
        if self.config.channel == ChannelType.DISCORD:
            return await self._send_discord(message)
        elif self.config.channel == ChannelType.TELEGRAM:
            return await self._send_telegram(message)
        return False
    
    async def _send_discord(self, message: str) -> bool:
        """发送到Discord"""
        try:
            # 尝试使用OpenClaw的message工具
            from openclaw import message_tool
            
            result = message_tool.send(
                channel="discord",
                target=self.config.target,
                message=message
            )
            return result.get("success", False)
        except ImportError:
            # 备用：使用webhook
            if self.config.webhook_url:
                return await self._send_discord_webhook(message)
            print(f"[Discord] Would send to {self.config.target}:\n{message[:200]}...")
            return True
    
    async def _send_discord_webhook(self, message: str) -> bool:
        """通过Webhook发送到Discord"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "content": message,
                "username": "Investment Analyst"
            }
            
            try:
                async with session.post(self.config.webhook_url, json=payload) as resp:
                    return resp.status == 204
            except Exception as e:
                print(f"Discord webhook error: {e}")
                return False
    
    async def _send_telegram(self, message: str) -> bool:
        """发送到Telegram"""
        try:
            # 尝试使用OpenClaw的message工具
            from openclaw import message_tool
            
            result = message_tool.send(
                channel="telegram",
                target=self.config.target,
                message=message
            )
            return result.get("success", False)
        except ImportError:
            # 备用：使用Bot API
            if self.config.bot_token:
                return await self._send_telegram_api(message)
            print(f"[Telegram] Would send to {self.config.target}:\n{message[:200]}...")
            return True
    
    async def _send_telegram_api(self, message: str) -> bool:
        """通过Bot API发送到Telegram"""
        import aiohttp
        
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "chat_id": self.config.target,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            try:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    return data.get("ok", False)
            except Exception as e:
                print(f"Telegram API error: {e}")
                return False
    
    # ============== 快捷方法 ==============
    
    async def send_daily_report(self, report_data: Dict) -> bool:
        """发送日报"""
        message = self.formatter.format_daily_report(report_data)
        return await self.send_message(message)
    
    async def send_weekly_report(self, report_data: Dict) -> bool:
        """发送周报"""
        message = self.formatter.format_weekly_report(report_data)
        return await self.send_message(message)
    
    async def send_alert(self, alert_type: str, message: str, data: Dict = None) -> bool:
        """发送预警"""
        formatted = self.formatter.format_alert(alert_type, message, data)
        return await self.send_message(formatted)
    
    async def send_technical_signal(self, symbol: str, signal: str, confidence: float, indicators: Dict) -> bool:
        """发送技术信号"""
        emoji = "💚 买入" if signal == "buy" else "❤️ 卖出" if signal == "sell" else "💛 持有"
        
        lines = [
            f"📈 **技术信号**",
            "",
            f"**{symbol}**",
            f"信号: {emoji}",
            f"置信度: {confidence:.1f}%",
            "",
            "**技术指标:**",
        ]
        
        if 'rsi' in indicators:
            lines.append(f"RSI: {indicators['rsi']:.1f}")
        if 'macd' in indicators:
            lines.append(f"MACD: {indicators['macd']:.3f}")
        if 'sma_20' in indicators:
            lines.append(f"SMA20: ${indicators['sma_20']:.2f}")
        
        message = "\n".join(lines)
        return await self.send_message(message)


class MultiNotifier:
    """多渠道推送器 - 同时推送到多个渠道"""
    
    def __init__(self, configs: List[NotificationConfig]):
        self.notifiers = [Notifier(config) for config in configs]
    
    async def send_to_all(self, message: str) -> Dict[str, bool]:
        """发送到所有渠道"""
        results = {}
        
        for notifier in self.notifiers:
            channel = notifier.config.channel.value
            success = await notifier.send_message(message)
            results[channel] = success
        
        return results
    
    async def send_daily_report(self, report_data: Dict) -> Dict[str, bool]:
        """发送日报到所有渠道"""
        results = {}
        
        for notifier in self.notifiers:
            channel = notifier.config.channel.value
            success = await notifier.send_daily_report(report_data)
            results[channel] = success
        
        return results


# ============== 配置加载 ==============

def load_notifier_config(config_path: str = "config/notifier.json") -> List[NotificationConfig]:
    """加载推送配置"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        # 创建默认配置
        default_config = [
            {
                "channel": "discord",
                "target": "your-discord-channel-id",
                "account_id": "default"
            }
        ]
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"Created default notifier config at {config_path}")
        print("Please update it with your actual channel settings")
    
    with open(config_file, 'r') as f:
        configs_data = json.load(f)
    
    return [
        NotificationConfig(
            channel=ChannelType(c["channel"]),
            target=c["target"],
            account_id=c.get("account_id"),
            webhook_url=c.get("webhook_url"),
            bot_token=c.get("bot_token")
        )
        for c in configs_data
    ]


# ============== 便捷函数 ==============

async def send_daily_report(report_data: Dict, config_path: str = "config/notifier.json"):
    """便捷函数：发送日报"""
    configs = load_notifier_config(config_path)
    notifier = MultiNotifier(configs)
    return await notifier.send_daily_report(report_data)


async def send_alert(alert_type: str, message: str, data: Dict = None, config_path: str = "config/notifier.json"):
    """便捷函数：发送预警"""
    configs = load_notifier_config(config_path)
    # 使用第一个配置
    if configs:
        notifier = Notifier(configs[0])
        return await notifier.send_alert(alert_type, message, data)
    return False


if __name__ == "__main__":
    # 测试
    async def test():
        # 创建测试配置
        config = NotificationConfig(
            channel=ChannelType.DISCORD,
            target="test-channel",
        )
        
        notifier = Notifier(config)
        
        # 测试日报
        test_report = {
            "date": "2026-03-14",
            "market_overview": {
                "S&P 500": {"change_pct": 1.2},
                "NASDAQ": {"change_pct": 1.5},
                "DOW": {"change_pct": 0.8}
            },
            "sector_performance": [
                {"name": "AI", "change_pct": 3.5},
                {"name": "Gaming", "change_pct": 2.1},
                {"name": "Internet", "change_pct": 1.8}
            ],
            "stock_picks": [
                {"symbol": "NVDA", "name": "NVIDIA", "signal": "buy", "confidence": 85},
                {"symbol": "META", "name": "Meta", "signal": "hold", "confidence": 60}
            ],
            "ai_insights": [
                "AI板块受ChatGPT-5发布预期推动",
                "美联储利率决议后市场情绪改善"
            ]
        }
        
        await notifier.send_daily_report(test_report)
    
    asyncio.run(test())
