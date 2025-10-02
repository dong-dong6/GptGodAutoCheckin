import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from unified_db_manager import get_db


class PointsHistoryManager:
    """积分历史记录管理器"""

    def __init__(self):
        """初始化数据库管理器

        使用统一数据库管理器(gptgod_checkin.db)
        """
        self.db = get_db()  # 使用统一数据库


    def record_exists(self, record_id):
        """检查记录是否已存在

        Args:
            record_id: 记录ID

        Returns:
            bool: 记录是否存在
        """
        result = self.db.execute_one(
            'SELECT id FROM points_history WHERE id = ?',
            (record_id,)
        )
        return result is not None

    def add_record(self, record_data, email=None):
        """添加一条积分记录

        Args:
            record_data: API返回的记录数据
            email: 账号邮箱
        """
        with self.db.get_connection() as conn:
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

                return True

            except Exception as e:
                logging.error(f"添加记录失败: {e}")
                raise  # 让上下文管理器处理回滚

    def batch_add_records(self, records, email=None):
        """批量添加积分记录

        Args:
            records: 记录列表
            email: 账号邮箱
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            added_count = 0
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

            logging.info(f"成功添加 {added_count} 条新记录")
            return added_count

    def get_latest_record_id(self, uid=None, email=None):
        """获取最新记录的ID

        Args:
            uid: 用户ID
            email: 账号邮箱
        """
        try:
            if uid:
                result = self.db.execute_one(
                    'SELECT MAX(id) FROM points_history WHERE uid = ?',
                    (uid,)
                )
            elif email:
                result = self.db.execute_one(
                    'SELECT MAX(id) FROM points_history WHERE email = ?',
                    (email,)
                )
            else:
                result = self.db.execute_one('SELECT MAX(id) FROM points_history')

            return result[0] if result and result[0] else 0

        except Exception as e:
            logging.error(f"获取最新记录ID失败: {e}")
            return 0

    def get_records_by_email(self, email, limit=100):
        """获取指定邮箱的积分记录

        Args:
            email: 邮箱地址
            limit: 返回记录数限制
        """
        results = self.db.execute('''
            SELECT id, uid, email, tokens, source, remark, ip, create_time, api_id
            FROM points_history
            WHERE email = ?
            ORDER BY create_time DESC
            LIMIT ?
        ''', (email, limit))

        records = []
        for row in results:
            records.append({
                'id': row[0],
                'uid': row[1],
                'email': row[2],
                'tokens': row[3],
                'source': row[4],
                'remark': row[5],
                'ip': row[6],
                'create_time': row[7],
                'api_id': row[8]
            })

        return records

    def get_uid_by_email(self, email):
        """根据邮箱获取UID"""
        result = self.db.execute_one(
            'SELECT uid FROM account_mapping WHERE email = ?',
            (email,)
        )
        return result[0] if result else None

    def get_statistics(self, email=None, uid=None):
        """获取统计信息

        Args:
            email: 如果指定，则获取该邮箱的统计
            uid: 如果指定，则获取该用户ID的统计
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 构建查询条件
            where_clause = ""
            params = []
            if email:
                where_clause = " WHERE email = ?"
                params.append(email)
            elif uid:
                where_clause = " WHERE uid = ?"
                params.append(uid)

            # 获取总记录数和总积分
            cursor.execute(f'''
                SELECT
                    COUNT(*) as total_count,
                    SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as total_earned,
                    SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as total_spent,
                    SUM(tokens) as net_points,
                    MIN(create_time) as first_record,
                    MAX(create_time) as last_record
                FROM points_history
                {where_clause}
            ''', params)

            result = cursor.fetchone()

            # 获取各来源统计
            cursor.execute(f'''
                SELECT
                    source,
                    COUNT(*) as count,
                    SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                    SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as spent
                FROM points_history
                {where_clause}
                GROUP BY source
            ''', params)

            source_stats = {}
            for row in cursor.fetchall():
                source_stats[row[0]] = {
                    'count': row[1],
                    'earned': row[2] or 0,
                    'spent': row[3] or 0
                }

            # 如果没有指定email或uid，获取总账户数
            if not email and not uid:
                cursor.execute('SELECT COUNT(DISTINCT email) FROM points_history')
                total_accounts = cursor.fetchone()[0] or 0
            else:
                total_accounts = 1

            return {
                'total_count': result[0] or 0,
                'total_earned': result[1] or 0,
                'total_spent': result[2] or 0,
                'net_points': result[3] or 0,
                'first_record': result[4],
                'last_record': result[5],
                'total_accounts': total_accounts,
                'by_source': source_stats,
                # 兼容旧字段名
                'total_records': result[0] or 0,
                'total_points': result[3] or 0,
                'earned_sources': source_stats  # 兼容前端期待的字段名
            }

    def get_daily_summary(self, days=30, email=None, uid=None):
        """获取每日积分汇总

        Args:
            days: 统计天数
            email: 如果指定，则获取该邮箱的汇总
            uid: 如果指定，则获取该用户ID的汇总
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 构建查询条件
            where_conditions = ["DATE(create_time) >= ?"]
            params = [cutoff_date]

            if email:
                where_conditions.append("email = ?")
                params.append(email)
            elif uid:
                where_conditions.append("uid = ?")
                params.append(uid)

            where_clause = " WHERE " + " AND ".join(where_conditions)

            if email or uid:
                cursor.execute(f'''
                    SELECT
                        DATE(create_time) as date,
                        SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                        SUM(CASE WHEN tokens < 0 THEN -tokens ELSE 0 END) as spent,
                        SUM(tokens) as net,
                        COUNT(*) as transactions
                    FROM points_history
                    {where_clause}
                    GROUP BY DATE(create_time)
                    ORDER BY date DESC
                ''', params)
            else:
                cursor.execute(f'''
                    SELECT
                        DATE(create_time) as date,
                        SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                        SUM(CASE WHEN tokens < 0 THEN -tokens ELSE 0 END) as spent,
                        SUM(tokens) as net,
                        COUNT(*) as transactions,
                        COUNT(DISTINCT email) as accounts_count
                    FROM points_history
                    {where_clause}
                    GROUP BY DATE(create_time)
                    ORDER BY date DESC
                ''', params)

            results = cursor.fetchall()

            if email or uid:
                return [
                    {
                        'date': row[0],
                        'earned': row[1] or 0,
                        'spent': row[2] or 0,
                        'net': row[3] or 0,
                        'transactions': row[4]
                    }
                    for row in results
                ]
            else:
                return [
                    {
                        'date': row[0],
                        'earned': row[1] or 0,
                        'spent': row[2] or 0,
                        'net': row[3] or 0,
                        'transactions': row[4],
                        'accounts': row[5]
                    }
                    for row in results
                ]

    def cleanup_old_records(self, days_to_keep=365):
        """清理旧记录

        Args:
            days_to_keep: 保留最近多少天的记录
        """
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')

        deleted = self.db.execute('''
            DELETE FROM points_history
            WHERE DATE(create_time) < ?
        ''', (cutoff_date,))

        logging.info(f"已清理 {deleted} 条旧记录")
        return deleted


# 使用示例
