#!/usr/bin/env python3
"""
日志迁移工具 - 将JSON日志迁移到SQLite数据库
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from checkin_logger_db import CheckinLoggerDB

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('log_migration.log', mode='w', encoding='utf-8')
        ]
    )

def auto_migrate_logs():
    """自动执行日志迁移"""
    print("开始自动日志迁移...")

    # 检查日志目录是否存在
    log_dir = 'checkin_logs'
    if not os.path.exists(log_dir):
        print(f"日志目录 {log_dir} 不存在，无需迁移")
        return True

    try:
        # 创建数据库日志记录器
        logger_db = CheckinLoggerDB()

        # 检查数据库中是否已有日志
        try:
            existing_sessions = logger_db.get_recent_sessions(1)
            if existing_sessions:
                print("数据库中已存在日志，无需迁移")
                return True
        except:
            pass

        # 执行迁移
        print(f"正在迁移 {log_dir} 到数据库...")
        if logger_db.migrate_from_json_logs(log_dir):
            print("[成功] 日志迁移成功!")

            # 验证迁移结果
            print("\n验证迁移结果:")
            stats = logger_db.get_statistics()

            print(f"- 总会话数: {stats['all_time']['total_sessions']}")
            print(f"- 总签到数: {stats['all_time']['total_checkins']}")
            print(f"- 成功签到: {stats['all_time']['successful_checkins']}")
            print(f"- 失败签到: {stats['all_time']['failed_checkins']}")
            print(f"- 总积分: {stats['all_time']['total_points_earned']}")

            # 备份原日志文件夹
            backup_dir = f"{log_dir}.backup"
            import shutil
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(log_dir, backup_dir)
            print(f"\n原日志文件夹已备份为: {backup_dir}")

            return True
        else:
            print("[失败] 日志迁移失败")
            return False

    except Exception as e:
        print(f"[错误] 迁移过程中出错: {e}")
        logging.error(f"日志迁移失败: {e}")
        return False

def main():
    """主函数"""
    setup_logging()

    print("=== GPT-GOD 日志迁移工具 ===")
    print("此工具将把 checkin_logs/ 目录中的JSON日志迁移到 SQLite 数据库中")

    # 自动执行迁移
    if auto_migrate_logs():
        print("\n[完成] 日志迁移完成！现在可以使用数据库日志了。")
        print("\n使用方法:")
        print("from checkin_logger_db import CheckinLoggerDB")
        print("logger = CheckinLoggerDB()")
        print("stats = logger.get_statistics()")
        print("\nWeb界面会自动使用数据库日志")
    else:
        print("\n[失败] 日志迁移失败，请查看日志了解详情")

if __name__ == '__main__':
    main()