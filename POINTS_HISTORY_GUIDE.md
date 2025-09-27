# 积分历史记录功能说明

## 功能概述

该功能模块用于自动获取和管理GPT-GOD账号的积分历史记录，包括：

1. **自动获取历史记录** - 从网站获取所有历史积分记录
2. **本地数据库存储** - 使用SQLite数据库持久化存储
3. **增量更新** - 只获取新记录，避免重复
4. **统计分析** - 提供多维度的积分统计功能

## 主要文件

### 1. points_history_manager.py
积分历史记录管理核心模块，提供：
- SQLite数据库管理
- 积分记录的增删查改
- 统计分析功能
- 数据导出功能

### 2. fetch_points_history.py
自动获取历史记录的主程序：
- 自动登录所有账号
- 获取每个账号的完整历史记录
- 支持分页处理（100条/页）
- 增量更新，避免重复获取

### 3. fetch_history.bat
Windows批处理脚本，方便运行历史记录获取程序

## 使用方法

### 1. 首次获取完整历史记录

```bash
# Windows
fetch_history.bat

# 或直接运行Python脚本
python fetch_points_history.py
```

首次运行会获取所有账号的完整历史记录，可能需要较长时间。

### 2. 日常自动更新

每次签到后会自动获取最新的积分记录（第一页），无需手动操作。

### 3. 查看统计信息

历史记录数据会自动保存到 `accounts_data/points_history.db`

可以通过以下方式查看：

```python
from points_history_manager import PointsHistoryManager

manager = PointsHistoryManager()

# 获取账号统计
stats = manager.get_statistics(email='your@email.com')
print(f"总获得积分: {stats['total_earned']}")
print(f"总消耗积分: {stats['total_spent']}")

# 获取历史记录
history = manager.get_account_history(email='your@email.com', days=30)
for record in history[:10]:
    print(f"{record['create_time']}: {record['source']} {record['tokens']}")

# 导出到JSON
manager.export_to_json('my_points_export.json', email='your@email.com')
```

## 数据结构

### 积分历史表 (points_history)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 记录ID（主键） |
| uid | INTEGER | 用户ID |
| email | TEXT | 账号邮箱 |
| tokens | INTEGER | 积分变化量 |
| source | TEXT | 来源（checkin/api/cdkey/invite等） |
| remark | TEXT | 备注信息 |
| create_time | TEXT | 创建时间 |
| api_id | INTEGER | API ID |
| synced_at | TEXT | 同步时间 |

### 账号映射表 (account_mapping)

| 字段 | 类型 | 说明 |
|------|------|------|
| uid | INTEGER | 用户ID（主键） |
| email | TEXT | 账号邮箱 |
| last_update | TEXT | 最后更新时间 |

## 统计功能

### 1. 总体统计
- 总记录数
- 总获得积分
- 总消耗积分
- 净积分余额

### 2. 按来源统计
- checkin（签到）
- api（API调用）
- cdkey（兑换码）
- invite（邀请）
- 其他来源

### 3. 时间维度统计
- 每日汇总
- 指定时间段统计
- 趋势分析

## 注意事项

1. **首次运行**：建议在网络稳定的环境下运行，避免中断
2. **增量更新**：系统会自动检测已存在的记录，避免重复
3. **数据安全**：所有数据保存在本地SQLite数据库中
4. **性能优化**：使用索引优化查询速度

## 故障排除

### 问题1：无法获取历史记录
- 检查账号密码是否正确
- 检查网络连接
- 查看日志文件了解详细错误

### 问题2：数据库错误
- 删除 `accounts_data/points_history.db` 重新初始化
- 检查磁盘空间是否充足

### 问题3：获取速度慢
- 这是正常现象，为避免频繁请求被限制
- 可以调整 `fetch_points_history.py` 中的延迟时间

## 扩展功能

未来可以基于历史数据实现：
- 积分趋势图表
- 异常消耗预警
- 积分使用报告
- 多账号对比分析