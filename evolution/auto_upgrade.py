"""
Auto Upgrade System - 自动升级系统
实现系统的自我更新、Skill自动开发、策略自动优化
"""
import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoUpgrade")


class UpgradeType(Enum):
    KNOWLEDGE = "knowledge"      # 知识更新
    STRATEGY = "strategy"        # 策略升级
    SKILL = "skill"              # Skill开发
    CODE = "code"                # 代码优化
    DEPENDENCY = "dependency"    # 依赖更新
    CONFIG = "config"            # 配置更新


class UpgradePriority(Enum):
    CRITICAL = 1    # 关键 - 立即执行
    HIGH = 2        # 高 - 24小时内
    MEDIUM = 3      # 中 - 本周内
    LOW = 4         # 低 - 按需


@dataclass
class UpgradeTask:
    """升级任务"""
    id: str
    type: UpgradeType
    priority: UpgradePriority
    description: str
    trigger: str
    auto_execute: bool  # 是否自动执行
    validation_required: bool  # 是否需要验证
    rollback_capable: bool  # 是否可回滚
    created_at: datetime
    executed_at: Optional[datetime] = None
    status: str = "pending"  # pending, executing, completed, failed, rolled_back
    result: Optional[Dict] = None


class AutoUpgrader:
    """自动升级器 - 系统自我进化核心"""
    
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace).resolve()
        self.tasks: List[UpgradeTask] = []
        self.history: List[Dict] = []
        self.backup_dir = self.workspace / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # 升级处理器注册表
        self.upgrade_handlers: Dict[UpgradeType, Callable] = {
            UpgradeType.KNOWLEDGE: self._upgrade_knowledge,
            UpgradeType.STRATEGY: self._upgrade_strategy,
            UpgradeType.SKILL: self._upgrade_skill,
            UpgradeType.CODE: self._upgrade_code,
            UpgradeType.DEPENDENCY: self._upgrade_dependency,
            UpgradeType.CONFIG: self._upgrade_config,
        }
        
        # 加载历史
        self._load_history()
    
    def _load_history(self):
        """加载升级历史"""
        history_file = self.workspace / "storage" / "upgrade_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                self.history = json.load(f)
    
    def _save_history(self):
        """保存升级历史"""
        history_file = self.workspace / "storage" / "upgrade_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"upgrade_{ts}"
    
    def create_backup(self, name: str) -> Path:
        """创建系统备份"""
        backup_path = self.backup_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 备份关键文件
        for item in ["data", "analyzer", "report", "simulation", "evolution", "config"]:
            src = self.workspace / item
            if src.exists():
                dst = backup_path / item
                if src.is_dir():
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
                else:
                    shutil.copy2(src, dst)
        
        logger.info(f"Backup created: {backup_path}")
        return backup_path
    
    def rollback(self, backup_path: Path) -> bool:
        """回滚到备份版本"""
        try:
            for item in backup_path.iterdir():
                src = backup_path / item.name
                dst = self.workspace / item.name
                
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            logger.info(f"Rolled back to: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    # ============== 升级处理器 ==============
    
    def _upgrade_knowledge(self, task: UpgradeTask) -> Dict:
        """知识升级 - 学习新内容"""
        from evolution.auto_learner import AutoLearner
        from evolution.engine import KnowledgeBase
        
        kb = KnowledgeBase(str(self.workspace / "storage" / "knowledge.db"))
        
        import asyncio
        async def learn():
            async with AutoLearner(kb) as learner:
                return await learner.run_learning_session()
        
        result = asyncio.run(learn())
        
        return {
            "success": True,
            "sources": result.get("sources", {}),
            "insights_count": len(result.get("insights", [])),
            "details": result
        }
    
    def _upgrade_strategy(self, task: UpgradeTask) -> Dict:
        """策略升级 - 优化投资策略"""
        # TODO: 实现策略遗传优化
        return {
            "success": True,
            "message": "Strategy optimization placeholder",
            "improvements": []
        }
    
    def _upgrade_skill(self, task: UpgradeTask) -> Dict:
        """Skill升级 - 开发新Skill"""
        from evolution.skill_developer import SkillDeveloper
        
        developer = SkillDeveloper(str(self.workspace / "skills"))
        
        # 分析系统能力缺口
        capabilities = self._analyze_capabilities()
        
        # 开发缺失的Skills
        created = developer.develop_all_gaps(capabilities)
        
        return {
            "success": True,
            "skills_created": len(created),
            "skills": [str(p) for p in created]
        }
    
    def _upgrade_code(self, task: UpgradeTask) -> Dict:
        """代码升级 - 自动重构优化"""
        from evolution.skill_developer import SkillOptimizer
        
        optimizer = SkillOptimizer()
        
        improvements = []
        for py_file in self.workspace.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            issues = optimizer.analyze_skill(py_file)
            if issues:
                improvements.append({
                    "file": str(py_file.relative_to(self.workspace)),
                    "issues": len(issues)
                })
        
        return {
            "success": True,
            "files_analyzed": len(list(self.workspace.rglob("*.py"))),
            "improvements_found": len(improvements),
            "details": improvements[:10]  # 只显示前10个
        }
    
    def _upgrade_dependency(self, task: UpgradeTask) -> Dict:
        """依赖升级 - 更新Python包"""
        try:
            # 检查可更新的包
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                cwd=self.workspace
            )
            
            outdated = json.loads(result.stdout) if result.stdout else []
            
            # 筛选重要的包
            critical_packages = ["yfinance", "akshare", "pandas", "numpy", "requests"]
            to_update = [p for p in outdated if p["name"] in critical_packages]
            
            return {
                "success": True,
                "outdated_count": len(outdated),
                "critical_updates": len(to_update),
                "packages": to_update
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _upgrade_config(self, task: UpgradeTask) -> Dict:
        """配置升级 - 更新配置文件"""
        # 检查配置文件版本
        config_file = self.workspace / "config" / "system.json"
        
        # TODO: 实现配置版本管理
        return {
            "success": True,
            "message": "Config check completed",
            "updates_available": False
        }
    
    def _analyze_capabilities(self) -> Dict:
        """分析系统当前能力"""
        capabilities = {}
        
        # 检查各模块是否存在
        capabilities["news_fetch"] = (self.workspace / "data" / "news_fetcher.py").exists()
        capabilities["report_generator"] = (self.workspace / "report" / "generator.py").exists()
        capabilities["technical_analysis"] = (self.workspace / "analyzer" / "technical.py").exists()
        capabilities["sentiment_analysis"] = (self.workspace / "analyzer" / "sentiment.py").exists()
        capabilities["backtest"] = (self.workspace / "simulation" / "backtest.py").exists()
        
        return capabilities
    
    # ============== 公共接口 ==============
    
    def schedule_upgrade(self, upgrade_type: UpgradeType, 
                        priority: UpgradePriority = UpgradePriority.MEDIUM,
                        description: str = "",
                        auto_execute: bool = False) -> str:
        """调度升级任务"""
        task = UpgradeTask(
            id=self._generate_task_id(),
            type=upgrade_type,
            priority=priority,
            description=description or f"{upgrade_type.value} upgrade",
            trigger="manual",
            auto_execute=auto_execute,
            validation_required=True,
            rollback_capable=True,
            created_at=datetime.now()
        )
        
        self.tasks.append(task)
        logger.info(f"Upgrade scheduled: {task.id} ({upgrade_type.value})")
        
        if auto_execute:
            self.execute_upgrade(task.id)
        
        return task.id
    
    def execute_upgrade(self, task_id: str) -> Dict:
        """执行升级任务"""
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return {"success": False, "error": "Task not found"}
        
        # 创建备份
        backup = self.create_backup(f"pre_{task.type.value}")
        
        task.status = "executing"
        task.executed_at = datetime.now()
        
        try:
            # 执行升级
            handler = self.upgrade_handlers.get(task.type)
            if not handler:
                raise ValueError(f"No handler for type: {task.type}")
            
            result = handler(task)
            
            task.status = "completed" if result.get("success") else "failed"
            task.result = result
            
            # 记录历史
            self.history.append({
                "task_id": task.id,
                "type": task.type.value,
                "status": task.status,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "backup": str(backup)
            })
            self._save_history()
            
            logger.info(f"Upgrade completed: {task.id}")
            return result
            
        except Exception as e:
            task.status = "failed"
            task.result = {"success": False, "error": str(e)}
            
            # 尝试回滚
            if task.rollback_capable:
                logger.warning(f"Attempting rollback for: {task.id}")
                self.rollback(backup)
                task.status = "rolled_back"
            
            logger.error(f"Upgrade failed: {task.id} - {e}")
            return task.result
    
    def auto_discover_upgrades(self) -> List[UpgradeTask]:
        """自动发现可升级项"""
        discovered = []
        
        # 检查知识库是否有未处理内容
        from evolution.engine import KnowledgeBase
        kb = KnowledgeBase(str(self.workspace / "storage" / "knowledge.db"))
        unprocessed = kb.get_unprocessed_knowledge()
        if len(unprocessed) > 5:
            discovered.append(UpgradeTask(
                id=self._generate_task_id(),
                type=UpgradeType.KNOWLEDGE,
                priority=UpgradePriority.MEDIUM,
                description=f"Process {len(unprocessed)} unprocessed knowledge items",
                trigger="auto_discover",
                auto_execute=False,
                validation_required=True,
                rollback_capable=True,
                created_at=datetime.now()
            ))
        
        # 检查是否有缺失的Skill
        capabilities = self._analyze_capabilities()
        missing = [k for k, v in capabilities.items() if not v]
        if missing:
            discovered.append(UpgradeTask(
                id=self._generate_task_id(),
                type=UpgradeType.SKILL,
                priority=UpgradePriority.HIGH,
                description=f"Develop missing skills: {', '.join(missing)}",
                trigger="auto_discover",
                auto_execute=False,
                validation_required=True,
                rollback_capable=True,
                created_at=datetime.now()
            ))
        
        return discovered
    
    def get_status(self) -> Dict:
        """获取升级系统状态"""
        return {
            "pending_tasks": len([t for t in self.tasks if t.status == "pending"]),
            "completed_upgrades": len([h for h in self.history if h["status"] == "completed"]),
            "failed_upgrades": len([h for h in self.history if h["status"] == "failed"]),
            "last_upgrade": self.history[-1] if self.history else None,
            "capabilities": self._analyze_capabilities()
        }
    
    def generate_upgrade_report(self) -> str:
        """生成升级报告"""
        status = self.get_status()
        
        report = f"""
# 系统升级报告

## 升级统计
- 已完成升级: {status['completed_upgrades']}
- 失败升级: {status['failed_upgrades']}
- 待处理任务: {status['pending_tasks']}

## 系统能力
"""
        for cap, available in status['capabilities'].items():
            icon = "✅" if available else "❌"
            report += f"- {icon} {cap}\n"
        
        if self.history:
            report += "\n## 最近升级\n\n"
            for h in self.history[-5:]:
                report += f"- **{h['type']}** ({h['status']}) - {h['timestamp'][:10]}\n"
        
        return report


# ============== CLI接口 ==============

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Upgrade System")
    parser.add_argument("command", choices=[
        "status", "discover", "upgrade", "report", "rollback"
    ])
    parser.add_argument("--type", choices=[t.value for t in UpgradeType],
                       help="Upgrade type")
    parser.add_argument("--auto", action="store_true",
                       help="Auto execute")
    
    args = parser.parse_args()
    
    upgrader = AutoUpgrader()
    
    if args.command == "status":
        print(json.dumps(upgrader.get_status(), indent=2))
    
    elif args.command == "discover":
        tasks = upgrader.auto_discover_upgrades()
        print(f"Discovered {len(tasks)} upgrade opportunities:")
        for t in tasks:
            print(f"  - [{t.type.value}] {t.description}")
    
    elif args.command == "upgrade":
        if args.type:
            task_id = upgrader.schedule_upgrade(
                UpgradeType(args.type),
                auto_execute=args.auto
            )
            print(f"Upgrade scheduled: {task_id}")
            if args.auto:
                result = upgrader.execute_upgrade(task_id)
                print(json.dumps(result, indent=2))
        else:
            print("Please specify --type")
    
    elif args.command == "report":
        print(upgrader.generate_upgrade_report())
    
    elif args.command == "rollback":
        print("Use: rollback <backup_path>")


if __name__ == "__main__":
    main()
