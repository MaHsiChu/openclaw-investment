"""
Alert Models - 预警数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class AlertType(Enum):
    """预警类型"""
    PRICE_THRESHOLD = "price_threshold"           # 价格突破/跌破
    TECHNICAL_INDICATOR = "technical_indicator"   # 技术指标触发
    VOLUME_SPIKE = "volume_spike"                 # 成交量异常
    MOVING_AVERAGE_CROSS = "ma_cross"            # 均线突破
    NEWS_SENTIMENT = "news_sentiment"            # 新闻情绪突变
    PORTFOLIO_PNL = "portfolio_pnl"              # 组合盈亏预警


class AlertCondition(Enum):
    """预警条件"""
    GREATER_THAN = "gt"           # 大于
    LESS_THAN = "lt"              # 小于
    EQUALS = "eq"                 # 等于
    CROSSES_ABOVE = "cross_up"    # 突破向上
    CROSSES_BELOW = "cross_down"  # 跌破向下
    CHANGES_BY = "change"         # 变化幅度


class AlertSeverity(Enum):
    """预警严重级别"""
    LOW = "low"           # 低 - 信息提示
    MEDIUM = "medium"     # 中 - 需要注意
    HIGH = "high"         # 高 - 及时关注
    CRITICAL = "critical" # 紧急 - 立即处理


class AlertStatus(Enum):
    """预警规则状态"""
    ENABLED = "enabled"   # 启用
    DISABLED = "disabled" # 禁用
    TRIGGERED = "triggered" # 已触发（冷却中）


@dataclass
class AlertRule:
    """预警规则定义"""
    id: str
    name: str
    symbol: str                    # 股票代码
    alert_type: AlertType
    condition: AlertCondition
    threshold: float              # 阈值
    severity: AlertSeverity = AlertSeverity.MEDIUM
    status: AlertStatus = AlertStatus.ENABLED
    
    # 可选参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 冷却期配置（避免重复预警）
    cooldown_minutes: int = 60
    last_triggered: Optional[str] = None
    
    # 通知配置
    notify_discord: bool = True
    notify_telegram: bool = False
    
    # 元数据
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "alert_type": self.alert_type.value,
            "condition": self.condition.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "status": self.status.value,
            "params": self.params,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered": self.last_triggered,
            "notify_discord": self.notify_discord,
            "notify_telegram": self.notify_telegram,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AlertRule":
        return cls(
            id=data["id"],
            name=data["name"],
            symbol=data["symbol"],
            alert_type=AlertType(data["alert_type"]),
            condition=AlertCondition(data["condition"]),
            threshold=data["threshold"],
            severity=AlertSeverity(data.get("severity", "medium")),
            status=AlertStatus(data.get("status", "enabled")),
            params=data.get("params", {}),
            cooldown_minutes=data.get("cooldown_minutes", 60),
            last_triggered=data.get("last_triggered"),
            notify_discord=data.get("notify_discord", True),
            notify_telegram=data.get("notify_telegram", False),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


@dataclass
class AlertHistory:
    """预警历史记录"""
    id: str
    rule_id: str
    rule_name: str
    symbol: str
    alert_type: AlertType
    severity: AlertSeverity
    
    # 触发时的数据
    trigger_value: float
    threshold: float
    condition: AlertCondition
    
    # 市场数据快照
    price: float
    price_change_pct: float
    volume: int
    
    # 额外信息
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 通知状态
    notified_discord: bool = False
    notified_telegram: bool = False
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged_at: Optional[str] = None  # 用户确认时间
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "symbol": self.symbol,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "trigger_value": self.trigger_value,
            "threshold": self.threshold,
            "condition": self.condition.value,
            "price": self.price,
            "price_change_pct": self.price_change_pct,
            "volume": self.volume,
            "message": self.message,
            "metadata": self.metadata,
            "notified_discord": self.notified_discord,
            "notified_telegram": self.notified_telegram,
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
        }


# 预设规则模板
ALERT_TEMPLATES = {
    "price_breakout": {
        "name": "价格突破",
        "alert_type": AlertType.PRICE_THRESHOLD,
        "condition": AlertCondition.CROSSES_ABOVE,
        "description": "当股价突破指定阻力位时触发",
    },
    "price_support": {
        "name": "支撑位跌破",
        "alert_type": AlertType.PRICE_THRESHOLD,
        "condition": AlertCondition.CROSSES_BELOW,
        "description": "当股价跌破指定支撑位时触发",
    },
    "rsi_overbought": {
        "name": "RSI超买",
        "alert_type": AlertType.TECHNICAL_INDICATOR,
        "condition": AlertCondition.GREATER_THAN,
        "threshold": 70,
        "params": {"indicator": "rsi", "period": 14},
        "description": "RSI超过70，可能超买",
    },
    "rsi_oversold": {
        "name": "RSI超卖",
        "alert_type": AlertType.TECHNICAL_INDICATOR,
        "condition": AlertCondition.LESS_THAN,
        "threshold": 30,
        "params": {"indicator": "rsi", "period": 14},
        "description": "RSI低于30，可能超卖",
    },
    "macd_golden_cross": {
        "name": "MACD金叉",
        "alert_type": AlertType.TECHNICAL_INDICATOR,
        "condition": AlertCondition.CROSSES_ABOVE,
        "threshold": 0,
        "params": {"indicator": "macd", "signal": "cross_above"},
        "description": "MACD线上穿信号线",
    },
    "volume_spike": {
        "name": "成交量异常",
        "alert_type": AlertType.VOLUME_SPIKE,
        "condition": AlertCondition.GREATER_THAN,
        "threshold": 2.0,  # 2倍平均成交量
        "params": {"comparison": "sma20"},
        "description": "成交量超过20日均量2倍",
    },
    "portfolio_loss": {
        "name": "组合亏损预警",
        "alert_type": AlertType.PORTFOLIO_PNL,
        "condition": AlertCondition.LESS_THAN,
        "threshold": -5.0,  # 亏损5%
        "params": {"metric": "total_pnl_pct"},
        "description": "组合亏损超过5%",
    },
}
