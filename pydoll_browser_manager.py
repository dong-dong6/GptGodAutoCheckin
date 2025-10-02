"""
Pydoll浏览器管理器 - 统一管理Pydoll浏览器实例的创建、配置和清理
"""
import os
import logging
import platform
from pathlib import Path


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

    # 如果都找不到，返回None让Pydoll使用默认路径
    logging.warning("未能自动检测到浏览器路径，将使用Pydoll默认配置")
    return None


class PydollBrowserManager:
    """Pydoll浏览器管理器 - 负责创建和管理Pydoll浏览器实例"""

    def __init__(self, headless=False):
        """初始化浏览器管理器

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.browser = None
        self.tab = None
        self.browser_path = find_browser_path()
        self._cloudflare_enabled = False

    async def create_browser(self):
        """创建浏览器实例

        Returns:
            Tab: Pydoll Tab实例
        """
        from pydoll.browser import Edge, Chrome

        # 根据检测到的浏览器路径选择浏览器类型
        if self.browser_path and 'msedge.exe' in self.browser_path.lower():
            logging.info(f"使用Edge浏览器: {self.browser_path}")
            self.browser = Edge()
        elif self.browser_path and 'chrome.exe' in self.browser_path.lower():
            logging.info(f"使用Chrome浏览器: {self.browser_path}")
            self.browser = Chrome()
        else:
            # 默认使用Edge
            logging.info("使用默认Edge浏览器")
            self.browser = Edge()

        # 如果有自定义路径，设置浏览器路径
        if self.browser_path:
            try:
                # Pydoll使用options设置路径
                if hasattr(self.browser, 'options'):
                    self.browser.options.binary_location = self.browser_path
            except Exception as e:
                logging.warning(f"设置浏览器路径失败，使用默认配置: {e}")

        # 启动浏览器
        logging.info("启动Pydoll浏览器...")
        self.tab = await self.browser.start()

        return self.tab

    async def enable_cloudflare_bypass(self):
        """启用Cloudflare自动绕过"""
        if self.tab and not self._cloudflare_enabled:
            logging.info("启用Cloudflare自动绕过...")
            await self.tab.enable_auto_solve_cloudflare_captcha()
            self._cloudflare_enabled = True

    async def disable_cloudflare_bypass(self):
        """禁用Cloudflare自动绕过"""
        if self.tab and self._cloudflare_enabled:
            logging.info("禁用Cloudflare自动绕过...")
            await self.tab.disable_auto_solve_cloudflare_captcha()
            self._cloudflare_enabled = False

    async def close(self):
        """关闭浏览器"""
        # 禁用Cloudflare绕过
        if self._cloudflare_enabled:
            try:
                await self.disable_cloudflare_bypass()
            except Exception as e:
                logging.debug(f"禁用Cloudflare绕过失败: {e}")

        # 关闭浏览器
        if self.browser:
            try:
                logging.info("关闭Pydoll浏览器...")
                await self.browser.stop()
            except Exception as e:
                logging.warning(f"关闭浏览器时出错: {e}")
            finally:
                self.browser = None
                self.tab = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return await self.create_browser()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()


def get_browser_type():
    """获取推荐的浏览器类型

    Returns:
        str: 'edge' 或 'chrome'
    """
    browser_path = find_browser_path()
    if browser_path:
        if 'msedge.exe' in browser_path.lower() or 'Microsoft Edge' in browser_path:
            return 'edge'
        elif 'chrome' in browser_path.lower():
            return 'chrome'
    return 'edge'  # 默认返回edge
