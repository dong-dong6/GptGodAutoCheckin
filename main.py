import time
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import schedule
import yaml
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from checkin_logger import CheckinLogger
from checkin_logger_db import CheckinLoggerDB
from data_manager import DataManager
from points_history_manager import PointsHistoryManager
from user_info_listener import capture_user_info_during_checkin, setup_user_info_listener
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloudflare_bypass.log', mode='w', encoding='utf-8')
    ]
)


def send_email_notification(subject, body, config):
    """发送邮件通知"""
    try:
        # 从配置中读取邮件设置
        smtp_config = config.get('smtp', {})
        if not smtp_config.get('enabled', False):
            logging.info("邮件通知功能未启用")
            return False

        smtp_server = smtp_config.get('server', 'smtp.gmail.com')
        smtp_port = smtp_config.get('port', 587)
        sender_email = smtp_config.get('sender_email', '')
        sender_password = smtp_config.get('sender_password', '')
        receiver_emails = smtp_config.get('receiver_emails', [])

        if not sender_email or not sender_password or not receiver_emails:
            logging.warning("邮件配置不完整，跳过发送")
            return False

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(receiver_emails) if isinstance(receiver_emails, list) else receiver_emails
        msg['Subject'] = subject

        # 添加邮件正文
        msg.attach(MIMEText(body, 'html'))

        # 发送邮件
        if smtp_port == 465:
            # SSL端口
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                if isinstance(receiver_emails, list):
                    for receiver in receiver_emails:
                        server.send_message(msg, from_addr=sender_email, to_addrs=[receiver])
                else:
                    server.send_message(msg, from_addr=sender_email, to_addrs=[receiver_emails])
        else:
            # TLS端口
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                if isinstance(receiver_emails, list):
                    for receiver in receiver_emails:
                        server.send_message(msg, from_addr=sender_email, to_addrs=[receiver])
                else:
                    server.send_message(msg, from_addr=sender_email, to_addrs=[receiver_emails])

        logging.info(f"邮件通知发送成功: {subject}")
        return True
    except Exception as e:
        logging.error(f"发送邮件失败: {str(e)}")
        return False

def get_chromium_options(browser_path: str, arguments: list) -> ChromiumOptions:
    options = ChromiumOptions()
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options


def fetch_history_page_api(driver, page_number, page_size=100, is_first_page_with_listener=False):
    """获取指定页积分历史数据，逻辑与 fetch_points_history.py 保持一致"""
    try:
        if not is_first_page_with_listener:
            driver.listen.start('/api/user/token/list')

        if page_number == 1 and not is_first_page_with_listener:
            logging.info("等待第1页API响应...")
            time.sleep(3)
        elif page_number > 1 or (page_number == 1 and is_first_page_with_listener):
            if page_number > 1:
                try:
                    next_button = None
                    next_selectors = [
                        'li[@title="下一页"]/button[not(@disabled)]',
                        'button[@aria-label="Next Page" and not(@disabled)]',
                        'li[contains(@class, "ant-pagination-next") and not(contains(@class, "ant-pagination-disabled"))]'
                    ]

                    for selector in next_selectors:
                        try:
                            next_button = driver.ele(f'xpath://{selector}')
                            if next_button:
                                logging.info(f"使用选择器 {selector} 定位到下一页按钮")
                                break
                        except Exception:
                            continue

                    if not next_button:
                        css_selectors = [
                            '.ant-pagination-next:not(.ant-pagination-disabled)',
                            'li.ant-pagination-next:not(.ant-pagination-disabled)'
                        ]
                        for css_selector in css_selectors:
                            try:
                                next_button = driver.ele(f'css:{css_selector}')
                                if next_button:
                                    logging.info(f"使用CSS选择器 {css_selector} 定位到下一页按钮")
                                    break
                            except Exception:
                                continue

                    if next_button:
                        next_button.click()
                        logging.info(f"点击下一页，准备获取第{page_number}页数据")
                        time.sleep(2)
                    else:
                        logging.error(f"未找到可用的下一页按钮，无法获取第{page_number}页")
                        return None
                except Exception as e:
                    logging.error(f"翻页到第{page_number}页时出错: {e}")
                    return None
            else:
                logging.info("第1页已预先监听，等待API响应...")

        resp = driver.listen.wait(timeout=10)

        if resp:
            response_body = resp.response.body
            if isinstance(response_body, str):
                import json
                data = json.loads(response_body)
            else:
                data = response_body

            if data.get('code') == 0:
                page_data = data.get('data', {}) or {}
                records = page_data.get('rows', []) or []
                logging.info(f"成功获取第{page_number}页数据，共{len(records)}条记录")
                return page_data
            logging.error(f"API返回异常: {data}")
        else:
            logging.error(f"未收到第{page_number}页响应")
    except Exception as e:
        logging.error(f"获取第{page_number}页失败: {e}")
    finally:
        if not is_first_page_with_listener:
            try:
                driver.listen.stop()
            except Exception:
                pass

    return None


