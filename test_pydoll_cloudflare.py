#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pydoll Cloudflare绕过测试脚本
测试Pydoll的自动Cloudflare验证绕过功能
"""

import asyncio
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_cloudflare_bypass():
    """测试Cloudflare绕过功能"""
    try:
        from pydoll.browser import Edge

        logging.info("="*60)
        logging.info("Pydoll Cloudflare绕过测试")
        logging.info("="*60)

        # 测试URL - 使用CF盾测试网站
        test_url = 'https://2026.wxe.me/'

        logging.info(f"目标URL: {test_url}")
        logging.info("启动Edge浏览器...")

        start_time = datetime.now()

        async with Edge() as browser:
            tab = await browser.start()
            logging.info("浏览器启动成功")

            # 方法1: 使用上下文管理器（同步等待验证完成）
            logging.info("\n--- 方法1: 使用上下文管理器 ---")
            logging.info("访问页面并等待Cloudflare验证...")

            async with tab.expect_and_bypass_cloudflare_captcha():
                await tab.go_to(test_url)
                logging.info("✅ Cloudflare验证已自动完成！")

            # 等待页面加载
            await asyncio.sleep(5)

            # 获取页面信息 (都是属性协程，需要await但不需要括号)
            current_url = await tab.current_url
            logging.info(f"当前URL: {current_url}")

            # 检查页面内容
            page_content = await tab.page_source
            if 'Cloudflare' in page_content and ('Checking' in page_content or 'Verifying' in page_content):
                logging.warning("⚠️ 仍在Cloudflare验证页面")
            else:
                logging.info("✅ 成功绕过Cloudflare，已进入目标网站")

            # 打印页面标题（如果存在）
            try:
                logging.info(f"页面HTML长度: {len(page_content)} 字符")

                # 尝试从HTML中提取标题
                import re
                title_match = re.search(r'<title>(.*?)</title>', page_content, re.IGNORECASE)
                if title_match:
                    logging.info(f"页面标题: {title_match.group(1)}")
            except Exception as e:
                logging.warning(f"无法获取页面详情: {e}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logging.info(f"\n总耗时: {duration:.2f}秒")

            # 保持浏览器打开一段时间以便观察
            logging.info("\n浏览器将保持打开10秒以便观察...")
            await asyncio.sleep(10)

    except ImportError as e:
        logging.error(f"导入Pydoll失败: {e}")
        logging.error("请确保已安装: pip install pydoll-python")
    except Exception as e:
        logging.error(f"测试过程出错: {e}", exc_info=True)


async def test_background_bypass():
    """测试后台自动绕过功能"""
    try:
        from pydoll.browser import Edge

        logging.info("\n" + "="*60)
        logging.info("测试后台自动绕过模式")
        logging.info("="*60)

        test_url = 'https://2026.wxe.me/'

        async with Edge() as browser:
            tab = await browser.start()

            # 方法2: 启用后台自动绕过
            logging.info("启用后台自动Cloudflare绕过...")
            await tab.enable_auto_solve_cloudflare_captcha()

            logging.info(f"访问页面: {test_url}")
            await tab.go_to(test_url)

            # 后台自动处理验证，代码继续执行
            logging.info("后台正在处理Cloudflare验证...")
            await asyncio.sleep(10)

            current_url = await tab.current_url
            page_content = await tab.page_source

            logging.info(f"当前URL: {current_url}")
            logging.info(f"页面HTML长度: {len(page_content)} 字符")

            # 禁用自动绕过
            await tab.disable_auto_solve_cloudflare_captcha()
            logging.info("已禁用后台自动绕过")

            await asyncio.sleep(5)

    except Exception as e:
        logging.error(f"后台绕过测试出错: {e}", exc_info=True)


async def main():
    """主函数"""
    logging.info("开始Pydoll Cloudflare绕过测试\n")

    # 测试方法1：上下文管理器
    await test_cloudflare_bypass()

    # 可选：测试方法2：后台自动绕过
    # await test_background_bypass()

    logging.info("\n测试完成！")


if __name__ == '__main__':
    asyncio.run(main())
