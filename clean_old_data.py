#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
清理旧数据并初始化新的快照系统
"""

import os
import shutil
from pathlib import Path

def clean_old_data():
    """清理旧的数据文件"""

    data_dir = Path('accounts_data')

    # 要删除的旧文件
    files_to_remove = [
        data_dir / 'accounts_summary.json',
        data_dir / 'points_history.json'
    ]

    for file in files_to_remove:
        if file.exists():
            print(f"删除旧文件: {file}")
            os.remove(file)

    # 清理points子目录
    points_dir = data_dir / 'points'
    if points_dir.exists():
        print(f"清理points目录")
        shutil.rmtree(points_dir)
        points_dir.mkdir()

    print("旧数据已清理完成")
    print("\n新系统说明：")
    print("- 只保留最新一次签到的积分数据")
    print("- 数据存储在 accounts_data/latest_snapshot.json")
    print("- Web界面只显示最新的积分分布")
    print("\n下次签到时会自动创建新的快照数据")

if __name__ == '__main__':
    clean_old_data()