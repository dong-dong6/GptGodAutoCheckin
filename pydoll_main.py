#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用Pydoll的GPT-GOD自动签到主程序
支持多账号、定时任务、邮件通知和数据库日志
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from config_manager import ConfigManager
from checkin_logger_db import CheckinLoggerDB
from points_history_manager import PointsHistoryManager
from pydoll_browser_manager import PydollBrowserManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pydoll_checkin.log', mode='w', encoding='utf-8')
    ]
)


async def perform_login(tab, email, password, domain):
    """
    执行登录操作

    Args:
        tab: Pydoll Tab实例
        email: 邮箱
        password: 密码
        domain: 域名

    Returns:
        bool: 是否登录成功
    """
    try:
        login_url = f'https://{domain}/#/login'
        logging.info(f"访问登录页面: {login_url}")
        await tab.go_to(login_url)
        await asyncio.sleep(5)

        # 填写登录表单
        login_script = f"""
        const emailInput = document.querySelector('input[type="email"]') ||
                          document.querySelector('input[placeholder*="邮箱"]') ||
                          document.querySelector('input[placeholder*="email"]');
        const passwordInput = document.querySelector('input[type="password"]');

        if (emailInput && passwordInput) {{
            emailInput.value = '{email}';
            passwordInput.value = '{password}';
            emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            passwordInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            return {{ success: true }};
        }}
        return {{ success: false, message: '未找到登录表单' }};
        """

        result = await tab.execute_script(login_script)
        if not result.get('success'):
            logging.error("登录表单填写失败")
            return False

        await asyncio.sleep(2)

        # 点击登录按钮
        click_login_script = """
        const loginButton = document.querySelector('button[type="submit"]') ||
                           Array.from(document.querySelectorAll('button')).find(btn =>
                               btn.textContent.includes('登录') || btn.textContent.includes('Login')
                           );
        if (loginButton) {
            loginButton.click();
            return { success: true };
        }
        return { success: false };
        """

        result = await tab.execute_script(click_login_script)
        if not result.get('success'):
            logging.error("未找到登录按钮")
            return False

        logging.info("已点击登录按钮，等待登录...")
        await asyncio.sleep(5)

        return True

    except Exception as e:
        logging.error(f"登录过程出错: {e}")
        return False


async def perform_checkin_pydoll(tab, email, domain, logger_db, session_id, data_manager):
    """
    使用Pydoll执行签到操作

    Args:
        tab: Pydoll Tab实例
        email: 账号邮箱
        domain: 网站域名
        logger_db: 数据库日志记录器
        session_id: 会话ID
        data_manager: 数据管理器

    Returns:
        dict: 签到结果
    """
    try:
        # 导航到签到页面
        checkin_url = f'https://{domain}/#/token'
        logging.info(f"导航到签到页面: {checkin_url}")
        await tab.go_to(checkin_url)
        await asyncio.sleep(8)

        # 查找并点击签到按钮
        checkin_script = """
        // 检查是否已签到
        const alreadyChecked = Array.from(document.querySelectorAll('button')).find(btn =>
            btn.textContent.includes('今天已签到')
        );

        if (alreadyChecked) {
            return { success: true, alreadyChecked: true, message: '今天已签到' };
        }

        // 查找签到按钮
        const checkinButton = Array.from(document.querySelectorAll('button')).find(btn =>
            btn.textContent.includes('签到') && !btn.textContent.includes('今天已签到')
        );

        if (checkinButton) {
            checkinButton.click();
            return { success: true, alreadyChecked: false, message: '签到成功' };
        }

        return { success: false, message: '未找到签到按钮' };
        """

        result = await tab.execute_script(checkin_script)

        if not result.get('success'):
            logging.error(f"签到失败: {result.get('message')}")
            logger_db.log_account_result(session_id, email, 'failed', result.get('message'), 0, domain)
            return {
                'success': False,
                'email': email,
                'message': result.get('message'),
                'domain': domain,
                'current_points': 0
            }

        if result.get('alreadyChecked'):
            logging.info(f"[已签到] 账号 {email} 今天已经签到过了")
            logger_db.log_account_result(session_id, email, 'already_checked', '今天已签到', 0, domain)
            message = '今天已签到'
            points_earned = 0
        else:
            logging.info(f"[签到成功] 账号 {email} 签到成功")
            await asyncio.sleep(3)
            message = '签到成功'
            points_earned = 5  # 假设签到获得5积分

            logger_db.log_account_result(session_id, email, 'success', message, points_earned, domain)

        # 获取当前积分
        await asyncio.sleep(2)
        current_points = await get_current_points(tab, email, data_manager)

        return {
            'success': True,
            'email': email,
            'message': message,
            'domain': domain,
            'points': points_earned,
            'current_points': current_points
        }

    except Exception as e:
        logging.error(f"签到过程出错: {e}", exc_info=True)
        logger_db.log_account_result(session_id, email, 'error', str(e), 0, domain)
        return {
            'success': False,
            'email': email,
            'message': str(e),
            'domain': domain,
            'current_points': 0
        }


