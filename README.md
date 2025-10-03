# GPT-GOD 自动签到系统

<div align="center">

一个功能完善的 GPT-GOD 网站自动签到工具，支持多账号管理、定时签到、积分统计和Web管理界面。

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com)

</div>

## ✨ 主要功能

- 🎯 **自动签到**：支持多账号批量签到，自动处理Cloudflare验证
- ⏰ **定时任务**：灵活配置多个签到时间点，自动执行
- 💰 **积分管理**：完整的积分历史记录、统计分析和趋势图表
- 🎁 **兑换码**：支持批量兑换积分码
- 🌐 **Web界面**：现代化管理后台，支持移动端
- 📊 **数据统计**：详细的签到日志、积分来源分布、每日汇总
- 🔐 **安全认证**：Web界面登录保护和API令牌认证
- 📧 **邮件通知**：签到结果邮件提醒（可选）
- 🔄 **域名切换**：主备域名自动切换
- 💾 **数据持久化**：SQLite数据库统一管理

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 已安装以下浏览器之一：
  - Microsoft Edge（推荐）
  - Google Chrome
  - Brave Browser

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/dong-dong6/GptGodAutoCheckin.git
cd GptGodAutoCheckin
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **配置账号**

首次运行会自动创建配置数据库，有两种方式添加账号：

**方式一：通过Web界面添加（推荐）**

```bash
python app.py
```

访问 `http://localhost:8739/add-account` 添加账号

**方式二：直接使用Web界面配置**

启动服务后，通过Web界面进行所有配置：
- 添加账号
- 设置定时任务
- 配置域名和邮件通知

无需创建任何配置文件。

## 📖 使用方法

### Web管理界面（推荐）

启动Web服务：

```bash
python main.py
```

访问 `http://localhost:8739`，使用配置的用户名密码登录。

**主要功能：**
- 📊 **仪表盘**：查看系统状态、签到统计
- ✅ **签到管理**：立即签到或查看签到记录
- 🎁 **兑换码**：批量兑换积分码
- 💰 **积分管理**：积分统计、历史记录、趋势分析
- 📋 **日志查看**：签到日志和统计信息
- ⚙️ **系统设置**：定时任务、域名、邮件、账号管理

### 命令行工具

**签到操作：**

```bash
python cli.py                    # 运行签到（显示浏览器）
python cli.py --headless         # 运行签到（无头模式）
```

**积分同步：**

```bash
python cli.py --sync             # 同步积分历史
python cli.py --sync --max-pages 5  # 限制每个账号最多5页
```

**查看配置：**

```bash
python cli.py --config           # 显示当前配置
```

## 🏗️ 项目结构

```
GptGodAutoCheckin/
├── main.py                    # Web服务入口
├── cli.py                     # 命令行工具
├── app.py                     # Flask应用主体
├── src/                       # 源代码目录
│   ├── core/                  # 核心业务逻辑
│   │   ├── browser_service.py      # 浏览器服务基类
│   │   ├── checkin_service.py      # 签到服务
│   │   ├── points_sync_service.py  # 积分同步服务
│   │   └── redeem_service.py       # 兑换码服务
│   ├── data/                  # 数据层
│   │   ├── database.py             # 数据库初始化
│   │   └── repositories/           # 数据仓库
│   │       ├── checkin_repository.py   # 签到记录
│   │       ├── points_repository.py    # 积分历史
│   │       └── config_repository.py    # 配置管理
│   ├── infrastructure/        # 基础设施
│   │   ├── browser/               # 浏览器管理
│   │   │   ├── browser_manager.py
│   │   │   └── cloudflare_bypasser.py
│   │   ├── notification/          # 通知服务
│   │   │   └── email_service.py
│   │   └── scheduler/             # 定时任务
│   │       └── task_scheduler.py
│   ├── web/                   # Web层
│   │   ├── routes/                # API路由
│   │   └── middlewares/           # 中间件
│   └── utils/                 # 工具类
├── accounts_data/             # 数据库文件目录
└── logs/                      # 日志文件目录
```

## 🎨 Web界面预览

### 仪表盘
- 服务状态、签到统计
- 快速操作入口
- 实时数据更新

### 签到管理
- 一键签到所有账号
- 实时进度显示（SSE流）
- 签到结果详情

### 积分管理
- 总积分统计
- 各账号积分分布
- 每日积分趋势图
- 积分来源饼图
- 详细历史记录

### 系统设置
- ⏰ 定时签到：多时间点配置
- 🌐 域名设置：主备域名切换
- 📧 SMTP邮件：按账号配置通知
- 👥 账号管理：添加/删除账号
- 🔧 配置管理：导出/导入/重置

## 🔧 技术架构

### 技术栈

- **后端框架**: Flask
- **浏览器自动化**: DrissionPage
- **数据库**: SQLite
- **前端**: 原生HTML/CSS/JavaScript + Chart.js
- **定时任务**: schedule
- **邮件通知**: smtplib
- **架构模式**: 分层架构 (Service-Repository模式)

### 数据库结构

统一使用 SQLite 数据库 `accounts_data/gptgod_checkin.db`

主要表：
- `account_config`: 账号配置
- `system_config`: 系统配置
- `checkin_sessions`: 签到会话
- `checkin_logs`: 签到日志
- `points_history`: 积分历史
- `account_mapping`: 账号映射

详细文档见 [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)

## 📡 API文档

### 认证方式

**方式一：Session认证**
通过 `/login` 登录后使用

**方式二：Bearer Token**
```bash
curl -H "Authorization: Bearer your-api-token" http://localhost:8739/api/status
```

