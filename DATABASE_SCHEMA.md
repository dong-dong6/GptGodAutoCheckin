# GPT-GOD 自动签到系统 - 数据库表结构说明

## 数据库文件
- **统一数据库**: `accounts_data/gptgod_checkin.db`
- 所有表都存储在同一个数据库文件中

---

## 一、签到相关表

### 1. checkin_sessions (签到会话表)
记录每次签到任务的执行情况

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 会话ID | PRIMARY KEY, AUTOINCREMENT |
| start_time | TEXT | 签到开始时间 | NOT NULL |
| end_time | TEXT | 签到结束时间 | - |
| trigger_type | TEXT | 触发类型 (manual/scheduled/api) | NOT NULL, DEFAULT 'manual' |
| trigger_by | TEXT | 触发者（用户名或系统） | - |
| total_accounts | INTEGER | 处理的账号总数 | DEFAULT 0 |
| success_count | INTEGER | 成功签到数 | DEFAULT 0 |
| failed_count | INTEGER | 失败签到数 | DEFAULT 0 |
| already_checked_count | INTEGER | 已签到数 | DEFAULT 0 |
| duration_seconds | REAL | 执行耗时（秒） | - |
| status | TEXT | 状态 (running/completed) | NOT NULL, DEFAULT 'running' |
| email_sent | BOOLEAN | 是否已发送邮件通知 | DEFAULT 0 |
| created_at | TEXT | 记录创建时间 | NOT NULL, DEFAULT (datetime('now')) |

### 2. account_checkin_logs (账号签到日志表)
记录每个账号的签到详情

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 日志ID | PRIMARY KEY, AUTOINCREMENT |
| session_id | INTEGER | 所属会话ID | NOT NULL, FOREIGN KEY |
| account_email | TEXT | 账号邮箱 | NOT NULL |
| checkin_time | TEXT | 签到时间 | NOT NULL |
| status | TEXT | 签到状态 (success/failed/already_checked/unknown) | NOT NULL |
| message | TEXT | 状态消息 | DEFAULT '' |
| points | INTEGER | 获得积分数 | DEFAULT 0 |
| domain | TEXT | 使用的域名 | - |
| created_at | TEXT | 记录创建时间 | NOT NULL, DEFAULT (datetime('now')) |

### 3. account_statistics (账号统计表)
汇总每个账号的签到统计信息

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| email | TEXT | 账号邮箱 | PRIMARY KEY |
| total_checkins | INTEGER | 总签到次数 | DEFAULT 0 |
| successful_checkins | INTEGER | 成功签到次数 | DEFAULT 0 |
| failed_checkins | INTEGER | 失败签到次数 | DEFAULT 0 |
| total_points | INTEGER | 累计获得积分 | DEFAULT 0 |
| last_checkin | TEXT | 最后签到时间 | - |
| consecutive_days | INTEGER | 连续签到天数 | DEFAULT 0 |
| first_checkin | TEXT | 首次签到时间 | - |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

---

## 二、配置相关表

### 4. system_config (系统配置表)
存储系统级配置参数

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| key | TEXT | 配置键 | PRIMARY KEY |
| value | TEXT | 配置值 | NOT NULL |
| data_type | TEXT | 数据类型 (str/int/bool/json) | NOT NULL, DEFAULT 'str' |
| description | TEXT | 配置说明 | - |
| created_at | TEXT | 创建时间 | NOT NULL, DEFAULT (datetime('now')) |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

### 5. domain_config (域名配置表)
配置签到网站的域名

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 配置ID | PRIMARY KEY, AUTOINCREMENT |
| primary_domain | TEXT | 主域名 | NOT NULL |
| backup_domain | TEXT | 备用域名 | - |
| auto_switch | BOOLEAN | 自动切换域名 | NOT NULL, DEFAULT 1 |
| created_at | TEXT | 创建时间 | NOT NULL, DEFAULT (datetime('now')) |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

### 6. schedule_config (定时任务配置表)
配置自动签到的时间

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 配置ID | PRIMARY KEY, AUTOINCREMENT |
| enabled | BOOLEAN | 是否启用定时任务 | NOT NULL, DEFAULT 1 |
| schedule_times | TEXT | 定时时间（JSON数组，如["09:00", "21:00"]） | NOT NULL |
| created_at | TEXT | 创建时间 | NOT NULL, DEFAULT (datetime('now')) |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

