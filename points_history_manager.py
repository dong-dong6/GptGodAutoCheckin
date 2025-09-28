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

    def get_statistics(self, email=None):
        """获取统计信息

        Args:
            email: 如果指定，则获取该邮箱的统计；否则获取全部统计
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            if email:
                # 获取指定邮箱的统计
                cursor.execute('''
                    SELECT
                        COUNT(*) as total_records,
                        SUM(tokens) as total_points,
                        MIN(create_time) as first_record,
                        MAX(create_time) as last_record
                    FROM points_history
                    WHERE email = ?
                ''', (email,))
            else:
                # 获取全部统计
                cursor.execute('''
                    SELECT
                        COUNT(*) as total_records,
                        SUM(tokens) as total_points,
                        COUNT(DISTINCT email) as total_accounts,
                        MIN(create_time) as first_record,
                        MAX(create_time) as last_record
                    FROM points_history
                ''')

            result = cursor.fetchone()

            if email:
                return {
                    'email': email,
                    'total_records': result[0] or 0,
                    'total_points': result[1] or 0,
                    'first_record': result[2],
                    'last_record': result[3]
                }
            else:
                return {
                    'total_records': result[0] or 0,
                    'total_points': result[1] or 0,
                    'total_accounts': result[2] or 0,
                    'first_record': result[3],
                    'last_record': result[4]
                }

    def get_daily_summary(self, days=30, email=None):
        """获取每日积分汇总

        Args:
            days: 统计天数
            email: 如果指定，则获取该邮箱的汇总
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            if email:
                cursor.execute('''
                    SELECT
                        DATE(create_time) as date,
                        SUM(tokens) as daily_points,
                        COUNT(*) as records_count
                    FROM points_history
                    WHERE email = ? AND DATE(create_time) >= ?
                    GROUP BY DATE(create_time)
                    ORDER BY date DESC
                ''', (email, cutoff_date))
            else:
                cursor.execute('''
                    SELECT
                        DATE(create_time) as date,
                        SUM(tokens) as daily_points,
                        COUNT(*) as records_count,
                        COUNT(DISTINCT email) as accounts_count
                    FROM points_history
                    WHERE DATE(create_time) >= ?
                    GROUP BY DATE(create_time)
                    ORDER BY date DESC
                ''', (cutoff_date,))

            results = cursor.fetchall()

            if email:
                return [
                    {
                        'date': row[0],
                        'points': row[1],
                        'records': row[2]
                    }
                    for row in results
                ]
            else:
                return [
                    {
                        'date': row[0],
                        'points': row[1],
                        'records': row[2],
                        'accounts': row[3]
                    }
                    for row in results
                ]

    def export_to_json(self, output_file='points_history_export.json'):
        """导出所有积分历史到JSON文件"""
        results = self.db.execute('''
            SELECT id, uid, email, tokens, source, remark, ip, create_time, api_id
            FROM points_history
            ORDER BY create_time DESC
        ''')

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

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logging.info(f"已导出 {len(records)} 条记录到 {output_file}")
        return len(records)

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
if __name__ == '__main__':
    manager = PointsHistoryManager()

    # 获取统计
    stats = manager.get_statistics()
    print(f"总统计: {stats}")

    # 获取每日汇总
    daily = manager.get_daily_summary(days=7)
    for day in daily:
        print(f"{day['date']}: {day['points']} 积分")

    # 导出数据
    manager.export_to_json()