**方式三：URL参数**
```bash
curl http://localhost:8739/api/status?token=your-api-token
```

### 主要API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/checkin-stream` | GET | 执行签到（SSE流） |
| `/api/redeem` | POST | 兑换积分码 |
| `/api/schedule` | GET/POST | 定时任务管理 |
| `/api/domains` | GET/POST | 域名配置 |
| `/api/points` | GET | 积分统计 |
| `/api/points/history/daily` | GET | 每日积分汇总 |
| `/api/points/history/overview` | GET | 积分历史概览 |
| `/api/logs` | GET | 签到日志 |
| `/api/stats` | GET | 统计信息 |
| `/api/config/accounts` | GET | 获取账号列表 |
| `/api/config/accounts/add` | POST | 添加账号 |
| `/api/config/accounts/remove` | POST | 删除账号 |

详细API文档见各端点的代码注释。

## 🛠️ 高级配置

### 浏览器自动检测

系统会自动检测以下浏览器（按优先级）：

**Windows:**
1. Microsoft Edge
2. Google Chrome
3. Brave Browser

**macOS:**
1. Google Chrome
2. Microsoft Edge
3. Brave Browser

**Linux:**
1. Google Chrome
2. Chromium
3. Microsoft Edge

无需任何配置，开箱即用。

### 定时任务

支持多个签到时间点：

```python
# 通过Web界面配置，或直接修改数据库
config_manager.update_schedule_config(
    enabled=True,
    times=["09:00", "14:00", "21:00"]
)
```

### 邮件通知

配置SMTP服务器后，签到结果会自动发送邮件：

```python
config_manager.update_smtp_config(
    enabled=True,
    server="smtp.gmail.com",
    port=587,
    sender_email="your@gmail.com",
    sender_password="your-app-password",
    receiver_emails=["receiver@example.com"]
)
```

### 域名切换

支持主备域名自动切换：

```python
config_manager.update_domain_config(
    primary="gptgod.online",
    backup="gptgod.work",
    auto_switch=True
)
```

## 🐛 故障排查

### 浏览器未找到

```
错误: 未找到浏览器！
```

**解决方案：**
安装支持的浏览器（Edge/Chrome/Brave）

### 签到失败

```
错误: 登录失败
```

**可能原因：**
1. 账号密码错误
2. 网络问题
3. Cloudflare验证失败

**解决方案：**
- 检查账号密码
- 检查网络连接
- 查看日志文件 `web_service.log`

### 数据库锁定

```
错误: database is locked
```

**解决方案：**
确保没有多个进程同时访问数据库

### 端口占用

```
错误: Address already in use
```

**解决方案：**
修改 `app.py` 中的端口号：
```python
app.run(host='0.0.0.0', port=8739)  # 改为其他端口
```

## 📝 开发指南

### 项目结构

```
GptGodAutoCheckin/
├── main.py                    # Web服务入口
├── cli.py                     # 命令行工具
├── app.py                     # Flask应用主体
├── API.md                     # API接口文档
├── DATABASE_SCHEMA.md         # 数据库结构文档
├── src/                       # 源代码目录
│   ├── core/                  # 核心业务逻辑
│   │   ├── browser_service.py      # 浏览器服务基类
│   │   ├── checkin_service.py      # 签到服务
│   │   └── points_sync_service.py  # 积分同步服务
│   ├── data/                  # 数据层
│   │   ├── database.py             # 数据库初始化
│   │   └── repositories/           # 数据仓库
│   │       ├── base_repository.py     # 基础仓库类
│   │       ├── checkin_repository.py  # 签到记录
│   │       ├── points_repository.py   # 积分历史
│   │       └── config_repository.py   # 配置管理
│   ├── infrastructure/        # 基础设施
│   │   ├── browser/               # 浏览器管理
│   │   │   ├── browser_manager.py
│   │   │   └── cloudflare_bypasser.py
│   │   ├── notification/          # 通知服务
│   │   │   └── email_service.py
│   │   └── scheduler/             # 定时任务
│   │       └── task_scheduler.py
│   ├── web/                   # Web层
│   │   ├── middlewares/           # 中间件
│   │   │   ├── auth_middleware.py
│   │   │   └── error_handler.py
│   │   └── routes/                # API路由（集成在app.py中）
│   └── utils/                 # 工具类
│       └── logger.py
├── accounts_data/             # 数据库文件目录
│   └── gptgod_checkin.db     # SQLite数据库
├── logs/                      # 日志文件目录
└── web_service.log           # Web服务日志
```

### 添加新功能

1. **修改数据库结构**：编辑 `src/data/database.py`
2. **添加配置项**：在 `src/data/repositories/config_repository.py` 中添加相关方法
3. **添加服务层**：在 `src/core/` 中创建新的服务类
4. **添加API端点**：在 `app.py` 中添加路由
5. **更新前端**：修改 HTML 模板
6. **更新文档**：更新 `DATABASE_SCHEMA.md` 和 `README.md`

### 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加某个功能'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## ⚠️ 免责声明

本项目仅供学习交流使用，请勿用于非法用途。使用本工具产生的任何后果由使用者自行承担。

## 🙏 致谢

- [DrissionPage](https://github.com/g1879/DrissionPage) - 强大的浏览器自动化工具
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Chart.js](https://www.chartjs.org/) - 数据可视化库

## 📮 联系方式

如有问题或建议，欢迎：
- 提交 [Issue](https://github.com/dong-dong6/GptGodAutoCheckin/issues)
- 发起 [Discussion](https://github.com/dong-dong6/GptGodAutoCheckin/discussions)

---

<div align="center">
Made with ❤️ by GPT-GOD Auto Checkin Team
</div>
