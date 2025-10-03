"""
浏览器管理器 - 统一管理浏览器实例的创建、配置和清理
"""
import os
import shutil
import tempfile
import random
import logging
import platform
from pathlib import Path
from DrissionPage import ChromiumPage, ChromiumOptions


def find_browser_path():
    """自动检测浏览器路径

    Returns:
        str: 浏览器可执行文件路径
    """
    system = platform.system()

    if system == "Windows":
        # Windows 浏览器路径列表
        possible_paths = [
            # Edge (推荐)
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            # Chrome
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            # Brave
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
    elif system == "Darwin":  # macOS
        possible_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    else:  # Linux
        possible_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/microsoft-edge",
            "/snap/bin/chromium",
        ]

    # 检查每个可能的路径
    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"自动检测到浏览器: {path}")
            return path

    # 如果都找不到，抛出异常
    raise FileNotFoundError(
        f"未找到浏览器！请安装以下浏览器之一：\n"
        f"{'、'.join(['Microsoft Edge', 'Google Chrome', 'Brave Browser'])}\n"
        f"已检查路径：\n" + "\n".join(f"  - {p}" for p in possible_paths)
    )


class BrowserManager:
    """浏览器管理器 - 负责创建和管理浏览器实例"""

    def __init__(self, headless=False):
        """初始化浏览器管理器

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.temp_dir = None
        self.random_port = None
        self.driver = None
        self.browser_path = find_browser_path()

    def _create_temp_dir(self):
        """创建临时数据目录"""
        self.temp_dir = tempfile.mkdtemp(prefix='browser_temp_')
        logging.info(f"创建临时目录: {self.temp_dir}")
        return self.temp_dir

    def _get_random_port(self):
        """生成随机端口"""
        self.random_port = random.randint(9222, 9999)
        logging.info(f"使用随机端口: {self.random_port}")
        return self.random_port

    def _get_browser_arguments(self, incognito=True):
        """获取浏览器启动参数

        Args:
            incognito: 是否使用无痕模式

        Returns:
            list: 浏览器启动参数列表
        """
        args = [
            f"--user-data-dir={self.temp_dir}",
            f"--remote-debugging-port={self.random_port}",
            "--window-size=1920,1080",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--lang=zh-CN",
            "--accept-lang=zh-CN,zh;q=0.9",
            "--disable-extensions",
            "--no-first-run",
            "--disable-background-networking",
        ]

        if incognito:
            args.append("--incognito")

        if self.headless:
            args.append("--headless=new")  # 使用新的无头模式

        return args

    def create_browser(self, incognito=True):
        """创建浏览器实例

        Args:
            incognito: 是否使用无痕模式

        Returns:
            ChromiumPage: 浏览器实例
        """
        # 创建临时目录和随机端口
        self._create_temp_dir()
        self._get_random_port()

        # 配置浏览器选项
        options = ChromiumOptions()
        options.set_browser_path(self.browser_path)

        # 添加启动参数
        for arg in self._get_browser_arguments(incognito):
            options.set_argument(arg)

        # 创建浏览器实例
        logging.info(f"启动浏览器: {self.browser_path}")
        self.driver = ChromiumPage(addr_or_opts=options)

        return self.driver

    def close(self):
        """关闭浏览器并清理临时目录"""
        # 关闭浏览器
        if self.driver:
            try:
                logging.info("关闭浏览器...")
                self.driver.quit()
            except Exception as e:
                logging.warning(f"关闭浏览器时出错: {e}")
            finally:
                self.driver = None

        # 清理临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                logging.info(f"清理临时目录: {self.temp_dir}")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                logging.warning(f"清理临时目录失败: {e}")
            finally:
                self.temp_dir = None

    def __enter__(self):
        """上下文管理器入口"""
        return self.create_browser()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()

    def __del__(self):
        """析构函数 - 确保资源被清理"""
        self.close()


def get_chromium_options(browser_path, arguments):
    """获取Chromium配置选项（向后兼容的辅助函数）

    Args:
        browser_path: 浏览器路径
        arguments: 浏览器参数列表

    Returns:
        ChromiumOptions: 配置好的选项对象
    """
    options = ChromiumOptions()
    options.set_browser_path(browser_path)
    for arg in arguments:
        options.set_argument(arg)
    return options
