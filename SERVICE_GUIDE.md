# GPT-GOD 自动化服务部署指南

## 功能说明
- **Web界面**：提供友好的操作界面
- **定时签到**：每天9点自动签到所有账号
- **兑换码服务**：支持批量兑换积分码
- **API接口**：提供RESTful API供外部调用

## 快速部署

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置账号
复制 `account.yml.example` 为 `account.yml` 并填写账号信息

### 3. 运行方式

#### 方式一：直接运行
```bash
python app.py
```

#### 方式二：使用批处理文件
双击运行 `start_app.bat`

#### 方式三：设置开机自启动（推荐）
1. 打开"任务计划程序" (taskschd.msc)
2. 创建基本任务
3. 名称：GPT-GOD自动签到服务
4. 触发器：计算机启动时
5. 操作：启动程序
   - 程序：`E:\AllCode\python\GptGodAutoCheckin\start_app.bat`
   - 起始位置：`E:\AllCode\python\GptGodAutoCheckin`
6. 完成后勾选"打开属性对话框"
7. 在属性中勾选"不管用户是否登录都要运行"和"使用最高权限运行"

## 使用说明

### Web界面
- 访问：http://localhost:8739
- 功能：手动签到、批量兑换码、查看状态

### API接口

#### 1. 手动触发签到
```bash
POST /api/checkin
```

#### 2. 兑换积分码
```bash
POST /api/redeem
Content-Type: application/json

{
  "codes": ["code1", "code2"],
  "account": "all"  // 或指定邮箱
}
```

#### 3. 查询状态
```bash
GET /api/status
```

#### 4. 获取签到日志
```bash
GET /api/logs
```

#### 5. 获取统计信息
```bash
GET /api/stats
```

## 日志文件
- `web_service.log` - Web服务日志
- `cloudflare_bypass.log` - 签到详细日志
- `startup.log` - 启动日志
- `checkin_logs/` - 签到记录JSON文件

## 外部调用示例

### Python
```python
import requests

# 触发签到
response = requests.post('http://localhost:8739/api/checkin')

# 兑换码
data = {
    "codes": ["ABC123", "DEF456"],
    "account": "all"
}
response = requests.post('http://localhost:8739/api/redeem', json=data)
```

### cURL
```bash
# 签到
curl -X POST http://localhost:8739/api/checkin

# 兑换
curl -X POST http://localhost:8739/api/redeem \
  -H "Content-Type: application/json" \
  -d '{"codes":["ABC123"],"account":"all"}'
```

## 注意事项
1. 服务需要管理员权限安装
2. 确保8739端口未被占用
3. 首次运行建议使用调试模式测试
4. Chrome浏览器需要提前安装

## 故障排除

### 服务无法启动
- 检查端口占用：`netstat -ano | findstr :8739`
- 查看服务日志：`service.log`
- 确保以管理员身份运行

### 签到失败
- 检查账号密码是否正确
- 查看 `cloudflare_bypass.log`
- 确保Chrome浏览器正常

### 兑换码失败
- 确认兑换码格式正确
- 检查账号是否已登录
- 查看页面是否有验证码

## 更新说明
- v2.0: 添加Web服务和Windows服务支持
- v1.0: 基础签到功能