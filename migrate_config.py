#!/usr/bin/env python3
"""
配置迁移工具 - 将YAML配置迁移到SQLite数据库
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

def migrate_config():
    """执行配置迁移"""
    print("开始配置迁移...")

    # 检查YAML文件是否存在
    yaml_file = 'account.yml'
    if not os.path.exists(yaml_file):
        print(f"错误: 找不到配置文件 {yaml_file}")
        return False

    try:
        # 创建配置管理器
        config_manager = ConfigManager()

        # 执行迁移
        print(f"正在迁移 {yaml_file} 到数据库...")
        if config_manager.migrate_from_yaml(yaml_file):
            print("✅ 配置迁移成功!")

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
            print("❌ 配置迁移失败")
            return False

    except Exception as e:
        print(f"❌ 迁移过程中出错: {e}")
        logging.error(f"配置迁移失败: {e}")
        return False

def test_config_access():
    """测试配置访问"""
    print("\n测试数据库配置访问:")

    try:
        config_manager = ConfigManager()

        # 测试各项配置
        domain_config = config_manager.get_domain_config()
        print(f"域名配置: {domain_config}")

        schedule_config = config_manager.get_schedule_config()
        print(f"定时配置: {schedule_config}")

        accounts = config_manager.get_accounts()
        print(f"账号数量: {len(accounts)}")

        print("✅ 配置访问测试通过")
        return True

    except Exception as e:
        print(f"❌ 配置访问测试失败: {e}")
        return False

def main():
    """主函数"""
    setup_logging()

    print("=== GPT-GOD 配置迁移工具 ===")
    print("此工具将把 account.yml 配置迁移到 SQLite 数据库中")

    # 确认操作
    confirm = input("\n是否继续迁移? (y/N): ").lower().strip()
    if confirm not in ('y', 'yes'):
        print("取消迁移")
        return

    # 执行迁移
    if migrate_config():
        # 测试配置访问
        if test_config_access():
            print("\n🎉 配置迁移完成！现在可以使用数据库配置了。")
            print("\n使用方法:")
            print("from config_manager import ConfigManager")
            print("config = ConfigManager()")
            print("all_config = config.get_all_config()")
        else:
            print("\n⚠️ 迁移完成但配置访问测试失败，请检查数据库文件")
    else:
        print("\n❌ 配置迁移失败，请查看日志了解详情")

if __name__ == '__main__':
    main()