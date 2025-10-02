import sqlite3
from contextlib import contextmanager
from pathlib import Path
import logging
from typing import Optional, Any, List, Tuple


class UnifiedDatabaseManager:
    """统一的数据库管理器 - 所有表都在一个数据库中"""

    _instance = None

    def __new__(cls, db_file='accounts_data/gptgod_checkin.db'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, db_file='accounts_data/gptgod_checkin.db'):
        if not self.initialized:
            self.db_file = Path(db_file)
            self.db_file.parent.mkdir(exist_ok=True, parents=True)
            self._init_all_tables()
            self.initialized = True

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: Tuple = ()) -> Optional[Any]:
        """执行单个查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            return cursor.lastrowid

    def execute_one(self, query: str, params: Tuple = ()) -> Optional[Any]:
        """执行查询并返回单条结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """批量执行查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)

    def _init_all_tables(self):
        """初始化所有表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # ========== 签到相关表 ==========
            # 创建签到会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checkin_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    trigger_type TEXT NOT NULL DEFAULT 'manual',
                    trigger_by TEXT,
                    total_accounts INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    already_checked_count INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    status TEXT NOT NULL DEFAULT 'running',
                    email_sent BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建账号签到记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_checkin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    account_email TEXT NOT NULL,
                    checkin_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    points INTEGER DEFAULT 0,
                    domain TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (session_id) REFERENCES checkin_sessions (id)
                )
            ''')

            # 创建账号统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_statistics (
                    email TEXT PRIMARY KEY,
                    total_checkins INTEGER DEFAULT 0,
                    successful_checkins INTEGER DEFAULT 0,
                    failed_checkins INTEGER DEFAULT 0,
                    total_points INTEGER DEFAULT 0,
                    last_checkin TEXT,
                    consecutive_days INTEGER DEFAULT 0,
                    first_checkin TEXT,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建签到相关索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_start_time ON checkin_sessions(start_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_logs_email ON account_checkin_logs(account_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_logs_session ON account_checkin_logs(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_logs_time ON account_checkin_logs(checkin_time)')

            # ========== 配置相关表 ==========
            # 创建系统配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    data_type TEXT NOT NULL DEFAULT 'str',
                    description TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建域名配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS domain_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    primary_domain TEXT NOT NULL,
                    backup_domain TEXT,
                    auto_switch BOOLEAN NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建定时任务配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    schedule_times TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建SMTP配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smtp_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled BOOLEAN NOT NULL DEFAULT 0,
                    server TEXT NOT NULL,
                    port INTEGER NOT NULL DEFAULT 587,
                    sender_email TEXT NOT NULL,
                    sender_password TEXT NOT NULL,
                    receiver_emails TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建Web认证配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_auth_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    api_token TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # 创建账号配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    send_email_notification BOOLEAN NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            # ========== 积分历史相关表 ==========
            # 创建积分历史表（完整版）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS points_history (
                    id INTEGER PRIMARY KEY,
                    uid INTEGER,
                    email TEXT,
                    tokens INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    remark TEXT,
                    ip TEXT,
                    create_time TEXT NOT NULL,
                    api_id INTEGER DEFAULT 0,
                    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建账号映射表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_mapping (
                    uid INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    last_update TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建积分相关索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_points_uid ON points_history (uid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_points_email ON points_history (email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_points_create_time ON points_history (create_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_points_source ON points_history (source)')

        logging.info("统一数据库所有表初始化完成")


# 获取全局数据库实例
def get_db() -> UnifiedDatabaseManager:
    """获取统一数据库管理器实例"""
    return UnifiedDatabaseManager()