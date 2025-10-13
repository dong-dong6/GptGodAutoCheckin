# SMTP 别名发送功能使用指南

## ✅ 已完成的修改

### 1. 数据库更新 (src/data/database.py)
- 添加了 `from_email` 字段用于存储代发邮箱地址
- 实现了自动数据库迁移

### 2. 配置管理器 (src/data/repositories/config_repository.py)
- `get_smtp_config()`: 现在返回 `from_email` 字段
- `update_smtp_config()`: 支持保存 `from_email` 参数

### 3. 邮件服务 (src/infrastructure/notification/email_service.py)
- 实现了代发功能：
  - `auth_email` (sender_email): 用于SMTP认证
  - `from_email`: 显示给收件人的发件邮箱
  - 如果 `from_email` 为空，则使用 `auth_email`

## 📋 剩余工作

### 4. 更新前端界面 (app.py)

在 SMTP 设置部分添加代发邮箱字段，在第1449行之后添加：

```html
<div class="form-group">
    <label>代发邮箱（可选）</label>
    <input type="email" id="from-email" placeholder="noreply@company.com">
    <p style="color: #6b7280; font-size: 12px; margin-top: 4px;">
        留空则使用认证邮箱作为发件人。<br>
        设置后，邮件将以此邮箱地址发送，但使用上面的认证邮箱登录SMTP
    </p>
</div>
```

### 5. 更新 JavaScript (app.py)

#### 修改 loadSmtp() 函数 (约2388行):
```javascript
document.getElementById('from-email').value = data.config.from_email || '';
```

#### 修改 saveSmtp() 函数 (约2404行):
```javascript
const fromEmail = document.getElementById('from-email').value;
```

然后在 fetch body 中添加:
```javascript
from_email: fromEmail,
```

### 6. 更新后端API (app.py 约2913行)

```python
from_email=data.get('from_email', ''),
```

### 7. 更新 Web 路由 (src/web/routes/config_routes.py 约33行)

```python
from_email=data.get('from_email', ''),
```

## 🧪 测试步骤

1. 启动应用: `python app.py`
2. 进入系统设置 → SMTP邮件设置
3. 配置：
   - **认证邮箱**: 你的Gmail账号（如 `yourname@gmail.com`）
   - **认证密码**: Gmail应用专用密码
   - **代发邮箱**: 你想显示的邮箱（如 `noreply@yourcompany.com`）
   - **发件人名称**: 显示名称（如 "GPT-GOD系统"）
4. 保存后运行测试: `python test_email_sender_name.py`

## 📧 工作原理

```
认证流程:
1. 使用 yourname@gmail.com + 密码 登录Gmail SMTP服务器
2. 设置邮件From字段为 noreply@yourcompany.com
3. 收件人看到的发件人是: GPT-GOD系统 <noreply@yourcompany.com>
```

## ⚠️ 注意事项

1. **Gmail限制**: Gmail可能会在邮件头中显示"代表xxx发送"
2. **SPF记录**: 如果使用自定义域名作为代发邮箱，建议配置SPF记录
3. **DMARC策略**: 某些邮件服务器可能拒绝代发邮件
4. **最佳实践**: 代发邮箱域名应该是你拥有的域名

## 🎯 使用场景

- 使用Gmail SMTP但想显示企业邮箱
- 使用个人邮箱认证但显示系统邮箱（如noreply@）
- 统一发件人地址，方便收件人识别

## 完整示例配置

```
认证邮箱: admin@gmail.com
认证密码: **** (Gmail应用专用密码)
代发邮箱: noreply@mycompany.com
发件人名称: MyCompany 自动签到系统
```

收件人将看到:
```
From: MyCompany 自动签到系统 <noreply@mycompany.com>
```
