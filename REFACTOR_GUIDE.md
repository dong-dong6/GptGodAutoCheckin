# 代码重构指南 (Code Refactoring Guide)

## 概述

本次重构旨在将现有的6662行代码（9个文件）从扁平结构重组为分层的工程化结构，提高代码的可维护性、可测试性和可扩展性。

## 当前状态（重构中）

### 已完成
- ✅ 创建新的目录结构
- ✅ 备份原有文件到新目录

### 进行中
- 🔄 重构计划文档

### 待完成
- ⏳ 拆分app.py（4101行 → 多个小文件）
- ⏳ 提取HTML模板
- ⏳ 统一数据访问层（Repository模式）
- ⏳ 抽取Service层
- ⏳ 更新导入路径
- ⏳ 测试重构后的功能

## 新目录结构

```
C:\GptGodAutoCheckin\
├── src/                              # 新的源代码目录
│   ├── core/                         # 核心业务逻辑
│   │   ├── checkin_service_legacy.py     # 签到服务（待重构）
│   │   └── points_sync_service_legacy.py # 积分同步服务（待重构）
│   ├── data/                         # 数据访问层
│   │   ├── database.py              # 统一数据库管理器
│   │   ├── repositories/            # 数据仓库
│   │   │   ├── checkin_repository.py
│   │   │   ├── points_repository.py
│   │   │   └── config_repository.py
│   │   └── models/                  # 数据模型（待创建）
│   ├── infrastructure/              # 基础设施层
│   │   ├── browser/                 # 浏览器相关
│   │   │   ├── browser_manager.py
│   │   │   └── cloudflare_bypasser.py
│   │   ├── notification/            # 通知服务（待创建）
│   │   └── scheduler/               # 定时任务（待创建）
│   ├── web/                         # Web服务层
│   │   ├── routes/                  # 路由模块（待拆分from app.py）
│   │   ├── middlewares/             # 中间件（待创建）
│   │   ├── templates/               # HTML模板（待提取）
│   │   └── static/                  # 静态资源
│   └── utils/                       # 工具类（待创建）
│
├── 旧文件（根目录）                   # 保留作为参考
│   ├── app.py                       # Web服务（4101行，待拆分）
│   ├── main.py                      # 签到主程序（705行）
│   ├── fetch_points_history.py      # 积分同步（471行）
│   └── ...                          # 其他旧文件
│
├── tests/                           # 测试目录（待创建测试）
├── scripts/                         # 脚本目录
├── logs/                            # 日志目录
├── accounts_data/                   # 数据目录
│   └── gptgod_checkin.db           # SQLite数据库
│
├── REFACTOR_GUIDE.md               # 本文档
└── README.md                        # 项目README
```

## 文件映射关系

### 已复制的文件

| 原文件 | 新位置 | 状态 |
|--------|--------|------|
| `browser_manager.py` | `src/infrastructure/browser/browser_manager.py` | ✅ 已复制 |
| `CloudflareBypasser.py` | `src/infrastructure/browser/cloudflare_bypasser.py` | ✅ 已复制 |
| `unified_db_manager.py` | `src/data/database.py` | ✅ 已复制 |
| `checkin_logger_db.py` | `src/data/repositories/checkin_repository.py` | ✅ 已复制 |
| `points_history_manager.py` | `src/data/repositories/points_repository.py` | ✅ 已复制 |
| `config_manager.py` | `src/data/repositories/config_repository.py` | ✅ 已复制 |
| `main.py` | `src/core/checkin_service_legacy.py` | ✅ 已复制 |
| `fetch_points_history.py` | `src/core/points_sync_service_legacy.py` | ✅ 已复制 |

### 待处理的文件

| 原文件 | 处理方式 | 优先级 |
|--------|----------|--------|
| `app.py` (4101行) | 拆分为多个路由模块 | 🔴 高 |
| `app.py` 内嵌HTML | 提取到 `templates/` | 🔴 高 |
| `main.py` 邮件功能 | 提取到 `infrastructure/notification/` | 🟡 中 |
| `main.py` 定时任务 | 提取到 `infrastructure/scheduler/` | 🟡 中 |

## 重构策略

### Phase 1: 拆分巨型文件（本周）

#### 1.1 拆分 app.py (4101行 → ~200行)

**目标**: 将Flask应用拆分为多个模块化的路由文件

