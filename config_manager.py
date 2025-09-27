import json
import sqlite3
from datetime import datetime
from pathlib import Path
import logging
import yaml
import os


class ConfigManager:
    """配置管理器 - 统一管理应用配置参数"""

    def __init__(self, data_dir='accounts_data'):
        """初始化配置管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db_file = self.data_dir / 'config.db'
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

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
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''')

            conn.commit()
            logging.info("配置数据库表初始化完成")

    def migrate_from_yaml(self, yaml_file_path='account.yml'):
        """从YAML文件迁移配置到数据库

        Args:
            yaml_file_path: YAML配置文件路径
        """
        if not os.path.exists(yaml_file_path):
            logging.warning(f"YAML配置文件 {yaml_file_path} 不存在")
            return False

        try:
            with open(yaml_file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # 迁移域名配置
                if 'domains' in config:
                    domains = config['domains']
                    cursor.execute('''
                        INSERT OR REPLACE INTO domain_config (id, primary_domain, backup_domain, auto_switch)
                        VALUES (1, ?, ?, ?)
                    ''', (
                        domains.get('primary', 'gptgod.work'),
                        domains.get('backup', 'gptgod.online'),
                        domains.get('auto_switch', True)
                    ))

                # 迁移定时任务配置
                if 'schedule' in config:
                    schedule = config['schedule']
                    times_json = json.dumps(schedule.get('times', ['09:00']))
                    cursor.execute('''
                        INSERT OR REPLACE INTO schedule_config (id, enabled, schedule_times)
                        VALUES (1, ?, ?)
                    ''', (schedule.get('enabled', True), times_json))

                # 迁移SMTP配置
                if 'smtp' in config:
                    smtp = config['smtp']
                    emails_json = json.dumps(smtp.get('receiver_emails', []))
                    cursor.execute('''
                        INSERT OR REPLACE INTO smtp_config (id, enabled, server, port, sender_email, sender_password, receiver_emails)
                        VALUES (1, ?, ?, ?, ?, ?, ?)
                    ''', (
                        smtp.get('enabled', False),
                        smtp.get('server', 'smtp.gmail.com'),
                        smtp.get('port', 587),
                        smtp.get('sender_email', ''),
                        smtp.get('sender_password', ''),
                        emails_json
                    ))

                # 迁移Web认证配置
                if 'web_auth' in config:
                    web_auth = config['web_auth']
                    cursor.execute('''
                        INSERT OR REPLACE INTO web_auth_config (id, enabled, username, password, api_token)
                        VALUES (1, ?, ?, ?, ?)
                    ''', (
                        web_auth.get('enabled', True),
                        web_auth.get('username', 'admin'),
                        web_auth.get('password', 'admin123'),
                        web_auth.get('api_token', '')
                    ))

                # 迁移账号配置
                if 'account' in config and isinstance(config['account'], list):
                    # 先清空现有账号
                    cursor.execute('DELETE FROM account_config')

                    # 插入新账号
                    for account in config['account']:
                        if 'mail' in account and 'password' in account:
                            cursor.execute('''
                                INSERT INTO account_config (email, password)
                                VALUES (?, ?)
                            ''', (account['mail'], account['password']))

                conn.commit()
                logging.info("YAML配置迁移完成")
                return True

        except Exception as e:
            logging.error(f"迁移配置失败: {e}")
            return False

    def get_domain_config(self):
        """获取域名配置"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT primary_domain, backup_domain, auto_switch FROM domain_config WHERE id = 1')
            result = cursor.fetchone()

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
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT enabled, schedule_times FROM schedule_config WHERE id = 1')
            result = cursor.fetchone()

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
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, server, port, sender_email, sender_password, receiver_emails
                FROM smtp_config WHERE id = 1
            ''')
            result = cursor.fetchone()

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
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT enabled, username, password, api_token FROM web_auth_config WHERE id = 1')
            result = cursor.fetchone()

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
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email, password FROM account_config WHERE enabled = 1')
            results = cursor.fetchall()

            accounts = []
            for result in results:
                accounts.append({
                    'mail': result[0],
                    'password': result[1]
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
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO domain_config (id, primary_domain, backup_domain, auto_switch, updated_at)
                VALUES (1, ?, ?, ?, datetime('now'))
            ''', (primary, backup, auto_switch))
            conn.commit()

    def update_schedule_config(self, enabled, times):
        """更新定时任务配置"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            times_json = json.dumps(times)
            cursor.execute('''
                INSERT OR REPLACE INTO schedule_config (id, enabled, schedule_times, updated_at)
                VALUES (1, ?, ?, datetime('now'))
            ''', (enabled, times_json))
            conn.commit()

    def update_smtp_config(self, enabled, server, port, sender_email, sender_password, receiver_emails):
        """更新SMTP配置"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            emails_json = json.dumps(receiver_emails)
            cursor.execute('''
                INSERT OR REPLACE INTO smtp_config (id, enabled, server, port, sender_email, sender_password, receiver_emails, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (enabled, server, port, sender_email, sender_password, emails_json))
            conn.commit()

    def update_web_auth_config(self, enabled, username, password, api_token=''):
        """更新Web认证配置"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO web_auth_config (id, enabled, username, password, api_token, updated_at)
                VALUES (1, ?, ?, ?, ?, datetime('now'))
            ''', (enabled, username, password, api_token))
            conn.commit()

    def add_account(self, email, password):
        """添加账号"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO account_config (email, password, updated_at)
                VALUES (?, ?, datetime('now'))
            ''', (email, password))
            conn.commit()

    def remove_account(self, email):
        """删除账号"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM account_config WHERE email = ?', (email,))
            conn.commit()

    def disable_account(self, email):
        """禁用账号"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE account_config SET enabled = 0 WHERE email = ?', (email,))
            conn.commit()

    def enable_account(self, email):
        """启用账号"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE account_config SET enabled = 1 WHERE email = ?', (email,))
            conn.commit()


# 使用示例
if __name__ == '__main__':
    config_manager = ConfigManager()

    # 从YAML迁移配置
    if config_manager.migrate_from_yaml('account.yml'):
        print("配置迁移成功")

        # 获取所有配置
        all_config = config_manager.get_all_config()
        print("迁移后的配置:")
        print(json.dumps(all_config, indent=2, ensure_ascii=False))
    else:
        print("配置迁移失败")