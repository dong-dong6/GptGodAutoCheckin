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
    # options.set_argument('--auto-open-devtools-for-tabs', 'true')  # we don't need this anymore
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options

def main():
    isHeadless = os.getenv('HEADLESS', 'false').lower() == 'true'

    if isHeadless:
        from pyvirtualdisplay import Display

        display = Display(visible=0, size=(1920, 1080))
        display.start()

    # Read accounts from account.yml
    with open('account.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    accounts = config
    checkin_results = []  # 存储签到结果

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

    for account in accounts['account']:
        email = account['mail']
        password = account['password']
        logging.info(f"Processing account: {email}")

        driver = None
        try:
            driver = ChromiumPage(addr_or_opts=options)
            driver.set.window.full()
            driver.get('https://gptgod.work/#/login')
            time.sleep(10)  # 等待登录页面加载

            # 等待页面元素加载
            time.sleep(3)  # 给页面一点时间渲染

            # 使用多种方式尝试定位邮箱输入框
            email_input = None
            try:
                # 方法1: 通过placeholder属性定位
                email_input = driver.ele('xpath://input[@placeholder="请输入邮箱"]', timeout=5)
                if not email_input:
                    # 方法2: 通过id定位
                    email_input = driver.ele('#email', timeout=5)
                if not email_input:
                    # 方法3: 通过type="text"和父元素包含mail图标
                    email_input = driver.ele('xpath://input[@type="text" and ancestor::div[contains(@class, "ant-form-item")]]', timeout=5)
            except:
                logging.error("无法定位邮箱输入框")

            # 使用多种方式尝试定位密码输入框
            password_input = None
            try:
                # 方法1: 通过placeholder属性定位
                password_input = driver.ele('xpath://input[contains(@placeholder, "密码")]', timeout=5)
                if not password_input:
                    # 方法2: 通过id定位
                    password_input = driver.ele('#password', timeout=5)
                if not password_input:
                    # 方法3: 通过type="password"定位
                    password_input = driver.ele('xpath://input[@type="password"]', timeout=5)
            except:
                logging.error("无法定位密码输入框")

            # 输入登录信息
            if email_input and password_input:
                email_input.clear()
                email_input.input(email)
                password_input.clear()
                password_input.input(password)
            else:
                logging.error("无法定位登录表单元素")

            # 使用更精确的选择器点击登录按钮
            login_button = None
            try:
                # 方法1: 通过class和样式定位 (最可靠)
                login_button = driver.ele('xpath://button[contains(@class, "ant-btn-primary") and contains(@class, "ant-btn-lg") and @style="width: 100%;"]', timeout=10)
                if not login_button:
                    # 方法2: 通过按钮文本定位
                    login_button = driver.ele('xpath://button[contains(@class, "ant-btn-primary")]/span[text()="登 录"]', timeout=5)
                if not login_button:
                    # 方法3: 通过父元素form定位按钮
                    login_button = driver.ele('xpath://form[@class[contains(., "ant-form")]]//button[contains(@class, "ant-btn-primary")]', timeout=5)
            except:
                logging.error("尝试多种方式定位登录按钮失败")

            if login_button:
                login_button.click()
                time.sleep(10)  # 等待登录完成
                logging.info("登录按钮点击成功")
            else:
                logging.error("无法找到登录按钮")

            # 切换到明亮模式（处理中英文两种情况）
            try:
                # 尝试查找中文或英文的切换按钮
                mode_switch = driver.ele('text:切换至明亮模式') or driver.ele('text:Switch to Light Mode')
                if mode_switch:
                    mode_switch.click()
                    time.sleep(3)  # 等待模式切换完成
                    logging.info("已切换至明亮模式/Switched to Light Mode")
            except:
                logging.info("可能已经是明亮模式或未找到切换按钮/May already be in Light Mode or button not found")

            print("等待首页完全加载结束/Waiting for homepage to load completely")
            driver.get('https://gptgod.work/#/token')
            time.sleep(10)  # 等待token页面加载

            # 等待页面完全加载
            time.sleep(5)

            # 尝试点击签到按钮
            try:
                # 首先检查是否已经签到
                already_checked = driver.ele('xpath://button[contains(., "今天已签到") or contains(., "已签到")]', timeout=3)
                if already_checked:
                    logging.info(f"[已签到] 账号 {email} 今天已经签到过了")
                    checkin_results.append({'email': email, 'status': '已签到', 'message': '今天已签到'})
                else:
                    check_button = None
                    # 方法1: 直接通过文本查找签到按钮（最简单有效）
                    check_button = driver.ele('xpath://button[span[contains(text(), "签到")]]', timeout=10)
                    if not check_button:
                        # 方法2: 通过包含"签到"和"积分"的按钮
                        check_button = driver.ele('xpath://button[contains(text(), "签到") or contains(., "签到")]', timeout=5)
                    if not check_button:
                        # 方法3: 查找h4"1. 签到"之后的第一个button
                        check_button = driver.ele('xpath://h4[contains(., "1.") and contains(., "签到")]/following::button[1]', timeout=5)
                    if not check_button:
                        # 方法4: 通过check图标SVG定位按钮
                        check_button = driver.ele('xpath://button[.//svg[@data-icon="check"]][1]', timeout=5)
                    if not check_button:
                        # 方法5: 查找所有按钮，遍历查找包含签到的
                        logging.info("尝试遍历所有按钮查找签到按钮")
                        buttons = driver.eles('tag:button')
                        for btn in buttons:
                            try:
                                btn_text = btn.text
                                if "签到" in btn_text or "领取" in btn_text:
                                    check_button = btn
                                    logging.info(f"找到签到按钮，文本: {btn_text}")
                                    break
                            except:
                                continue
                    if check_button:
                        check_button.click()
                        time.sleep(5)
                        logging.info("签到按钮点击成功/Check-in button clicked successfully")

                        # 处理可能的Cloudflare验证
                        cf_bypasser = CloudflareBypasser(driver)
                        cf_bypasser.bypass()
                        logging.info("Cloudflare验证完成")

                        # 刷新页面后验证签到是否成功
                        logging.info("刷新页面验证签到状态...")
                        driver.refresh()
                        time.sleep(8)  # 等待页面重新加载

                        # 验证签到是否成功
                        try:
                            # 检查按钮文本是否变为"今天已签到"
                            success_button = driver.ele('xpath://button[contains(., "今天已签到") or contains(., "已签到")]', timeout=10)
                            if success_button:
                                logging.info(f"[成功] 账号 {email} 签到成功！按钮已变为'今天已签到'")
                                checkin_results.append({'email': email, 'status': '签到成功', 'message': '获得2000积分'})
                            else:
                                # 再次尝试查找disabled的签到按钮
                                disabled_button = driver.ele('xpath://button[@disabled and .//span[@aria-label="check"]]', timeout=5)
                                if disabled_button:
                                    button_text = disabled_button.text if disabled_button else ""
                                    logging.info(f"[成功] 账号 {email} 签到成功！签到按钮已禁用，按钮文本: {button_text}")
                                    checkin_results.append({'email': email, 'status': '签到成功', 'message': button_text})
                                else:
                                    # 检查是否还有可点击的签到按钮（说明签到失败）
                                    still_clickable = driver.ele('xpath://button[not(@disabled) and .//span[contains(text(), "签到")]]', timeout=3)
                                    if still_clickable:
                                        logging.error(f"[失败] 账号 {email} 签到失败！签到按钮仍可点击")
                                        checkin_results.append({'email': email, 'status': '签到失败', 'message': '按钮仍可点击'})
                                    else:
                                        logging.warning(f"[未知] 账号 {email} 签到状态未知")
                                        checkin_results.append({'email': email, 'status': '状态未知', 'message': '无法确定签到状态'})
                        except Exception as e:
                            logging.warning(f"无法验证签到状态: {str(e)}")
                    else:
                        logging.info("未找到签到按钮，可能已经签到")
            except:
                logging.info("未找到签到按钮或已经签到/Check-in button not found or already checked in")

            logging.info("操作完成/Operation completed!")
            logging.info(f"页面标题/Page title: {driver.title}")

            # 等待一段时间以便查看结果
            time.sleep(10)
        except Exception as e:
            logging.error(f"处理账号 {email} 时发生错误/Error occurred with account {email}: {str(e)}")
        finally:
            if driver is not None:
                logging.info('关闭浏览器/Closing the browser.')
                driver.quit()
            else:
                logging.info('浏览器未启动/Driver was not instantiated.')
        # 账号之间的等待时间
        time.sleep(2)

    # 发送邮件汇总
    if checkin_results:
        # 构建邮件内容
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"GPT-GOD 签到报告 - {datetime.now().strftime('%Y-%m-%d')}"

        # 构建HTML格式的邮件正文
        success_count = len([r for r in checkin_results if '成功' in r['status']])
        failed_count = len([r for r in checkin_results if '失败' in r['status']])

        body = f"""
        <html>
        <head>
            <style>
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                .success {{
                    color: green;
                    font-weight: bold;
                }}
                .failed {{
                    color: red;
                    font-weight: bold;
                }}
                .already {{
                    color: blue;
                }}
                .unknown {{
                    color: orange;
                }}
                .summary {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <h2>GPT-GOD 自动签到报告</h2>
            <div class="summary">
                <p><strong>签到时间：</strong>{current_time}</p>
                <p><strong>账号总数：</strong>{len(checkin_results)}</p>
                <p><strong>签到成功：</strong><span class="success">{success_count}</span></p>
                <p><strong>签到失败：</strong><span class="failed">{failed_count}</span></p>
            </div>

            <table>
                <tr>
                    <th>账号</th>
                    <th>状态</th>
                    <th>备注</th>
                </tr>
        """

        for result in checkin_results:
            status_class = ''
            if '成功' in result['status']:
                status_class = 'success'
            elif '失败' in result['status']:
                status_class = 'failed'
            elif '已签到' in result['status']:
                status_class = 'already'
            else:
                status_class = 'unknown'

            body += f"""
                <tr>
                    <td>{result['email']}</td>
                    <td class="{status_class}">{result['status']}</td>
                    <td>{result['message']}</td>
                </tr>
            """

        body += """
            </table>
            <p style="color: gray; font-size: 12px; margin-top: 20px;">此邮件由 GPT-GOD 自动签到程序发送</p>
        </body>
        </html>
        """

        # 发送邮件
        send_email_notification(subject, body, config)

    if isHeadless:
        display.stop()

def job():
    main()

schedule.every().day.at("09:00").do(job)

if __name__ == '__main__':
    main()
