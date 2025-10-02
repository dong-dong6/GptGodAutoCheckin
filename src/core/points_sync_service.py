"""
积分同步服务
从GPT-GOD网站同步积分历史记录
"""
import logging
import time
import json
from src.core.browser_service import BrowserService
from src.data.repositories.points_repository import PointsHistoryManager
from src.data.repositories.config_repository import ConfigManager


class PointsSyncService(BrowserService):
    """
    积分同步服务类
    继承BrowserService，实现积分历史同步逻辑
    """

    def __init__(self, headless=False):
        """
        初始化积分同步服务

        Args:
            headless: 是否使用无头模式
        """
        super().__init__(headless=headless)
        self.points_manager = PointsHistoryManager()
        self.config_manager = ConfigManager()

    def fetch_account_history(self, domain, email, password, max_pages=None):
        """
        获取单个账号的积分历史

        Args:
            domain: 域名
            email: 邮箱
            password: 密码
            max_pages: 最大页数（None表示获取全部）

        Returns:
            dict: 同步结果
                {
                    'success': bool,
                    'email': str,
                    'total_records': int,
                    'new_records': int,
                    'message': str
                }
        """
        result = {
            'success': False,
            'email': email,
            'total_records': 0,
            'new_records': 0,
            'message': ''
        }

        try:
            with self.get_browser() as driver:
                # 登录账号
                if not self.login_account(domain, email, password):
                    result['message'] = '登录失败'
                    return result

                # 导航到积分历史页面
                history_url = f'https://{domain}/#/account/tokens'
                logging.info(f"访问积分历史页面: {history_url}")
                driver.get(history_url)
                time.sleep(5)

                # 开始监听API
                driver.listen.start('api/balance/list', method='POST')

                all_records = []
                page = 1

                while True:
                    if max_pages and page > max_pages:
                        logging.info(f"已达到最大页数限制: {max_pages}")
                        break

                    logging.info(f"获取第 {page} 页积分历史...")

                    # 触发页面加载（滚动或点击）
                    try:
                        # 执行JavaScript来加载更多数据
                        driver.run_js('window.scrollTo(0, document.body.scrollHeight);')
                        time.sleep(2)
                    except:
                        pass

                    # 等待API响应
                    try:
                        resp = driver.listen.wait(timeout=10)

                        if resp and resp.response.status == 200:
                            body = resp.response.body

                            if isinstance(body, str):
                                body = json.loads(body)

                            if body.get('code') == 0:
                                data = body.get('data', {})
                                records = data.get('records', [])

                                if not records:
                                    logging.info("没有更多记录")
                                    break

                                all_records.extend(records)
                                logging.info(f"第 {page} 页获取到 {len(records)} 条记录")

                                # 检查是否还有更多页
                                has_more = data.get('hasMore', False)
                                if not has_more:
                                    logging.info("已获取所有记录")
                                    break

                                page += 1
                                time.sleep(1)  # 避免请求过快
                            else:
                                logging.warning(f"API返回错误: {body.get('message', 'Unknown')}")
                                break
                        else:
                            logging.warning(f"API响应异常: status={resp.response.status if resp else 'None'}")
                            break

                    except Exception as e:
                        logging.error(f"监听API失败: {e}")
                        break

                # 停止监听
                try:
                    driver.listen.stop()
                except:
                    pass

                # 保存记录到数据库
                if all_records:
                    logging.info(f"开始保存 {len(all_records)} 条记录到数据库...")
                    new_count = self.points_manager.batch_add_records(all_records, email)

                    result['success'] = True
                    result['total_records'] = len(all_records)
                    result['new_records'] = new_count
                    result['message'] = f'成功同步 {new_count} 条新记录'

                    logging.info(f"✅ 账号 {email}: 总共 {len(all_records)} 条，新增 {new_count} 条")
                else:
                    result['success'] = True
                    result['message'] = '没有找到积分记录'
                    logging.warning(f"账号 {email} 没有积分历史记录")

                return result

        except Exception as e:
            logging.error(f"获取积分历史失败: {e}", exc_info=True)
            result['message'] = f'同步异常: {str(e)}'
            return result

    def sync_all_accounts(self, domain=None, max_pages=None):
        """
        同步所有账号的积分历史

        Args:
            domain: 域名（可选，默认从配置读取）
            max_pages: 每个账号的最大页数（None表示获取全部）

        Returns:
            dict: 批量同步结果统计
        """
        # 获取域名配置
        if not domain:
            domain_config = self.config_manager.get_domain_config()
            domain = domain_config.get('primary', 'gptgod.online')

        # 获取所有账号
        accounts = self.config_manager.get_accounts()

        if not accounts:
            logging.warning("没有配置任何账号")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'total_records': 0,
                'new_records': 0,
                'results': []
            }

        results = []
        success_count = 0
        failed_count = 0
        total_records = 0
        new_records = 0

        # 逐个同步
        for account in accounts:
            email = account['mail']
            password = account['password']

            logging.info(f"\n{'='*60}")
            logging.info(f"同步账号: {email}")
            logging.info(f"{'='*60}")

            result = self.fetch_account_history(domain, email, password, max_pages)
            results.append(result)

            if result['success']:
                success_count += 1
                total_records += result['total_records']
                new_records += result['new_records']
            else:
                failed_count += 1

            # 账号间等待
            time.sleep(2)

        logging.info(f"\n{'='*60}")
        logging.info(f"同步完成统计:")
        logging.info(f"  总账号数: {len(accounts)}")
        logging.info(f"  成功: {success_count}")
        logging.info(f"  失败: {failed_count}")
        logging.info(f"  总记录数: {total_records}")
        logging.info(f"  新增记录: {new_records}")
        logging.info(f"{'='*60}")

        return {
            'total': len(accounts),
            'success': success_count,
            'failed': failed_count,
            'total_records': total_records,
            'new_records': new_records,
            'results': results
        }
