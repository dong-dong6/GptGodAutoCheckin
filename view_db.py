#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查看数据库中的积分历史数据
"""

import sqlite3
from datetime import datetime
from pathlib import Path

def view_database_info():
    """查看数据库详细信息"""
    db_path = Path('accounts_data/points_history.db')

    if not db_path.exists():
        print("数据库文件不存在！")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("=" * 60)
    print("GPT-GOD 积分历史数据库信息")
    print("=" * 60)

    # 1. 数据库文件信息
    file_size = db_path.stat().st_size / 1024  # KB
    print(f"\n📁 数据库文件: {db_path}")
    print(f"   文件大小: {file_size:.2f} KB")

    # 2. 表结构信息
    print("\n📋 数据库表结构:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   - {table_name}: {count} 条记录")

        # 显示表的列信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"      • {col[1]} ({col[2]})")

    # 3. 积分历史统计
    print("\n📊 积分历史统计:")

    # 总记录数
    cursor.execute("SELECT COUNT(*) FROM points_history")
    total_records = cursor.fetchone()[0]
    print(f"   总记录数: {total_records}")

    if total_records > 0:
        # 账号数量
        cursor.execute("SELECT COUNT(DISTINCT email) FROM points_history WHERE email IS NOT NULL")
        account_count = cursor.fetchone()[0]
        print(f"   账号数量: {account_count}")

        # 时间范围
        cursor.execute("SELECT MIN(create_time), MAX(create_time) FROM points_history")
        min_time, max_time = cursor.fetchone()
        print(f"   时间范围: {min_time} ~ {max_time}")

        # 积分统计
        cursor.execute("""
            SELECT
                SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as spent,
                SUM(tokens) as net
            FROM points_history
        """)
        earned, spent, net = cursor.fetchone()
        print(f"   总获得积分: {earned or 0}")
        print(f"   总消耗积分: {spent or 0}")
        print(f"   净积分: {net or 0}")

        # 按来源统计
        print("\n📈 按来源分类:")
        cursor.execute("""
            SELECT
                source,
                COUNT(*) as count,
                SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
                SUM(CASE WHEN tokens < 0 THEN ABS(tokens) ELSE 0 END) as spent
            FROM points_history
            GROUP BY source
            ORDER BY count DESC
        """)
        sources = cursor.fetchall()
        for source, count, earned, spent in sources:
            print(f"   {source}:")
            print(f"      次数: {count}, 获得: {earned or 0}, 消耗: {spent or 0}")

        # 最近的记录
        print("\n📝 最近5条记录:")
        cursor.execute("""
            SELECT id, email, tokens, source, create_time
            FROM points_history
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_records = cursor.fetchall()
        for record in recent_records:
            id, email, tokens, source, create_time = record
            email_display = email if email else "N/A"
            print(f"   [{id}] {create_time} | {email_display}")
            print(f"        {source}: {'+' if tokens > 0 else ''}{tokens} 积分")

        # 各账号统计
        if account_count > 0:
            print("\n👥 各账号统计:")
            cursor.execute("""
                SELECT
                    email,
                    COUNT(*) as record_count,
                    SUM(tokens) as total_points,
                    MAX(create_time) as last_activity
                FROM points_history
                WHERE email IS NOT NULL
                GROUP BY email
                ORDER BY total_points DESC
            """)
            accounts = cursor.fetchall()
            for email, record_count, total_points, last_activity in accounts:
                print(f"   {email}:")
                print(f"      记录数: {record_count}, 总积分: {total_points}")
                print(f"      最后活动: {last_activity}")

    # 4. 索引信息
    print("\n🔍 数据库索引:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    for index in indexes:
        if not index[0].startswith('sqlite_'):
            print(f"   - {index[0]}")

    conn.close()

    print("\n" + "=" * 60)
    print("💡 提示:")
    print("  1. 运行 fetch_history.bat 获取完整历史记录")
    print("  2. 每次签到会自动更新最新记录")
    print("  3. 数据永久保存在本地SQLite数据库中")
    print("=" * 60)

if __name__ == '__main__':
    view_database_info()