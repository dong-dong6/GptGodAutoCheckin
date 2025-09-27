import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

class DataManager:
    """统一的数据管理器，管理账号积分、签到记录等所有持久化数据"""

    def __init__(self, data_dir='accounts_data'):
        """初始化数据管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 创建子目录
        self.points_dir = self.data_dir / 'points'
        self.points_dir.mkdir(exist_ok=True)

        # 文件路径
        self.summary_file = self.data_dir / 'accounts_summary.json'
        self.points_history_file = self.data_dir / 'points_history.json'
        self.latest_snapshot_file = self.data_dir / 'latest_snapshot.json'  # 最新快照文件

        # 加载数据
        self.summary = self._load_summary()
        self.points_history = self._load_points_history()
        self.latest_snapshot = self._load_latest_snapshot()

    def _load_summary(self):
        """加载账户汇总数据"""
        if self.summary_file.exists():
            try:
                with open(self.summary_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载汇总数据失败: {e}")

        return {
            'accounts': {},  # 账户详细信息
            'total_points': 0,  # 所有账户总积分
            'last_update': None,  # 最后更新时间
            'statistics': {  # 统计信息
                'total_accounts': 0,
                'active_accounts': 0,
                'inactive_accounts': 0
            }
        }

    def _load_points_history(self):
        """加载积分历史记录"""
        if self.points_history_file.exists():
            try:
                with open(self.points_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载积分历史失败: {e}")

        return []  # 列表格式，每个元素包含时间戳和各账号积分

    def _save_summary(self):
        """保存汇总数据"""
        try:
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                json.dump(self.summary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存汇总数据失败: {e}")

    def _save_points_history(self):
        """保存积分历史"""
        try:
            # 只保留最近30天的历史记录
            if len(self.points_history) > 30 * 24:  # 假设每小时记录一次，30天约720条
                self.points_history = self.points_history[-720:]

            with open(self.points_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.points_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存积分历史失败: {e}")

    def _load_latest_snapshot(self):
        """加载最新快照数据"""
        if self.latest_snapshot_file.exists():
            try:
                with open(self.latest_snapshot_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载最新快照失败: {e}")

        return {
            'timestamp': None,
            'accounts': {},
            'total_points': 0,
            'last_checkin_time': None
        }

    def _save_latest_snapshot(self):
        """保存最新快照"""
        try:
            with open(self.latest_snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(self.latest_snapshot, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存最新快照失败: {e}")

    def update_account_info(self, email, user_data):
        """更新账户信息 - 只更新最新快照，不修改历史数据

        Args:
            email: 账号邮箱
            user_data: 从API获取的用户数据
        """
        if not user_data:
            return

        # 更新最新快照
        if email not in self.latest_snapshot['accounts']:
            self.latest_snapshot['accounts'][email] = {
                'email': email,
                'uid': None,
                'current_points': 0,
                'register_time': None,
                'last_login_time': None,
                'invite_code': None,
                'updated_at': None
            }

        account = self.latest_snapshot['accounts'][email]

        # 更新用户信息
        account['uid'] = user_data.get('uid')
        account['current_points'] = user_data.get('tokens', 0)
        account['register_time'] = user_data.get('register_time')
        account['last_login_time'] = user_data.get('last_login_time')
        account['invite_code'] = user_data.get('invite_code')
        account['updated_at'] = datetime.now().isoformat()

        # 更新总积分
        total_points = sum(acc['current_points'] for acc in self.latest_snapshot['accounts'].values())
        self.latest_snapshot['total_points'] = total_points
        self.latest_snapshot['timestamp'] = datetime.now().isoformat()
        self.latest_snapshot['last_checkin_time'] = datetime.now().isoformat()

        # 保存最新快照
        self._save_latest_snapshot()

        logging.info(f"更新账号 {email} 快照 - 积分: {account['current_points']}")

    def get_latest_snapshot_data(self):
        """获取最新快照数据用于Web展示

        Returns:
            dict: 最新的积分数据
        """
        if not self.latest_snapshot['accounts']:
            return {
                'total_points': 0,
                'accounts': [],
                'statistics': {
                    'total_accounts': 0,
                    'average_points': 0
                },
                'last_update': None
            }

        accounts_list = []
        total_points = self.latest_snapshot['total_points']

        for email, account in self.latest_snapshot['accounts'].items():
            points = account['current_points']
            percentage = (points / total_points * 100) if total_points > 0 else 0

            accounts_list.append({
                'email': email,
                'uid': account.get('uid'),
                'points': points,
                'percentage': round(percentage, 2)
            })

        # 按积分降序排序
        accounts_list.sort(key=lambda x: x['points'], reverse=True)

        return {
            'total_points': total_points,
            'accounts': accounts_list,
            'statistics': {
                'total_accounts': len(self.latest_snapshot['accounts']),
                'average_points': total_points / len(self.latest_snapshot['accounts']) if self.latest_snapshot['accounts'] else 0
            },
            'last_update': self.latest_snapshot.get('timestamp')
        }

    def record_checkin(self, email, success, points_earned=0):
        """记录签到信息 - 仅更新最新快照中的签到时间

        Args:
            email: 账号邮箱
            success: 是否签到成功
            points_earned: 获得的积分
        """
        # 这个方法现在只用于记录日志，实际数据更新在update_account_info中完成
        if success:
            logging.info(f"账号 {email} 签到成功，获得 {points_earned} 积分")

    def add_points_snapshot(self):
        """添加当前时刻的积分快照到历史记录（可选功能）"""
        if self.latest_snapshot['accounts']:
            snapshot = {
                'time': datetime.now().isoformat(),
                'total_points': self.latest_snapshot['total_points'],
                'accounts': {}
            }

            for email, account in self.latest_snapshot['accounts'].items():
                snapshot['accounts'][email] = {
                    'points': account['current_points'],
                    'uid': account.get('uid')
                }

            self.points_history.append(snapshot)
            self._save_points_history()

    def get_points_distribution(self):
        """获取积分分布情况 - 基于最新快照"""
        distribution = {
            '0-1000': 0,
            '1000-5000': 0,
            '5000-10000': 0,
            '10000-50000': 0,
            '50000-100000': 0,
            '100000+': 0
        }

        for email, account in self.latest_snapshot['accounts'].items():
            points = account['current_points']
            if points < 1000:
                distribution['0-1000'] += 1
            elif points < 5000:
                distribution['1000-5000'] += 1
            elif points < 10000:
                distribution['5000-10000'] += 1
            elif points < 50000:
                distribution['10000-50000'] += 1
            elif points < 100000:
                distribution['50000-100000'] += 1
            else:
                distribution['100000+'] += 1

        return distribution

    def get_accounts_points_detail(self):
        """获取各账号积分详细分布 - 基于最新快照"""
        return self.get_latest_snapshot_data()

    def get_top_accounts(self, limit=10):
        """获取积分最多的账户 - 基于最新快照"""
        accounts = []
        for email, account in self.latest_snapshot['accounts'].items():
            accounts.append({
                'email': email,
                'points': account['current_points'],
                'uid': account.get('uid')
            })

        # 按积分排序
        accounts.sort(key=lambda x: x['points'], reverse=True)
        return accounts[:limit]

    def get_points_trend(self, days=7):
        """获取积分趋势 - 从历史记录中提取

        Args:
            days: 最近几天的数据
        """
        if not self.points_history:
            return []

        # 获取最近N天的数据
        cutoff_time = datetime.now() - timedelta(days=days)
        trend = []

        for snapshot in self.points_history:
            try:
                snapshot_time = datetime.fromisoformat(snapshot['time'])
                if snapshot_time > cutoff_time:
                    trend.append({
                        'time': snapshot['time'],
                        'total_points': snapshot['total_points']
                    })
            except:
                continue

        return trend

# 使用示例
if __name__ == '__main__':
    manager = DataManager()

    # 模拟更新账户信息
    test_user_data = {
        'uid': 12345,
        'tokens': 5000,
        'register_time': '2024-01-01 10:00:00',
        'last_login_time': '2024-12-20 15:30:00',
        'invite_code': 'abc123'
    }

    manager.update_account_info('test@example.com', test_user_data)
    manager.record_checkin('test@example.com', True, 2000)

    # 获取统计
    print("积分分布:", manager.get_points_distribution())
    print("Top账户:", manager.get_top_accounts(5))