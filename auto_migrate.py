#!/usr/bin/env python3
"""
自动配置迁移工具 - 将YAML配置自动迁移到SQLite数据库
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('config_migration.log', mode='w', encoding='utf-8')
        ]
    )

def auto_migrate_config():
    """自动执行配置迁移"""
    print("开始自动配置迁移...")

    # 检查YAML文件是否存在
    yaml_file = 'account.yml'
    if not os.path.exists(yaml_file):
        print(f"错误: 找不到配置文件 {yaml_file}")
        return False

    try:
        # 创建配置管理器
        config_manager = ConfigManager()

        # 检查数据库中是否已有配置
        try:
            existing_config = config_manager.get_all_config()
            if existing_config['account']:
                print("数据库中已存在配置，无需迁移")
                return True
        except:
            pass

        # 执行迁移
        print(f"正在迁移 {yaml_file} 到数据库...")
        if config_manager.migrate_from_yaml(yaml_file):
            print("[成功] 配置迁移成功!")

            # 验证迁移结果
            print("\n验证迁移结果:")
            all_config = config_manager.get_all_config()

            print(f"- 域名配置: {all_config['domains']}")
            print(f"- 定时任务: {all_config['schedule']}")
            print(f"- SMTP配置: {'已启用' if all_config['smtp']['enabled'] else '已禁用'}")
            print(f"- Web认证: {'已启用' if all_config['web_auth']['enabled'] else '已禁用'}")
            print(f"- 账号数量: {len(all_config['account'])}")

            # 备份原YAML文件
            backup_file = f"{yaml_file}.backup"
            import shutil
            shutil.copy2(yaml_file, backup_file)
            print(f"\n原配置文件已备份为: {backup_file}")

            return True
        else:
            print("[失败] 配置迁移失败")
            return False

    except Exception as e:
        print(f"[错误] 迁移过程中出错: {e}")
        logging.error(f"配置迁移失败: {e}")
        return False

def main():
    """主函数"""
    setup_logging()

    print("=== GPT-GOD 自动配置迁移工具 ===")

    # 自动执行迁移
    if auto_migrate_config():
        print("\n[完成] 配置迁移完成！现在可以使用数据库配置了。")
        print("\n使用方法:")
        print("from config_manager import ConfigManager")
        print("config = ConfigManager()")
        print("all_config = config.get_all_config()")
        print("\n可以运行 python config_web.py 启动配置管理Web界面")
    else:
        print("\n[失败] 配置迁移失败，请查看日志了解详情")

if __name__ == '__main__':
    main()