### 7. smtp_config (SMTP邮件配置表)
配置邮件通知服务

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 配置ID | PRIMARY KEY, AUTOINCREMENT |
| enabled | BOOLEAN | 是否启用邮件通知 | NOT NULL, DEFAULT 0 |
| server | TEXT | SMTP服务器地址 | NOT NULL |
| port | INTEGER | SMTP端口 | NOT NULL, DEFAULT 587 |
| sender_email | TEXT | 发件人邮箱 | NOT NULL |
| sender_password | TEXT | 发件人密码/授权码 | NOT NULL |
| receiver_emails | TEXT | 收件人邮箱列表（JSON数组） | NOT NULL |
| created_at | TEXT | 创建时间 | NOT NULL, DEFAULT (datetime('now')) |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

### 8. web_auth_config (Web认证配置表)
配置Web界面的访问认证

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 配置ID | PRIMARY KEY, AUTOINCREMENT |
| enabled | BOOLEAN | 是否启用认证 | NOT NULL, DEFAULT 1 |
| username | TEXT | 用户名 | NOT NULL |
| password | TEXT | 密码（明文存储） | NOT NULL |
| api_token | TEXT | API访问令牌 | - |
| created_at | TEXT | 创建时间 | NOT NULL, DEFAULT (datetime('now')) |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

### 9. account_config (账号配置表)
存储GPT-GOD网站的账号信息

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 账号ID | PRIMARY KEY, AUTOINCREMENT |
| email | TEXT | 账号邮箱 | UNIQUE, NOT NULL |
| password | TEXT | 账号密码 | NOT NULL |
| enabled | BOOLEAN | 是否启用 | NOT NULL, DEFAULT 1 |
| created_at | TEXT | 创建时间 | NOT NULL, DEFAULT (datetime('now')) |
| updated_at | TEXT | 更新时间 | NOT NULL, DEFAULT (datetime('now')) |

---

## 三、积分历史表

### 10. points_history (积分历史表)
记录从GPT-GOD网站获取的积分历史记录

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 记录ID（来自API） | PRIMARY KEY |
| uid | INTEGER | 用户ID（来自API） | - |
| email | TEXT | 账号邮箱 | - |
| tokens | INTEGER | 积分变化量（正数为获得，负数为消耗） | NOT NULL |
| source | TEXT | 积分来源（如：签到、使用、兑换等） | NOT NULL |
| remark | TEXT | 备注信息（JSON格式） | - |
| ip | TEXT | IP地址 | - |
| create_time | TEXT | 创建时间（来自API） | NOT NULL |
| api_id | INTEGER | API ID | DEFAULT 0 |
| synced_at | TEXT | 同步时间 | DEFAULT CURRENT_TIMESTAMP |

### 11. account_mapping (账号映射表)
将用户ID与邮箱地址关联

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| uid | INTEGER | 用户ID | PRIMARY KEY |
| email | TEXT | 账号邮箱 | NOT NULL |
| last_update | TEXT | 最后更新时间 | DEFAULT CURRENT_TIMESTAMP |

---

## 索引说明

### 签到相关索引
- `idx_session_start_time`: checkin_sessions表的start_time索引
- `idx_account_logs_email`: account_checkin_logs表的account_email索引
- `idx_account_logs_session`: account_checkin_logs表的session_id索引
- `idx_account_logs_time`: account_checkin_logs表的checkin_time索引

### 积分历史索引
- `idx_points_uid`: points_history表的uid索引
- `idx_points_email`: points_history表的email索引
- `idx_points_create_time`: points_history表的create_time索引
- `idx_points_source`: points_history表的source索引

---

## 数据类型说明

1. **INTEGER**: 整数类型
2. **TEXT**: 文本类型，存储字符串
3. **REAL**: 浮点数类型
4. **BOOLEAN**: 布尔类型（实际存储为0或1）

## 时间格式
- 所有时间字段均使用ISO 8601格式：`YYYY-MM-DD HH:MM:SS`
- 默认使用UTC时间

## JSON字段格式示例

### schedule_times (定时时间)
```json
["09:00", "15:00", "21:00"]
```

### receiver_emails (收件人列表)
```json
["user1@example.com", "user2@example.com"]
```

### remark (积分备注)
```json
{
    "ip": "192.168.1.1",
    "device": "Chrome",
    "action": "daily_checkin"
}
```

---

## 注意事项

1. **数据完整性**: 所有外键关系都需要保持数据完整性
2. **并发控制**: 数据库操作使用事务保证原子性
3. **备份策略**: 建议定期备份数据库文件
4. **密码安全**: web_auth_config表中的密码应考虑加密存储
5. **数据清理**: points_history表可能会增长很快，需要定期清理旧数据

## 维护建议

1. **定期优化**: 使用 `VACUUM` 命令优化数据库
2. **监控大小**: 监控数据库文件大小，特别是积分历史数据
3. **索引维护**: 根据查询性能定期评估和调整索引
4. **数据归档**: 考虑将超过一年的历史数据归档到其他存储