def fetch_points_history_for_account(driver, email, domain='gptgod.online'):
    try:
        driver.get(f'https://{domain}/#/token?tab=history')
        time.sleep(5)

        manager = PointsHistoryManager()
        total_new_records = 0
        all_records = []

        driver.listen.start('/api/user/token/list')
        logging.info("开始监听积分历史API")

        first_page_data = None

        try:
            logging.info(f"账号 {email} 开始获取积分历史记录")
            page_size_selectors = [
                '.ant-select.ant-pagination-options-size-changer',
                '.ant-pagination-options-size-changer .ant-select-selector',
                '.ant-select-selection-item[title*="条/页"]'
            ]

            page_size_dropdown = None
            for selector in page_size_selectors:
                try:
                    page_size_dropdown = driver.ele(f'css:{selector}')
                    if page_size_dropdown:
                        logging.info(f"找到分页大小选择器: {selector}")
                        break
                except Exception:
                    continue

            if page_size_dropdown:
                current_text = getattr(page_size_dropdown, 'text', '未知')
                logging.info(f"当前分页设置: {current_text}")

                page_size_dropdown.click()
                logging.info("展开分页下拉菜单")
                time.sleep(2)

                size_100_selectors = [
                    'div.ant-select-item[title="100 条/页"]',
                    'div.ant-select-item:contains("100")',
                    '.rc-virtual-list-holder div[title*="100"]',
                    '.ant-select-item-option-content:contains("100")'
                ]

                option_found = False
                for option_selector in size_100_selectors:
                    try:
                        option_100 = driver.ele(f'css:{option_selector}')
                        if option_100:
                            option_100.click()
                            logging.info(f"成功切换为100条/页，选择器: {option_selector}")
                            option_found = True
                            time.sleep(3)
                            break
                    except Exception:
                        continue

                if option_found:
                    logging.info("等待分页切换触发的API响应...")
                    resp = driver.listen.wait(timeout=15)
                    if resp and resp.response.body:
                        response_body = resp.response.body
                        if isinstance(response_body, str):
                            import json
                            data = json.loads(response_body)
                        else:
                            data = response_body

                        if data.get('code') == 0:
                            first_page_data = data.get('data', {}) or {}
                            records = first_page_data.get('rows', []) or []
                            logging.info(f"切换分页后预获取到{len(records)}条记录")
                        else:
                            logging.warning(f"分页API返回异常: {data}")
                    else:
                        logging.warning("未捕获到分页API响应，继续使用当前数据")
                else:
                    logging.warning("未找到100条/页选项，使用默认分页设置")
            else:
                logging.warning("未找到分页大小选择器，使用默认分页设置")
        except Exception as e:
            logging.debug(f"设置分页大小时出错: {e}")
        finally:
            try:
                driver.listen.stop()
            except Exception:
                pass

        time.sleep(2)

        page = 1

        while True:
            logging.info(f"正在获取第{page}页积分记录...")

            if page == 1 and first_page_data:
                logging.info("使用分页设置时获取到的第1页数据")
                page_data = first_page_data
            else:
                page_data = fetch_history_page_api(driver, page)
                if not page_data:
                    logging.warning(f"第{page}页未获取到数据，终止拉取")
                    break

            records = page_data.get('rows', []) or []
            if not records:
                logging.info("没有更多记录，结束拉取")
                break

            new_records = []
            for record in records:
                if not manager.record_exists(record.get('id')):
                    new_records.append(record)
                else:
                    logging.debug(f"跳过重复记录: ID={record.get('id')}")

            if new_records:
                added_count = manager.batch_add_records(new_records, email)
                total_new_records += added_count
                all_records.extend(new_records)
                logging.info(f"第{page}页: 获取{len(new_records)}条记录，写入{added_count}条")
            else:
                logging.info(f"第{page}页: {len(records)}条记录均已存在")

            has_next_page = False
            try:
                next_selectors = [
                    'li[@title="下一页"]/button[not(@disabled)]',
                    'button[@aria-label="Next Page" and not(@disabled)]',
                    'li[contains(@class, "ant-pagination-next") and not(contains(@class, "ant-pagination-disabled"))]',
                    '.ant-pagination-next:not(.ant-pagination-disabled)',
                    'li.ant-pagination-next:not(.ant-pagination-disabled)'
                ]

                for selector in next_selectors:
                    if selector.startswith('.'):
                        next_button = driver.ele(f'css:{selector}')
                    else:
                        next_button = driver.ele(f'xpath://{selector}')

                    if next_button:
                        has_next_page = True
                        logging.info(f"检测到下一页按钮: {selector}")
                        break

                if not has_next_page:
                    logging.info("未检测到可用的下一页按钮，抓取结束")
                    break

            except Exception as e:
                logging.warning(f"检测下一页按钮时异常: {e}")
                break

            page += 1
            time.sleep(2)

        logging.info(f"账号 {email} 本次新增 {total_new_records} 条积分记录")
        return all_records
    except Exception as e:
        logging.error(f"获取积分历史记录失败: {e}")
    finally:
        try:
            driver.listen.stop()
        except Exception:
            pass

    return []




