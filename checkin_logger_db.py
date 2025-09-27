import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging


class CheckinLoggerDB:
    """基于数据库的签到日志记录器"""

    def __init__(self, data_dir='accounts_data'):
        """初始化数据库日志记录器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db_file = self.data_dir / 'checkin_logs.db'
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

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

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_start_time ON checkin_sessions(start_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_logs_email ON account_checkin_logs(account_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_logs_session ON account_checkin_logs(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_logs_time ON account_checkin_logs(checkin_time)')

            conn.commit()
            logging.info("签到日志数据库表初始化完成")

    def migrate_from_json_logs(self, log_dir='checkin_logs'):
        """从JSON日志文件迁移到数据库

        Args:
            log_dir: JSON日志文件目录
        """
        log_path = Path(log_dir)
        if not log_path.exists():
            logging.warning(f"日志目录 {log_dir} 不存在")
            return False

        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                migrated_sessions = 0
                migrated_logs = 0

                # 迁移每日日志文件
                for log_file in log_path.glob('checkin_*.json'):
                    if 'summary' in log_file.name:
                        continue

                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            sessions = json.load(f)

                        for session in sessions:
                            # 插入会话记录
                            cursor.execute('''
                                INSERT INTO checkin_sessions (
                                    start_time, end_time, trigger_type, trigger_by,
                                    total_accounts, success_count, failed_count, already_checked_count,
                                    duration_seconds, status, email_sent
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                session.get('start_time'),
                                session.get('end_time'),
                                session.get('trigger_type', 'manual'),
                                session.get('trigger_by'),
                                session.get('total_accounts', 0),
                                session.get('success_count', 0),
                                session.get('failed_count', 0),
                                session.get('already_checked_count', 0),
                                session.get('duration_seconds'),
                                session.get('status', 'completed'),
                                session.get('email_sent', False)
                            ))

                            session_id = cursor.lastrowid
                            migrated_sessions += 1

                            # 插入账号日志
                            for account in session.get('accounts', []):
                                cursor.execute('''
                                    INSERT INTO account_checkin_logs (
                                        session_id, account_email, checkin_time, status, message, points
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    session_id,
                                    account.get('email'),
                                    account.get('time'),
                                    account.get('status'),
                                    account.get('message', ''),
                                    account.get('points', 0)
                                ))
                                migrated_logs += 1

                                # 更新账号统计
                                self._update_account_statistics(
                                    cursor,
                                    account.get('email'),
                                    account.get('status'),
                                    account.get('points', 0),
                                    account.get('time')
                                )

                    except Exception as e:
                        logging.error(f"迁移日志文件 {log_file} 失败: {e}")
                        continue

                conn.commit()
                logging.info(f"日志迁移完成: {migrated_sessions} 个会话, {migrated_logs} 条记录")
                return True

        except Exception as e:
            logging.error(f"日志迁移失败: {e}")
            return False

    def _update_account_statistics(self, cursor, email, status, points, checkin_time):
        """更新账号统计信息"""
        # 获取或创建账号统计记录
        cursor.execute('SELECT * FROM account_statistics WHERE email = ?', (email,))
        result = cursor.fetchone()

        if result:
            # 更新现有记录
            total_checkins = result[1] + 1
            successful_checkins = result[2] + (1 if status == 'success' else 0)
            failed_checkins = result[3] + (1 if status == 'failed' else 0)
            total_points = result[4] + points

            cursor.execute('''
                UPDATE account_statistics
                SET total_checkins = ?, successful_checkins = ?, failed_checkins = ?,
                    total_points = ?, last_checkin = ?, updated_at = datetime('now')
                WHERE email = ?
            ''', (total_checkins, successful_checkins, failed_checkins,
                  total_points, checkin_time, email))
        else:
            # 创建新记录
            cursor.execute('''
                INSERT INTO account_statistics (
                    email, total_checkins, successful_checkins, failed_checkins,
                    total_points, last_checkin, first_checkin
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (email, 1,
                  1 if status == 'success' else 0,
                  1 if status == 'failed' else 0,
                  points, checkin_time, checkin_time))

    def log_checkin_start(self, trigger_type='manual', trigger_by=None):
        """记录签到开始"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO checkin_sessions (start_time, trigger_type, trigger_by)
                VALUES (?, ?, ?)
            ''', (datetime.now().isoformat(), trigger_type, trigger_by))
            session_id = cursor.lastrowid
            conn.commit()
            return session_id

    def log_account_result(self, session_id, account_email, status, message='', points=0, domain=None):
        """记录单个账号签到结果"""
        checkin_time = datetime.now().isoformat()

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # 插入账号日志
            cursor.execute('''
                INSERT INTO account_checkin_logs (
                    session_id, account_email, checkin_time, status, message, points, domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, account_email, checkin_time, status, message, points, domain))

            # 更新账号统计
            self._update_account_statistics(cursor, account_email, status, points, checkin_time)

            # 更新会话统计
            if status == 'success':
                cursor.execute('UPDATE checkin_sessions SET success_count = success_count + 1 WHERE id = ?', (session_id,))
            elif status == 'failed':
                cursor.execute('UPDATE checkin_sessions SET failed_count = failed_count + 1 WHERE id = ?', (session_id,))
            elif status == 'already_checked':
                cursor.execute('UPDATE checkin_sessions SET already_checked_count = already_checked_count + 1 WHERE id = ?', (session_id,))

            cursor.execute('UPDATE checkin_sessions SET total_accounts = total_accounts + 1 WHERE id = ?', (session_id,))
            conn.commit()

    def log_checkin_end(self, session_id, email_sent=False):
        """记录签到结束"""
        end_time = datetime.now().isoformat()

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # 获取开始时间计算耗时
            cursor.execute('SELECT start_time FROM checkin_sessions WHERE id = ?', (session_id,))
            result = cursor.fetchone()

            if result:
                start_time = datetime.fromisoformat(result[0])
                duration = (datetime.fromisoformat(end_time) - start_time).total_seconds()

                cursor.execute('''
                    UPDATE checkin_sessions
                    SET end_time = ?, status = 'completed', email_sent = ?, duration_seconds = ?
                    WHERE id = ?
                ''', (end_time, email_sent, duration, session_id))
                conn.commit()

    def get_statistics(self):
        """获取统计信息"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # 全部时间统计
            cursor.execute('''
                SELECT
                    COUNT(*) as total_sessions,
                    SUM(total_accounts) as total_checkins,
                    SUM(success_count) as successful_checkins,
                    SUM(failed_count) as failed_checkins,
                    SUM(already_checked_count) as already_checked_count
                FROM checkin_sessions WHERE status = 'completed'
            ''')
            all_time = cursor.fetchone()

            # 总积分
            cursor.execute('SELECT SUM(total_points) FROM account_statistics')
            total_points = cursor.fetchone()[0] or 0

            # 最近7天统计
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute('''
                SELECT
                    SUM(total_accounts) as total,
                    SUM(success_count) as success,
                    SUM(failed_count) as failed
                FROM checkin_sessions
                WHERE status = 'completed' AND start_time >= ?
            ''', (seven_days_ago,))
            recent_7_days = cursor.fetchone()

            # 最近30天统计
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute('''
                SELECT
                    SUM(total_accounts) as total,
                    SUM(success_count) as success,
                    SUM(failed_count) as failed
                FROM checkin_sessions
                WHERE status = 'completed' AND start_time >= ?
            ''', (thirty_days_ago,))
            recent_30_days = cursor.fetchone()

            # 今日统计
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT
                    COUNT(*) as sessions,
                    SUM(total_accounts) as accounts,
                    SUM(success_count) as success,
                    SUM(failed_count) as failed
                FROM checkin_sessions
                WHERE date(start_time) = ?
            ''', (today,))
            today_stats = cursor.fetchone()

            return {
                'all_time': {
                    'total_sessions': all_time[0] or 0,
                    'total_checkins': all_time[1] or 0,
                    'successful_checkins': all_time[2] or 0,
                    'failed_checkins': all_time[3] or 0,
                    'already_checked_count': all_time[4] or 0,
                    'total_points_earned': total_points
                },
                'recent_7_days': {
                    'total': recent_7_days[0] or 0,
                    'success': recent_7_days[1] or 0,
                    'failed': recent_7_days[2] or 0
                },
                'recent_30_days': {
                    'total': recent_30_days[0] or 0,
                    'success': recent_30_days[1] or 0,
                    'failed': recent_30_days[2] or 0
                },
                'today': {
                    'sessions': today_stats[0] or 0,
                    'accounts': today_stats[1] or 0,
                    'success': today_stats[2] or 0,
                    'failed': today_stats[3] or 0
                }
            }

    def get_account_history(self, email, days=30):
        """获取账号历史记录"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT checkin_time, status, message, points, domain
                FROM account_checkin_logs
                WHERE account_email = ? AND checkin_time >= ?
                ORDER BY checkin_time DESC
            ''', (email, cutoff_date))

            results = cursor.fetchall()
            return [
                {
                    'time': result[0],
                    'status': result[1],
                    'message': result[2],
                    'points': result[3],
                    'domain': result[4]
                }
                for result in results
            ]

    def get_recent_sessions(self, limit=10):
        """获取最近的签到会话"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, start_time, end_time, trigger_type, total_accounts,
                       success_count, failed_count, duration_seconds, status
                FROM checkin_sessions
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))

            results = cursor.fetchall()
            return [
                {
                    'id': result[0],
                    'start_time': result[1],
                    'end_time': result[2],
                    'trigger_type': result[3],
                    'total_accounts': result[4],
                    'success_count': result[5],
                    'failed_count': result[6],
                    'duration_seconds': result[7],
                    'status': result[8]
                }
                for result in results
            ]

    def get_account_statistics(self):
        """获取所有账号统计信息"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT email, total_checkins, successful_checkins, failed_checkins,
                       total_points, last_checkin, consecutive_days
                FROM account_statistics
                ORDER BY total_points DESC
            ''')

            results = cursor.fetchall()
            return [
                {
                    'email': result[0],
                    'total_checkins': result[1],
                    'successful_checkins': result[2],
                    'failed_checkins': result[3],
                    'total_points': result[4],
                    'last_checkin': result[5],
                    'consecutive_days': result[6]
                }
                for result in results
            ]


# 使用示例
if __name__ == '__main__':
    logger = CheckinLoggerDB()

    # 迁移现有JSON日志
    logger.migrate_from_json_logs('checkin_logs')

    # 测试新功能
    session_id = logger.log_checkin_start('manual', 'admin')
    logger.log_account_result(session_id, 'test@example.com', 'success', '签到成功', 2000)
    logger.log_checkin_end(session_id, email_sent=True)

    # 获取统计
    stats = logger.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))