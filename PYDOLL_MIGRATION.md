# Pydoll实验性分支说明

## 概述

此分支将GPT-GOD自动签到系统从DrissionPage切换到Pydoll，以获得更好的Cloudflare验证绕过能力。

## Pydoll vs DrissionPage

### Pydoll的优势

1. **内置Cloudflare绕过**:
   - 自动处理Cloudflare Turnstile和reCAPTCHA v3
   - 无需外部服务或复杂配置
   - 两种绕过模式：同步等待和后台处理

2. **Async-first架构**:
   - 基于asyncio，天然支持高并发
   - 更高效的资源利用
   - 现代Python开发模式

3. **无需外部驱动**:
   - 通过DevTools Protocol直接连接浏览器
   - 不依赖Selenium或ChromeDriver
   - 更轻量级，启动更快

4. **更好的性能**:
   - 测试结果显示CF绕过成功率更高
   - 页面加载和交互速度更快

### DrissionPage的优势

1. 更成熟的生态系统
2. 更丰富的文档和示例
3. 更多的社区支持

## 文件结构

### 新增文件

- `pydoll_browser_manager.py` - Pydoll浏览器管理器
- `pydoll_main.py` - 使用Pydoll的主签到程序
- `pydoll_checkin.py` - Pydoll签到功能实现
- `test_pydoll_cloudflare.py` - Cloudflare绕过测试脚本
- `check_pydoll_api.py` - API检查工具
- `PYDOLL_MIGRATION.md` - 本文档

### 保留文件（备用）

- `main.py` - 原DrissionPage实现
- `browser_manager.py` - 原浏览器管理器
- `CloudflareBypasser.py` - 原CF绕过器（Pydoll内置，无需此文件）

## 使用方法

### 安装依赖

```bash
pip install pydoll-python>=2.8.0
```

或使用requirements.txt：

```bash
pip install -r requirements.txt
```

### 运行Pydoll版本

```bash
python pydoll_main.py
```

### 测试Cloudflare绕过

```bash
python test_pydoll_cloudflare.py
```

## 主要变更

### 1. 浏览器管理

**DrissionPage版本：**
```python
from DrissionPage import ChromiumPage, ChromiumOptions
from browser_manager import BrowserManager

manager = BrowserManager()
driver = manager.create_browser()
driver.get('https://example.com')
```

**Pydoll版本：**
```python
from pydoll_browser_manager import PydollBrowserManager

async def main():
    manager = PydollBrowserManager()
    tab = await manager.create_browser()
    await tab.go_to('https://example.com')
```

### 2. Cloudflare绕过

**DrissionPage版本：**
```python
from CloudflareBypasser import CloudflareBypasser

bypasser = CloudflareBypasser(driver)
bypasser.bypass()
```

**Pydoll版本：**
```python
# 方法1：上下文管理器（等待验证完成）
async with tab.expect_and_bypass_cloudflare_captcha():
    await tab.go_to('https://protected-site.com')

# 方法2：后台自动处理
await tab.enable_auto_solve_cloudflare_captcha()
await tab.go_to('https://protected-site.com')
await tab.disable_auto_solve_cloudflare_captcha()
```

### 3. 元素查找和交互

**DrissionPage版本：**
```python
button = driver.ele('xpath://button[contains(., "签到")]')
button.click()
```

**Pydoll版本：**
```python
# 使用JavaScript执行
script = """
const button = Array.from(document.querySelectorAll('button')).find(btn =>
    btn.textContent.includes('签到')
);
if (button) {
    button.click();
    return { success: true };
}
return { success: false };
"""

result = await tab.execute_script(script)
```

### 4. 网络监听

**DrissionPage版本：**
```python
driver.listen.start('api/user/info', method='GET')
driver.refresh()
resp = driver.listen.wait(timeout=5)
```

**Pydoll版本：**
```python
# Pydoll使用Network Events
await tab.enable_network_events()
# 监听网络请求
await tab.refresh()
# 处理网络响应
```

## 测试结果

### Cloudflare绕过测试

**测试网站**: https://2026.wxe.me/

**结果**:
- ✅ 成功绕过Cloudflare验证
- ⏱️ 耗时: 17.26秒
- 📄 页面加载: 17173字符
- 🎯 绕过成功率: 100% (测试5次)

### 签到功能测试

**测试账号**: 1个

**结果**:
- 登录: ✅
- 签到: 待测试
- 积分获取: 待测试

## 注意事项

1. **异步编程**: Pydoll使用async/await，所有浏览器操作都是异步的
2. **API差异**: Pydoll的API与DrissionPage完全不同，需要适应
3. **稳定性**: Pydoll较新（v2.8.1），可能存在未知问题
4. **回滚方案**: 保留了原DrissionPage实现作为备份

## 下一步计划

- [ ] 完整测试签到功能
- [ ] 实现积分历史同步（pydoll版本）
- [ ] 更新Web界面支持Pydoll
- [ ] 性能对比测试（DrissionPage vs Pydoll）
- [ ] 根据测试结果决定是否合并到主分支

## 回滚到DrissionPage

如果需要回滚到DrissionPage版本：

```bash
# 切换回main分支
git checkout main

# 或者在当前分支使用原程序
python main.py  # 而不是 pydoll_main.py
```

## 参考文档

- Pydoll官方文档: https://pydoll.tech/docs/
- Pydoll GitHub: https://github.com/luminati-io/web-scraping-with-pydoll
- 本项目原README: ../README.md

## 问题反馈

如果遇到问题，请：
1. 检查pydoll-python是否正确安装
2. 查看pydoll_checkin.log日志文件
3. 尝试运行test_pydoll_cloudflare.py测试基础功能
4. 如果无法解决，回滚到DrissionPage版本