def perform_checkin(driver, email, domain, logger_info, data_manager):
    """执行签到操作"""
    # 解析日志记录器信息
    use_db_logger = logger_info.get('use_db_logger', False)
    if use_db_logger:
        logger_db = logger_info['logger_db']
        session_id = logger_info['session_id']
    else:
        logger = logger_info['logger']
        log_idx = logger_info['log_idx']

    try:
        # 导航到签到页面
        driver.get(f'https://{domain}/#/token')
        logging.info("等待首页完全加载结束/Waiting for homepage to load completely")
        time.sleep(10)

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
            buttons = driver.eles('xpath://button')
            for button in buttons:
                button_text = button.text
                if "签到" in button_text and "今天已签到" not in button_text:
                    checkin_button = button
                    break

        # 检查是否已经签到
        already_checked = driver.ele('xpath://button[contains(., "今天已签到")]')
        if already_checked:
            logging.info(f"[已签到] 账号 {email} 今天已经签到过了")

            # 记录日志
            if use_db_logger:
                logger_db.log_account_result(session_id, email, 'already_checked', '今天已签到', 0, domain)
            else:
                logger.log_account_result(log_idx, email, 'already_checked', '今天已签到', 0)

            # 已签到的账号也获取一次积分信息用于更新记录
            driver.listen.start('api/user/info', method='GET')
            driver.refresh()
            time.sleep(3)

            current_points = 0
            try:
                resp = driver.listen.wait(timeout=5)
                if resp and resp.response.status == 200:
                    body = resp.response.body
                    if isinstance(body, str):
                        import json
                        body = json.loads(body)

                    if body.get('code') == 0 and 'data' in body:
                        user_info = body['data']
                        current_points = user_info.get('tokens', 0)
                        if data_manager:
                            data_manager.update_account_info(email, user_info)
                            logging.info(f"账号 {email} 当前积分: {current_points}")
            except Exception as e:
                logging.debug(f"获取用户信息失败: {e}")
            finally:
                try:
                    driver.listen.stop()
                except:
                    pass

            # 已签到的账号也获取历史积分记录，获取到重复记录为止
            try:
                fetch_points_history_for_account(driver, email, domain)
            except Exception as e:
                logging.warning(f"获取历史积分记录失败: {e}")

            return {
                'success': True,
                'email': email,
                'message': '今天已签到',
                'domain': domain,
                'points': 0,
                'current_points': current_points
            }

        if not checkin_button:
            logging.info("未找到签到按钮，可能已经签到")

            # 记录日志
            if use_db_logger:
                logger_db.log_account_result(session_id, email, 'unknown', '未找到签到按钮', 0, domain)
            else:
                logger.log_account_result(log_idx, email, 'unknown', '未找到签到按钮', 0)

            return {
                'success': False,
                'email': email,
                'message': '未找到签到按钮',
                'domain': domain,
                'current_points': 0
            }

        # 点击签到按钮
        checkin_button.click()
        logging.info("签到按钮点击成功/Check-in button clicked successfully")
        time.sleep(3)

        # Cloudflare验证
        driver_bypasser = CloudflareBypasser(driver)
        driver_bypasser.bypass()
        logging.info("Cloudflare验证完成")

        # 启动监听器准备捕获刷新后的用户信息
        driver.listen.start('api/user/info', method='GET')

        # 刷新页面验证签到状态
        logging.info("刷新页面验证签到状态...")
        driver.refresh()
        time.sleep(8)

        # 检查签到结果
        if driver.ele('xpath://button[contains(., "今天已签到")]'):
            logging.info(f"[成功] 账号 {email} 签到成功！按钮已变为'今天已签到'")

            # 获取签到后的用户信息
            current_points = 0
            points_earned = 2000  # 默认值

            try:
                # 等待API响应
                resp = driver.listen.wait(timeout=5)
                if resp and resp.response.status == 200:
                    body = resp.response.body
                    if isinstance(body, str):
                        import json
                        body = json.loads(body)

                    if body.get('code') == 0 and 'data' in body:
                        user_info = body['data']
                        current_points = user_info.get('tokens', 0)

                        if data_manager:
                            data_manager.update_account_info(email, user_info)
                            data_manager.record_checkin(email, True, points_earned)
                            logging.info(f"账号 {email} 签到成功，当前积分: {current_points}")

                            # 获取并保存历史积分记录，获取到重复记录为止
                            try:
                                fetch_points_history_for_account(driver, email, domain)
                            except Exception as e:
                                logging.warning(f"获取历史积分记录失败: {e}")
            except Exception as e:
                logging.debug(f"获取签到后用户信息失败: {e}")
            finally:
                try:
                    driver.listen.stop()
                except:
                    pass

            # 记录成功日志
            if use_db_logger:
                logger_db.log_account_result(session_id, email, 'success', '签到成功', points_earned, domain)
            else:
                logger.log_account_result(log_idx, email, 'success', '签到成功', points_earned)
            return {
                'success': True,
                'email': email,
                'message': '签到成功',
                'domain': domain,
                'points': points_earned,
                'current_points': current_points
            }
        else:
            logging.info(f"[未知] 账号 {email} 签到状态未知")

            # 记录日志
            if use_db_logger:
                logger_db.log_account_result(session_id, email, 'unknown', '签到状态未知', 0, domain)
            else:
                logger.log_account_result(log_idx, email, 'unknown', '签到状态未知', 0)

            try:
                driver.listen.stop()
            except:
                pass

            return {
                'success': False,
                'email': email,
                'message': '签到状态未知',
                'domain': domain,
                'current_points': 0
            }

    except Exception as e:
        logging.error(f"签到过程出错: {str(e)}")

        # 记录失败日志
        if use_db_logger:
            logger_db.log_account_result(session_id, email, 'failed', str(e), 0, domain)
        else:
            logger.log_account_result(log_idx, email, 'failed', str(e), 0)
        try:
            driver.listen.stop()
        except:
            pass
        return {
            'success': False,
            'email': email,
            'message': str(e),
            'domain': domain,
            'current_points': 0
        }

