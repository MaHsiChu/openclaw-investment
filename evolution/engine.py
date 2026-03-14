"""Evolution Engine - 自我进化引擎
负责管理系统的自动学习、升级和Skill开发
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


class EvolutionType(Enum):
    KNOWLEDGE = "knowledge"      # 知识学习
    STRATEGY = "strategy"        # 策略优化
    SKILL = "skill"              # Skill开发
    CODE = "code"                # 代码重构
    MCP = "mcp"                  # MCP集成


class EvolutionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class EvolutionRecord:
    """进化记录"""
    id: str
    timestamp: datetime
    type: EvolutionType
    status: EvolutionStatus
    trigger: str  # manual, scheduled, event
    description: str
    changes: List[Dict[str, Any]]
    test_results: Optional[Dict] = None
    deployed: bool = False
    rollback_version: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "status": self.status.value,
            "trigger": self.trigger,
            "description": self.description,
            "changes": self.changes,
            "test_results": self.test_results,
            "deployed": self.deployed,
            "rollback_version": self.rollback_version
        }


class KnowledgeBase:
    """知识库管理"""
    
    def __init__(self, db_path: str = "storage/knowledge.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # 知识条目表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    source_type TEXT,
                    title TEXT,
                    content TEXT,
                    summary TEXT,
                    tags TEXT,
                    relevance_score REAL,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 学习记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date TEXT,
                    sources_scanned INTEGER,
                    new_items_added INTEGER,
                    key_insights TEXT,
                    applied_changes TEXT
                )
            """)
            conn.commit()
    
    def add_knowledge(self, source: str, source_type: str, title: str,
                      content: str, summary: str, tags: List[str],
                      relevance_score: float = 0.0) -> int:
        """添加知识条目"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO knowledge_items 
                (source, source_type, title, content, summary, tags, relevance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source, source_type, title, content, summary, 
                  json.dumps(tags), relevance_score))
            conn.commit()
            return cursor.lastrowid
    
    def get_unprocessed_knowledge(self, limit: int = 10) -> List[Dict]:
        """获取未处理的知识"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM knowledge_items 
                WHERE processed = FALSE
                ORDER BY relevance_score DESC
                LIMIT ?
            """, (limit,))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def mark_processed(self, item_id: int):
        """标记为已处理"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE knowledge_items SET processed = TRUE WHERE id = ?
            """, (item_id,))
            conn.commit()


class StrategyGenePool:
    """策略基因池 - 管理策略进化"""
    
    def __init__(self, db_path: str = "storage/strategies.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT,
                    params TEXT,
                    performance_score REAL,
                    win_rate REAL,
                    sharpe_ratio REAL,
                    generation INTEGER,
                    parent_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            conn.commit()
    
    def add_strategy(self, name: str, strategy_type: str, params: Dict,
                     generation: int = 1, parent_ids: List[int] = None) -> int:
        """添加新策略"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO strategies 
                (name, type, params, generation, parent_ids)
                VALUES (?, ?, ?, ?, ?)
            """, (name, strategy_type, json.dumps(params), generation,
                  json.dumps(parent_ids or [])))
            conn.commit()
            return cursor.lastrowid
    
    def get_top_strategies(self, limit: int = 10) -> List[Dict]:
        """获取表现最好的策略"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM strategies 
                WHERE is_active = TRUE
                ORDER BY performance_score DESC
                LIMIT ?
            """, (limit,))
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def update_performance(self, strategy_id: int, performance: Dict):
        """更新策略表现"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE strategies SET
                    performance_score = ?,
                    win_rate = ?,
                    sharpe_ratio = ?
                WHERE id = ?
            """, (performance.get('score'), performance.get('win_rate'),
                  performance.get('sharpe'), strategy_id))
            conn.commit()


class EvolutionEngine:
    """进化引擎主类"""
    
    def __init__(self, db_path: str = "storage/evolution.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_base = KnowledgeBase()
        self.strategy_pool = StrategyGenePool()
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_log (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    type TEXT,
                    status TEXT,
                    trigger TEXT,
                    description TEXT,
                    changes TEXT,
                    test_results TEXT,
                    deployed BOOLEAN,
                    rollback_version TEXT
                )
            """)
            conn.commit()
    
    def _generate_id(self) -> str:
        """生成进化ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]
        return f"evo_{timestamp}_{hash_suffix}"
    
    def start_evolution(self, evo_type: EvolutionType, trigger: str,
                       description: str) -> str:
        """开始一次进化"""
        evo_id = self._generate_id()
        record = EvolutionRecord(
            id=evo_id,
            timestamp=datetime.now(),
            type=evo_type,
            status=EvolutionStatus.IN_PROGRESS,
            trigger=trigger,
            description=description,
            changes=[]
        )
        self._save_record(record)
        return evo_id
    
    def _save_record(self, record: EvolutionRecord):
        """保存进化记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evolution_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.timestamp.isoformat(),
                record.type.value,
                record.status.value,
                record.trigger,
                record.description,
                json.dumps(record.changes),
                json.dumps(record.test_results) if record.test_results else None,
                record.deployed,
                record.rollback_version
            ))
            conn.commit()
    
    def add_change(self, evo_id: str, change_type: str, description: str,
                   details: Dict[str, Any]):
        """记录变更"""
        record = self.get_record(evo_id)
        if record:
            record.changes.append({
                "type": change_type,
                "description": description,
                "details": details,
                "timestamp": datetime.now().isoformat()
            })
            self._save_record(record)
    
    def complete_evolution(self, evo_id: str, test_results: Dict = None):
        """完成进化"""
        record = self.get_record(evo_id)
        if record:
            record.status = EvolutionStatus.COMPLETED
            record.test_results = test_results
            self._save_record(record)
    
    def get_record(self, evo_id: str) -> Optional[EvolutionRecord]:
        """获取进化记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM evolution_log WHERE id = ?
            """, (evo_id,))
            row = cursor.fetchone()
            if row:
                return EvolutionRecord(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    type=EvolutionType(row[2]),
                    status=EvolutionStatus(row[3]),
                    trigger=row[4],
                    description=row[5],
                    changes=json.loads(row[6]) if row[6] else [],
                    test_results=json.loads(row[7]) if row[7] else None,
                    deployed=row[8],
                    rollback_version=row[9]
                )
        return None
    
    def get_recent_evolutions(self, limit: int = 10) -> List[EvolutionRecord]:
        """获取最近的进化记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM evolution_log 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            records = []
            for row in cursor.fetchall():
                records.append(EvolutionRecord(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    type=EvolutionType(row[2]),
                    status=EvolutionStatus(row[3]),
                    trigger=row[4],
                    description=row[5],
                    changes=json.loads(row[6]) if row[6] else [],
                    test_results=json.loads(row[7]) if row[7] else None,
                    deployed=row[8],
                    rollback_version=row[9]
                ))
            return records
    
    # ============== 进化任务 ==============
    
    def scan_for_knowledge(self) -> List[Dict]:
        """扫描新知识"""
        # TODO: 实现知识扫描
        return []
    
    def evolve_strategy(self, parent_strategy_id: Optional[int] = None) -> int:
        """进化策略"""
        # TODO: 实现策略进化
        return 0
    
    def develop_skill(self, skill_spec: Dict) -> str:
        """开发新Skill"""
        # TODO: 实现自动Skill开发
        return ""


if __name__ == "__main__":
    # 测试
    engine = EvolutionEngine()
    
    # 开始一次进化
    evo_id = engine.start_evolution(
        EvolutionType.KNOWLEDGE,
        "test",
        "测试知识学习进化"
    )
    print(f"Started evolution: {evo_id}")
    
    # 添加变更
    engine.add_change(evo_id, "knowledge_add", "添加了新的投资策略知识", {
        "source": "test",
        "items": 5
    })
    
    # 完成
    engine.complete_evolution(evo_id, {"success": True})
    
    # 查询
    record = engine.get_record(evo_id)
    print(f"Record: {record.to_dict()}")
