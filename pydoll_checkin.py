#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用Pydoll进行GPT-GOD自动签到的实验性实现
对比DrissionPage的性能和Cloudflare绕过能力
"""

import asyncio
import logging
import json
from datetime import datetime
from config_manager import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def pydoll_checkin(email, password, domain='gptgod.online'):
    """
    使用Pydoll执行签到

    Args:
        email: 账号邮箱
        password: 账号密码
        domain: 网站域名

    Returns:
        dict: 签到结果 {'success': bool, 'message': str, 'points': int}
    """
    try:
        from pydoll.browser import Edge

        start_time = datetime.now()
        logging.info(f"="*60)
        logging.info(f"开始签到: {email}")
        logging.info(f"域名: {domain}")
        logging.info(f"="*60)

        async with Edge() as browser:
            tab = await browser.start()

            # 启用自动Cloudflare绕过
            await tab.enable_auto_solve_cloudflare_captcha()

            # 1. 访问登录页面
            login_url = f'https://{domain}/#/login'
            logging.info(f"访问登录页面: {login_url}")
            await tab.go_to(login_url)
            await asyncio.sleep(5)

            # 检查是否绕过Cloudflare
            current_url = await tab.current_url
            page_html = await tab.page_source

            if 'Cloudflare' in page_html and 'Checking' in page_html:
                logging.warning("仍在Cloudflare验证页面，等待绕过...")
                await asyncio.sleep(10)

            # 2. 填写登录表单
            logging.info("查找登录表单...")

            # 使用JavaScript查找并填写表单
            login_script = f"""
            // 查找邮箱输入框
            const emailInput = document.querySelector('input[type="email"]') ||
                              document.querySelector('input[placeholder*="邮箱"]') ||
                              document.querySelector('input[placeholder*="email"]');

            // 查找密码输入框
            const passwordInput = document.querySelector('input[type="password"]');

            if (emailInput && passwordInput) {{
                emailInput.value = '{email}';
                passwordInput.value = '{password}';

                // 触发input事件
                emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                passwordInput.dispatchEvent(new Event('input', {{ bubbles: true }}));

                return {{ success: true, message: '表单已填写' }};
            }} else {{
                return {{ success: false, message: '未找到登录表单' }};
            }}
            """

            result = await tab.execute_script(login_script)
            if not result.get('success'):
                logging.error(f"登录表单填写失败: {result.get('message')}")
                return {'success': False, 'message': '未找到登录表单', 'points': 0}

            logging.info("登录信息已填写")
            await asyncio.sleep(2)

            # 3. 点击登录按钮
            click_login_script = """
            const loginButton = document.querySelector('button[type="submit"]') ||
                               Array.from(document.querySelectorAll('button')).find(btn =>
                                   btn.textContent.includes('登录') || btn.textContent.includes('Login')
                               );

            if (loginButton) {
                loginButton.click();
                return { success: true };
            } else {
                return { success: false, message: '未找到登录按钮' };
            }
            """

            result = await tab.execute_script(click_login_script)
            if not result.get('success'):
                logging.error("未找到登录按钮")
                return {'success': False, 'message': '未找到登录按钮', 'points': 0}

            logging.info("已点击登录按钮，等待登录...")
            await asyncio.sleep(5)

            # 4. 导航到签到页面
            checkin_url = f'https://{domain}/#/token'
            logging.info(f"导航到签到页面: {checkin_url}")
            await tab.go_to(checkin_url)
            await asyncio.sleep(5)

            # 5. 查找并点击签到按钮
            checkin_script = """
            // 先检查是否已签到
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
            } else {
                return { success: false, message: '未找到签到按钮' };
            }
            """

            result = await tab.execute_script(checkin_script)

            if not result.get('success'):
                logging.error(f"签到失败: {result.get('message')}")
                return {'success': False, 'message': result.get('message'), 'points': 0}

            if result.get('alreadyChecked'):
                logging.info("今天已经签到过了")
                message = '今天已签到'
            else:
                logging.info("签到按钮已点击")
                message = '签到成功'
                await asyncio.sleep(3)

            # 6. 获取当前积分
            await asyncio.sleep(2)

            get_points_script = """
            // 尝试从页面中获取积分信息
            const pointsElement = document.querySelector('[class*="token"]') ||
                                 document.querySelector('[class*="point"]');

            if (pointsElement) {
                return { success: true, points: pointsElement.textContent };
            }

            return { success: false };
            """

            points_result = await tab.execute_script(get_points_script)
            current_points = 0

            if points_result.get('success'):
                try:
                    points_text = points_result.get('points', '0')
                    # 提取数字
                    import re
                    match = re.search(r'\d+', points_text)
                    if match:
                        current_points = int(match.group())
                        logging.info(f"当前积分: {current_points}")
                except Exception as e:
                    logging.debug(f"解析积分失败: {e}")

            # 禁用自动绕过
            await tab.disable_auto_solve_cloudflare_captcha()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logging.info(f"签到完成，总耗时: {duration:.2f}秒")

            return {
                'success': True,
                'message': message,
                'points': current_points,
                'duration': duration
            }

    except ImportError as e:
        logging.error(f"导入Pydoll失败: {e}")
        return {'success': False, 'message': 'Pydoll未安装', 'points': 0}
    except Exception as e:
        logging.error(f"签到过程出错: {e}", exc_info=True)
        return {'success': False, 'message': str(e), 'points': 0}


async def test_pydoll_checkin():
    """测试Pydoll签到功能"""
    # 从配置中获取账号
    config_manager = ConfigManager()
    accounts = config_manager.get_accounts()

    if not accounts:
        logging.error("未找到任何账号配置")
        return

    # 测试第一个账号
    account = accounts[0]
    email = account['mail']
    password = account['password']

    logging.info(f"\n{'='*60}")
    logging.info(f"Pydoll签到测试")
    logging.info(f"{'='*60}\n")

    # 测试主域名
    result = await pydoll_checkin(email, password, 'gptgod.online')

    logging.info(f"\n{'='*60}")
    logging.info(f"测试结果:")
    logging.info(f"  成功: {result['success']}")
    logging.info(f"  消息: {result['message']}")
    logging.info(f"  积分: {result['points']}")
    if 'duration' in result:
        logging.info(f"  耗时: {result['duration']:.2f}秒")
    logging.info(f"{'='*60}\n")


if __name__ == '__main__':
    asyncio.run(test_pydoll_checkin())
