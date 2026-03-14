"""
Alert Engine - 预警检测引擎
"""
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from alerts.models import (
    AlertCondition, AlertHistory, AlertRule, AlertSeverity, 
    AlertStatus, AlertType
)
from analyzer.technical import TechnicalAnalyzer
from data.market_data import MarketDataManager

logger = logging.getLogger(__name__)


class AlertEngine:
    """预警检测引擎"""
    
    def __init__(self, db_path: str = "storage/alerts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        self.dm = MarketDataManager()
        
        # 缓存规则避免重复查询
        self._rules_cache: Dict[str, AlertRule] = {}
        self._cache_timestamp: Optional[datetime] = None
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 预警规则表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    severity TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'enabled',
                    params TEXT,
                    cooldown_minutes INTEGER DEFAULT 60,
                    last_triggered TEXT,
                    notify_discord INTEGER DEFAULT 1,
                    notify_telegram INTEGER DEFAULT 0,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 预警历史表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    trigger_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    condition TEXT NOT NULL,
                    price REAL NOT NULL,
                    price_change_pct REAL,
                    volume INTEGER,
                    message TEXT NOT NULL,
                    metadata TEXT,
                    notified_discord INTEGER DEFAULT 0,
                    notified_telegram INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TEXT,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
                )
            """)
            
            conn.commit()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _load_rules(self, force_refresh: bool = False) -> List[AlertRule]:
        """加载所有启用的规则"""
        # 使用缓存避免频繁查询
        if not force_refresh and self._rules_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < timedelta(minutes=1):
                return list(self._rules_cache.values())
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM alert_rules WHERE status = ?",
                (AlertStatus.ENABLED.value,)
            )
            rows = cursor.fetchall()
        
        rules = []
        for row in rows:
            rule = self._row_to_rule(row)
            rules.append(rule)
            self._rules_cache[rule.id] = rule
        
        self._cache_timestamp = datetime.now()
        return rules
    
    def _row_to_rule(self, row) -> AlertRule:
        """数据库行转Rule对象"""
        import json
        return AlertRule(
            id=row[0],
            name=row[1],
            symbol=row[2],
            alert_type=AlertType(row[3]),
            condition=AlertCondition(row[4]),
            threshold=row[5],
            severity=AlertSeverity(row[6]),
            status=AlertStatus(row[7]),
            params=json.loads(row[8]) if row[8] else {},
            cooldown_minutes=row[9],
            last_triggered=row[10],
            notify_discord=bool(row[11]),
            notify_telegram=bool(row[12]),
            description=row[13] or "",
            created_at=row[14],
            updated_at=row[15],
        )
    
    def check_all_rules(self) -> List[AlertHistory]:
        """检查所有规则，返回触发的预警"""
        rules = self._load_rules()
        triggered = []
        
        for rule in rules:
            try:
                alert = self._check_rule(rule)
                if alert:
                    triggered.append(alert)
            except Exception as e:
                logger.error(f"Error checking rule {rule.id}: {e}")
        
        return triggered
    
    def _check_rule(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查单个规则是否触发"""
        # 检查冷却期
        if rule.last_triggered:
            last = datetime.fromisoformat(rule.last_triggered)
            cooldown = timedelta(minutes=rule.cooldown_minutes)
            if datetime.now() - last < cooldown:
                return None
        
        # 根据预警类型分发检查
        check_methods = {
            AlertType.PRICE_THRESHOLD: self._check_price,
            AlertType.TECHNICAL_INDICATOR: self._check_technical,
            AlertType.VOLUME_SPIKE: self._check_volume,
            AlertType.MOVING_AVERAGE_CROSS: self._check_ma_cross,
            AlertType.NEWS_SENTIMENT: self._check_sentiment,
            AlertType.PORTFOLIO_PNL: self._check_portfolio,
        }
        
        check_method = check_methods.get(rule.alert_type)
        if not check_method:
            logger.warning(f"Unknown alert type: {rule.alert_type}")
            return None
        
        return check_method(rule)
    
    def _check_price(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查价格预警"""
        # 获取最新价格
        df = self.dm.get_cached_data(rule.symbol, days=5)
        if df.empty or len(df) < 2:
            return None
        
        latest = df.iloc[0]
        prev = df.iloc[1]
        
        current_price = float(latest.get('close', 0))
        prev_price = float(prev.get('close', 0))
        
        triggered = False
        trigger_value = current_price
        
        if rule.condition == AlertCondition.GREATER_THAN:
            triggered = current_price > rule.threshold
        elif rule.condition == AlertCondition.LESS_THAN:
            triggered = current_price < rule.threshold
        elif rule.condition == AlertCondition.CROSSES_ABOVE:
            triggered = prev_price <= rule.threshold < current_price
        elif rule.condition == AlertCondition.CROSSES_BELOW:
            triggered = prev_price >= rule.threshold > current_price
        
        if not triggered:
            return None
        
        return self._create_alert(rule, trigger_value, current_price, df)
    
    def _check_technical(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查技术指标预警"""
        df = self.dm.get_cached_data(rule.symbol, days=30)
        if df.empty or len(df) < 20:
            return None
        
        analyzer = TechnicalAnalyzer(df)
        ind = analyzer.analyze()
        
        indicator = rule.params.get('indicator', 'rsi')
        triggered = False
        trigger_value = 0.0
        
        if indicator == 'rsi':
            trigger_value = ind.rsi_14 if ind.rsi_14 else 0
        elif indicator == 'macd':
            trigger_value = ind.macd if ind.macd else 0
        elif indicator == 'sma20':
            trigger_value = ind.sma_20 if ind.sma_20 else 0
        else:
            return None
        
        # 应用条件
        if rule.condition == AlertCondition.GREATER_THAN:
            triggered = trigger_value > rule.threshold
        elif rule.condition == AlertCondition.LESS_THAN:
            triggered = trigger_value < rule.threshold
        elif rule.condition == AlertCondition.CROSSES_ABOVE:
            # 简化处理，实际需要更多历史数据
            triggered = trigger_value > rule.threshold
        elif rule.condition == AlertCondition.CROSSES_BELOW:
            triggered = trigger_value < rule.threshold
        
        if not triggered:
            return None
        
        latest = df.iloc[0]
        current_price = float(latest.get('close', 0))
        
        return self._create_alert(
            rule, trigger_value, current_price, df,
            extra_metadata={'indicator': indicator, 'indicator_value': trigger_value}
        )
    
    def _check_volume(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查成交量预警"""
        df = self.dm.get_cached_data(rule.symbol, days=30)
        if df.empty or len(df) < 20:
            return None
        
        latest = df.iloc[0]
        current_volume = float(latest.get('volume', 0))
        
        # 计算20日均量
        avg_volume = df['volume'].head(20).mean()
        if avg_volume == 0:
            return None
        
        volume_ratio = current_volume / avg_volume
        
        triggered = False
        if rule.condition == AlertCondition.GREATER_THAN:
            triggered = volume_ratio > rule.threshold
        elif rule.condition == AlertCondition.LESS_THAN:
            triggered = volume_ratio < rule.threshold
        
        if not triggered:
            return None
        
        current_price = float(latest.get('close', 0))
        
        return self._create_alert(
            rule, volume_ratio, current_price, df,
            extra_metadata={'volume_ratio': volume_ratio, 'avg_volume': avg_volume}
        )
    
    def _check_ma_cross(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查均线突破"""
        df = self.dm.get_cached_data(rule.symbol, days=60)
        if df.empty or len(df) < 50:
            return None
        
        analyzer = TechnicalAnalyzer(df)
        ind = analyzer.analyze()
        
        sma20 = ind.sma_20
        sma50 = ind.sma_50
        
        if not sma20 or not sma50:
            return None
        
        # 金叉: SMA20上穿SMA50
        # 死叉: SMA20下穿SMA50
        triggered = False
        
        if rule.condition == AlertCondition.CROSSES_ABOVE:
            triggered = sma20 > sma50  # 简化判断
        elif rule.condition == AlertCondition.CROSSES_BELOW:
            triggered = sma20 < sma50
        
        if not triggered:
            return None
        
        latest = df.iloc[0]
        current_price = float(latest.get('close', 0))
        
        return self._create_alert(
            rule, sma20, current_price, df,
            extra_metadata={'sma20': sma20, 'sma50': sma50}
        )
    
    def _check_sentiment(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查新闻情绪（需要NewsAPI配置）"""
        # TODO: 集成sentiment analyzer
        logger.debug("Sentiment check not implemented yet")
        return None
    
    def _check_portfolio(self, rule: AlertRule) -> Optional[AlertHistory]:
        """检查组合盈亏"""
        # TODO: 集成portfolio manager
        logger.debug("Portfolio check not implemented yet")
        return None
    
    def _create_alert(
        self, 
        rule: AlertRule, 
        trigger_value: float, 
        current_price: float,
        df: pd.DataFrame,
        extra_metadata: Optional[Dict] = None
    ) -> AlertHistory:
        """创建预警记录"""
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else latest
        
        price_change = current_price - float(prev.get('close', current_price))
        price_change_pct = (price_change / float(prev.get('close', current_price))) * 100 if prev.get('close') else 0
        
        # 生成消息
        condition_desc = {
            AlertCondition.GREATER_THAN: f"超过 {rule.threshold}",
            AlertCondition.LESS_THAN: f"低于 {rule.threshold}",
            AlertCondition.CROSSES_ABOVE: f"向上突破 {rule.threshold}",
            AlertCondition.CROSSES_BELOW: f"向下跌破 {rule.threshold}",
        }
        
        message = f"{rule.name}: {rule.symbol} {condition_desc.get(rule.condition, '')}"
        if extra_metadata and 'indicator' in extra_metadata:
            message += f" ({extra_metadata['indicator'].upper()}: {trigger_value:.2f})"
        
        alert = AlertHistory(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            rule_name=rule.name,
            symbol=rule.symbol,
            alert_type=rule.alert_type,
            severity=rule.severity,
            trigger_value=trigger_value,
            threshold=rule.threshold,
            condition=rule.condition,
            price=current_price,
            price_change_pct=price_change_pct,
            volume=int(latest.get('volume', 0)),
            message=message,
            metadata=extra_metadata or {},
        )
        
        # 保存到数据库
        self._save_alert(alert)
        
        # 更新规则最后触发时间
        self._update_rule_triggered(rule.id)
        
        logger.info(f"Alert triggered: {message}")
        
        return alert
    
    def _save_alert(self, alert: AlertHistory):
        """保存预警到历史"""
        import json
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO alert_history 
                (id, rule_id, rule_name, symbol, alert_type, severity,
                 trigger_value, threshold, condition, price, price_change_pct,
                 volume, message, metadata, notified_discord, notified_telegram,
                 created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id, alert.rule_id, alert.rule_name, alert.symbol,
                alert.alert_type.value, alert.severity.value,
                alert.trigger_value, alert.threshold, alert.condition.value,
                alert.price, alert.price_change_pct, alert.volume,
                alert.message, json.dumps(alert.metadata),
                int(alert.notified_discord), int(alert.notified_telegram),
                alert.created_at,
            ))
            conn.commit()
    
    def _update_rule_triggered(self, rule_id: str):
        """更新规则最后触发时间"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE alert_rules SET last_triggered = ? WHERE id = ?",
                (now, rule_id)
            )
            conn.commit()
        
        # 更新缓存
        if rule_id in self._rules_cache:
            self._rules_cache[rule_id].last_triggered = now


if __name__ == "__main__":
    # 测试
    engine = AlertEngine()
    print("AlertEngine initialized")
    
    # 检查规则
    alerts = engine.check_all_rules()
    print(f"Triggered alerts: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert.message}")
