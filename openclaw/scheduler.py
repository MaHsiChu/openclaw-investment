"""
Scheduler - 定时任务调度器
使用APScheduler实现定时数据更新、报告生成和推送
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# 延迟导入APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)


class JobType(Enum):
    DATA_UPDATE = "data_update"          # 数据更新
    DAILY_REPORT = "daily_report"        # 日报生成
    WEEKLY_REPORT = "weekly_report"      # 周报生成
    AUTO_LEARN = "auto_learn"            # 自动学习
    SYSTEM_CHECK = "system_check"        # 系统检查
    PORTFOLIO_CHECK = "portfolio_check"  # 组合检查


@dataclass
class ScheduledJob:
    """定时任务定义"""
    id: str
    type: JobType
    name: str
    description: str
    cron: str  # cron表达式，如 "0 9 * * 1-5" (工作日9:00)
    timezone: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None  # success, failed


class InvestmentScheduler:
    """投资系统定时任务调度器"""
    
    DEFAULT_JOBS = [
        ScheduledJob(
            id="market_open_update",
            type=JobType.DATA_UPDATE,
            name="开盘数据更新",
            description="美股开盘前更新数据",
            cron="30 9 * * 1-5",  # 工作日 9:30 EST
            timezone="US/Eastern"
        ),
        ScheduledJob(
            id="market_close_report",
            type=JobType.DAILY_REPORT,
            name="收盘日报",
            description="美股收盘后生成日报",
            cron="5 16 * * 1-5",  # 工作日 16:05 EST
            timezone="US/Eastern"
        ),
        ScheduledJob(
            id="evening_auto_learn",
            type=JobType.AUTO_LEARN,
            name="晚间自动学习",
            description="自动学习新知识",
            cron="0 21 * * *",  # 每天 21:00 CST
            timezone="Asia/Shanghai"
        ),
        ScheduledJob(
            id="weekly_report",
            type=JobType.WEEKLY_REPORT,
            name="周末周报",
            description="生成本周投资周报",
            cron="0 18 * * 5",  # 周五 18:00 CST
            timezone="Asia/Shanghai"
        ),
        ScheduledJob(
            id="hourly_portfolio_check",
            type=JobType.PORTFOLIO_CHECK,
            name="组合检查",
            description="每小时检查投资组合",
            cron="0 * * * *",  # 每小时
            timezone="Asia/Shanghai"
        ),
    ]
    
    def __init__(self, config_path: str = "config/scheduler.json"):
        self.config_path = Path(config_path)
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.jobs: Dict[str, ScheduledJob] = {}
        self.job_handlers: Dict[JobType, Callable] = {}
        
        # 注册默认任务处理器
        self._register_default_handlers()
        
        # 加载配置
        self._load_jobs()
    
    def _register_default_handlers(self):
        """注册默认任务处理器"""
        self.job_handlers[JobType.DATA_UPDATE] = self._handle_data_update
        self.job_handlers[JobType.DAILY_REPORT] = self._handle_daily_report
        self.job_handlers[JobType.WEEKLY_REPORT] = self._handle_weekly_report
        self.job_handlers[JobType.AUTO_LEARN] = self._handle_auto_learn
        self.job_handlers[JobType.SYSTEM_CHECK] = self._handle_system_check
        self.job_handlers[JobType.PORTFOLIO_CHECK] = self._handle_portfolio_check
    
    def _load_jobs(self):
        """加载任务配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                jobs_data = json.load(f)
                for job_data in jobs_data:
                    job = ScheduledJob(**job_data)
                    self.jobs[job.id] = job
        else:
            # 使用默认配置
            for job in self.DEFAULT_JOBS:
                self.jobs[job.id] = job
            self._save_jobs()
    
    def _save_jobs(self):
        """保存任务配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump([asdict(job) for job in self.jobs.values()], f, indent=2, default=str)
    
    def _on_job_executed(self, event):
        """任务执行完成回调"""
        job_id = event.job_id
        if job_id in self.jobs:
            self.jobs[job_id].last_run = datetime.now()
            self.jobs[job_id].last_status = "success"
            self._save_jobs()
            logger.info(f"Job {job_id} executed successfully")
    
    def _on_job_error(self, event):
        """任务执行错误回调"""
        job_id = event.job_id
        if job_id in self.jobs:
            self.jobs[job_id].last_run = datetime.now()
            self.jobs[job_id].last_status = "failed"
            self._save_jobs()
            logger.error(f"Job {job_id} failed: {event.exception}")
    
    # ============== 任务处理器 ==============
    
    async def _handle_data_update(self):
        """处理数据更新任务"""
        logger.info("Running scheduled data update")
        
        try:
            from data.market_data import MarketDataManager
            
            dm = MarketDataManager()
            
            # 更新所有板块
            for sector_name in dm.sectors:
                stocks = dm.get_sector_stocks(sector_name)
                for stock in stocks:
                    dm.update_stock_data(
                        stock["symbol"],
                        sector_name,
                        stock.get("market_type", "US")
                    )
            
            logger.info("Data update completed")
            
        except Exception as e:
            logger.error(f"Data update failed: {e}")
            raise
    
    async def _handle_daily_report(self):
        """处理日报生成任务"""
        logger.info("Running scheduled daily report generation")
        
        try:
            # 生成报告
            from report.daily_report import DailyReportGenerator
            from openclaw.notifier import send_daily_report
            
            generator = DailyReportGenerator()
            report = generator.generate()
            
            # 发送报告
            await send_daily_report(report)
            
            logger.info("Daily report sent")
            
        except Exception as e:
            logger.error(f"Daily report failed: {e}")
            raise
    
    async def _handle_weekly_report(self):
        """处理周报生成任务"""
        logger.info("Running scheduled weekly report generation")
        
        try:
            from report.weekly_report import WeeklyReportGenerator
            from openclaw.notifier import load_notifier_config, MultiNotifier
            
            generator = WeeklyReportGenerator()
            report = generator.generate()
            
            # 发送周报
            configs = load_notifier_config()
            if configs:
                notifier = MultiNotifier(configs)
                await notifier.send_weekly_report(report)
            
            logger.info("Weekly report sent")
            
        except Exception as e:
            logger.error(f"Weekly report failed: {e}")
            raise
    
    async def _handle_auto_learn(self):
        """处理自动学习任务"""
        logger.info("Running scheduled auto learning")
        
        try:
            from evolution.auto_learner import AutoLearner
            from evolution.engine import KnowledgeBase
            
            kb = KnowledgeBase()
            
            async with AutoLearner(kb) as learner:
                result = await learner.run_learning_session()
                logger.info(f"Auto learn completed: {result}")
            
        except Exception as e:
            logger.error(f"Auto learn failed: {e}")
            raise
    
    async def _handle_system_check(self):
        """处理系统检查任务"""
        logger.info("Running scheduled system check")
        
        try:
            from evolution.auto_upgrade import AutoUpgrader
            
            upgrader = AutoUpgrader()
            status = upgrader.get_status()
            
            # 检查是否有需要升级的项目
            if status['pending_tasks'] > 0:
                logger.info(f"Found {status['pending_tasks']} pending upgrades")
            
            logger.info("System check completed")
            
        except Exception as e:
            logger.error(f"System check failed: {e}")
            raise
    
    async def _handle_portfolio_check(self):
        """处理投资组合检查任务"""
        logger.info("Running scheduled portfolio check")
        
        try:
            from storage.database import DatabaseManager
            
            db = DatabaseManager()
            
            # TODO: 检查持仓盈亏，触发预警
            logger.info("Portfolio check completed")
            
        except Exception as e:
            logger.error(f"Portfolio check failed: {e}")
            raise
    
    # ============== 公共接口 ==============
    
    def start(self):
        """启动调度器"""
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler()
            
            # 添加事件监听
            self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
            
            # 注册所有启用的任务
            for job in self.jobs.values():
                if job.enabled:
                    self._add_job_to_scheduler(job)
            
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def _add_job_to_scheduler(self, job: ScheduledJob):
        """添加任务到调度器"""
        handler = self.job_handlers.get(job.type)
        if not handler:
            logger.warning(f"No handler for job type: {job.type}")
            return
        
        # 解析cron表达式
        parts = job.cron.split()
        if len(parts) != 5:
            logger.error(f"Invalid cron expression: {job.cron}")
            return
        
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=job.timezone
        )
        
        self.scheduler.add_job(
            handler,
            trigger=trigger,
            id=job.id,
            name=job.name,
            replace_existing=True
        )
        
        logger.info(f"Added job: {job.id} ({job.cron})")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
            logger.info("Scheduler stopped")
    
    def add_job(self, job: ScheduledJob):
        """添加新任务"""
        self.jobs[job.id] = job
        self._save_jobs()
        
        if self.scheduler and job.enabled:
            self._add_job_to_scheduler(job)
    
    def remove_job(self, job_id: str):
        """移除任务"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            
            if self.scheduler:
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass
    
    def enable_job(self, job_id: str):
        """启用任务"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            self._save_jobs()
            
            if self.scheduler:
                self._add_job_to_scheduler(self.jobs[job_id])
    
    def disable_job(self, job_id: str):
        """禁用任务"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            self._save_jobs()
            
            if self.scheduler:
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "running": self.scheduler is not None and self.scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "enabled": job.enabled,
                    "cron": job.cron,
                    "timezone": job.timezone,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "last_status": job.last_status
                }
                for job in self.jobs.values()
            ]
        }
    
    def run_job_now(self, job_id: str):
        """立即执行任务"""
        if job_id not in self.jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        job = self.jobs[job_id]
        handler = self.job_handlers.get(job.type)
        
        if handler:
            logger.info(f"Manually running job: {job_id}")
            return asyncio.create_task(handler())
        else:
            raise ValueError(f"No handler for job type: {job.type}")


# ============== 全局实例 ==============

_scheduler_instance: Optional[InvestmentScheduler] = None


def get_scheduler() -> InvestmentScheduler:
    """获取全局调度器实例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = InvestmentScheduler()
    return _scheduler_instance


async def start_scheduler():
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.start()


async def stop_scheduler():
    """停止全局调度器"""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None


if __name__ == "__main__":
    # 测试
    async def test():
        scheduler = InvestmentScheduler()
        
        # 打印状态
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, default=str))
        
        # 启动调度器
        scheduler.start()
        
        print("\nScheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            scheduler.stop()
    
    asyncio.run(test())
