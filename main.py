#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GPT-GOD自动签到系统 - Web服务入口
启动Flask Web应用，提供Web界面和API接口
"""

import sys
import os

# 添加src到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入Flask应用
from app import app

# 从命令行工具导入函数供其他模块使用
from cli import run_checkin, run_sync_points, show_config


def main():
    """启动Flask Web服务"""
    # 从环境变量读取配置，或使用默认值
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 8739))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print("="*60)
    print("GPT-GOD自动签到系统 - Web服务")
    print("="*60)
    print(f"Web界面: http://localhost:{port}")
    print(f"调试模式: {'开启' if debug else '关闭'}")
    print("="*60)
    print("提示:")
    print("  - 使用 python cli.py 运行命令行工具")
    print("  - 使用 python main.py 启动Web服务")
    print("="*60)

    # 启动Flask应用
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug  # 调试模式下启用自动重载
    )


if __name__ == '__main__':
    main()
