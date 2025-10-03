# API 接口文档

## 认证方式

### 方式一：Session认证
通过 `/login` 登录后，Session自动保持登录状态

### 方式二：Bearer Token
```bash
curl -H "Authorization: Bearer your-api-token" http://localhost:8739/api/status
```

### 方式三：URL参数
```bash
curl http://localhost:8739/api/status?token=your-api-token
```

## API端点

### 系统相关

#### GET /api/status
获取系统状态

**响应示例**:
```json
{
  "status": "running",
  "last_checkin": "2025-10-03 12:00:00",
  "accounts_count": 8
}
```

---

### 认证相关

#### POST /login
用户登录

**请求体**:
```json
{
  "username": "admin",
  "password": "password"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "登录成功"
}
```

#### GET /logout
用户登出

**响应**: 重定向到登录页

---

### 签到相关

#### POST /api/checkin
触发手动签到任务

**请求体**:
```json
{
  "trigger_by": "admin"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "签到任务已启动"
}
```

#### GET /api/checkin-stream
签到任务实时流（SSE）

**响应**: Server-Sent Events流

```
data: {"type": "start", "total": 8}
data: {"type": "progress", "email": "test@example.com", "message": "签到成功"}
data: {"type": "complete", "success": 5, "failed": 3}
```

#### GET /api/checkin/logs
获取签到日志

**参数**:
- `session_id` (可选): 会话ID
- `limit` (可选): 返回数量，默认100

**响应示例**:
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "session_id": "abc123",
      "email": "test@example.com",
      "status": "success",
      "message": "签到成功",
      "points_earned": 5,
      "domain": "gptgod.online",
      "created_at": "2025-10-03 12:00:00"
    }
  ]
}
```

#### GET /api/checkin/sessions
获取签到会话列表

**参数**:
- `limit` (可选): 返回数量，默认50

**响应示例**:
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "abc123",
      "total_accounts": 8,
      "start_time": "2025-10-03 12:00:00",
      "end_time": "2025-10-03 12:05:00",
      "status": "completed"
    }
  ]
}
```

---

### 积分相关

#### GET /api/points
获取积分统计信息

**响应示例**:
```json
{
  "success": true,
  "total_points": 15000,
  "accounts": [
    {
      "email": "test@example.com",
      "points": 5000,
      "uid": "user123"
    }
  ]
}
```

#### GET /api/points/history
获取积分历史记录

**参数**:
- `email` (可选): 筛选指定账号
- `limit` (可选): 返回数量，默认100
- `offset` (可选): 偏移量，默认0

**响应示例**:
```json
{
  "success": true,
  "total": 1500,
  "records": [
    {
      "id": 1,
      "email": "test@example.com",
      "amount": 5,
      "description": "每日签到",
      "created_at": "2025-10-03 12:00:00"
    }
  ]
}
```

#### GET /api/points/statistics
获取积分统计数据

**响应示例**:
```json
{
  "success": true,
  "total_points": 15000,
  "total_records": 1500,
  "by_source": {
    "每日签到": 1000,
    "兑换码": 500,
    "其他": 50
  },
  "by_date": {
    "2025-10-01": 100,
    "2025-10-02": 120,
    "2025-10-03": 150
  }
}
```

#### POST /api/points/sync
同步积分历史

**请求体**:
```json
{
  "max_pages": 5
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "积分同步任务已启动"
}
```

---

### 配置相关

#### GET /api/config/accounts
获取账号列表

**响应示例**:
```json
{
  "success": true,
  "accounts": [
    {
      "mail": "test@example.com",
      "enabled": true,
      "send_email_notification": false
    }
  ]
}
```

#### POST /api/config/accounts
添加账号

**请求体**:
```json
{
  "email": "new@example.com",
  "password": "password123",
  "send_email_notification": true
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "账号添加成功"
}
```

#### DELETE /api/config/accounts
删除账号

**请求体**:
```json
{
  "email": "test@example.com"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "账号删除成功"
}
```

#### GET /api/config/domains
获取域名配置

**响应示例**:
```json
{
  "success": true,
  "primary": "gptgod.online",
  "backup": "gptgod.work",
  "auto_switch": true
}
```

#### POST /api/config/domains
更新域名配置

**请求体**:
```json
{
  "primary": "gptgod.online",
  "backup": "gptgod.work",
  "auto_switch": true
}
```

#### GET /api/config/smtp
获取SMTP配置

