"""
Tests for Alerts Module
"""
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.models import (
    AlertRule, AlertHistory, AlertType, AlertCondition, 
    AlertSeverity, AlertStatus, ALERT_TEMPLATES
)
from alerts.manager import AlertManager
from alerts.engine import AlertEngine


class TestAlertModels(unittest.TestCase):
    """测试预警模型"""
    
    def test_alert_rule_creation(self):
        """测试创建预警规则"""
        rule = AlertRule(
            id="test-123",
            name="AAPL突破预警",
            symbol="AAPL",
            alert_type=AlertType.PRICE_THRESHOLD,
            condition=AlertCondition.GREATER_THAN,
            threshold=200.0,
            severity=AlertSeverity.HIGH,
        )
        
        self.assertEqual(rule.symbol, "AAPL")
        self.assertEqual(rule.threshold, 200.0)
        self.assertEqual(rule.status, AlertStatus.ENABLED)
    
    def test_alert_rule_to_dict(self):
        """测试规则序列化"""
        rule = AlertRule(
            id="test-123",
            name="测试规则",
            symbol="NVDA",
            alert_type=AlertType.TECHNICAL_INDICATOR,
            condition=AlertCondition.LESS_THAN,
            threshold=30.0,
            params={"indicator": "rsi", "period": 14},
        )
        
        data = rule.to_dict()
        self.assertEqual(data["symbol"], "NVDA")
        self.assertEqual(data["params"]["indicator"], "rsi")
    
    def test_alert_templates_exist(self):
        """测试预设模板存在"""
        self.assertIn("price_breakout", ALERT_TEMPLATES)
        self.assertIn("rsi_overbought", ALERT_TEMPLATES)
        self.assertIn("macd_golden_cross", ALERT_TEMPLATES)


class TestAlertManager(unittest.TestCase):
    """测试预警管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.test_db = "storage/test_alerts.db"
        # 删除旧测试数据库
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.manager = AlertManager(db_path=self.test_db)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_create_rule(self):
        """测试创建规则"""
        rule = AlertRule(
            id=None,
            name="测试规则",
            symbol="AAPL",
            alert_type=AlertType.PRICE_THRESHOLD,
            condition=AlertCondition.GREATER_THAN,
            threshold=200.0,
        )
        
        created = self.manager.create_rule(rule)
        self.assertIsNotNone(created.id)
        self.assertEqual(created.symbol, "AAPL")
    
    def test_get_rules(self):
        """测试获取规则列表"""
        # 创建测试规则
        for i in range(3):
            rule = AlertRule(
                id=None,
                name=f"规则{i}",
                symbol="AAPL",
                alert_type=AlertType.PRICE_THRESHOLD,
                condition=AlertCondition.GREATER_THAN,
                threshold=100.0 + i,
            )
            self.manager.create_rule(rule)
        
        rules = self.manager.get_rules()
        self.assertEqual(len(rules), 3)
    
    def test_update_rule(self):
        """测试更新规则"""
        rule = AlertRule(
            id=None,
            name="原名称",
            symbol="AAPL",
            alert_type=AlertType.PRICE_THRESHOLD,
            condition=AlertCondition.GREATER_THAN,
            threshold=200.0,
        )
        created = self.manager.create_rule(rule)
        
        updated = self.manager.update_rule(created.id, {"name": "新名称", "threshold": 250.0})
        self.assertEqual(updated.name, "新名称")
        self.assertEqual(updated.threshold, 250.0)
    
    def test_delete_rule(self):
        """测试删除规则"""
        rule = AlertRule(
            id=None,
            name="待删除",
            symbol="AAPL",
            alert_type=AlertType.PRICE_THRESHOLD,
            condition=AlertCondition.GREATER_THAN,
            threshold=200.0,
        )
        created = self.manager.create_rule(rule)
        
        success = self.manager.delete_rule(created.id)
        self.assertTrue(success)
        
        # 确认已删除
        found = self.manager.get_rule(created.id)
        self.assertIsNone(found)
    
    def test_create_from_template(self):
        """测试从模板创建规则"""
        rule = self.manager.create_rule_from_template(
            template_key="rsi_overbought",
            symbol="NVDA",
        )
        
        self.assertIsNotNone(rule)
        self.assertEqual(rule.symbol, "NVDA")
        self.assertEqual(rule.alert_type, AlertType.TECHNICAL_INDICATOR)
        self.assertEqual(rule.threshold, 70.0)
    
    def test_statistics(self):
        """测试统计功能"""
        # 创建规则
        rule = AlertRule(
            id=None,
            name="统计测试",
            symbol="AAPL",
            alert_type=AlertType.PRICE_THRESHOLD,
            condition=AlertCondition.GREATER_THAN,
            threshold=200.0,
        )
        self.manager.create_rule(rule)
        
        stats = self.manager.get_statistics()
        self.assertEqual(stats["rules"]["total"], 1)
        self.assertEqual(stats["rules"]["enabled"], 1)


class TestAlertEngine(unittest.TestCase):
    """测试预警引擎"""
    
    def setUp(self):
        """测试前准备"""
        self.test_db = "storage/test_alerts_engine.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.engine = AlertEngine(db_path=self.test_db)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine)
        self.assertTrue(os.path.exists(self.test_db))


def run_tests():
    """运行测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAlertModels))
    suite.addTests(loader.loadTestsFromTestCase(TestAlertManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAlertEngine))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
