# 积分统计功能说明

## 功能介绍

新增了账户积分统计功能，可以自动获取每个账号的积分信息并进行统计分析。

## 主要功能

### 1. 自动获取积分
- 在每次签到后自动获取账号的当前积分
- 记录积分变化历史
- 计算总获得积分和消费积分

### 2. 数据持久化存储
- 所有数据存储在 `accounts_data/` 目录下
- `accounts_summary.json` - 账户汇总数据
- `points_history.json` - 积分历史记录

### 3. Web界面展示
- 总积分显示
- 积分分布（0-1000, 1000-5000等）
- Top 10 账号排行榜
- 账号活跃度统计

### 4. API接口
- `/api/points` - 获取积分统计信息
- `/api/points/trend` - 获取积分趋势（支持参数：days=7）
- `/api/points/export` - 导出积分数据（支持参数：type=full/summary/points）

## 使用方法

### 1. 查看积分统计
访问Web界面，积分统计卡片会自动显示：
- 所有账号的总积分
- 积分分布情况
- Top账号排行榜

### 2. 测试积分获取
```bash
python test_points.py
```

### 3. 导出数据
通过API导出数据：
```bash
# 导出汇总数据
curl http://localhost:8739/api/points/export?type=summary

# 导出完整数据
curl http://localhost:8739/api/points/export?type=full

# 导出积分数据
curl http://localhost:8739/api/points/export?type=points
```

## 数据结构

### 账户信息
```json
{
  "email": "user@example.com",
  "uid": 12345,
  "current_points": 5000,
  "highest_points": 10000,
  "lowest_points": 0,
  "total_earned": 20000,
  "total_spent": 15000,
  "checkin_days": 30,
  "point_changes": [...]
}
```

### 积分分布
```json
{
  "0-1000": 5,
  "1000-5000": 10,
  "5000-10000": 8,
  "10000-50000": 3,
  "50000-100000": 1,
  "100000+": 0
}
```

## 注意事项

1. 首次运行时会自动创建 `accounts_data` 目录
2. 积分数据会在每次签到后自动更新
3. 历史记录最多保留30天的数据
4. 每个账号的积分变化记录最多保留100条

## 邮件通知

签到邮件通知中新增了积分统计内容：
- 所有账号的总积分
- 积分分布情况
- Top 5账号
- 每个账号的当前积分

## 故障排查

如果积分获取失败：
1. 检查网络连接
2. 确认账号登录状态
3. 查看 `web_service.log` 日志
4. 尝试运行 `test_points.py` 进行测试