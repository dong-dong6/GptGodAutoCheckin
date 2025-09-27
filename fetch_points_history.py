#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
从GPT-GOD网站获取历史积分记录
"""

import json
import logging
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from points_history_manager import PointsHistoryManager
from main import get_chromium_options
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config():
    """加载配置文件"""
    try:
        with open('account.yml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"加载配置失败: {e}")
        return {}

def login_account(driver, email, password, domain='gptgod.online'):
    """登录账号"""
    try:
        # 访问登录页面
        driver.get(f'https://{domain}/#/login')
        time.sleep(5)

        # 输入邮箱和密码
        email_input = driver.ele('xpath://input[@placeholder="请输入邮箱"]', timeout=10)
        password_input = driver.ele('xpath://input[@type="password"]', timeout=10)

        if email_input and password_input:
            email_input.clear()
            email_input.input(email)
            password_input.clear()
            password_input.input(password)

            # 点击登录
            login_button = driver.ele('xpath://button[contains(@class, "ant-btn-primary")]', timeout=5)
            if login_button:
                login_button.click()
                time.sleep(5)
                logging.info(f"账号 {email} 登录成功")
                return True
    except Exception as e:
        logging.error(f"登录失败: {e}")
    return False

def fetch_history_page(driver, page_number, page_size=100, is_first_page_with_listener=False):
    """获取一页历史记录 - 使用API监听

    Args:
        driver: 浏览器驱动
        page_number: 页码
        page_size: 每页记录数
        is_first_page_with_listener: 第一页是否已经启动了监听器

    Returns:
        dict: API响应数据
    """
    try:
        # 如果不是已启动监听器的第一页，则启动新的监听器
        if not is_first_page_with_listener:
            driver.listen.start('/api/user/token/list')

        if page_number == 1 and not is_first_page_with_listener:
            # 第一页且没有预启动监听器：等待API请求
            logging.info("等待第1页API请求...")
            time.sleep(3)  # 等待页面自动加载API数据

        elif page_number > 1 or (page_number == 1 and is_first_page_with_listener):
            # 后续页或已预启动监听器的第一页：点击获取数据
            if page_number > 1:
                # 点击下一页
                try:
                    # 查找下一页按钮 - 使用多种选择器策略
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
                                logging.info(f"使用选择器找到下一页按钮: {selector}")
                                break
                        except:
                            continue

                    # 如果xpath失败，尝试CSS选择器
                    if not next_button:
                        css_selectors = [
                            '.ant-pagination-next:not(.ant-pagination-disabled)',
                            'li.ant-pagination-next:not(.ant-pagination-disabled)'
                        ]
                        for css_selector in css_selectors:
                            try:
                                next_button = driver.ele(f'css:{css_selector}')
                                if next_button:
                                    logging.info(f"使用CSS选择器找到下一页按钮: {css_selector}")
                                    break
                            except:
                                continue

                    if next_button:
                        next_button.click()
                        logging.info(f"点击下一页，获取第{page_number}页")
                        time.sleep(2)  # 等待页面加载
                    else:
                        logging.error(f"未找到下一页按钮，无法获取第{page_number}页")
                        if not is_first_page_with_listener:
                            driver.listen.stop()
                        return None

                except Exception as e:
                    logging.error(f"点击下一页时出错: {e}")
                    if not is_first_page_with_listener:
                        driver.listen.stop()
                    return None
            else:
                # 第一页且已预启动监听器，直接等待即可
                logging.info("第1页已预启动监听器，直接等待API响应...")

        # 等待API响应
        resp = driver.listen.wait(timeout=10)

        if resp:
            response_body = resp.response.body
            if isinstance(response_body, str):
                import json
                data = json.loads(response_body)
            else:
                data = response_body

            if data.get('code') == 0:
                page_data = data.get('data', {})
                records = page_data.get('rows', [])
                logging.info(f"成功获取第{page_number}页数据，共{len(records)}条记录")

                # 停止监听
                if not is_first_page_with_listener:
                    driver.listen.stop()
                return page_data
            else:
                logging.error(f"API返回错误: {data}")
        else:
            logging.error(f"未收到第{page_number}页的响应")

        # 停止监听
        if not is_first_page_with_listener:
            try:
                driver.listen.stop()
            except:
                pass

    except Exception as e:
        logging.error(f"获取第{page_number}页失败: {e}")
        if not is_first_page_with_listener:
            try:
                driver.listen.stop()
            except:
                pass

    return None

def fetch_all_history(email, password, domain='gptgod.online'):
    """获取账号的所有历史记录

    Args:
        email: 账号邮箱
        password: 账号密码
        domain: 域名

    Returns:
        list: 所有历史记录
    """
    all_records = []
    driver = None

    try:
        # 创建浏览器实例
        browser_path = "/usr/bin/google-chrome"
        arguments = [
            "--lang=zh-CN",
            "--accept-lang=zh-CN,zh;q=0.9",
            "--disable-gpu",
            "--disable-dev-tools"
        ]

        options = get_chromium_options(browser_path, arguments)
        driver = ChromiumPage(addr_or_opts=options)
        driver.set.window.max()

        # 登录
        if not login_account(driver, email, password, domain):
            logging.error(f"账号 {email} 登录失败")
            return []

        # 初始化数据库管理器
        manager = PointsHistoryManager()

        # 导航到历史记录页面
        driver.get(f'https://{domain}/#/token?tab=history')
        time.sleep(5)

        # 先启动API监听器（在任何操作之前）
        driver.listen.start('/api/user/token/list')
        logging.info("已启动API监听器")

        # 存储第一页数据（设置分页时获取）
        first_page_data = None

        # 设置每页显示100条记录
        try:
            # 查找分页大小选择器 - 基于实际HTML结构
            page_size_selectors = [
                '.ant-select.ant-pagination-options-size-changer',  # 主选择器
                '.ant-pagination-options-size-changer .ant-select-selector',  # 选择器容器
                '.ant-select-selection-item[title*="条/页"]'  # 当前显示的选项
            ]

            page_size_dropdown = None
            for selector in page_size_selectors:
                try:
                    page_size_dropdown = driver.ele(f'css:{selector}')
                    if page_size_dropdown:
                        logging.info(f"找到分页选择器: {selector}")
                        break
                except:
                    continue

            if page_size_dropdown:
                current_text = page_size_dropdown.text if hasattr(page_size_dropdown, 'text') else "未知"
                logging.info(f"当前分页设置: {current_text}")

                # 点击分页选择器打开下拉菜单
                page_size_dropdown.click()
                logging.info("点击了分页选择器")
                time.sleep(2)

                # 查找100条/页选项
                size_100_selectors = [
                    'div.ant-select-item[title="100 条/页"]',  # 精确匹配
                    'div.ant-select-item:contains("100")',    # 包含100的选项
                    '.rc-virtual-list-holder div[title*="100"]',  # 虚拟列表中的选项
                    '.ant-select-item-option-content:contains("100")'  # 选项内容
                ]

                option_found = False
                for option_selector in size_100_selectors:
                    try:
                        option_100 = driver.ele(f'css:{option_selector}')
                        if option_100:
                            option_100.click()
                            logging.info(f"成功点击100条/页选项，使用选择器: {option_selector}")
                            option_found = True
                            time.sleep(3)  # 等待页面重新加载
                            break
                    except Exception as e:
                        logging.debug(f"选择器 {option_selector} 失败: {e}")

                if option_found:
                    # 等待API响应（由于设置100条/页会触发新的API请求）
                    logging.info("等待100条/页设置触发的API响应...")
                    resp = driver.listen.wait(timeout=10)
                    if resp:
                        response_body = resp.response.body
                        if isinstance(response_body, str):
                            import json
                            data = json.loads(response_body)
                        else:
                            data = response_body

                        if data.get('code') == 0:
                            first_page_data = data.get('data', {})
                            records = first_page_data.get('rows', [])
                            logging.info(f"设置100条/页后获取到{len(records)}条记录，将作为第1页数据")
                        else:
                            logging.warning("设置分页后API返回错误")
                    else:
                        logging.warning("未捕获到设置分页后的API响应")
                else:
                    logging.warning("未找到100条/页选项，继续使用默认分页")
                    # 点击页面其他地方关闭下拉菜单
                    try:
                        driver.ele('css:body').click()
                        time.sleep(1)
                    except:
                        pass
            else:
                logging.warning("未找到分页大小选择器，将使用默认分页(20条/页)")

        except Exception as e:
            logging.warning(f"设置分页大小失败: {e}")

        # 停止之前的监听器
        try:
            driver.listen.stop()
        except:
            pass

        time.sleep(2)  # 等待页面稳定

        page = 1
        stop_fetching = False

        while not stop_fetching:
            logging.info(f"正在获取第{page}页...")

            # 获取当前页数据
            if page == 1 and first_page_data:
                # 第一页直接使用设置分页时获取的数据
                logging.info("使用设置分页时获取的第1页数据")
                page_data = first_page_data
            else:
                # 其他页面正常获取
                try:
                    page_data = fetch_history_page(driver, page)
                except Exception as e:
                    logging.error(f"获取第{page}页时出错: {e}")
                    logging.info("等待5分钟后重试...")
                    time.sleep(300)  # 等待5分钟
                    continue

                if not page_data:
                    logging.warning(f"第{page}页未获取到数据，等待5分钟后重试...")
                    time.sleep(300)  # 等待5分钟
                    continue

            records = page_data.get('rows', [])
            if not records:
                logging.info("没有更多记录")
                break

            # 检查重复记录（基于API返回的ID）
            new_records = []
            for record in records:
                # 检查是否已存在相同ID的记录
                if not manager.record_exists(record.get('id')):
                    new_records.append(record)
                else:
                    logging.debug(f"跳过重复记录: ID={record.get('id')}")

            if new_records:
                all_records.extend(new_records)
                # 批量保存到数据库
                added_count = manager.batch_add_records(new_records, email)
                logging.info(f"第{page}页: 获取{len(new_records)}条新记录，成功保存{added_count}条")
            else:
                logging.info(f"第{page}页: 所有记录都已存在，跳过")

            # 如果所有记录都是重复的，可能已经获取完毕
            if len(new_records) == 0 and len(records) > 0:
                logging.info("所有记录都已存在，可能已获取完所有新数据")
                # 但继续获取下一页，确保完整性

            # 检查DOM中是否还有下一页按钮
            logging.info(f"当前页: {page}, 本页记录数: {len(records)}")

            # 检查下一页按钮是否存在且可用
            has_next_page = False
            try:
                # 检查多种可能的下一页按钮选择器
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
                        logging.info(f"找到可用的下一页按钮: {selector}")
                        break

                if not has_next_page:
                    logging.info("未找到可用的下一页按钮，已到最后一页")
                    break

            except Exception as e:
                logging.warning(f"检查下一页按钮时出错: {e}")
                break

            if stop_fetching:
                break

            page += 1
            time.sleep(2)  # 避免请求过快

        logging.info(f"账号 {email} 共获取 {len(all_records)} 条新记录")

        # 获取并显示统计信息
        stats = manager.get_statistics(email=email)
        logging.info(f"账号统计 - 总记录数: {stats['total_count']}, 总获得: {stats['total_earned']}, 总消耗: {stats['total_spent']}")

    except Exception as e:
        logging.error(f"获取历史记录失败: {e}")
    finally:
        if driver:
            driver.quit()

    return all_records

def fetch_all_accounts_history():
    """获取所有账号的历史记录"""
    config = load_config()
    accounts = config.get('account', [])
    domain_config = config.get('domains', {})
    primary_domain = domain_config.get('primary', 'gptgod.online')

    if not accounts:
        logging.error("没有找到账号配置")
        return

    logging.info(f"开始获取 {len(accounts)} 个账号的历史记录")

    manager = PointsHistoryManager()
    total_new_records = 0

    for i, account in enumerate(accounts):
        email = account.get('mail')
        password = account.get('password')

        if not email or not password:
            continue

        logging.info(f"[{i+1}/{len(accounts)}] 处理账号: {email}")

        # 获取该账号的历史记录
        records = fetch_all_history(email, password, primary_domain)
        total_new_records += len(records)

        # 休息一下，避免频繁操作
        if i < len(accounts) - 1:
            time.sleep(5)

    logging.info(f"所有账号处理完成，共获取 {total_new_records} 条新记录")

    # 导出汇总数据
    export_file = manager.export_to_json('points_history_export.json')
    logging.info(f"数据已导出到: {export_file}")

    # 显示总体统计
    overall_stats = manager.get_statistics()
    logging.info("=" * 50)
    logging.info("总体统计信息:")
    logging.info(f"  总记录数: {overall_stats['total_count']}")
    logging.info(f"  总获得积分: {overall_stats['total_earned']}")
    logging.info(f"  总消耗积分: {overall_stats['total_spent']}")
    logging.info(f"  净积分: {overall_stats['net_points']}")
    logging.info("各来源统计:")
    for source, data in overall_stats['by_source'].items():
        logging.info(f"  {source}: 次数={data['count']}, 获得={data['earned']}, 消耗={data['spent']}")

if __name__ == '__main__':
    # 运行主函数
    fetch_all_accounts_history()