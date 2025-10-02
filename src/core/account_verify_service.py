"""
账号验证服务
验证GPT-GOD账号凭证是否有效
"""
import logging
from src.core.browser_service import BrowserService


class AccountVerifyService(BrowserService):
    """
    账号验证服务类
    继承BrowserService，实现账号验证逻辑
    """

    def __init__(self, headless=True):  # 验证通常使用无头模式
        """
        初始化账号验证服务

        Args:
            headless: 是否使用无头模式（默认True）
        """
        super().__init__(headless=headless)

    def verify_account(self, domain, email, password):
        """
        验证单个账号

        Args:
            domain: 域名
            email: 邮箱
            password: 密码

        Returns:
            dict: 验证结果
                {
                    'success': bool,
                    'email': str,
                    'valid': bool,
                    'message': str
                }
        """
        result = {
            'success': False,
            'email': email,
            'valid': False,
            'message': ''
        }

        try:
            with self.get_browser() as driver:
                # 尝试登录
                login_success = self.login_account(domain, email, password)

                if login_success:
                    result['success'] = True
                    result['valid'] = True
                    result['message'] = '账号有效'
                    logging.info(f"✅ 账号有效: {email}")
                else:
                    result['success'] = True
                    result['valid'] = False
                    result['message'] = '账号无效或密码错误'
                    logging.warning(f"❌ 账号无效: {email}")

                return result

        except Exception as e:
            logging.error(f"验证账号时出错: {e}", exc_info=True)
            result['success'] = False
            result['message'] = f'验证异常: {str(e)}'
            return result

    def batch_verify(self, domain, accounts):
        """
        批量验证多个账号

        Args:
            domain: 域名
            accounts: 账号列表 [{'mail': '...', 'password': '...'}, ...]

        Returns:
            dict: 批量验证结果统计
        """
        if not accounts:
            return {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'error': 0,
                'results': []
            }

        results = []
        valid_count = 0
        invalid_count = 0
        error_count = 0

        for account in accounts:
            email = account['mail']
            password = account['password']

            logging.info(f"\n{'='*60}")
            logging.info(f"验证账号: {email}")
            logging.info(f"{'='*60}")

            result = self.verify_account(domain, email, password)
            results.append(result)

            if result['success']:
                if result['valid']:
                    valid_count += 1
                else:
                    invalid_count += 1
            else:
                error_count += 1

        logging.info(f"\n{'='*60}")
        logging.info(f"验证完成统计:")
        logging.info(f"  总数: {len(accounts)}")
        logging.info(f"  有效: {valid_count}")
        logging.info(f"  无效: {invalid_count}")
        logging.info(f"  错误: {error_count}")
        logging.info(f"{'='*60}")

        return {
            'total': len(accounts),
            'valid': valid_count,
            'invalid': invalid_count,
            'error': error_count,
            'results': results
        }
