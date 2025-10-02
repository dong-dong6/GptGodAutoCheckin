"""
浏览器服务基类
为所有需要浏览器自动化的服务提供统一的浏览器管理和Cloudflare绕过能力
"""
import logging
import time
from contextlib import contextmanager
from src.infrastructure.browser.browser_manager import BrowserManager
from src.infrastructure.browser.cloudflare_bypasser import CloudflareBypasser


class BrowserService:
    """
    浏览器服务基类
    提供统一的浏览器创建、管理和Cloudflare绕过功能
    """

    def __init__(self, headless=False):
        """
        初始化浏览器服务

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.browser_manager = None
        self.driver = None
        self.bypasser = None

    @contextmanager
    def get_browser(self):
        """
        上下文管理器：创建并管理浏览器生命周期

        Usage:
            with service.get_browser() as driver:
                driver.get('https://example.com')

        Yields:
            driver: ChromiumPage实例
        """
        try:
            # 创建浏览器
            self.browser_manager = BrowserManager(headless=self.headless)
            self.driver = self.browser_manager.create_browser()
            self.bypasser = CloudflareBypasser(self.driver)

            logging.info("浏览器创建成功")
            yield self.driver

        finally:
            # 清理资源
            if self.browser_manager:
                self.browser_manager.close()
                logging.info("浏览器已关闭")

    def bypass_cloudflare(self, max_retries=3):
        """
        绕过Cloudflare验证

        Args:
            max_retries: 最大重试次数

        Returns:
            bool: 是否成功绕过

        Raises:
            RuntimeError: 如果浏览器未初始化
        """
        if not self.driver or not self.bypasser:
            raise RuntimeError("浏览器未初始化，请先调用get_browser()")

        for attempt in range(max_retries):
            try:
                logging.info(f"尝试绕过Cloudflare（第{attempt + 1}/{max_retries}次）...")

                if self.bypasser.bypass():
                    logging.info("✅ Cloudflare绕过成功")
                    return True
                else:
                    logging.warning(f"第{attempt + 1}次绕过失败")
                    if attempt < max_retries - 1:
                        time.sleep(2)

            except Exception as e:
                logging.error(f"绕过Cloudflare时出错: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise

        logging.error("❌ 所有Cloudflare绕过尝试均失败")
        return False

    def login_account(self, domain, email, password):
        """
        登录GPT-GOD账号

        Args:
            domain: 域名
            email: 邮箱
            password: 密码

        Returns:
            bool: 是否登录成功

        Raises:
            RuntimeError: 如果浏览器未初始化
        """
        if not self.driver:
            raise RuntimeError("浏览器未初始化，请先调用get_browser()")

        try:
            login_url = f'https://{domain}/#/login'
            logging.info(f"访问登录页面: {login_url}")

            self.driver.get(login_url)
            time.sleep(5)

            # 检查并绕过Cloudflare
            if not self.bypasser.is_bypassed():
                if not self.bypass_cloudflare():
                    logging.error("无法绕过Cloudflare验证")
                    return False

            # 填写登录表单
            logging.info(f"填写登录信息: {email}")

            # 查找邮箱输入框
            email_input = self.driver.ele('@type=email', timeout=10)
            if not email_input:
                logging.error("未找到邮箱输入框")
                return False

            # 查找密码输入框
            password_input = self.driver.ele('@type=password', timeout=10)
            if not password_input:
                logging.error("未找到密码输入框")
                return False

            # 输入凭证
            email_input.input(email)
            time.sleep(0.5)
            password_input.input(password)
            time.sleep(0.5)

            # 查找并点击登录按钮
            login_button = self.driver.ele('xpath://button[@type="submit"]', timeout=10)
            if not login_button:
                # 尝试查找包含"登录"文本的按钮
                buttons = self.driver.eles('tag:button')
                for btn in buttons:
                    if '登录' in btn.text or 'Login' in btn.text:
                        login_button = btn
                        break

            if not login_button:
                logging.error("未找到登录按钮")
                return False

            login_button.click()
            logging.info("已点击登录按钮，等待登录...")
            time.sleep(5)

            # 验证是否登录成功（检查URL变化或特定元素）
            current_url = self.driver.url
            if '#/login' not in current_url:
                logging.info(f"✅ 账号 {email} 登录成功")
                return True
            else:
                logging.warning(f"⚠️ 账号 {email} 可能登录失败（仍在登录页面）")
                return False

        except Exception as e:
            logging.error(f"登录过程出错: {e}", exc_info=True)
            return False

    def wait_for_page_load(self, timeout=10):
        """
        等待页面加载完成

        Args:
            timeout: 超时时间（秒）
        """
        if self.driver:
            time.sleep(2)  # 简单等待，可以改进为更智能的检测
            logging.debug("页面加载等待完成")