**步骤**:
1. 提取HTML模板到 `templates/`
2. 按功能拆分路由：
   - `auth_routes.py` - 登录、登出、认证
   - `checkin_routes.py` - 签到相关API
   - `config_routes.py` - 配置管理API
   - `points_routes.py` - 积分相关API
   - `redeem_routes.py` - 兑换码API
   - `logs_routes.py` - 日志查询API
3. 创建精简的 `src/web/app.py` 作为应用入口

**预期文件大小**:
- `src/web/app.py`: ~150行
- 每个路由文件: ~200-300行
- 总计: ~1500行（比原来更清晰）

#### 1.2 重构 main.py (705行)

**目标**: 抽取核心签到逻辑到Service层

**步骤**:
1. 创建 `CheckinService` 类
2. 提取邮件通知到 `NotificationService`
3. 主文件变为简单的CLI入口

**预期文件大小**:
- `main.py`: ~80行
- `CheckinService`: ~350行
- `NotificationService`: ~150行

### Phase 2: 统一数据访问层（下周）

#### 2.1 引入Repository模式

**目标**: 规范化数据访问，便于测试和维护

**步骤**:
1. 创建 `BaseRepository` 基类
2. 重构现有Repository类继承基类
3. 统一接口和异常处理

#### 2.2 创建数据模型

**目标**: 类型安全和数据验证

**步骤**:
1. 创建 `models/account.py`
2. 创建 `models/checkin.py`
3. 创建 `models/points.py`

### Phase 3: 完善基础设施（下周）

#### 3.1 通知服务

**文件**: `src/infrastructure/notification/`
- `email_sender.py` - 邮件发送器
- `notification_service.py` - 通知服务抽象

#### 3.2 定时任务

**文件**: `src/infrastructure/scheduler/`
- `task_scheduler.py` - 定时任务调度器

### Phase 4: 测试和文档（下下周）

#### 4.1 添加单元测试
- Repository层测试
- Service层测试
- 目标覆盖率: 70%

#### 4.2 更新文档
- API文档
- 部署文档
- 开发文档

## 如何使用当前代码

### 运行旧版本（仍然可用）

```bash
# 签到任务
python main.py

# Web服务
python app.py

# 积分同步
python fetch_points_history.py
```

### 运行新版本（重构完成后）

```bash
# 签到任务
python -m src.core.checkin_service

# Web服务
python -m src.web.app

# 积分同步
python -m src.core.points_sync_service
```

## 注意事项

### 兼容性
- ✅ 旧文件保留在根目录，保证向后兼容
- ✅ 数据库结构不变，无需迁移
- ✅ API接口保持一致

### 导入路径
重构后，导入路径会从：
```python
from browser_manager import BrowserManager
from config_manager import ConfigManager
```

变为：
```python
from src.infrastructure.browser.browser_manager import BrowserManager
from src.data.repositories.config_repository import ConfigRepository
```

### 数据库
- 数据库文件位置不变：`accounts_data/gptgod_checkin.db`
- 数据库结构不变
- 无需迁移数据

## 回滚方案

如果重构出现问题，可以随时回滚：

```bash
# 使用根目录的旧文件
python main.py      # 而不是 python -m src.core.checkin_service
python app.py       # 而不是 python -m src.web.app
```

所有旧文件都保留在根目录，可以随时切换回去。

## 进度跟踪

### 第1周（本周）
- [x] 分析代码结构
- [x] 设计新目录结构
- [x] 创建目录和复制文件
- [ ] 拆分 app.py 路由
- [ ] 提取 HTML 模板
- [ ] 测试重构后的Web服务

### 第2周
- [ ] 重构数据访问层（Repository）
- [ ] 抽取Service层
- [ ] 创建数据模型
- [ ] 测试核心业务逻辑

### 第3周
- [ ] 完善基础设施层
- [ ] 添加单元测试
- [ ] 更新文档
- [ ] 性能测试

## 参考资料

- [Flask项目结构最佳实践](https://flask.palletsprojects.com/patterns/)
- [Repository Pattern in Python](https://www.cosmicpython.com/book/chapter_02_repository.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## 联系方式

如有问题或建议，请：
1. 查看 `README.md` 了解项目功能
2. 查看 `DATABASE.md` 了解数据库结构
3. 参考根目录的旧代码作为实现参考

---

**最后更新**: 2025-10-02
**重构状态**: 🔄 进行中
**完成度**: 20%
