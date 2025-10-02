"""
兑换码服务
处理GPT-GOD兑换码兑换逻辑
"""
import logging
import time
from src.core.browser_service import BrowserService


class RedeemService(BrowserService):
    """
    兑换码服务类
    继承BrowserService，实现兑换码兑换逻辑
    """

    def __init__(self, headless=False):
        """
        初始化兑换码服务

        Args:
            headless: 是否使用无头模式
        """
        super().__init__(headless=headless)

    def redeem_code(self, domain, email, password, code):
        """
        兑换兑换码

        Args:
            domain: 域名
            email: 邮箱
            password: 密码
            code: 兑换码

        Returns:
            dict: 兑换结果
                {
                    'success': bool,
                    'email': str,
                    'code': str,
                    'message': str,
                    'reward': str  # 兑换获得的奖励描述
                }
        """
        result = {
            'success': False,
            'email': email,
            'code': code,
            'message': '',
            'reward': ''
        }

        try:
            with self.get_browser() as driver:
                # 登录账号
                if not self.login_account(domain, email, password):
                    result['message'] = '登录失败'
                    return result

                # 导航到兑换页面
                redeem_url = f'https://{domain}/#/redeem'
                logging.info(f"访问兑换页面: {redeem_url}")
                driver.get(redeem_url)
                time.sleep(5)

                # 查找兑换码输入框
                code_input = None
                try:
                    # 尝试多种选择器
                    code_input = driver.ele('@placeholder=请输入兑换码', timeout=5)
                    if not code_input:
                        code_input = driver.ele('@placeholder*=兑换', timeout=5)
                    if not code_input:
                        code_input = driver.ele('tag:input', timeout=5)
                except:
                    pass

                if not code_input:
                    logging.error("未找到兑换码输入框")
                    result['message'] = '未找到兑换码输入框'
                    return result

                # 输入兑换码
                logging.info(f"输入兑换码: {code}")
                code_input.input(code)
                time.sleep(1)

                # 查找兑换按钮
                redeem_button = None
                try:
                    redeem_button = driver.ele('xpath://button[contains(., "兑换")]', timeout=5)
                    if not redeem_button:
                        # 尝试查找submit按钮
                        redeem_button = driver.ele('@type=submit', timeout=5)
                except:
                    pass

                if not redeem_button:
                    logging.error("未找到兑换按钮")
                    result['message'] = '未找到兑换按钮'
                    return result

                # 点击兑换按钮
                logging.info("点击兑换按钮")
                redeem_button.click()
                time.sleep(3)

                # 检查兑换结果
                # 方法1: 查找成功提示
                success_messages = [
                    'xpath://div[contains(., "兑换成功")]',
                    'xpath://div[contains(., "成功")]',
                    'xpath://div[contains(@class, "success")]'
                ]

                is_success = False
                reward_text = ''

                for selector in success_messages:
                    try:
                        success_ele = driver.ele(selector, timeout=2)
                        if success_ele:
                            is_success = True
                            reward_text = success_ele.text
                            break
                    except:
                        continue

                # 方法2: 查找错误提示
                if not is_success:
                    error_messages = [
                        'xpath://div[contains(., "已使用")]',
                        'xpath://div[contains(., "无效")]',
                        'xpath://div[contains(., "错误")]',
                        'xpath://div[contains(@class, "error")]'
                    ]

                    for selector in error_messages:
                        try:
                            error_ele = driver.ele(selector, timeout=2)
                            if error_ele:
                                result['message'] = error_ele.text
                                logging.warning(f"兑换失败: {error_ele.text}")
                                return result
                        except:
                            continue

                # 如果找到成功消息
                if is_success:
                    result['success'] = True
                    result['message'] = '兑换成功'
                    result['reward'] = reward_text
                    logging.info(f"✅ 兑换成功: {email} - {code}")
                    logging.info(f"   奖励: {reward_text}")
                else:
                    # 未找到明确的成功或失败消息，可能需要等待
                    time.sleep(2)
                    result['message'] = '兑换结果未知（未找到明确提示）'
                    logging.warning(f"兑换结果未知: {email} - {code}")

                return result

        except Exception as e:
            logging.error(f"兑换过程出错: {e}", exc_info=True)
            result['message'] = f'兑换异常: {str(e)}'
            return result

    def batch_redeem(self, domain, email, password, codes):
        """
        批量兑换多个兑换码

        Args:
            domain: 域名
            email: 邮箱
            password: 密码
            codes: 兑换码列表

        Returns:
            dict: 批量兑换结果统计
        """
        if not codes:
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'results': []
            }

        results = []
        success_count = 0
        failed_count = 0

        for code in codes:
            logging.info(f"\n{'='*60}")
            logging.info(f"兑换码: {code}")
            logging.info(f"{'='*60}")

            result = self.redeem_code(domain, email, password, code)
            results.append(result)

            if result['success']:
                success_count += 1
            else:
                failed_count += 1

            # 兑换码之间等待，避免被限流
            time.sleep(2)

        logging.info(f"\n{'='*60}")
        logging.info(f"兑换完成统计:")
        logging.info(f"  总数: {len(codes)}")
        logging.info(f"  成功: {success_count}")
        logging.info(f"  失败: {failed_count}")
        logging.info(f"{'='*60}")

        return {
            'total': len(codes),
            'success': success_count,
            'failed': failed_count,
            'results': results
        }
