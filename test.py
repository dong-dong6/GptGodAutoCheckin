import time
import logging
import os

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
        logging.FileHandler('cloudflare_bypass.log', mode='w')
    ]
)


def get_chromium_options(browser_path: str, arguments: list) -> ChromiumOptions:
    options = ChromiumOptions()
    options.set_argument('--auto-open-devtools-for-tabs', 'true')  # we don't need this anymore
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
    with open('account.yml', 'r') as f:
        accounts = yaml.safe_load(f)

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
        "-accept-lang=en-US",
    ]

    options = get_chromium_options(browser_path, arguments)

    for account in accounts['account']:
        email = account['mail']
        password = account['password']
        logging.info(f"Processing account: {email}")

        driver = None
        try:
            driver = ChromiumPage(addr_or_opts=options)
            driver.get('https://gptgod.online/#/login')
            time.sleep(10)  # 等待登录页面加载

            # 登录
            ele = driver.ele("#email")
            ele.input(email)
            driver.ele("#password").input(password)
            driver.ele(
                'tag:button@@class=ant-btn css-1jr6e2p ant-btn-primary ant-btn-color-primary ant-btn-variant-solid ant-btn-lg').click()
            time.sleep(10)  # 等待登录完成

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
            driver.get('https://gptgod.online/#/token')
            time.sleep(10)  # 等待token页面加载

            # 尝试点击签到按钮（处理中英文两种情况）
            try:
                check_button = driver.ele(
                    'tag:button@@class=ant-btn css-apn68 ant-btn-default ant-btn-color-default ant-btn-variant-outlined')
                if check_button:
                    check_button.click()
                    time.sleep(5)
                    logging.info("签到按钮点击成功/Check-in button clicked successfully")
            except:
                logging.info("未找到签到按钮或已经签到/Check-in button not found or already checked in")

            cf_bypasser = CloudflareBypasser(driver)
            cf_bypasser.bypass()

            logging.info("操作完成/Operation completed!")
            logging.info(f"页面标题/Page title: {driver.title}")

            # 等待一段时间以便查看结果
            time.sleep(5)
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

    if isHeadless:
        display.stop()

def job():
    main()

schedule.every().day.at("09:00").do(job)

if __name__ == '__main__':
    while True:
        schedule.run_pending()
        time.sleep(1)