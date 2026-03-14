"""
Alert Manager - 预警管理器
提供预警规则的CRUD操作
"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from alerts.models import AlertRule, AlertHistory, AlertStatus, ALERT_TEMPLATES

logger = logging.getLogger(__name__)


class AlertManager:
    """预警管理器"""
    
    def __init__(self, db_path: str = "storage/alerts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
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
                    acknowledged_at TEXT
                )
            """)
            conn.commit()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    # ------------------------------------------------------------------
    # 规则CRUD
    # ------------------------------------------------------------------
    
    def create_rule(self, rule: AlertRule) -> AlertRule:
        """创建新规则"""
        if not rule.id:
            rule.id = str(uuid.uuid4())
        
        rule.created_at = datetime.now().isoformat()
        rule.updated_at = rule.created_at
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO alert_rules 
                (id, name, symbol, alert_type, condition, threshold, severity,
                 status, params, cooldown_minutes, notify_discord, notify_telegram,
                 description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.id, rule.name, rule.symbol, rule.alert_type.value,
                rule.condition.value, rule.threshold, rule.severity.value,
                rule.status.value, json.dumps(rule.params), rule.cooldown_minutes,
                int(rule.notify_discord), int(rule.notify_telegram),
                rule.description, rule.created_at, rule.updated_at,
            ))
            conn.commit()
        
        logger.info(f"Created alert rule: {rule.name} ({rule.id})")
        return rule
    
    def create_rule_from_template(
        self, 
        template_key: str, 
        symbol: str,
        custom_name: Optional[str] = None,
        custom_threshold: Optional[float] = None,
        **kwargs
    ) -> Optional[AlertRule]:
        """从模板创建规则"""
        if template_key not in ALERT_TEMPLATES:
            logger.error(f"Template not found: {template_key}")
            return None
        
        template = ALERT_TEMPLATES[template_key]
        
        rule = AlertRule(
            id=str(uuid.uuid4()),
            name=custom_name or f"{template['name']} - {symbol}",
            symbol=symbol,
            alert_type=template['alert_type'],
            condition=template['condition'],
            threshold=custom_threshold if custom_threshold is not None else template.get('threshold', 0),
            description=template.get('description', ''),
            **kwargs
        )
        
        if 'params' in template:
            rule.params = template['params'].copy()
        
        return self.create_rule(rule)
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取单个规则"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM alert_rules WHERE id = ?",
                (rule_id,)
            )
            row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_rule(row)
    
    def get_rules(
        self, 
        symbol: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        alert_type = None
    ) -> List[AlertRule]:
        """获取规则列表"""
        query = "SELECT * FROM alert_rules WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type.value)
        
        query += " ORDER BY created_at DESC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return [self._row_to_rule(row) for row in rows]
    
    def update_rule(self, rule_id: str, updates: Dict) -> Optional[AlertRule]:
        """更新规则"""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        
        # 更新字段
        allowed_fields = [
            'name', 'threshold', 'severity', 'status', 'params',
            'cooldown_minutes', 'notify_discord', 'notify_telegram', 'description'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(rule, field):
                setattr(rule, field, value)
        
        rule.updated_at = datetime.now().isoformat()
        
        # 保存到数据库
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE alert_rules SET
                    name = ?,
                    threshold = ?,
                    severity = ?,
                    status = ?,
                    params = ?,
                    cooldown_minutes = ?,
                    notify_discord = ?,
                    notify_telegram = ?,
                    description = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                rule.name, rule.threshold, rule.severity.value,
                rule.status.value, json.dumps(rule.params),
                rule.cooldown_minutes, int(rule.notify_discord),
                int(rule.notify_telegram), rule.description,
                rule.updated_at, rule.id,
            ))
            conn.commit()
        
        logger.info(f"Updated alert rule: {rule.name} ({rule.id})")
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除规则"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM alert_rules WHERE id = ?",
                (rule_id,)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Deleted alert rule: {rule_id}")
                return True
            return False
    
    def enable_rule(self, rule_id: str) -> Optional[AlertRule]:
        """启用规则"""
        return self.update_rule(rule_id, {'status': AlertStatus.ENABLED})
    
    def disable_rule(self, rule_id: str) -> Optional[AlertRule]:
        """禁用规则"""
        return self.update_rule(rule_id, {'status': AlertStatus.DISABLED})
    
    # ------------------------------------------------------------------
    # 历史记录
    # ------------------------------------------------------------------
    
    def get_alert_history(
        self,
        symbol: Optional[str] = None,
        rule_id: Optional[str] = None,
        limit: int = 100,
        unread_only: bool = False
    ) -> List[AlertHistory]:
        """获取预警历史"""
        query = "SELECT * FROM alert_history WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        
        if unread_only:
            query += " AND acknowledged_at IS NULL"
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        return [self._row_to_history(row) for row in rows]
    
    def get_unread_count(self) -> int:
        """获取未读预警数量"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM alert_history WHERE acknowledged_at IS NULL"
            )
            return cursor.fetchone()[0]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认（标记已读）预警"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE alert_history SET acknowledged_at = ? WHERE id = ?",
                (now, alert_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def acknowledge_all(self) -> int:
        """确认所有未读预警"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE alert_history SET acknowledged_at = ? WHERE acknowledged_at IS NULL",
                (now,)
            )
            conn.commit()
            return cursor.rowcount
    
    def clear_history(self, days: int = 30) -> int:
        """清理旧历史记录"""
        cutoff = (datetime.now() - __import__('datetime').timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM alert_history WHERE created_at < ?",
                (cutoff,)
            )
            conn.commit()
            return cursor.rowcount
    
    # ------------------------------------------------------------------
    # 导入/导出
    # ------------------------------------------------------------------
    
    def export_rules(self, symbol: Optional[str] = None) -> str:
        """导出规则为JSON"""
        rules = self.get_rules(symbol=symbol)
        data = {
            'export_time': datetime.now().isoformat(),
            'rule_count': len(rules),
            'rules': [rule.to_dict() for rule in rules]
        }
        return json.dumps(data, indent=2)
    
    def import_rules(self, json_str: str) -> Dict:
        """从JSON导入规则"""
        try:
            data = json.loads(json_str)
            rules_data = data.get('rules', [])
            
            imported = 0
            failed = 0
            
            for rule_data in rules_data:
                try:
                    # 重置ID避免冲突
                    rule_data['id'] = None
                    rule = AlertRule.from_dict(rule_data)
                    self.create_rule(rule)
                    imported += 1
                except Exception as e:
                    logger.error(f"Failed to import rule: {e}")
                    failed += 1
            
            return {'success': True, 'imported': imported, 'failed': failed}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    
    def _row_to_rule(self, row) -> AlertRule:
        """数据库行转Rule对象"""
        from alerts.models import AlertType, AlertCondition, AlertSeverity
        
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
    
    def _row_to_history(self, row) -> AlertHistory:
        """数据库行转History对象"""
        from alerts.models import AlertType, AlertSeverity, AlertCondition
        
        return AlertHistory(
            id=row[0],
            rule_id=row[1],
            rule_name=row[2],
            symbol=row[3],
            alert_type=AlertType(row[4]),
            severity=AlertSeverity(row[5]),
            trigger_value=row[6],
            threshold=row[7],
            condition=AlertCondition(row[8]),
            price=row[9],
            price_change_pct=row[10],
            volume=row[11],
            message=row[12],
            metadata=json.loads(row[13]) if row[13] else {},
            notified_discord=bool(row[14]),
            notified_telegram=bool(row[15]),
            created_at=row[16],
            acknowledged_at=row[17],
        )
    
    def get_statistics(self) -> Dict:
        """获取预警统计"""
        with self._get_connection() as conn:
            # 规则统计
            cursor = conn.execute("SELECT COUNT(*) FROM alert_rules")
            total_rules = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM alert_rules WHERE status = ?",
                (AlertStatus.ENABLED.value,)
            )
            enabled_rules = cursor.fetchone()[0]
            
            # 历史统计
            cursor = conn.execute("SELECT COUNT(*) FROM alert_history")
            total_alerts = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM alert_history WHERE acknowledged_at IS NULL"
            )
            unread_alerts = cursor.fetchone()[0]
            
            # 今日预警
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = conn.execute(
                "SELECT COUNT(*) FROM alert_history WHERE created_at LIKE ?",
                (f'{today}%',)
            )
            today_alerts = cursor.fetchone()[0]
        
        return {
            'rules': {
                'total': total_rules,
                'enabled': enabled_rules,
                'disabled': total_rules - enabled_rules,
            },
            'alerts': {
                'total': total_alerts,
                'unread': unread_alerts,
                'today': today_alerts,
            }
        }


if __name__ == "__main__":
    # 测试
    manager = AlertManager()
    print("AlertManager initialized")
    
    # 创建测试规则
    from alerts.models import AlertRule, AlertType, AlertCondition, AlertSeverity
    
    rule = AlertRule(
        id=None,
        name="AAPL突破测试",
        symbol="AAPL",
        alert_type=AlertType.PRICE_THRESHOLD,
        condition=AlertCondition.GREATER_THAN,
        threshold=200.0,
        severity=AlertSeverity.MEDIUM,
    )
    
    created = manager.create_rule(rule)
    print(f"Created rule: {created.id}")
    
    # 获取统计
    stats = manager.get_statistics()
    print(f"Statistics: {stats}")
