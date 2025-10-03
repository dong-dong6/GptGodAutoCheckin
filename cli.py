#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GPT-GOD自动签到命令行工具
提供签到、积分同步、配置查看等功能
"""

import sys
import logging
import argparse
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, 'C:\\GptGodAutoCheckin')

from src.core.checkin_service import CheckinService
from src.core.points_sync_service import PointsSyncService
from src.data.repositories.config_repository import ConfigManager


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/checkin.log', mode='a', encoding='utf-8')
    ]
)


def run_checkin(headless=False, trigger_type='manual', trigger_by=None):
    """
    运行签到任务

    Args:
        headless: 是否使用无头模式
        trigger_type: 触发类型 ('manual', 'scheduled', 'api')
        trigger_by: 触发者（用户名或系统标识）
    """
    logging.info("="*60)
    logging.info("GPT-GOD自动签到任务开始")
    logging.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"触发方式: {trigger_type}")
    if trigger_by:
        logging.info(f"触发者: {trigger_by}")
    logging.info("="*60)

    try:
        # 创建签到服务
        service = CheckinService(headless=headless)

        # 执行批量签到
        result = service.batch_checkin()

        # 输出结果
        logging.info("\n" + "="*60)
        logging.info("签到任务完成")
        logging.info(f"总账号数: {result['total']}")
        logging.info(f"成功: {result['success']}")
        logging.info(f"失败: {result['failed']}")
        logging.info("="*60)

        # 详细结果
        for item in result['results']:
            status = "✅" if item['success'] else "❌"
            logging.info(f"{status} {item['email']}: {item['message']}")

        return result

    except Exception as e:
        logging.error(f"签到任务异常: {e}", exc_info=True)
        return None


def run_sync_points(headless=True, max_pages=None):
    """
    运行积分同步任务

    Args:
        headless: 是否使用无头模式
        max_pages: 每个账号最大页数
    """
    logging.info("="*60)
    logging.info("积分历史同步任务开始")
    logging.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("="*60)

    try:
        # 创建积分同步服务
        service = PointsSyncService(headless=headless)

        # 执行同步
        result = service.sync_all_accounts(max_pages=max_pages)

        # 输出结果
        logging.info("\n" + "="*60)
        logging.info("同步任务完成")
        logging.info(f"总账号数: {result['total']}")
        logging.info(f"成功: {result['success']}")
        logging.info(f"失败: {result['failed']}")
        logging.info(f"总记录数: {result['total_records']}")
        logging.info(f"新增记录: {result['new_records']}")
        logging.info("="*60)

        return result

    except Exception as e:
        logging.error(f"同步任务异常: {e}", exc_info=True)
        return None


def show_config():
    """显示当前配置"""
    try:
        config_manager = ConfigManager()

        logging.info("="*60)
        logging.info("当前配置")
        logging.info("="*60)

        # 域名配置
        domain_config = config_manager.get_domain_config()
        logging.info("\n域名配置:")
        logging.info(f"  主域名: {domain_config.get('primary', 'N/A')}")
        logging.info(f"  备用域名: {domain_config.get('backup', 'N/A')}")
        logging.info(f"  自动切换: {domain_config.get('auto_switch', False)}")

        # 账号配置
        accounts = config_manager.get_accounts()
        logging.info(f"\n账号配置: {len(accounts)} 个账号")
        for i, account in enumerate(accounts, 1):
            email = account['mail']
            send_email = account.get('send_email_notification', False)
            logging.info(f"  {i}. {email} (邮件通知: {'启用' if send_email else '禁用'})")

        # 定时任务配置
        schedule_config = config_manager.get_schedule_config()
        logging.info("\n定时任务配置:")
        logging.info(f"  启用: {schedule_config.get('enabled', False)}")
        logging.info(f"  时间: {schedule_config.get('times', [])}")

        # SMTP配置
        smtp_config = config_manager.get_smtp_config()
        logging.info("\nSMTP配置:")
        logging.info(f"  启用: {smtp_config.get('enabled', False)}")
        if smtp_config.get('enabled'):
            logging.info(f"  服务器: {smtp_config.get('server', 'N/A')}")
            logging.info(f"  端口: {smtp_config.get('port', 'N/A')}")
            logging.info(f"  收件人: {', '.join(smtp_config.get('receiver_emails', []))}")

        logging.info("="*60)

    except Exception as e:
        logging.error(f"读取配置失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='GPT-GOD自动签到命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py                     # 运行签到（显示浏览器）
  python cli.py --headless          # 运行签到（无头模式）
  python cli.py --sync              # 同步积分历史
  python cli.py --config            # 显示配置
  python cli.py --sync --max-pages 5  # 同步积分（每个账号最多5页）
        """
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='使用无头模式运行浏览器'
    )

    parser.add_argument(
        '--sync',
        action='store_true',
        help='同步积分历史（而不是签到）'
    )

    parser.add_argument(
        '--config',
        action='store_true',
        help='显示当前配置'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='同步时每个账号的最大页数'
    )

    parser.add_argument(
        '--trigger-type',
        type=str,
        default='manual',
        help='触发类型: manual, scheduled, api'
    )

    parser.add_argument(
        '--trigger-by',
        type=str,
        default=None,
        help='触发者标识'
    )

    args = parser.parse_args()

    # 显示配置
    if args.config:
        show_config()
        return

    # 同步积分
    if args.sync:
        result = run_sync_points(headless=args.headless, max_pages=args.max_pages)
        if result and result['success'] > 0:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # 默认运行签到
        result = run_checkin(
            headless=args.headless,
            trigger_type=args.trigger_type,
            trigger_by=args.trigger_by
        )
        if result and result['success'] > 0:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
