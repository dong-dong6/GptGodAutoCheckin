import json
import logging
import time

def get_user_info(driver, domain='gptgod.online'):
    """获取用户信息，包括积分等数据

    Args:
        driver: DrissionPage实例（已登录状态）
        domain: 使用的域名

    Returns:
        dict: 用户信息数据，失败返回None
    """
    try:
        # 方法1：使用JavaScript fetch在浏览器环境中执行
        js_code = """
        async function getUserInfo() {
            try {
                const response = await fetch('https://%s/api/user/info', {
                    method: 'GET',
                    headers: {
                        'accept': 'application/json, text/plain, */*',
                        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cache-control': 'no-cache',
                        'pragma': 'no-cache'
                    },
                    credentials: 'include'
                });
                const data = await response.json();
                return data;
            } catch (error) {
                return { error: error.toString() };
            }
        }
        return getUserInfo();
        """ % domain

        # 执行JavaScript代码
        result = driver.run_js(js_code)

        # 如果第一次没有获取到，等待后重试
        if not result or not isinstance(result, dict):
            time.sleep(2)
            # 使用同步方式再试一次
            js_sync_code = """
            var xhr = new XMLHttpRequest();
            xhr.open('GET', 'https://%s/api/user/info', false);
            xhr.setRequestHeader('accept', 'application/json, text/plain, */*');
            xhr.send();
            if (xhr.status === 200) {
                return JSON.parse(xhr.responseText);
            } else {
                return { error: 'Request failed', status: xhr.status };
            }
            """ % domain

            result = driver.run_js(js_sync_code)

        if result and isinstance(result, dict):
            if result.get('code') == 0 and 'data' in result:
                user_data = result['data']
                logging.info(f"成功获取用户信息: UID={user_data.get('uid')}, 积分={user_data.get('tokens')}")
                return user_data
            elif 'error' not in result:
                # 可能直接返回了data
                if 'uid' in result and 'tokens' in result:
                    logging.info(f"成功获取用户信息: UID={result.get('uid')}, 积分={result.get('tokens')}")
                    return result
            else:
                logging.warning(f"API返回错误: {result}")
                return None
        else:
            logging.warning(f"无法解析API响应: {result}")
            return None

    except Exception as e:
        logging.error(f"获取用户信息失败: {e}")
        # 备用方法：尝试通过页面元素获取积分信息
        try:
            # 尝试从页面上直接获取积分显示
            points_element = driver.ele('xpath://span[contains(text(), "积分")]/following-sibling::*[1]', timeout=3)
            if not points_element:
                points_element = driver.ele('xpath://*[contains(@class, "points") or contains(@class, "tokens")]', timeout=3)

            if points_element:
                points_text = points_element.text
                # 尝试提取数字
                import re
                points_match = re.search(r'(\d+)', points_text)
                if points_match:
                    points = int(points_match.group(1))
                    logging.info(f"从页面获取积分: {points}")
                    return {'tokens': points}
        except:
            pass

        return None


def get_user_info_batch(driver, accounts_info, domain='gptgod.online'):
    """批量获取多个账号的用户信息

    Args:
        driver: DrissionPage实例
        accounts_info: 账号信息列表 [{email, password}, ...]
        domain: 使用的域名

    Returns:
        dict: {email: user_data}
    """
    results = {}

    for account in accounts_info:
        email = account['email']
        logging.info(f"正在获取账号 {email} 的信息...")

        try:
            # 如果当前不是该账号，需要重新登录
            # 这里假设每个账号需要单独登录获取
            # 在实际使用中，可能需要在签到时顺便获取
            user_data = get_user_info(driver, domain)
            if user_data:
                results[email] = user_data
            else:
                results[email] = None

        except Exception as e:
            logging.error(f"获取账号 {email} 信息失败: {e}")
            results[email] = None

    return results


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # 这里仅作为示例，实际使用时需要有已登录的driver实例
    print("请在实际签到流程中调用get_user_info函数")