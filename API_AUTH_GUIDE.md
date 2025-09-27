# API认证使用说明

## 认证配置
在 `account.yml` 中配置：
```yaml
web_auth:
  enabled: true       # 是否启用认证
  username: admin     # 登录用户名
  password: yourpass  # 登录密码
  api_token: ''       # API令牌（留空自动生成）
```

## 获取API令牌
1. 启动服务后访问：http://localhost:8739/login?show_token=true
2. 登录后页面会显示API令牌
3. 或查看启动日志中的令牌

## Web界面访问
1. 浏览器访问：http://localhost:8739
2. 输入用户名和密码登录
3. 登录后24小时内有效

## API调用方式

### 方式1：Header认证（推荐）
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_API_TOKEN'
}

# 签到
response = requests.post('http://localhost:8739/api/checkin', headers=headers)

# 兑换码
data = {
    "codes": ["code1", "code2"],
    "account": "all"
}
response = requests.post('http://localhost:8739/api/redeem', headers=headers, json=data)
```

### 方式2：URL参数认证
```bash
# 签到
curl -X POST "http://localhost:8739/api/checkin?token=YOUR_API_TOKEN"

# 兑换码
curl -X POST "http://localhost:8739/api/redeem?token=YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"codes":["ABC123"]}'
```

### 方式3：禁用认证（仅内网使用）
设置 `web_auth.enabled: false` 可完全禁用认证

## 错误响应
未认证时返回：
```json
{
  "error": "Unauthorized",
  "message": "请提供有效的认证令牌"
}
```
状态码：401

## 安全建议
1. **修改默认密码**：首次使用请修改admin123为强密码
2. **保护API令牌**：不要在公开代码中暴露令牌
3. **使用HTTPS**：生产环境建议配置反向代理使用HTTPS
4. **定期更换**：定期更新密码和API令牌

## 调用示例

### Python完整示例
```python
import requests
import json

class GPTGodAPI:
    def __init__(self, base_url='http://localhost:8739', token='YOUR_TOKEN'):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {token}'}

    def checkin(self):
        """执行签到"""
        response = requests.post(f'{self.base_url}/api/checkin', headers=self.headers)
        return response.json()

    def redeem(self, codes, account='all'):
        """兑换码"""
        data = {'codes': codes, 'account': account}
        response = requests.post(f'{self.base_url}/api/redeem',
                                headers=self.headers, json=data)
        return response.json()

    def status(self):
        """查询状态"""
        response = requests.get(f'{self.base_url}/api/status', headers=self.headers)
        return response.json()

# 使用示例
api = GPTGodAPI(token='your_token_here')
print(api.checkin())
print(api.redeem(['CODE123']))
```

### 外部系统集成
可以通过Webhook、定时任务等方式调用API：
- IFTTT
- Zapier
- GitHub Actions
- Jenkins
- 自定义定时脚本