**响应示例**:
```json
{
  "success": true,
  "enabled": true,
  "server": "smtp.gmail.com",
  "port": 587,
  "sender_email": "sender@gmail.com",
  "receiver_emails": ["receiver@example.com"]
}
```

#### POST /api/config/smtp
更新SMTP配置

**请求体**:
```json
{
  "enabled": true,
  "server": "smtp.gmail.com",
  "port": 587,
  "sender_email": "sender@gmail.com",
  "sender_password": "password",
  "receiver_emails": ["receiver@example.com"]
}
```

---

### 定时任务相关

#### GET /api/schedule
获取定时任务配置

**响应示例**:
```json
{
  "success": true,
  "enabled": true,
  "times": ["09:00", "13:00", "21:00"],
  "next_run": "2025-10-03 21:00:00"
}
```

#### POST /api/schedule
更新定时任务配置

**请求体**:
```json
{
  "enabled": true,
  "times": ["09:00", "13:00", "21:00"]
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "定时任务配置已更新"
}
```

---

### 兑换码相关

#### POST /api/redeem
兑换积分码

**请求体**:
```json
{
  "codes": "CODE1,CODE2,CODE3",
  "email": "test@example.com"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "兑换任务已启动"
}
```

#### GET /api/redeem-stream
兑换码任务实时流（SSE）

**响应**: Server-Sent Events流

```
data: {"type": "start", "total": 3}
data: {"type": "progress", "code": "CODE1", "message": "兑换成功"}
data: {"type": "complete", "success": 2, "failed": 1}
```

---

### 日志相关

#### GET /api/logs/sessions
获取签到会话统计

**响应示例**:
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "abc123",
      "total_accounts": 8,
      "success_count": 5,
      "failed_count": 3,
      "start_time": "2025-10-03 12:00:00"
    }
  ]
}
```

#### GET /api/logs/statistics
获取日志统计信息

**响应示例**:
```json
{
  "success": true,
  "total_sessions": 100,
  "total_checkins": 800,
  "success_rate": 0.95,
  "by_date": {
    "2025-10-01": {"success": 8, "failed": 0},
    "2025-10-02": {"success": 7, "failed": 1}
  }
}
```

---

## 错误响应

所有API在出错时返回统一格式：

```json
{
  "success": false,
  "error": "错误类型",
  "message": "详细错误信息"
}
```

### 常见错误码

- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证或认证失败
- `403 Forbidden`: 无权限访问
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

---

## SSE (Server-Sent Events) 接口

### /api/checkin-stream

实时推送签到进度

**事件类型**:
- `start`: 任务开始
- `progress`: 单个账号处理进度
- `complete`: 任务完成
- `error`: 发生错误

### /api/redeem-stream

实时推送兑换码处理进度

**事件类型**:
- `start`: 任务开始
- `progress`: 单个兑换码处理进度
- `complete`: 任务完成
- `error`: 发生错误

---

## 使用示例

### Python

```python
import requests

# 登录
session = requests.Session()
session.post('http://localhost:8739/login', json={
    'username': 'admin',
    'password': 'password'
})

# 获取账号列表
response = session.get('http://localhost:8739/api/config/accounts')
accounts = response.json()['accounts']

# 触发签到
session.post('http://localhost:8739/api/checkin', json={
    'trigger_by': 'api'
})
```

### cURL

```bash
# 使用Token认证
TOKEN="your-api-token"

# 获取系统状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8739/api/status

# 添加账号
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","password":"pwd123"}' \
  http://localhost:8739/api/config/accounts

# 触发签到
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"trigger_by":"api"}' \
  http://localhost:8739/api/checkin
```

### JavaScript

```javascript
// 使用Fetch API
async function getStatus() {
  const response = await fetch('http://localhost:8739/api/status', {
    headers: {
      'Authorization': 'Bearer your-api-token'
    }
  });
  const data = await response.json();
  console.log(data);
}

// 监听SSE流
const eventSource = new EventSource('http://localhost:8739/api/checkin-stream?token=your-api-token');

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log('签到进度:', data);
});

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('签到完成:', data);
  eventSource.close();
});
```

---

## 注意事项

1. **认证**: 所有API（除登录页面）都需要认证
2. **速率限制**: 建议不要频繁调用，避免对服务器造成压力
3. **SSE连接**: 使用完毕后记得关闭EventSource连接
4. **时区**: 所有时间均为服务器本地时间
5. **编码**: 所有请求和响应均使用UTF-8编码

---

**最后更新**: 2025-10-03