def process_account_with_retry(account, options, domains, logger_info, data_manager):
    """处理单个账号签到，支持域名切换重试"""
    # 解析日志记录器信息
    use_db_logger = logger_info.get('use_db_logger', False)
    if use_db_logger:
        logger_db = logger_info['logger_db']
        session_id = logger_info['session_id']
    else:
        logger = logger_info['logger']
        log_idx = logger_info['log_idx']

    email = account['mail']
    password = account['password']

    for domain in domains:
        logging.info(f"\n{'='*50}")
        logging.info(f"尝试使用域名: {domain} - 账号: {email}")
        driver = None

        try:
            driver = ChromiumPage(addr_or_opts=options)
            driver.set.window.full()

            # 访问登录页面
            login_url = f'https://{domain}/#/login'
            driver.get(login_url)

            # 等待页面完全加载
            logging.info("等待页面完全加载...")
            time.sleep(8)  # 给页面足够的加载时间

            # 检查页面是否正常加载
            if "login" not in driver.url.lower():
                logging.warning(f"页面未正确加载到登录页，当前URL: {driver.url}")
                if len(domains) > 1 and domain != domains[-1]:
                    continue  # 尝试下一个域名

            # 多种方式尝试定位邮箱输入框
            email_input = None
            for selector in [
                'xpath://input[@placeholder="请输入邮箱"]',
                'xpath://input[@type="text" and contains(@class, "ant-input")]',
                'xpath://input[@type="email"]',
                '#email'
            ]:
                try:
                    email_input = driver.ele(selector, timeout=3)
                    if email_input:
                        break
                except:
                    continue

            if not email_input:
                logging.error(f"无法在 {domain} 找到邮箱输入框")
                if len(domains) > 1 and domain != domains[-1]:
                    continue
                raise Exception("无法定位邮箱输入框")

            # 多种方式尝试定位密码输入框
            password_input = None
            for selector in [
                'xpath://input[@type="password"]',
                'xpath://input[contains(@placeholder, "密码")]',
                '#password'
            ]:
                try:
                    password_input = driver.ele(selector, timeout=3)
                    if password_input:
                        break
                except:
                    continue

            if not password_input:
                logging.error(f"无法在 {domain} 找到密码输入框")
                if len(domains) > 1 and domain != domains[-1]:
                    continue
                raise Exception("无法定位密码输入框")

            # 输入登录信息
            logging.info("输入登录信息...")
            email_input.clear()
            email_input.input(email)
            time.sleep(0.5)
            password_input.clear()
            password_input.input(password)
            time.sleep(0.5)

            # 查找登录按钮
            login_button = None
            for selector in [
                'xpath://button[contains(@class, "ant-btn-primary")]',
                'xpath://button[contains(., "登录")]',
                'xpath://button[contains(., "Login")]',
                'xpath://button[@type="submit"]'
            ]:
                try:
                    login_button = driver.ele(selector, timeout=3)
                    if login_button and not login_button.attr('disabled'):
                        break
                except:
                    continue

            if not login_button:
                logging.error(f"无法在 {domain} 找到登录按钮")
                if len(domains) > 1 and domain != domains[-1]:
                    continue
                raise Exception("无法找到登录按钮")

            # 点击登录
            login_button.click()
            logging.info("登录按钮点击成功")

            # 等待登录完成和页面跳转
            time.sleep(8)

            # 检查是否登录成功
            if "login" in driver.url.lower():
                logging.error(f"登录失败，仍在登录页面: {driver.url}")
                if len(domains) > 1 and domain != domains[-1]:
                    continue
                raise Exception("登录失败")

            # 准备日志记录器信息
            if use_db_logger:
                current_logger_info = {
                    'use_db_logger': True,
                    'logger_db': logger_db,
                    'session_id': session_id
                }
            else:
                current_logger_info = {
                    'use_db_logger': False,
                    'logger': logger,
                    'log_idx': log_idx
                }

            # 签到操作
            result = perform_checkin(driver, email, domain, current_logger_info, data_manager)

            if result['success']:
                return result
            elif len(domains) > 1 and domain != domains[-1]:
                logging.info(f"在 {domain} 签到失败，尝试备用域名...")
                continue
            else:
                return result

        except Exception as e:
            logging.error(f"在 {domain} 处理账号 {email} 失败: {str(e)}")
            if len(domains) > 1 and domain != domains[-1]:
                logging.info("尝试备用域名...")
                continue
            else:
                # 记录失败
                if use_db_logger:
                    logger_db.log_account_result(session_id, email, 'failed', str(e), 0, domain)
                else:
                    logger.log_account_result(log_idx, email, 'failed', str(e), 0)
                return {
                    'success': False,
                    'email': email,
                    'message': str(e),
                    'domain': domain
                }
        finally:
            if driver:
                try:
                    logging.info("关闭浏览器/Closing the browser.")
                    driver.quit()
                except:
                    pass
                time.sleep(3)

    # 所有域名都失败
    if use_db_logger:
        logger_db.log_account_result(session_id, email, 'failed', '所有域名均失败', 0)
    else:
        logger.log_account_result(log_idx, email, 'failed', '所有域名均失败', 0)
    return {
        'success': False,
        'email': email,
        'message': '所有域名均无法签到',
        'domain': 'all'
    }

