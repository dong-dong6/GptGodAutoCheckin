#!/usr/bin/env python3
"""
测试数据库中的配置
"""
import sqlite3
import os
from pathlib import Path

def check_database():
    """检查数据库配置"""
    db_path = Path("accounts_data/gptgod_checkin.db")

    if not db_path.exists():
        print("X 数据库文件不存在")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print("=== 检查账号配置 ===")
        cursor.execute("SELECT email, send_email_notification FROM account_config WHERE enabled = 1")
        accounts = cursor.fetchall()

        if not accounts:
            print("X 没有找到启用的账号")
            return False

        print(f"+ 找到 {len(accounts)} 个启用的账号")

        email_enabled_count = 0
        for email, send_email in accounts:
            if send_email:
                email_enabled_count += 1
                print(f"  [邮件] {email} (已启用邮件通知)")
            else:
                print(f"  [账号] {email}")

        print(f"\n统计:")
        print(f"  总账号数: {len(accounts)}")
        print(f"  启用邮件通知: {email_enabled_count}")

        # 检查SMTP配置
        print("\n=== 检查SMTP配置 ===")
        cursor.execute("SELECT key, value FROM system_config WHERE key LIKE 'smtp_%'")
        smtp_configs = cursor.fetchall()

        if not smtp_configs:
            print("X 没有找到SMTP配置")
        else:
            print("+ SMTP配置:")
            for key, value in smtp_configs:
                if 'password' in key.lower():
                    print(f"  {key}: ***已配置***")
                else:
                    print(f"  {key}: {value}")

        conn.close()
        return True

    except Exception as e:
        print(f"X 数据库检查失败: {e}")
        return False

def check_recent_logs():
    """检查最近的签到日志"""
    db_path = Path("accounts_data/gptgod_checkin.db")

    if not db_path.exists():
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print("\n=== 检查最近的签到会话 ===")
        cursor.execute("""
            SELECT id, start_time, trigger_type, total_accounts, success_count, failed_count, email_sent
            FROM checkin_sessions
            ORDER BY start_time DESC
            LIMIT 5
        """)
        sessions = cursor.fetchall()

        if not sessions:
            print("❌ 没有找到签到会话记录")
        else:
            print("✅ 最近的签到会话:")
            for session in sessions:
                email_status = "✅已发送" if session[6] else "❌未发送"
                print(f"  会话{session[0]}: {session[1]} | {session[2]} | "
                      f"账号:{session[3]} | 成功:{session[4]} | 失败:{session[5]} | 邮件:{email_status}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 日志检查失败: {e}")
        return False

if __name__ == "__main__":
    print("GPT-GOD 系统配置检查")
    print("=" * 50)

    # 检查数据库
    if check_database():
        print("\n✅ 数据库检查通过")
    else:
        print("\n❌ 数据库检查失败")

    # 检查日志
    if check_recent_logs():
        print("✅ 日志检查通过")
    else:
        print("❌ 日志检查失败")

    print("\n" + "=" * 50)
    print("检查完成！")