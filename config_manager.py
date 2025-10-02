import json
from datetime import datetime
from pathlib import Path
import logging
import yaml
import os
from unified_db_manager import get_db


class ConfigManager:
    """配置管理器 - 统一管理应用配置参数"""

    def __init__(self, data_dir='accounts_data'):
        """初始化配置管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db = get_db()

    def get_domain_config(self):
        """获取域名配置"""
        result = self.db.execute_one(
            'SELECT primary_domain, backup_domain, auto_switch FROM domain_config WHERE id = 1'
        )

        if result:
            return {
                'primary': result[0],
                'backup': result[1],
                'auto_switch': bool(result[2])
            }

        # 默认配置
        return {
            'primary': 'gptgod.work',
            'backup': 'gptgod.online',
            'auto_switch': True
        }

    def get_schedule_config(self):
        """获取定时任务配置"""
        result = self.db.execute_one(
            'SELECT enabled, schedule_times FROM schedule_config WHERE id = 1'
        )

        if result:
            return {
                'enabled': bool(result[0]),
                'times': json.loads(result[1])
            }

        # 默认配置
        return {
            'enabled': True,
            'times': ['09:00']
        }

    def get_smtp_config(self):
        """获取SMTP配置"""
        result = self.db.execute_one('''
            SELECT enabled, server, port, sender_email, sender_password, receiver_emails
            FROM smtp_config WHERE id = 1
        ''')

        if result:
            return {
                'enabled': bool(result[0]),
                'server': result[1],
                'port': result[2],
                'sender_email': result[3],
                'sender_password': result[4],
                'receiver_emails': json.loads(result[5])
            }

        # 默认配置
        return {
            'enabled': False,
            'server': 'smtp.gmail.com',
            'port': 587,
            'sender_email': '',
            'sender_password': '',
            'receiver_emails': []
        }

    def get_web_auth_config(self):
        """获取Web认证配置"""
        result = self.db.execute_one(
            'SELECT enabled, username, password, api_token FROM web_auth_config WHERE id = 1'
        )

        if result:
            return {
                'enabled': bool(result[0]),
                'username': result[1],
                'password': result[2],
                'api_token': result[3]
            }

        # 默认配置
        return {
            'enabled': True,
            'username': 'admin',
            'password': 'admin123',
            'api_token': ''
        }

    def get_accounts(self):
        """获取账号列表"""
        results = self.db.execute(
            'SELECT email, password, send_email_notification FROM account_config WHERE enabled = 1'
        )

        accounts = []
        for result in results:
            accounts.append({
                'mail': result[0],
                'password': result[1],
                'send_email_notification': bool(result[2])
            })

        return accounts

    def get_all_config(self):
        """获取所有配置，兼容原YAML格式"""
        return {
            'domains': self.get_domain_config(),
            'schedule': self.get_schedule_config(),
            'smtp': self.get_smtp_config(),
            'web_auth': self.get_web_auth_config(),
            'account': self.get_accounts()
        }

    def update_domain_config(self, primary, backup=None, auto_switch=True):
        """更新域名配置"""
        self.db.execute('''
            INSERT OR REPLACE INTO domain_config (id, primary_domain, backup_domain, auto_switch, updated_at)
            VALUES (1, ?, ?, ?, datetime('now'))
        ''', (primary, backup, auto_switch))

    def update_schedule_config(self, enabled, times):
        """更新定时任务配置"""
        times_json = json.dumps(times)
        self.db.execute('''
            INSERT OR REPLACE INTO schedule_config (id, enabled, schedule_times, updated_at)
            VALUES (1, ?, ?, datetime('now'))
        ''', (enabled, times_json))

    def update_smtp_config(self, enabled, server, port, sender_email, sender_password, receiver_emails):
        """更新SMTP配置"""
        emails_json = json.dumps(receiver_emails)
        self.db.execute('''
            INSERT OR REPLACE INTO smtp_config (id, enabled, server, port, sender_email, sender_password, receiver_emails, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (enabled, server, port, sender_email, sender_password, emails_json))

    def update_web_auth_config(self, enabled, username, password, api_token=''):
        """更新Web认证配置"""
        self.db.execute('''
            INSERT OR REPLACE INTO web_auth_config (id, enabled, username, password, api_token, updated_at)
            VALUES (1, ?, ?, ?, ?, datetime('now'))
        ''', (enabled, username, password, api_token))

    def add_account(self, email, password):
        """添加账号"""
        self.db.execute('''
            INSERT OR REPLACE INTO account_config (email, password, updated_at)
            VALUES (?, ?, datetime('now'))
        ''', (email, password))

    def remove_account(self, email):
        """删除账号"""
        self.db.execute('DELETE FROM account_config WHERE email = ?', (email,))

    def disable_account(self, email):
        """禁用账号"""
        self.db.execute('UPDATE account_config SET enabled = 0 WHERE email = ?', (email,))

    def enable_account(self, email):
        """启用账号"""
        self.db.execute('UPDATE account_config SET enabled = 1 WHERE email = ?', (email,))

    def update_account_email_notification(self, email, send_notification):
        """更新账号邮件通知设置

        Args:
            email: 账号邮箱
            send_notification: 是否发送邮件通知 (True/False)
        """
        self.db.execute('''
            UPDATE account_config
            SET send_email_notification = ?, updated_at = datetime('now')
            WHERE email = ?
        ''', (send_notification, email))


# 使用示例
