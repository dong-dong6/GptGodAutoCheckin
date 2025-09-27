#!/usr/bin/env python3
"""
全量迁移工具 - 将YAML配置和JSON日志全部迁移到SQLite数据库
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager
from checkin_logger_db import CheckinLoggerDB

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('full_migration.log', mode='w', encoding='utf-8')
        ]
    )

def migrate_all():
    """执行完整迁移"""
    print("=== GPT-GOD 数据库完整迁移工具 ===")
    print("将配置和日志统一迁移到数据库中...")

    success_count = 0
    total_count = 2

    # 1. 迁移配置
    print("\n[1/2] 迁移配置数据...")
    config_success = False

    yaml_file = 'account.yml'
    if os.path.exists(yaml_file):
        try:
            config_manager = ConfigManager()

            # 检查是否已有配置
            try:
                existing_config = config_manager.get_all_config()
                if existing_config['account']:
                    print("数据库配置已存在，跳过配置迁移")
                    config_success = True
            except:
                pass

            if not config_success:
                if config_manager.migrate_from_yaml(yaml_file):
                    print("[成功] 配置迁移完成")
                    config_success = True

                    # 显示迁移结果
                    config = config_manager.get_all_config()
                    print(f"- 域名配置: {config['domains']['primary']} -> {config['domains']['backup']}")
                    print(f"- 定时任务: {'已启用' if config['schedule']['enabled'] else '已禁用'}")
                    print(f"- SMTP: {'已启用' if config['smtp']['enabled'] else '已禁用'}")
                    print(f"- 账号数量: {len(config['account'])}个")
                else:
                    print("[失败] 配置迁移失败")
        except Exception as e:
            print(f"[错误] 配置迁移出错: {e}")
    else:
        print(f"配置文件 {yaml_file} 不存在，跳过配置迁移")
        config_success = True

    if config_success:
        success_count += 1

    # 2. 迁移日志
    print("\n[2/2] 迁移日志数据...")
    log_success = False

    log_dir = 'checkin_logs'
    if os.path.exists(log_dir):
        try:
            logger_db = CheckinLoggerDB()

            # 检查是否已有日志
            try:
                existing_sessions = logger_db.get_recent_sessions(1)
                if existing_sessions:
                    print("数据库日志已存在，跳过日志迁移")
                    log_success = True
            except:
                pass

            if not log_success:
                if logger_db.migrate_from_json_logs(log_dir):
                    print("[成功] 日志迁移完成")
                    log_success = True

                    # 显示迁移结果
                    stats = logger_db.get_statistics()
                    print(f"- 会话数量: {stats['all_time']['total_sessions']}个")
                    print(f"- 签到记录: {stats['all_time']['total_checkins']}条")
                    print(f"- 成功率: {stats['all_time']['successful_checkins']}/{stats['all_time']['total_checkins']}")
                    print(f"- 总积分: {stats['all_time']['total_points_earned']}")
                else:
                    print("[失败] 日志迁移失败")
        except Exception as e:
            print(f"[错误] 日志迁移出错: {e}")
    else:
        print(f"日志目录 {log_dir} 不存在，跳过日志迁移")
        log_success = True

    if log_success:
        success_count += 1

    # 3. 创建备份
    print("\n[3/3] 创建数据备份...")
    try:
        import shutil

        # 备份配置文件
        if os.path.exists(yaml_file):
            backup_config = f"{yaml_file}.backup"
            if not os.path.exists(backup_config):
                shutil.copy2(yaml_file, backup_config)
                print(f"配置文件已备份为: {backup_config}")

        # 备份日志文件夹
        if os.path.exists(log_dir):
            backup_logs = f"{log_dir}.backup"
            if not os.path.exists(backup_logs):
                shutil.copytree(log_dir, backup_logs)
                print(f"日志目录已备份为: {backup_logs}")

        print("[成功] 数据备份完成")
    except Exception as e:
        print(f"[警告] 备份创建失败: {e}")

    # 4. 显示结果
    print(f"\n=== 迁移完成 ({success_count}/{total_count}) ===")

    if success_count == total_count:
        print("[完成] 所有数据已成功迁移到数据库！")
        print("\n数据库文件位置:")
        print("- 配置数据库: accounts_data/config.db")
        print("- 日志数据库: accounts_data/checkin_logs.db")
        print("\n现在可以：")
        print("1. 运行 python app.py 启动Web管理界面")
        print("2. 运行 python main.py 使用数据库配置进行签到")
        print("3. 所有配置和日志都会自动使用数据库版本")
        return True
    else:
        print("[部分完成] 部分迁移完成，请查看日志了解详情")
        return False

def main():
    """主函数"""
    setup_logging()
    return migrate_all()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)