async def get_current_points(tab, email, data_manager):
    """
    获取当前积分

    Args:
        tab: Pydoll Tab实例
        email: 邮箱
        data_manager: 数据管理器

    Returns:
        int: 当前积分
    """
    try:
        # 刷新页面获取最新信息
        await tab.refresh()
        await asyncio.sleep(3)

        # 尝试从页面中获取积分
        get_points_script = """
        const pointsElement = document.querySelector('[class*="token"]') ||
                             document.querySelector('[class*="point"]');
        if (pointsElement) {
            return { success: true, points: pointsElement.textContent };
        }
        return { success: false };
        """

        result = await tab.execute_script(get_points_script)
        if result.get('success'):
            import re
            points_text = result.get('points', '0')
            match = re.search(r'\d+', points_text)
            if match:
                current_points = int(match.group())
                logging.info(f"账号 {email} 当前积分: {current_points}")
                return current_points

        return 0

    except Exception as e:
        logging.debug(f"获取积分失败: {e}")
        return 0


async def checkin_single_account(account, domains, logger_db, session_id, data_manager):
    """
    单个账号的签到流程

    Args:
        account: 账号信息字典
        domains: 域名列表
        logger_db: 数据库日志记录器
        session_id: 会话ID
        data_manager: 数据管理器

    Returns:
        dict: 签到结果
    """
    email = account['mail']
    password = account['password']

    logging.info(f"\n{'='*60}")
    logging.info(f"开始签到: {email}")
    logging.info(f"{'='*60}")

    browser_manager = PydollBrowserManager(headless=False)

    try:
        # 创建浏览器
        tab = await browser_manager.create_browser()

        # 启用Cloudflare绕过
        await browser_manager.enable_cloudflare_bypass()

        # 尝试每个域名
        for domain in domains:
            try:
                logging.info(f"尝试域名: {domain}")

                # 执行登录
                login_success = await perform_login(tab, email, password, domain)

                if not login_success:
                    logging.warning(f"域名 {domain} 登录失败，尝试下一个")
                    continue

                # 执行签到
                result = await perform_checkin_pydoll(
                    tab, email, domain, logger_db, session_id, data_manager
                )

                if result['success']:
                    return result

            except Exception as e:
                logging.error(f"域名 {domain} 签到失败: {e}")
                continue

        # 所有域名都失败
        logger_db.log_account_result(session_id, email, 'failed', '所有域名均失败', 0, domains[0])
        return {
            'success': False,
            'email': email,
            'message': '所有域名均失败',
            'domain': domains[0],
            'current_points': 0
        }

    except Exception as e:
        logging.error(f"账号 {email} 签到异常: {e}", exc_info=True)
        logger_db.log_account_result(session_id, email, 'error', str(e), 0, domains[0])
        return {
            'success': False,
            'email': email,
            'message': str(e),
            'domain': domains[0],
            'current_points': 0
        }

    finally:
        # 关闭浏览器
        await browser_manager.close()


async def run_checkin_task():
    """运行签到任务"""
    logging.info("\n" + "="*60)
    logging.info("启动Pydoll签到任务")
    logging.info("="*60 + "\n")

    # 初始化配置和数据库
    config_manager = ConfigManager()
    config = config_manager.get_all_config()
    accounts = config_manager.get_accounts()

    if not accounts:
        logging.error("未找到任何账号配置")
        return

    # 初始化日志和数据管理
    logger_db = CheckinLoggerDB()
    session_id = logger_db.create_session(len(accounts))
    data_manager = PointsHistoryManager()

    # 获取域名配置
    domains_config = config.get('domains', {})
    primary_domain = domains_config.get('primary', 'gptgod.online')
    backup_domain = domains_config.get('backup', 'gptgod.work')
    domains = [primary_domain, backup_domain]

    # 签到统计
    total_accounts = len(accounts)
    successful_checkins = 0
    failed_checkins = 0

    # 逐个账号签到
    for account in accounts:
        result = await checkin_single_account(
            account, domains, logger_db, session_id, data_manager
        )

        if result['success']:
            successful_checkins += 1
        else:
            failed_checkins += 1

        # 账号之间等待一段时间
        await asyncio.sleep(3)

    # 打印统计信息
    logging.info(f"\n{'='*60}")
    logging.info(f"签到任务完成")
    logging.info(f"总账号数: {total_accounts}")
    logging.info(f"成功: {successful_checkins}")
    logging.info(f"失败: {failed_checkins}")
    logging.info(f"{'='*60}\n")


def main():
    """主函数"""
    asyncio.run(run_checkin_task())


if __name__ == '__main__':
    main()
