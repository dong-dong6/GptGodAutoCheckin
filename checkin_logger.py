import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class CheckinLogger:
    """签到日志记录器"""

    def __init__(self, log_dir='checkin_logs'):
        """初始化日志记录器

        Args:
            log_dir: 日志存储目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 创建今天的日志文件
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_log_file = self.log_dir / f'checkin_{today}.json'
        self.summary_log_file = self.log_dir / 'checkin_summary.json'

        # 初始化日志数据
        self.daily_logs = self._load_daily_logs()
        self.summary = self._load_summary()

    def _load_daily_logs(self):
        """加载今日日志"""
        if self.daily_log_file.exists():
            try:
                with open(self.daily_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _load_summary(self):
        """加载汇总数据"""
        if self.summary_log_file.exists():
            try:
                with open(self.summary_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        return {
            'total_checkins': 0,
            'successful_checkins': 0,
            'failed_checkins': 0,
            'total_points_earned': 0,
            'accounts': {},
            'last_checkin_time': None
        }

    def _save_daily_logs(self):
        """保存今日日志"""
        with open(self.daily_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.daily_logs, f, ensure_ascii=False, indent=2)

    def _save_summary(self):
        """保存汇总数据"""
        with open(self.summary_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=2)

    def log_checkin_start(self, trigger_type='manual', trigger_by=None):
        """记录签到开始

        Args:
            trigger_type: 触发类型 (manual/scheduled/api)
            trigger_by: 触发者（用户名或IP）
        """
        log_entry = {
            'id': len(self.daily_logs) + 1,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'trigger_type': trigger_type,
            'trigger_by': trigger_by,
            'accounts': [],
            'total_accounts': 0,
            'success_count': 0,
            'failed_count': 0,
            'already_checked_count': 0,
            'status': 'running'
        }

        self.daily_logs.append(log_entry)
        self._save_daily_logs()

        return len(self.daily_logs) - 1  # 返回日志索引

    def log_account_result(self, log_index, account_email, status, message='', points=0):
        """记录单个账号签到结果

        Args:
            log_index: 日志索引
            account_email: 账号邮箱
            status: 状态 (success/failed/already_checked)
            message: 消息
            points: 获得积分
        """
        if log_index < len(self.daily_logs):
            account_log = {
                'email': account_email,
                'time': datetime.now().isoformat(),
                'status': status,
                'message': message,
                'points': points
            }

            self.daily_logs[log_index]['accounts'].append(account_log)

            # 更新统计
            if status == 'success':
                self.daily_logs[log_index]['success_count'] += 1
            elif status == 'failed':
                self.daily_logs[log_index]['failed_count'] += 1
            elif status == 'already_checked':
                self.daily_logs[log_index]['already_checked_count'] += 1

            self._save_daily_logs()

            # 更新汇总数据
            if account_email not in self.summary['accounts']:
                self.summary['accounts'][account_email] = {
                    'total_checkins': 0,
                    'successful_checkins': 0,
                    'failed_checkins': 0,
                    'total_points': 0,
                    'last_checkin': None,
                    'consecutive_days': 0
                }

            account_summary = self.summary['accounts'][account_email]
            account_summary['total_checkins'] += 1

            if status == 'success':
                account_summary['successful_checkins'] += 1
                account_summary['total_points'] += points
                self.summary['total_points_earned'] += points
                self.summary['successful_checkins'] += 1
            elif status == 'failed':
                account_summary['failed_checkins'] += 1
                self.summary['failed_checkins'] += 1

            account_summary['last_checkin'] = datetime.now().isoformat()
            self.summary['total_checkins'] += 1

            self._save_summary()

    def log_checkin_end(self, log_index, email_sent=False):
        """记录签到结束

        Args:
            log_index: 日志索引
            email_sent: 是否发送了邮件
        """
        if log_index < len(self.daily_logs):
            self.daily_logs[log_index]['end_time'] = datetime.now().isoformat()
            self.daily_logs[log_index]['status'] = 'completed'
            self.daily_logs[log_index]['email_sent'] = email_sent
            self.daily_logs[log_index]['total_accounts'] = len(self.daily_logs[log_index]['accounts'])

            # 计算耗时
            start = datetime.fromisoformat(self.daily_logs[log_index]['start_time'])
            end = datetime.fromisoformat(self.daily_logs[log_index]['end_time'])
            duration = (end - start).total_seconds()
            self.daily_logs[log_index]['duration_seconds'] = duration

            self._save_daily_logs()

            # 更新汇总
            self.summary['last_checkin_time'] = datetime.now().isoformat()
            self._save_summary()

    def get_statistics(self):
        """获取统计信息"""
        # 计算最近7天和30天的统计
        now = datetime.now()
        seven_days_ago = now.replace(hour=0, minute=0, second=0) - timedelta(days=7)
        thirty_days_ago = now.replace(hour=0, minute=0, second=0) - timedelta(days=30)

        recent_7_days = {'total': 0, 'success': 0, 'failed': 0}
        recent_30_days = {'total': 0, 'success': 0, 'failed': 0}

        # 遍历所有日志文件
        for log_file in self.log_dir.glob('checkin_*.json'):
            if log_file == self.summary_log_file:
                continue

            try:
                # 从文件名提取日期
                date_str = log_file.stem.replace('checkin_', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                # 加载日志
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)

                for log in logs:
                    if log.get('status') == 'completed':
                        if file_date >= seven_days_ago:
                            recent_7_days['total'] += log.get('total_accounts', 0)
                            recent_7_days['success'] += log.get('success_count', 0)
                            recent_7_days['failed'] += log.get('failed_count', 0)

                        if file_date >= thirty_days_ago:
                            recent_30_days['total'] += log.get('total_accounts', 0)
                            recent_30_days['success'] += log.get('success_count', 0)
                            recent_30_days['failed'] += log.get('failed_count', 0)
            except:
                continue

        return {
            'all_time': {
                'total_checkins': self.summary['total_checkins'],
                'successful_checkins': self.summary['successful_checkins'],
                'failed_checkins': self.summary['failed_checkins'],
                'total_points_earned': self.summary['total_points_earned']
            },
            'recent_7_days': recent_7_days,
            'recent_30_days': recent_30_days,
            'today': {
                'sessions': len(self.daily_logs),
                'accounts': sum(log['total_accounts'] for log in self.daily_logs),
                'success': sum(log['success_count'] for log in self.daily_logs),
                'failed': sum(log['failed_count'] for log in self.daily_logs)
            }
        }

    def get_account_history(self, email, days=30):
        """获取账号历史记录

        Args:
            email: 账号邮箱
            days: 查询天数
        """
        history = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for log_file in sorted(self.log_dir.glob('checkin_*.json')):
            if log_file == self.summary_log_file:
                continue

            try:
                # 从文件名提取日期
                date_str = log_file.stem.replace('checkin_', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                if file_date < cutoff_date:
                    continue

                # 加载日志
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)

                for log in logs:
                    for account in log.get('accounts', []):
                        if account['email'] == email:
                            history.append({
                                'date': date_str,
                                'time': account['time'],
                                'status': account['status'],
                                'message': account.get('message', ''),
                                'points': account.get('points', 0)
                            })
            except:
                continue

        return history

# 使用示例
if __name__ == '__main__':
    logger = CheckinLogger()

    # 开始签到
    log_idx = logger.log_checkin_start('manual', 'admin')

    # 记录账号结果
    logger.log_account_result(log_idx, 'test@example.com', 'success', '签到成功', 2000)
    logger.log_account_result(log_idx, 'test2@example.com', 'already_checked', '今天已签到')

    # 结束签到
    logger.log_checkin_end(log_idx, email_sent=True)

    # 获取统计
    stats = logger.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))