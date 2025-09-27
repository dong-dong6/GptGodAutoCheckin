import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

class PointsHistoryManager:
    """积分历史记录管理器"""

    def __init__(self, db_path='accounts_data/points_history.db'):
        """初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

        # 初始化数据库
        self.init_database()

    def init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 创建积分历史表
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

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_uid ON points_history (uid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON points_history (email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_create_time ON points_history (create_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON points_history (source)')

        # 创建账号映射表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_mapping (
                uid INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                last_update TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def add_record(self, record_data, email=None):
        """添加一条积分记录

        Args:
            record_data: API返回的记录数据
            email: 账号邮箱
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # 检查记录是否已存在
            cursor.execute('SELECT id FROM points_history WHERE id = ?', (record_data['id'],))
            if cursor.fetchone():
                return False  # 记录已存在

            # 解析IP地址
            ip = None
            try:
                remark = record_data.get('remark', '')
                if remark:
                    import json
                    remark_data = json.loads(remark)
                    ip = remark_data.get('ip')
            except:
                pass

            # 插入新记录
            cursor.execute('''
                INSERT INTO points_history (id, uid, email, tokens, source, remark, ip, create_time, api_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_data['id'],
                record_data['uid'],
                email,
                record_data['tokens'],
                record_data['source'],
                record_data.get('remark', ''),
                ip,
                record_data['create_time'],
                record_data.get('api_id', 0)
            ))

            # 更新账号映射
            if email:
                cursor.execute('''
                    INSERT OR REPLACE INTO account_mapping (uid, email, last_update)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (record_data['uid'], email))

            conn.commit()
            return True

        except Exception as e:
            logging.error(f"添加记录失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def batch_add_records(self, records, email=None):
        """批量添加积分记录

        Args:
            records: 记录列表
            email: 账号邮箱
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        added_count = 0
        try:
            for record in records:
                # 检查记录是否已存在
                cursor.execute('SELECT id FROM points_history WHERE id = ?', (record['id'],))
                if cursor.fetchone():
                    continue  # 跳过已存在的记录

                # 解析IP地址
                ip = None
                try:
                    remark = record.get('remark', '')
                    if remark:
                        import json
                        remark_data = json.loads(remark)
                        ip = remark_data.get('ip')
                except:
                    pass

                # 插入新记录
                cursor.execute('''
                    INSERT INTO points_history (id, uid, email, tokens, source, remark, ip, create_time, api_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['id'],
                    record['uid'],
                    email,
                    record['tokens'],
                    record['source'],
                    record.get('remark', ''),
                    ip,
                    record['create_time'],
                    record.get('api_id', 0)
                ))
                added_count += 1

            # 更新账号映射
            if email and records:
                uid = records[0]['uid']
                cursor.execute('''
                    INSERT OR REPLACE INTO account_mapping (uid, email, last_update)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (uid, email))

            conn.commit()
            logging.info(f"成功添加 {added_count} 条新记录")
            return added_count

        except Exception as e:
            logging.error(f"批量添加记录失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def get_latest_record_id(self, uid=None, email=None):
        """获取最新记录的ID

        Args:
            uid: 用户ID
            email: 账号邮箱
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            if uid:
                cursor.execute('SELECT MAX(id) FROM points_history WHERE uid = ?', (uid,))
            elif email:
                cursor.execute('SELECT MAX(id) FROM points_history WHERE email = ?', (email,))
            else:
                cursor.execute('SELECT MAX(id) FROM points_history')

            result = cursor.fetchone()
            return result[0] if result and result[0] else 0

        finally:
            conn.close()

    def get_account_history(self, email=None, uid=None, days=30, source_filter=None):
        """获取账号积分历史

        Args:
            email: 账号邮箱
            uid: 用户ID
            days: 查询天数
            source_filter: 来源过滤 (checkin, api, cdkey, invite等)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # 构建查询条件
            conditions = []
            params = []

            if uid:
                conditions.append('uid = ?')
                params.append(uid)
            elif email:
                conditions.append('email = ?')
                params.append(email)

            if days:
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                conditions.append('create_time >= ?')
                params.append(cutoff_date)

            if source_filter:
                if isinstance(source_filter, list):
                    placeholders = ','.join(['?'] * len(source_filter))
                    conditions.append(f'source IN ({placeholders})')
                    params.extend(source_filter)
                else:
                    conditions.append('source = ?')
                    params.append(source_filter)

            # 执行查询
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            query = f'''
                SELECT id, uid, email, tokens, source, remark, create_time, api_id
                FROM points_history
                WHERE {where_clause}
                ORDER BY create_time DESC
            '''

            cursor.execute(query, params)

            # 格式化结果
            columns = ['id', 'uid', 'email', 'tokens', 'source', 'remark', 'create_time', 'api_id']
            records = []
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                records.append(record)

            return records

        finally:
            conn.close()

    def record_exists(self, record_id):
        """检查记录是否已存在

        Args:
            record_id: 记录ID

        Returns:
            bool: True if exists, False otherwise
        """
        if not record_id:
            return False

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM points_history WHERE id = ?', (record_id,))
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

    def check_duplicate_record(self, email, tokens, source, create_time):
        """检查是否存在重复记录

        Args:
            email: 账号邮箱
            tokens: 积分数量
            source: 来源
            create_time: 创建时间

        Returns:
            bool: True if duplicate exists, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # 检查是否存在相同的记录（基于邮箱、积分、来源、时间）
            cursor.execute('''
                SELECT COUNT(*) FROM points_history
                WHERE email = ? AND tokens = ? AND source = ? AND create_time = ?
            ''', (email, tokens, source, create_time))

            count = cursor.fetchone()[0]
            return count > 0

        finally:
            conn.close()

    def get_statistics(self, email=None, uid=None):
        """获取账号积分统计

        Args:
            email: 账号邮箱
            uid: 用户ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # 构建查询条件
            condition = ''
            param = None
            if uid:
                condition = 'WHERE uid = ?'
                param = uid
            elif email:
                condition = 'WHERE email = ?'
                param = email

            # 统计各来源积分 - 分别统计获得和消耗
            query = f'''
                SELECT
                    source,
                    COUNT(*) as count,
                    SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                    SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as spent
                FROM points_history
                {condition}
                GROUP BY source
            '''

            if param:
                cursor.execute(query, (param,))
            else:
                cursor.execute(query)

            source_stats = {}
            # 分别存储获得积分来源和消耗积分来源
            earned_sources = {}
            spent_sources = {}

            for row in cursor.fetchall():
                source, count, earned, spent = row
                source_stats[row[0]] = {
                    'count': row[1],
                    'earned': row[2],
                    'spent': row[3]
                }

                # 如果有获得积分，加入获得来源
                if earned > 0:
                    earned_sources[source] = {
                        'count': count if earned > 0 else 0,
                        'earned': earned,
                        'spent': 0
                    }

                # 如果有消耗积分，加入消耗来源
                if spent > 0:
                    spent_sources[source] = {
                        'count': count if spent > 0 else 0,
                        'earned': 0,
                        'spent': spent
                    }

            # 获取总计
            query = f'''
                SELECT
                    COUNT(*) as total_count,
                    SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as total_earned,
                    SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as total_spent,
                    SUM(tokens) as net_points
                FROM points_history
                {condition}
            '''

            if param:
                cursor.execute(query, (param,))
            else:
                cursor.execute(query)

            result = cursor.fetchone()

            return {
                'total_count': result[0] or 0,
                'total_earned': result[1] or 0,
                'total_spent': result[2] or 0,
                'net_points': result[3] or 0,
                'by_source': source_stats,
                'earned_sources': earned_sources,  # 新增：只包含获得积分的来源
                'spent_sources': spent_sources    # 新增：只包含消耗积分的来源
            }

        finally:
            conn.close()

    def get_daily_summary(self, email=None, uid=None, days=30):
        """获取每日积分汇总

        Args:
            email: 账号邮箱
            uid: 用户ID
            days: 统计天数
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # 构建查询条件
            conditions = []
            params = []

            if uid:
                conditions.append('uid = ?')
                params.append(uid)
            elif email:
                conditions.append('email = ?')
                params.append(email)

            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            conditions.append('create_time >= ?')
            params.append(cutoff_date)

            where_clause = ' AND '.join(conditions) if conditions else '1=1'

            # 按日汇总
            query = f'''
                SELECT
                    DATE(create_time) as date,
                    SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                    SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as spent,
                    SUM(tokens) as net,
                    COUNT(*) as transactions
                FROM points_history
                WHERE {where_clause}
                GROUP BY DATE(create_time)
                ORDER BY date DESC
            '''

            cursor.execute(query, params)

            daily_summary = []
            for row in cursor.fetchall():
                daily_summary.append({
                    'date': row[0],
                    'earned': row[1] or 0,
                    'spent': row[2] or 0,
                    'net': row[3] or 0,
                    'transactions': row[4] or 0
                })

            return daily_summary

        finally:
            conn.close()

    def export_to_json(self, output_file='points_history_export.json', email=None, uid=None):
        """导出数据到JSON文件

        Args:
            output_file: 输出文件名
            email: 账号邮箱（可选，用于过滤）
            uid: 用户ID（可选，用于过滤）
        """
        records = self.get_account_history(email=email, uid=uid, days=None)
        statistics = self.get_statistics(email=email, uid=uid)

        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_records': len(records),
            'statistics': statistics,
            'records': records
        }

        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logging.info(f"数据已导出到 {output_path}")
        return str(output_path)


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    manager = PointsHistoryManager()

    # 测试数据
    test_record = {
        'id': 12345,
        'uid': 23477,
        'tokens': 2000,
        'source': 'checkin',
        'remark': '{"ip":"127.0.0.1"}',
        'create_time': '2025-09-23 13:46:08',
        'api_id': 0
    }

    # 添加记录
    manager.add_record(test_record, email='test@example.com')

    # 获取统计
    stats = manager.get_statistics(email='test@example.com')
    print("统计信息:", stats)

    # 获取历史
    history = manager.get_account_history(email='test@example.com', days=30)
    print(f"历史记录: {len(history)} 条")