def load_config():
    """加载配置 - 优先使用数据库配置，如果不存在则使用YAML配置"""
    config_manager = ConfigManager()

    # 检查数据库中是否有配置
    try:
        # 尝试获取配置
        config = config_manager.get_all_config()

        # 检查是否有账号配置（作为数据库配置是否初始化的标志）
        if config['account']:
            logging.info("使用数据库配置")
            return config
        else:
            logging.info("数据库配置为空，尝试从YAML迁移")
    except Exception as e:
        logging.warning(f"读取数据库配置失败: {e}，尝试从YAML迁移")

    # 如果数据库配置不存在或为空，尝试从YAML迁移
    yaml_file = 'account.yml'
    if os.path.exists(yaml_file):
        logging.info(f"从 {yaml_file} 迁移配置到数据库")
        if config_manager.migrate_from_yaml(yaml_file):
            logging.info("配置迁移成功，使用数据库配置")
            return config_manager.get_all_config()
        else:
            logging.error("配置迁移失败，回退到YAML配置")
            # 回退到YAML配置
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logging.error(f"读取YAML配置失败: {e}")
                raise
    else:
        logging.error(f"配置文件 {yaml_file} 不存在")
        raise FileNotFoundError(f"配置文件 {yaml_file} 不存在")


def main(trigger_type='manual', trigger_by=None):
    isHeadless = os.getenv('HEADLESS', 'false').lower() == 'true'

    if isHeadless:
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1920, 1080))
        display.start()

    # Read configuration - prioritize database config over YAML
    config = load_config()

    accounts = config.get('account', [])

    # 获取域名配置
    domain_config = config.get('domains', {})
    primary_domain = domain_config.get('primary', 'gptgod.work')
    backup_domain = domain_config.get('backup', 'gptgod.online')
    auto_switch = domain_config.get('auto_switch', True)

    # 设置域名列表
    domains = [primary_domain]
    if auto_switch and backup_domain and backup_domain != primary_domain:
        domains.append(backup_domain)

    # 初始化日志记录器 - 优先使用数据库版本
    try:
        logger_db = CheckinLoggerDB()
        session_id = logger_db.log_checkin_start(trigger_type, trigger_by)
        use_db_logger = True
        logger = None  # 初始化为None
        log_idx = None  # 初始化为None
        logging.info("使用数据库日志记录器")
    except Exception as e:
        logging.warning(f"数据库日志记录器初始化失败，回退到文件日志: {e}")
        logger = CheckinLogger()
        log_idx = logger.log_checkin_start(trigger_type, trigger_by)
        logger_db = None  # 初始化为None
        session_id = None  # 初始化为None
        use_db_logger = False

    # 初始化数据管理器
    data_manager = DataManager()

    # 浏览器配置
    browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")
    arguments = [
        "--incognito",  # 启用隐私模式
        "-no-first-run",
        "-force-color-profile=srgb",
        "-metrics-recording-only",
        "-password-store=basic",
        "-use-mock-keychain",
        "-export-tagged-pdf",
        "-no-default-browser-check",
        "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
        "-deny-permission-prompts",
        "-disable-gpu",
        "--lang=zh-CN",  # 设置浏览器语言为中文
        "--accept-lang=zh-CN,zh;q=0.9",  # 设置接受的语言为中文
        "--disable-dev-tools"
    ]

    options = get_chromium_options(browser_path, arguments)

    # 汇总结果
    all_results = []
    success_count = 0
    fail_count = 0
    total_points = 0

    # 处理每个账号
    for account in accounts:
        # 准备日志记录器信息
        if use_db_logger:
            logger_info = {
                'use_db_logger': True,
                'logger_db': logger_db,
                'session_id': session_id
            }
        else:
            logger_info = {
                'use_db_logger': False,
                'logger': logger,
                'log_idx': log_idx
            }

        result = process_account_with_retry(account, options, domains, logger_info, data_manager)
        all_results.append(result)

        if result['success']:
            success_count += 1
            total_points += result.get('points', 0)
        else:
            fail_count += 1

        logging.info(f"账号 {result['email']} 处理完成: {result['message']}")

    # 添加积分快照
    data_manager.add_points_snapshot()

    # 记录签到结束
    email_sent = False

    # 生成邮件内容
    if config.get('smtp', {}).get('enabled', False):
        # 获取积分统计信息
        points_distribution = data_manager.get_points_distribution()
        top_accounts = data_manager.get_top_accounts(5)

        email_body = f"""
        <html>
        <body>
            <h2>GPT-GOD 签到报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h2>

            <h3>📊 统计信息</h3>
            <ul>
                <li>总账号数: {len(accounts)}</li>
                <li>成功签到: {success_count}</li>
                <li>签到失败: {fail_count}</li>
                <li>获得积分: {total_points}</li>
                <li>所有账号总积分: {data_manager.summary['total_points']}</li>
            </ul>

            <h3>💰 积分分布</h3>
            <table border="1" style="border-collapse: collapse;">
                <tr><th>积分范围</th><th>账号数量</th></tr>
        """

        for range_key, count in points_distribution.items():
            email_body += f"<tr><td>{range_key}</td><td>{count}</td></tr>"

        email_body += """
            </table>

            <h3>🏆 Top 5 账号</h3>
            <table border="1" style="border-collapse: collapse;">
                <tr><th>账号</th><th>积分</th></tr>
        """

        for acc in top_accounts[:5]:
            email_body += f"<tr><td>{acc['email']}</td><td>{acc['points']}</td></tr>"

        email_body += """
            </table>

            <h3>📝 详细结果</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>账号</th>
                    <th>域名</th>
                    <th>状态</th>
                    <th>消息</th>
                    <th>获得积分</th>
                    <th>当前积分</th>
                </tr>
        """

        for result in all_results:
            status_emoji = "✅" if result['success'] else "❌"
            email_body += f"""
                <tr>
                    <td>{result['email']}</td>
                    <td>{result.get('domain', 'N/A')}</td>
                    <td>{status_emoji}</td>
                    <td>{result['message']}</td>
                    <td>{result.get('points', 0)}</td>
                    <td>{result.get('current_points', 'N/A')}</td>
                </tr>
            """

        email_body += """
            </table>

            <h3>📋 运行日志</h3>
            <pre style="background: #f0f0f0; padding: 10px; overflow-x: auto;">
        """

        # 读取日志文件内容
        try:
            with open('cloudflare_bypass.log', 'r', encoding='utf-8') as f:
                log_content = f.read()
                # 限制日志长度
                if len(log_content) > 50000:
                    log_content = log_content[-50000:]
                email_body += log_content.replace('<', '&lt;').replace('>', '&gt;')
        except:
            email_body += "无法读取日志文件"

        email_body += """
            </pre>
        </body>
        </html>
        """

        subject = f"GPT-GOD 签到报告 - {datetime.now().strftime('%Y-%m-%d')}"
        email_sent = send_email_notification(subject, email_body, config)

    # 记录签到结束
    if use_db_logger:
        logger_db.log_checkin_end(session_id, email_sent)
        # 获取统计信息
        stats = logger_db.get_statistics()
        logging.info(f"今日签到统计: 成功 {success_count} 个, 失败 {fail_count} 个")
        logging.info(f"总计签到次数: {stats['all_time']['successful_checkins']}")
    else:
        logger.log_checkin_end(log_idx, email_sent)
        # 输出统计信息
        stats = logger.get_statistics()
        logging.info(f"今日签到统计: 成功 {success_count} 个, 失败 {fail_count} 个")
        logging.info(f"总计签到次数: {stats['all_time']['successful_checkins']}")
    logging.info(f"总计获得积分: {stats['all_time']['total_points_earned']}")

    logging.info("操作完成/Operation completed!")
    logging.info(f"页面标题/Page title: GPT-GOD")

    if isHeadless:
        display.stop()

if __name__ == '__main__':
    main()