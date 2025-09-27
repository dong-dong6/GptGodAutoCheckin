**仅在windows环境测试过**

## 功能特性
- 🕒 自动签到：每天9点自动执行签到
- 🌐 Web界面：提供友好的管理界面
- 📧 邮件通知：签到结果通过邮件发送
- 🎁 兑换码管理：支持批量兑换积分码
- 📊 统计分析：详细的签到日志和统计数据
- 💰 积分历史：自动获取并保存所有历史积分记录
- 📈 积分可视化：饼状图展示积分分布
- 🔐 API接口：提供RESTful API供外部调用

## 快速开始

### 1. 配置账号
在`account.yml`中填写你的账号密码，支持多账号：
```yaml
account:
  - mail: your_email@example.com
    password: your_password
  - mail: another_email@example.com
    password: another_password
```

### 2. 运行服务

#### 方式一：直接运行
```bash
python app.py
```
访问 http://localhost:8739 使用Web界面

#### 方式二：设置计划任务（推荐）

windows上计划任务中添加每日任务，即可自动签到
![image](https://github.com/user-attachments/assets/8ec5cf56-b42a-4573-9e50-7eb40c9e7703)
![image](https://github.com/user-attachments/assets/78a719c2-3c62-4cc0-a18b-164c12a4bc1d)
![image](https://github.com/user-attachments/assets/0ab20b28-b2ea-488b-a665-68918c7a0b8a)
在这里中：
- 程序或脚本：使用 `start_app.bat` 的全路径
- 起始位置：使用项目文件夹路径

## 详细文档
- [服务部署指南](SERVICE_GUIDE.md)
- [API认证指南](API_AUTH_GUIDE.md)
- [积分历史功能](POINTS_HISTORY_GUIDE.md)

## 要求
- Windows系统
- Python 3.8+
- Chrome浏览器
