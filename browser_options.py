#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
浏览器配置选项模块
提供统一的ChromiumOptions配置
"""

from DrissionPage import ChromiumOptions

def get_chromium_options(browser_path, arguments):
    """创建并配置ChromiumOptions"""
    options = ChromiumOptions()
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options