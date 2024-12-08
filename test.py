import time
import logging
import os
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
            ele = driver.ele("#email")
            ele.input(email)
            driver.ele("#password").input(password)
            driver.ele(
                'tag:button@@class=ant-btn css-1jr6e2p ant-btn-primary ant-btn-color-primary ant-btn-variant-solid ant-btn-lg').click()
            time.sleep(5)
            print("等待首页完全加载结束")
            driver.get('https://gptgod.online/#/token')
            driver.ele(
                'tag:button@@class=ant-btn css-apn68 ant-btn-default ant-btn-color-default ant-btn-variant-outlined').check()
            time.sleep(5)
            cf_bypasser = CloudflareBypasser(driver)
            cf_bypasser.bypass()

            logging.info("Enjoy the content!")
            logging.info(f"Title of the page: {driver.title}")

            # Sleep for a while to let the user see the result if needed
            time.sleep(5)
        except Exception as e:
            logging.error(f"An error occurred with account {email}: {str(e)}")
        finally:
            if driver is not None:
                logging.info('Closing the browser.')
                driver.quit()
            else:
                logging.info('Driver was not instantiated.')
        # Optional sleep between accounts
        time.sleep(2)

    if isHeadless:
        display.stop()
if __name__ == '__main__':
    main()
