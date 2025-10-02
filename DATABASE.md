# 数据库文档

## 概述

GPT-GOD自动签到系统使用SQLite数据库存储所有数据，统一保存在 `accounts_data/gptgod_checkin.db` 文件中。

## 数据库结构

### 1. 账号配置表 (account_config)

存储GPT-GOD账号的登录凭证和配置信息。

```sql
CREATE TABLE account_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**字段说明：**
- `id`: 主键，自增
- `email`: 账号邮箱（唯一）
- `password`: 账号密码
- `enabled`: 是否启用（1=启用，0=禁用）
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. 系统配置表 (system_config)

存储系统级配置，如定时任务、域名、邮件等设置。

```sql
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**字段说明：**
- `key`: 配置键名（主键）
- `value`: 配置值（JSON格式）
- `description`: 配置说明
- `updated_at`: 更新时间

**常用配置键：**
- `schedule`: 定时任务配置
- `domains`: 域名配置
- `smtp`: 邮件服务器配置
- `web_auth`: Web界面认证配置

### 3. 签到日志会话表 (checkin_sessions)

记录每次签到任务的整体信息。

```sql
CREATE TABLE checkin_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    trigger_type TEXT NOT NULL,
    trigger_by TEXT,
    total_accounts INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    email_sent INTEGER DEFAULT 0,
    error_message TEXT
)
```

**字段说明：**
- `id`: 会话ID，自增
- `start_time`: 开始时间
- `end_time`: 结束时间
- `trigger_type`: 触发类型（scheduled/manual/api）
- `trigger_by`: 触发者（system/admin/用户名）
- `total_accounts`: 总账号数
- `success_count`: 成功数量
- `failed_count`: 失败数量
- `status`: 状态（running/completed/failed）
- `email_sent`: 是否发送邮件通知
- `error_message`: 错误信息

### 4. 签到日志详情表 (checkin_logs)

记录每个账号的签到详细信息。

```sql
CREATE TABLE checkin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    account_email TEXT NOT NULL,
    checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    message TEXT,
    points_earned INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES checkin_sessions(id)
)
```

**字段说明：**
- `id`: 主键，自增
- `session_id`: 所属会话ID（外键）
- `account_email`: 账号邮箱
- `checkin_time`: 签到时间
- `status`: 签到状态（success/failed/skipped）
- `message`: 详细信息
- `points_earned`: 获得的积分

### 5. 积分历史表 (points_history)

记录所有积分变动历史。

```sql
CREATE TABLE points_history (
    id INTEGER PRIMARY KEY,
    uid INTEGER NOT NULL,
    tokens INTEGER NOT NULL,
    source TEXT NOT NULL,
    create_time TEXT NOT NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**字段说明：**
- `id`: 记录ID（与API返回的ID一致）
- `uid`: 用户ID
- `tokens`: 积分变动（正数=获得，负数=消耗）
- `source`: 来源（签到/兑换码/GPT-4对话等）
- `create_time`: 创建时间
- `synced_at`: 同步到本地数据库的时间

**索引：**
- `idx_points_history_uid`: 按用户ID索引
- `idx_points_history_create_time`: 按创建时间索引
- `idx_points_history_source`: 按来源索引

### 6. 账号映射表 (account_mapping)

维护用户ID与邮箱的映射关系。

```sql
CREATE TABLE account_mapping (
    uid INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**字段说明：**
- `uid`: 用户ID（主键）
- `email`: 邮箱地址（唯一）
- `last_update`: 最后更新时间

## 数据管理类

### ConfigManager (config_manager.py)

管理系统配置和账号配置。

**主要方法：**
- `get_accounts()`: 获取所有账号
- `add_account(email, password)`: 添加账号
- `remove_account(email)`: 删除账号
- `get_schedule_config()`: 获取定时任务配置
- `update_schedule_config(enabled, times)`: 更新定时任务配置
- `get_domain_config()`: 获取域名配置
- `update_domain_config(primary, backup, auto_switch)`: 更新域名配置
- `get_smtp_config()`: 获取SMTP配置
- `update_smtp_config(...)`: 更新SMTP配置

### CheckinLoggerDB (checkin_logger_db.py)

管理签到日志。

**主要方法：**
- `log_checkin_start(trigger_type, trigger_by)`: 开始签到会话
- `log_account_result(session_id, email, status, message, points)`: 记录账号签到结果
- `log_checkin_end(session_id, email_sent)`: 结束签到会话
- `get_recent_sessions(limit)`: 获取最近的签到会话
- `get_statistics()`: 获取统计信息

### PointsHistoryManager (points_history_manager.py)

管理积分历史数据。

**主要方法：**
- `add_record(record_id, uid, tokens, source, create_time)`: 添加单条记录
- `batch_add_records(records, email)`: 批量添加记录
- `get_account_history(email, uid, days, source_filter)`: 获取账号历史
- `get_statistics(email, uid)`: 获取统计信息
- `get_daily_summary(email, uid, days)`: 获取每日汇总
- `record_exists(record_id)`: 检查记录是否存在
- `cleanup_old_records(days_to_keep)`: 清理旧记录

## 数据备份

### 导出配置

通过Web界面或API导出配置：

```bash
curl http://localhost:8739/api/config/export > backup.json
```

### 备份数据库

直接复制数据库文件：

```bash
cp accounts_data/gptgod_checkin.db accounts_data/backup_$(date +%Y%m%d).db
```

## 数据库维护

### 清理旧数据

删除30天前的签到日志：

```python
from checkin_logger_db import CheckinLoggerDB

logger = CheckinLoggerDB()
deleted = logger.cleanup_old_logs(days=30)
print(f"已删除 {deleted} 条旧日志")
```

### 数据库压缩

SQLite会自动管理空间，如需手动压缩：

```sql
VACUUM;
```

### 重建索引

```sql
REINDEX;
```

## 安全建议

1. **定期备份**：建议每周备份数据库文件
2. **权限控制**：确保数据库文件只有应用有读写权限
3. **密码安全**：账号密码以明文存储，请确保系统安全
4. **日志清理**：定期清理旧日志以节省空间

## 注意事项

1. 所有时间戳使用UTC时区
2. 积分历史的ID与GPT-GOD API返回的ID保持一致，确保去重
3. 配置值使用JSON格式存储，便于扩展
4. 外键约束确保数据完整性
5. 索引优化查询性能

## 常见查询示例

### 查询今日签到统计

```sql
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
    SUM(points_earned) as total_points
FROM checkin_logs
WHERE DATE(checkin_time) = DATE('now');
```

### 查询账号总积分

```sql
SELECT
    am.email,
    SUM(ph.tokens) as total_points
FROM points_history ph
JOIN account_mapping am ON ph.uid = am.uid
GROUP BY am.email
ORDER BY total_points DESC;
```

### 查询积分来源分布

```sql
SELECT
    source,
    COUNT(*) as count,
    SUM(CASE WHEN tokens > 0 THEN tokens ELSE 0 END) as earned,
    SUM(CASE WHEN tokens < 0 THEN -tokens ELSE 0 END) as spent
FROM points_history
GROUP BY source
ORDER BY earned DESC;
```
