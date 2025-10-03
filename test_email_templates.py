#!/usr/bin/env python3
"""
测试新的邮件模板功能
"""
import sys
import os
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_email_templates():
    """测试邮件模板"""
    try:
        from infrastructure.notification.email_service import EmailService

        # 模拟SMTP配置
        smtp_config = {
            'enabled': False,  # 设置为False避免实际发送
            'server': 'smtp.gmail.com',
            'port': 587,
            'sender_email': 'test@example.com',
            'sender_password': 'password',
            'receiver_emails': ['admin@example.com']
        }

        email_service = EmailService(smtp_config)

        print("=== 测试个人邮件模板 ===")

        # 模拟成功签到结果
        success_result = {
            'email': 'user@example.com',
            'success': True,
            'message': '签到成功，获得5积分',
            'current_points': 1025,
            'domain': 'gptgod.online',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print("成功签到邮件模板:")
        print("-" * 50)
        # 由于邮件服务未启用，这里会返回False，但我们主要是想看看模板是否正确构建
        result = email_service.send_personal_checkin_notification(success_result)
        print(f"发送结果: {result}")

        # 模拟失败签到结果
        fail_result = {
            'email': 'user@example.com',
            'success': False,
            'message': '登录失败：账号或密码错误',
            'current_points': 0,
            'domain': 'gptgod.online',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print("\n失败签到邮件模板:")
        print("-" * 50)
        result = email_service.send_personal_checkin_notification(fail_result)
        print(f"发送结果: {result}")

        print("\n=== 测试全局邮件模板 ===")

        # 模拟多个账号结果
        global_results = {
            'results': [
                {
                    'email': 'user1@example.com',
                    'success': True,
                    'message': '签到成功，获得5积分',
                    'current_points': 1025,
                    'domain': 'gptgod.online'
                },
                {
                    'email': 'user2@example.com',
                    'success': False,
                    'message': '登录失败：账号或密码错误',
                    'current_points': 0,
                    'domain': 'gptgod.online'
                },
                {
                    'email': 'user3@example.com',
                    'success': True,
                    'message': '签到成功，获得5积分',
                    'current_points': 580,
                    'domain': 'gptgod.work'
                }
            ]
        }

        print("全局汇总邮件模板:")
        print("-" * 50)
        result = email_service.send_checkin_notification(
            global_results,
            success_count=2,
            failed_count=1
        )
        print(f"发送结果: {result}")

        print("\n✅ 邮件模板测试完成")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def show_email_config_info():
    """显示邮件配置信息"""
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path("accounts_data/gptgod_checkin.db")
        if not db_path.exists():
            print("❌ 数据库文件不存在")
            return

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print("\n=== 当前邮件配置状态 ===")

        # 检查账号配置
        cursor.execute("SELECT email, send_email_notification FROM account_config WHERE enabled = 1")
        accounts = cursor.fetchall()

        print("账号邮件通知配置:")
        personal_accounts = []
        for email, send_email in accounts:
            if send_email:
                personal_accounts.append(email)
                print(f"  ✅ {email} - 启用个人邮件")
            else:
                print(f"  ❌ {email} - 未启用")

        # 检查SMTP配置
        cursor.execute("SELECT key, value FROM system_config WHERE key LIKE 'smtp_%'")
        smtp_configs = dict(cursor.fetchall())

        print("\nSMTP配置:")
        if not smtp_configs:
            print("  ❌ 未配置SMTP")
        else:
            enabled = smtp_configs.get('smtp_enabled', 'false') == 'true'
            server = smtp_configs.get('smtp_server', '')
            port = smtp_configs.get('smtp_port', '')
            sender = smtp_configs.get('smtp_sender_email', '')
            receivers = smtp_configs.get('smtp_receiver_emails', '')

            print(f"  启用状态: {'✅ 启用' if enabled else '❌ 禁用'}")
            print(f"  服务器: {server}")
            print(f"  端口: {port}")
            print(f"  发件人: {sender}")
            print(f"  收件人: {receivers}")

        conn.close()

        print(f"\n=== 邮件发送预期效果 ===")
        print(f"个人邮件将发送给 {len(personal_accounts)} 个账号:")
        for email in personal_accounts:
            print(f"  - {email}")

        if smtp_configs:
            print(f"全局邮件将发送给系统配置的收件人")
        else:
            print("❌ 未配置SMTP，无法发送邮件")

    except Exception as e:
        print(f"❌ 检查配置失败: {e}")

if __name__ == "__main__":
    print("GPT-GOD 邮件模板测试")
    print("=" * 50)

    # 显示当前配置
    show_email_config_info()

    # 测试邮件模板
    test_email_templates()

    print("\n" + "=" * 50)
    print("测试完成！")