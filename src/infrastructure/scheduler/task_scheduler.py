"""
定时任务调度器
管理定时签到和其他定时任务
"""
import schedule
import threading
import logging
import time
from typing import Callable, List, Dict, Any, Optional
from datetime import datetime


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self):
        """初始化调度器"""
        self.enabled = False
        self.running = False
        self.schedule_thread: Optional[threading.Thread] = None
        self.scheduled_times: List[str] = []
        self._stop_flag = threading.Event()

    def configure(self, enabled: bool, times: List[str]) -> None:
        """
        配置定时任务

        Args:
            enabled: 是否启用定时任务
            times: 定时时间列表，格式如 ['09:00', '13:00', '21:00']
        """
        self.enabled = enabled
        self.scheduled_times = times

        if enabled:
            logging.info(f"定时任务已启用，计划时间: {', '.join(times)}")
        else:
            logging.info("定时任务已禁用")

    def schedule_daily_task(self, time_str: str, task: Callable) -> None:
        """
        添加每日定时任务

        Args:
            time_str: 时间字符串，格式 'HH:MM'
            task: 要执行的任务函数
        """
        try:
            schedule.every().day.at(time_str).do(task)
            logging.info(f"已添加定时任务: 每天 {time_str}")
        except Exception as e:
            logging.error(f"添加定时任务失败 ({time_str}): {e}")

    def schedule_checkin(self, times: List[str], checkin_func: Callable) -> None:
        """
        设置签到定时任务

        Args:
            times: 定时时间列表
            checkin_func: 签到函数
        """
        # 清除现有任务
        schedule.clear()

        if not self.enabled or not times:
            logging.info("定时签到未启用或无时间配置")
            return

        # 添加所有定时任务
        for time_str in times:
            try:
                schedule.every().day.at(time_str).do(checkin_func)
                logging.info(f"已设置定时签到: {time_str}")
            except Exception as e:
                logging.error(f"设置定时签到失败 ({time_str}): {e}")

    def start(self) -> None:
        """启动调度器"""
        if self.running:
            logging.warning("调度器已在运行中")
            return

        self.running = True
        self._stop_flag.clear()

        self.schedule_thread = threading.Thread(
            target=self._run_scheduler,
            daemon=True,
            name="TaskScheduler"
        )
        self.schedule_thread.start()
        logging.info("定时任务调度器已启动")

    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            return

        self.running = False
        self._stop_flag.set()

        if self.schedule_thread:
            self.schedule_thread.join(timeout=5)
            self.schedule_thread = None

        logging.info("定时任务调度器已停止")

    def _run_scheduler(self) -> None:
        """运行调度器循环"""
        while self.running and not self._stop_flag.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logging.error(f"调度器运行错误: {e}", exc_info=True)
                time.sleep(60)

    def reload(self, enabled: bool, times: List[str], checkin_func: Callable) -> None:
        """
        重新加载定时任务配置

        Args:
            enabled: 是否启用
            times: 定时时间列表
            checkin_func: 签到函数
        """
        logging.info("重新加载定时任务配置...")

        # 更新配置
        self.configure(enabled, times)

        # 重新设置任务
        self.schedule_checkin(times, checkin_func)

        logging.info("定时任务配置已重新加载")

    def get_next_run_time(self) -> Optional[datetime]:
        """
        获取下次运行时间

        Returns:
            下次运行时间，如果没有任务则返回None
        """
        jobs = schedule.get_jobs()
        if not jobs:
            return None

        # 找出最近的下次运行时间
        next_times = [job.next_run for job in jobs if job.next_run]
        if not next_times:
            return None

        return min(next_times)

    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态

        Returns:
            状态字典
        """
        next_run = self.get_next_run_time()

        return {
            'enabled': self.enabled,
            'running': self.running,
            'scheduled_times': self.scheduled_times,
            'next_run': next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else None,
            'jobs_count': len(schedule.get_jobs())
        }

    def clear_all(self) -> None:
        """清除所有定时任务"""
        schedule.clear()
        self.scheduled_times = []
        logging.info("已清除所有定时任务")


# 全局单例实例
_global_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """
    获取全局调度器实例（单例模式）

    Returns:
        TaskScheduler实例
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler()
    return _global_scheduler


# 示例使用
if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 创建调度器
    scheduler = TaskScheduler()

    # 定义签到任务
    def test_checkin():
        print(f"执行签到任务: {datetime.now()}")
        logging.info("签到任务执行中...")

    # 配置定时任务
    scheduler.configure(enabled=True, times=['09:00', '13:00', '21:00'])

    # 设置签到任务
    scheduler.schedule_checkin(['09:00', '13:00'], test_checkin)

    # 启动调度器
    scheduler.start()

    # 查看状态
    print("调度器状态:", scheduler.get_status())

    # 保持运行（实际应用中不需要这个）
    try:
        while True:
            time.sleep(10)
            status = scheduler.get_status()
            print(f"下次运行: {status['next_run']}")
    except KeyboardInterrupt:
        scheduler.stop()
        print("调度器已停止")
