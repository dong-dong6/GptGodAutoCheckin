"""
日志工具类
提供统一的日志管理和格式化
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LoggerManager:
    """日志管理器"""

    _instance: Optional['LoggerManager'] = None
    _initialized = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化日志管理器（只执行一次）"""
        if not LoggerManager._initialized:
            self.loggers = {}
            LoggerManager._initialized = True

    def setup_logger(
        self,
        name: str = 'app',
        level: int = logging.INFO,
        log_dir: str = 'logs',
        log_file: Optional[str] = None,
        console: bool = True,
        file_logging: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        format_string: Optional[str] = None
    ) -> logging.Logger:
        """
        设置日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_dir: 日志目录
            log_file: 日志文件名（默认使用name.log）
            console: 是否输出到控制台
            file_logging: 是否输出到文件
            max_bytes: 单个日志文件最大字节数
            backup_count: 日志文件备份数量
            format_string: 自定义日志格式

        Returns:
            配置好的Logger对象
        """
        # 如果已存在则返回
        if name in self.loggers:
            return self.loggers[name]

        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        # 清除现有handlers
        logger.handlers.clear()

        # 设置日志格式
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        formatter = logging.Formatter(format_string)

        # 控制台handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # 文件handler
        if file_logging:
            # 创建日志目录
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)

            # 确定日志文件名
            if log_file is None:
                log_file = f"{name}.log"

            log_file_path = log_path / log_file

            # 使用RotatingFileHandler（按大小轮转）
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # 保存logger
        self.loggers[name] = logger

        return logger

    def get_logger(self, name: str = 'app') -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            Logger对象
        """
        if name not in self.loggers:
            return self.setup_logger(name)
        return self.loggers[name]

    def set_level(self, name: str, level: int) -> None:
        """
        设置日志级别

        Args:
            name: 日志记录器名称
            level: 日志级别
        """
        if name in self.loggers:
            self.loggers[name].setLevel(level)
            for handler in self.loggers[name].handlers:
                handler.setLevel(level)


class TimedLogger:
    """带时间戳的日志工具"""

    def __init__(self, logger: logging.Logger):
        """
        初始化

        Args:
            logger: Logger对象
        """
        self.logger = logger
        self.start_time: Optional[datetime] = None

    def start(self, message: str) -> None:
        """
        开始计时并记录日志

        Args:
            message: 日志信息
        """
        self.start_time = datetime.now()
        self.logger.info(f"[START] {message}")

    def end(self, message: str) -> float:
        """
        结束计时并记录日志

        Args:
            message: 日志信息

        Returns:
            耗时（秒）
        """
        if self.start_time is None:
            self.logger.warning("计时器未启动")
            return 0.0

        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"[END] {message} (耗时: {elapsed:.2f}秒)")
        self.start_time = None

        return elapsed

    def log_with_time(self, message: str, level: int = logging.INFO) -> None:
        """
        记录带时间戳的日志

        Args:
            message: 日志信息
            level: 日志级别
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        self.logger.log(level, f"[{timestamp}] {message}")


# 便捷函数
def get_logger(name: str = 'app') -> logging.Logger:
    """
    获取日志记录器（便捷函数）

    Args:
        name: 日志记录器名称

    Returns:
        Logger对象
    """
    manager = LoggerManager()
    return manager.get_logger(name)


def setup_app_logging(
    log_level: int = logging.INFO,
    log_dir: str = 'logs'
) -> logging.Logger:
    """
    设置应用日志（便捷函数）

    Args:
        log_level: 日志级别
        log_dir: 日志目录

    Returns:
        应用Logger
    """
    manager = LoggerManager()
    return manager.setup_logger(
        name='app',
        level=log_level,
        log_dir=log_dir,
        console=True,
        file_logging=True
    )


# 示例使用
if __name__ == '__main__':
    # 设置日志
    logger = setup_app_logging(log_level=logging.DEBUG)

    # 基本日志
    logger.debug("这是DEBUG信息")
    logger.info("这是INFO信息")
    logger.warning("这是WARNING信息")
    logger.error("这是ERROR信息")

    # 计时日志
    timed = TimedLogger(logger)
    timed.start("测试任务开始")

    import time
    time.sleep(1)

    timed.end("测试任务完成")

    # 创建模块专用日志
    manager = LoggerManager()
    checkin_logger = manager.setup_logger(
        name='checkin',
        log_file='checkin.log',
        level=logging.INFO
    )

    checkin_logger.info("签到模块日志")

    print("日志工具类创建成功")
