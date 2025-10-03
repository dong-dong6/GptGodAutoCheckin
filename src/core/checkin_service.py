"""
签到服务
统一管理签到业务逻辑，包括登录、Cloudflare绕过、签到操作
"""
import logging
import time
from datetime import datetime
from src.core.browser_service import BrowserService
from src.data.repositories.checkin_repository import CheckinLoggerDB
from src.data.repositories.config_repository import ConfigManager
from src.infrastructure.notification.email_service import EmailService


class CheckinService(BrowserService):
    """
    签到服务类
    继承BrowserService，实现签到业务逻辑
    """

    def __init__(self, headless=False):
        """
        初始化签到服务

        Args:
            headless: 是否使用无头模式
        """
        super().__init__(headless=headless)
        self.logger_db = CheckinLoggerDB()
        self.config_manager = ConfigManager()

        # 初始化邮件服务
        smtp_config = self.config_manager.get_smtp_config()
        self.email_service = EmailService(smtp_config)

    def perform_checkin(self, domain, email, password, session_id=None):
        """
        执行单个账号的签到

        Args:
            domain: 域名
            email: 邮箱
            password: 密码
            session_id: 签到会话ID（可选）

        Returns:
            dict: 签到结果
                {
                    'success': bool,
                    'email': str,
                    'message': str,
                    'points_earned': int,
                    'current_points': int,
                    'domain': str
                }
        """
        result = {
            'success': False,
            'email': email,
            'message': '',
            'points_earned': 0,
            'current_points': 0,
            'domain': domain
        }

        try:
            with self.get_browser() as driver:
                # 登录账号
                if not self.login_account(domain, email, password):
                    result['message'] = '登录失败'
                    if session_id:
                        self.logger_db.log_account_result(
                            session_id, email, 'login_failed', '登录失败', 0, domain
                        )
                    return result

                # 导航到签到页面
                checkin_url = f'https://{domain}/#/token'
                logging.info(f"导航到签到页面: {checkin_url}")
                driver.get(checkin_url)
                logging.info("等待签到页面完全加载...")
                time.sleep(10)

                # 检查是否已签到
                already_checked_btn = driver.ele('xpath://button[contains(., "今天已签到")]')
                if already_checked_btn:
                    logging.info(f"[已签到] 账号 {email} 今天已经签到过了")
                    result['success'] = True
                    result['message'] = '今天已签到'
                    result['current_points'] = self._get_current_points(driver, email)

                    if session_id:
                        self.logger_db.log_account_result(
                            session_id, email, 'already_checked', '今天已签到',
                            0, domain
                        )

                    return result

                # 查找签到按钮
                checkin_button = None

                # 方法1: 通过文本内容查找
                try:
                    checkin_button = driver.ele('xpath://button[contains(., "签到")]', timeout=5)
                except:
                    pass

                # 方法2: 如果未找到，遍历所有按钮
                if not checkin_button:
                    logging.info("尝试遍历所有按钮查找签到按钮")
                    buttons = driver.eles('tag:button')
                    for button in buttons:
                        button_text = button.text
                        if "签到" in button_text and "今天已签到" not in button_text:
                            checkin_button = button
                            break

                if not checkin_button:
                    logging.warning(f"未找到签到按钮: {email}")
                    result['message'] = '未找到签到按钮'

                    if session_id:
                        self.logger_db.log_account_result(
                            session_id, email, 'button_not_found', '未找到签到按钮',
                            0, domain
                        )

                    return result

                # 点击签到按钮（点击后会触发CF验证）
                logging.info(f"点击签到按钮: {email}")
                checkin_button.click()
                time.sleep(5)  # 增加等待时间

                # 点击签到后检查并绕过Cloudflare验证
                if not self.bypasser.is_bypassed():
                    logging.info("点击签到后检测到Cloudflare验证，尝试绕过...")
                    if not self.bypass_cloudflare():
                        result['message'] = 'Cloudflare验证失败'
                        if session_id:
                            self.logger_db.log_account_result(
                                session_id, email, 'cf_failed', 'Cloudflare验证失败', 0, domain
                            )
                        return result
                    logging.info("✅ Cloudflare验证已通过")

                time.sleep(3)

                # 签到成功
                logging.info(f"✅ 签到成功: {email}")
                result['success'] = True
                result['message'] = '签到成功'
                result['points_earned'] = 5  # 假设每次签到获得5积分
                result['current_points'] = self._get_current_points(driver, email)

                if session_id:
                    self.logger_db.log_account_result(
                        session_id, email, 'success', '签到成功',
                        result['points_earned'], domain
                    )

                return result

        except Exception as e:
            logging.error(f"签到过程出错: {e}", exc_info=True)
            result['message'] = f'签到异常: {str(e)}'

            if session_id:
                self.logger_db.log_account_result(
                    session_id, email, 'error', str(e), 0, domain
                )

            return result

    def _get_current_points(self, driver, email):
        """
        获取当前积分（从页面或API）

        Args:
            driver: 浏览器实例
            email: 邮箱

        Returns:
            int: 当前积分
        """
        try:
            # 尝试监听API获取用户信息
            driver.listen.start('api/user/info', method='GET')
            driver.refresh()
            time.sleep(3)

            resp = driver.listen.wait(timeout=5)
            if resp and resp.response.status == 200:
                body = resp.response.body
                if isinstance(body, str):
                    import json
                    body = json.loads(body)

                if body.get('code') == 0 and 'data' in body:
                    user_info = body['data']
                    current_points = user_info.get('tokens', 0)
                    logging.info(f"账号 {email} 当前积分: {current_points}")
                    return current_points

        except Exception as e:
            logging.debug(f"获取积分失败: {e}")

        finally:
            try:
                driver.listen.stop()
            except:
                pass

        return 0

    def batch_checkin(self, domains=None):
        """
        批量签到所有账号

        Args:
            domains: 域名列表（可选，默认从配置读取）

        Returns:
            dict: 批量签到结果统计
        """
        # 获取域名配置
        if not domains:
            domain_config = self.config_manager.get_domain_config()
            primary_domain = domain_config.get('primary', 'gptgod.online')
            backup_domain = domain_config.get('backup', 'gptgod.work')
            domains = [primary_domain, backup_domain]

        # 获取所有账号
        accounts = self.config_manager.get_accounts()

        if not accounts:
            logging.warning("没有配置任何账号")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'results': []
            }

        # 创建签到会话
        session_id = self.logger_db.create_session(len(accounts))

        results = []
        success_count = 0
        failed_count = 0

        # 逐个签到
        for account in accounts:
            email = account['mail']
            password = account['password']
            send_email = account.get('send_email_notification', False)  # 获取账号级别的邮件通知配置

            # 尝试每个域名
            account_success = False
            for domain in domains:
                logging.info(f"\n{'='*60}")
                logging.info(f"签到账号: {email} @ {domain}")
                logging.info(f"{'='*60}")

                result = self.perform_checkin(domain, email, password, session_id)
                result['send_email_notification'] = send_email  # 添加邮件通知标记
                results.append(result)

                if result['success']:
                    account_success = True
                    success_count += 1
                    break  # 成功后跳过其他域名

            if not account_success:
                failed_count += 1

            # 账号间等待，避免被限流
            time.sleep(2)

        # 发送邮件通知（只包含配置了发送邮件的账号）
        email_sent = False
        logging.info("=== 开始检查邮件发送逻辑 ===")
        logging.info(f"总共有 {len(results)} 个账号签到结果")

        # 调试：打印所有账号的邮件通知配置
        for i, result in enumerate(results):
            send_email = result.get('send_email_notification', False)
            logging.info(f"账号 {i+1}: {result['email']}, 邮件通知: {send_email}")

        try:
            # 筛选需要发送邮件的账号结果
            email_results = [r for r in results if r.get('send_email_notification', False)]
            logging.info(f"筛选出 {len(email_results)} 个需要发送邮件的账号")

            if email_results:
                # 统计需要发送邮件的账号的成功/失败数
                email_success = sum(1 for r in email_results if r['success'])
                email_failed = len(email_results) - email_success

                logging.info(f"准备发送邮件: 成功{email_success}个, 失败{email_failed}个")
                email_sent = self.email_service.send_checkin_notification(
                    results={'results': email_results},
                    success_count=email_success,
                    failed_count=email_failed
                )
                if email_sent:
                    logging.info(f"✅ 邮件通知已发送 (包含{len(email_results)}个账号的结果)")
                else:
                    logging.warning("❌ 邮件通知发送失败")
            else:
                logging.info("⚠️ 没有账号配置发送邮件通知，跳过")
        except Exception as e:
            logging.error(f"❌ 发送邮件通知异常: {e}", exc_info=True)

        logging.info("=== 邮件发送逻辑结束 ===")

        # 结束会话
        self.logger_db.log_checkin_end(session_id, email_sent=email_sent)

        return {
            'total': len(accounts),
            'success': success_count,
            'failed': failed_count,
            'results': results
        }
