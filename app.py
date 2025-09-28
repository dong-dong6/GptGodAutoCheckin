import time
import logging
import threading
import os
import hashlib
import secrets
import sqlite3
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, make_response, Response
import schedule
import yaml
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from main import send_email_notification, get_chromium_options, load_config
from checkin_logger_db import CheckinLoggerDB
from points_history_manager import PointsHistoryManager
from config_manager import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_service.log', mode='a', encoding='utf-8')
    ]
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # 生成随机密钥
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # 会话24小时有效

# 全局变量存储任务状态
task_status = {
    'last_checkin': None,
    'last_redeem': None,
    'checkin_results': [],
    'redeem_results': [],
    'schedule_times': []  # 存储当前的定时时间
}

# 认证配置
AUTH_CONFIG = {
    'enabled': True,  # 是否启用认证
    'username': '',  # 从配置文件读取
    'password_hash': '',  # 密码的MD5哈希
    'api_token': ''  # API访问令牌
}

def load_auth_config():
    """加载认证配置"""
    try:
        config_manager = ConfigManager()
        auth_config = config_manager.get_web_auth_config()

        AUTH_CONFIG['enabled'] = auth_config['enabled']
        AUTH_CONFIG['username'] = auth_config['username']
        AUTH_CONFIG['password_hash'] = hashlib.md5(auth_config['password'].encode()).hexdigest()
        AUTH_CONFIG['api_token'] = auth_config['api_token'] or secrets.token_urlsafe(32)

        logging.info(f"认证配置加载完成，用户名: {AUTH_CONFIG['username']}")
    except Exception as e:
        logging.warning(f"加载认证配置失败，使用默认配置: {e}")
        AUTH_CONFIG['username'] = 'admin'
        AUTH_CONFIG['password_hash'] = hashlib.md5('admin123'.encode()).hexdigest()
        AUTH_CONFIG['api_token'] = secrets.token_urlsafe(32)

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AUTH_CONFIG['enabled']:
            return f(*args, **kwargs)

        # 检查是否已登录（会话认证）
        if session.get('authenticated'):
            return f(*args, **kwargs)

        # 检查API令牌（用于API调用）
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token == AUTH_CONFIG['api_token']:
                return f(*args, **kwargs)

        # 检查URL参数中的token（方便调试）
        url_token = request.args.get('token')
        if url_token and url_token == AUTH_CONFIG['api_token']:
            return f(*args, **kwargs)

        # 如果是API请求，返回401
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized', 'message': '请提供有效的认证令牌'}), 401

        # 否则重定向到登录页面
        return redirect(url_for('login', next=request.url))

    return decorated_function

# 登录页面模板 - Apple风格
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - GPT-GOD</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(180deg, #f2f2f7 0%, #ffffff 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 48px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
            width: 100%;
            max-width: 420px;
            border: 1px solid rgba(255, 255, 255, 0.7);
        }
        .logo {
            text-align: center;
            margin-bottom: 40px;
        }
        .logo-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #007AFF, #5856D6);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 36px;
            color: white;
        }
        h2 {
            text-align: center;
            color: #1d1d1f;
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #86868b;
            margin-bottom: 40px;
            font-size: 15px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #1d1d1f;
            font-size: 13px;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            border: 1px solid #d2d2d7;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.2s;
            background: white;
        }
        input:focus {
            outline: none;
            border-color: #007AFF;
            box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        }
        .btn {
            width: 100%;
            background: #007AFF;
            color: white;
            border: none;
            padding: 14px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 17px;
            font-weight: 500;
            transition: all 0.2s;
            margin-top: 10px;
        }
        .btn:hover {
            background: #0051D5;
            transform: scale(0.98);
        }
        .btn:active {
            transform: scale(0.96);
        }
        .error {
            background: #FEE4E2;
            color: #DC2626;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 14px;
        }
        .divider {
            text-align: center;
            color: #86868b;
            margin: 30px 0;
            position: relative;
            font-size: 13px;
        }
        .divider:before {
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            width: 100%;
            height: 1px;
            background: #d2d2d7;
        }
        .divider span {
            background: rgba(255, 255, 255, 0.9);
            padding: 0 20px;
            position: relative;
        }
        .footer-link {
            text-align: center;
            margin-top: 30px;
        }
        .footer-link a {
            color: #007AFF;
            text-decoration: none;
            font-size: 14px;
        }
        .footer-link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <div class="logo-icon">🤖</div>
            <h2>GPT-GOD</h2>
            <p class="subtitle">使用您的账户登录</p>
        </div>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post" action="/login">
            <div class="form-group">
                <label for="username">用户名</label>
                <input type="text" id="username" name="username" required autofocus placeholder="输入用户名">
            </div>
            <div class="form-group">
                <label for="password">密码</label>
                <input type="password" id="password" name="password" required placeholder="输入密码">
            </div>
            <input type="hidden" name="next" value="{{ next_url }}">
            <button type="submit" class="btn">登录</button>
        </form>
        {% if show_token %}
        <div class="divider"><span>API Token</span></div>
        <div style="background: #f2f2f7; padding: 12px; border-radius: 10px; word-break: break-all; font-family: monospace; font-size: 12px;">
            {{ api_token }}
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

# HTML模板 - 带左侧菜单栏的现代布局
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GPT-GOD 控制中心</title>
    <script src="https://cdn.bootcdn.net/ajax/libs/Chart.js/4.4.0/chart.umd.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
            background: #f5f7fa;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* 主布局 */
        .app-layout {
            display: flex;
            min-height: 100vh;
            transition: all 0.3s ease;
        }

        /* 侧边栏 */
        .sidebar {
            width: 280px;
            background: #fff;
            border-right: 1px solid #e5e7eb;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
            position: fixed;
            top: 0;
            left: 0;
            height: 100vh;
            overflow-y: auto;
            z-index: 1000;
            transition: transform 0.3s ease;
        }

        .sidebar.mobile-hidden {
            transform: translateX(-100%);
        }

        .sidebar-header {
            padding: 24px 20px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #007AFF, #5856D6);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
        }

        .logo-text {
            font-size: 18px;
            font-weight: 700;
            color: #1f2937;
        }

        .menu-list {
            padding: 20px 0;
            list-style: none;
        }

        .menu-item {
            margin: 4px 16px;
        }

        .menu-link {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            color: #6b7280;
            text-decoration: none;
            border-radius: 10px;
            transition: all 0.2s;
            font-weight: 500;
            cursor: pointer;
        }

        .menu-link:hover {
            background: #f8f9fa;
            color: #007AFF;
        }

        .menu-link.active {
            background: rgba(0, 122, 255, 0.1);
            color: #007AFF;
        }

        .menu-icon {
            font-size: 20px;
            width: 24px;
            text-align: center;
        }

        .menu-text {
            font-size: 14px;
        }

        /* 主内容区 */
        .main-content {
            flex: 1;
            margin-left: 280px;
            min-height: 100vh;
            transition: margin-left 0.3s ease;
        }

        .main-content.sidebar-collapsed {
            margin-left: 0;
        }

        /* 顶部导航栏 */
        .top-navbar {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid #e5e7eb;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 900;
        }

        .navbar-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .mobile-menu-btn {
            display: none;
            background: none;
            border: none;
            font-size: 24px;
            color: #6b7280;
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
            transition: all 0.2s;
        }

        .mobile-menu-btn:hover {
            background: #f3f4f6;
        }

        .page-title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
        }

        .navbar-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .nav-btn {
            background: transparent;
            border: 1px solid #e5e7eb;
            color: #6b7280;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .nav-btn:hover {
            background: #f9fafb;
            border-color: #d1d5db;
        }

        /* 内容容器 */
        .content-container {
            padding: 24px;
            max-width: 1400px;
        }

        /* 页面内容区域 */
        .page-content {
            display: none;
        }

        .page-content.active {
            display: block;
        }
        /* 卡片样式 */
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(0, 0, 0, 0.05);
        }

        .card-title {
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-title-icon {
            font-size: 22px;
        }

        /* 按钮样式 */
        .btn {
            background: #007AFF;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 500;
            transition: all 0.2s;
            margin: 8px 4px;
        }

        .btn:hover {
            background: #0051D5;
            transform: translateY(-1px);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: #f3f4f6;
            color: #374151;
        }

        .btn-secondary:hover {
            background: #e5e7eb;
        }

        .btn-small {
            background: #f3f4f6;
            color: #374151;
            padding: 6px 12px;
            font-size: 13px;
            margin: 4px;
        }

        .btn-danger {
            background: #ef4444;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        /* 状态样式 */
        .status {
            padding: 12px;
            border-radius: 10px;
            margin: 10px 0;
            font-size: 14px;
        }

        .success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }

        .error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }

        .info {
            background: #dbeafe;
            color: #1e40af;
            border: 1px solid #bfdbfe;
        }

        /* 表单样式 */
        .form-group {
            margin: 20px 0;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #374151;
            font-size: 14px;
        }

        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            transition: all 0.2s;
        }

        /* 美化选择器样式 */
        select {
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
            background-position: right 0.5rem center;
            background-repeat: no-repeat;
            background-size: 1.5em 1.5em;
            padding-right: 2.5rem;
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
        }

        select:focus {
            outline: none;
            border-color: #007AFF;
            box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        }

        input:focus, textarea:focus {
            outline: none;
            border-color: #007AFF;
            box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        }

        /* 历史记录控制器样式 */
        .history-controls {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
            flex-wrap: wrap;
            align-items: center;
        }

        .history-controls select {
            min-width: 160px;
            flex: 0 0 auto;
        }

        .history-controls .btn-secondary {
            flex: 0 0 auto;
            white-space: nowrap;
        }

        /* Checkbox样式 */
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }

        .checkbox-label input[type="checkbox"] {
            width: auto;
            margin: 0;
        }

        .time-input-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .time-input-group input {
            flex: 0 0 auto;
        }

        /* 加载动画 */
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }

        .spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid #007AFF;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* 统计网格 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .stat-item {
            background: #f8fafc;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #007AFF;
        }

        .stat-item h4 {
            margin: 0 0 12px 0;
            color: #007AFF;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 4px;
        }

        /* Tab样式 */
        .tabs {
            display: flex;
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 20px;
            overflow-x: auto;
        }

        .tab-btn {
            background: transparent;
            border: none;
            padding: 12px 24px;
            cursor: pointer;
            font-size: 14px;
            color: #6b7280;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .tab-btn.active {
            color: #007AFF;
            border-bottom-color: #007AFF;
        }

        .tab-btn:hover {
            color: #007AFF;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* 图表容器 */
        .chart-container {
            position: relative;
            height: 350px;
            margin: 20px 0;
        }

        /* 徽章 */
        .info-badge {
            display: inline-block;
            background: #f3f4f6;
            color: #374151;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            margin: 4px;
        }

        /* 移动端适配 */
        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                transform: translateX(-100%);
            }

            .sidebar.mobile-visible {
                transform: translateX(0);
            }

            .main-content {
                margin-left: 0;
            }

            .mobile-menu-btn {
                display: block;
            }

            .top-navbar {
                padding: 12px 16px;
            }

            .content-container {
                padding: 16px;
            }

            .card {
                padding: 20px;
                margin-bottom: 16px;
            }

            .page-title {
                font-size: 20px;
            }

            .stats-grid {
                grid-template-columns: 1fr;
                gap: 16px;
            }

            .tabs {
                gap: 0;
            }

            .tab-btn {
                padding: 10px 16px;
                font-size: 13px;
            }

            .navbar-right .nav-btn {
                padding: 6px 12px;
                font-size: 13px;
            }

            .chart-container {
                height: 300px;
            }
        }

        @media (max-width: 480px) {
            .content-container {
                padding: 12px;
            }

            .card {
                padding: 16px;
            }

            .btn {
                padding: 10px 16px;
                font-size: 14px;
            }

            .stat-value {
                font-size: 24px;
            }
        }

        /* 遮罩层（移动端菜单） */
        .mobile-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 999;
        }

        .mobile-overlay.active {
            display: block;
        }

        /* 收纳设置项 */
        .settings-section {
            margin-top: 20px;
        }

        .settings-toggle {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            transition: all 0.2s;
        }

        .settings-toggle:hover {
            background: #f1f5f9;
        }

        .settings-toggle.active {
            border-color: #007AFF;
            background: rgba(0, 122, 255, 0.05);
        }

        .settings-content {
            display: none;
            padding: 20px;
            border: 1px solid #e2e8f0;
            border-top: none;
            border-radius: 0 0 8px 8px;
            background: white;
        }

        .settings-content.active {
            display: block;
        }

        .toggle-icon {
            transition: transform 0.2s;
        }

        .settings-toggle.active .toggle-icon {
            transform: rotate(90deg);
        }

        /* 模态框 */
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }

        .modal-content {
            background: white;
            margin: 10% auto;
            padding: 32px;
            border-radius: 16px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .modal-title {
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
        }

        .close {
            color: #6b7280;
            font-size: 28px;
            font-weight: 300;
            cursor: pointer;
            line-height: 20px;
        }

        .close:hover {
            color: #374151;
        }
    </style>
</head>
<body>
    <!-- 移动端遮罩 -->
    <div class="mobile-overlay" onclick="toggleMobileSidebar()"></div>

    <div class="app-layout">
        <!-- 侧边栏 -->
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="logo-icon">🤖</div>
                <div class="logo-text">GPT-GOD</div>
            </div>

            <ul class="menu-list">
                <li class="menu-item">
                    <a class="menu-link active" onclick="switchPage('dashboard')">
                        <span class="menu-icon">🏠</span>
                        <span class="menu-text">仪表盘</span>
                    </a>
                </li>
                <li class="menu-item">
                    <a class="menu-link" onclick="switchPage('checkin')">
                        <span class="menu-icon">✅</span>
                        <span class="menu-text">签到管理</span>
                    </a>
                </li>
                <li class="menu-item">
                    <a class="menu-link" onclick="switchPage('redeem')">
                        <span class="menu-icon">🎁</span>
                        <span class="menu-text">兑换码</span>
                    </a>
                </li>
                <li class="menu-item">
                    <a class="menu-link" onclick="switchPage('points')">
                        <span class="menu-icon">💰</span>
                        <span class="menu-text">积分管理</span>
                    </a>
                </li>
                <li class="menu-item">
                    <a class="menu-link" onclick="switchPage('logs')">
                        <span class="menu-icon">📋</span>
                        <span class="menu-text">日志查看</span>
                    </a>
                </li>
                <li class="menu-item">
                    <a class="menu-link" onclick="switchPage('settings')">
                        <span class="menu-icon">⚙️</span>
                        <span class="menu-text">系统设置</span>
                    </a>
                </li>
            </ul>
        </div>

        <!-- 主内容区 -->
        <div class="main-content" id="mainContent">
            <!-- 顶部导航栏 -->
            <div class="top-navbar">
                <div class="navbar-left">
                    <button class="mobile-menu-btn" onclick="toggleMobileSidebar()">
                        ☰
                    </button>
                    <h1 class="page-title" id="pageTitle">仪表盘</h1>
                </div>
                <div class="navbar-right">
                    <button class="nav-btn" onclick="openPasswordModal()">修改密码</button>
                    <button class="nav-btn" onclick="location.href='/logout'">退出登录</button>
                </div>
            </div>

            <!-- 内容容器 -->
            <div class="content-container">
                <!-- 仪表盘页面 -->
                <div id="dashboard-page" class="page-content active">
                    <div class="stats-grid">
                        <div class="stat-item">
                            <h4>服务状态</h4>
                            <p class="stat-value">{{ checkin_status }}</p>
                            <p style="color: #6b7280; font-size: 14px;">当前状态</p>
                        </div>
                        <div class="stat-item">
                            <h4>上次签到</h4>
                            <p class="stat-value">{{ last_checkin }}</p>
                            <p style="color: #6b7280; font-size: 14px;">最近操作时间</p>
                        </div>
                        <div class="stat-item">
                            <h4>启动时间</h4>
                            <p class="stat-value">{{ start_time }}</p>
                            <p style="color: #6b7280; font-size: 14px;">服务运行时间</p>
                        </div>
                        <div class="stat-item">
                            <h4>定时任务</h4>
                            <p class="stat-value" id="schedule-status">{{ '已启用' if schedule_times else '已禁用' }}</p>
                            <p style="color: #6b7280; font-size: 14px;" id="schedule-info">{{ '定时时间: ' + ', '.join(schedule_times) if schedule_times else '定时签到已禁用' }}</p>
                        </div>
                    </div>

                    <div class="card">
                        <h2 class="card-title">
                            <span class="card-title-icon">📈</span>
                            快速统计
                        </h2>
                        <div id="quick-stats">
                            <div class="stats-grid">
                                <div class="stat-item">
                                    <h4>总积分</h4>
                                    <p class="stat-value">加载中...</p>
                                </div>
                                <div class="stat-item">
                                    <h4>活跃账号</h4>
                                    <p class="stat-value">{{ accounts|length }}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 签到管理页面 -->
                <div id="checkin-page" class="page-content">
                    <div class="card">
                        <h2 class="card-title">
                            <span class="card-title-icon">✅</span>
                            签到管理
                        </h2>
                        <div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">
                            <span class="info-badge">当前状态：{{ checkin_status }}</span>
                            <span class="info-badge">上次签到：{{ last_checkin }}</span>
                            <span class="info-badge">配置账号：{{ accounts|length }} 个</span>
                        </div>

                        <div style="margin-bottom: 20px;">
                            <p style="color: #6b7280; margin-bottom: 16px;">点击下方按钮执行一次性签到，或等待定时任务自动执行</p>
                        </div>

                        <button class="btn" onclick="triggerCheckin()">立即签到</button>
                        <div id="checkin-loading" class="loading">
                            <div class="spinner"></div>
                            <p>正在签到，请稍候...</p>
                        </div>
                        <div id="checkin-result"></div>
                    </div>
                </div>

                <!-- 兑换码页面 -->
                <div id="redeem-page" class="page-content">
                    <div class="card">
                        <h2 class="card-title">
                            <span class="card-title-icon">🎁</span>
                            兑换码管理
                        </h2>

                        <div style="margin-bottom: 20px;">
                            <div class="info-badge">支持批量兑换</div>
                            <div class="info-badge">自动分配账号</div>
                            <div class="info-badge">实时反馈结果</div>
                        </div>

                        <div class="form-group">
                            <label>兑换码（每行一个）</label>
                            <textarea id="redeem-codes" placeholder="请输入兑换码，支持批量操作&#10;每行一个兑换码&#10;例如：&#10;ABCD1234&#10;EFGH5678&#10;IJKL9012" rows="6"></textarea>
                        </div>
                        <div class="form-group">
                            <label>选择账号</label>
                            <select id="account-select">
                                <option value="all">所有账号（推荐）</option>
                                {% for account in accounts %}
                                <option value="{{ account }}">{{ account }}</option>
                                {% endfor %}
                            </select>
                            <p style="color: #6b7280; font-size: 12px; margin-top: 8px;">
                                选择"所有账号"将自动为每个兑换码分配不同的账号进行兑换
                            </p>
                        </div>
                        <button class="btn" onclick="redeemCodes()">开始兑换</button>
                        <div id="redeem-loading" class="loading">
                            <div class="spinner"></div>
                            <p>正在兑换，请稍候...</p>
                        </div>
                        <div id="redeem-result"></div>
                    </div>
                </div>

                <!-- 积分管理页面（合并统计和历史） -->
                <div id="points-page" class="page-content">
                    <div class="card">
                        <h2 class="card-title">
                            <span class="card-title-icon">💰</span>
                            积分管理中心
                        </h2>

                        <!-- Tab切换 -->
                        <div class="tabs">
                            <button class="tab-btn active" onclick="switchTab('statistics')">积分统计</button>
                            <button class="tab-btn" onclick="switchTab('history')">历史记录</button>
                            <button class="tab-btn" onclick="switchTab('trend')">趋势分析</button>
                            <button class="tab-btn" onclick="switchTab('sources')">来源分布</button>
                        </div>

                        <!-- 积分统计Tab -->
                        <div id="statistics-tab" class="tab-content active">
                            <div style="margin-bottom: 20px;">
                                <button class="btn btn-secondary" onclick="loadPointsStatistics()">刷新数据</button>
                                <span class="info-badge">实时统计</span>
                                <span class="info-badge">多维分析</span>
                            </div>
                            <div id="points-statistics">
                                <div class="stats-grid">
                                    <div class="stat-item">
                                        <h4>总积分</h4>
                                        <p class="stat-value">加载中...</p>
                                        <p style="color: #6b7280; font-size: 14px;">所有账号总和</p>
                                    </div>
                                    <div class="stat-item">
                                        <h4>账号统计</h4>
                                        <p>总账号: {{ accounts|length }}</p>
                                        <p>活跃: 加载中...</p>
                                        <p style="color: #6b7280; font-size: 14px;">配置状态</p>
                                    </div>
                                    <div class="stat-item">
                                        <h4>平均积分</h4>
                                        <p class="stat-value">计算中...</p>
                                        <p style="color: #6b7280; font-size: 14px;">单账号平均</p>
                                    </div>
                                    <div class="stat-item">
                                        <h4>数据状态</h4>
                                        <p class="stat-value">待更新</p>
                                        <p style="color: #6b7280; font-size: 14px;">点击刷新按钮更新</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 历史记录Tab -->
                        <div id="history-tab" class="tab-content">
                            <div class="history-controls">
                                <select id="account-filter">
                                    <option value="">所有账号</option>
                                    {% for account in accounts %}
                                    <option value="{{ account }}">{{ account }}</option>
                                    {% endfor %}
                                </select>
                                <select id="days-filter">
                                    <option value="7">最近7天</option>
                                    <option value="30" selected>最近30天</option>
                                    <option value="90">最近90天</option>
                                </select>
                                <button class="btn btn-secondary" onclick="loadHistoryData()">刷新数据</button>
                            </div>
                            <div id="history-records">
                                <div style="padding: 40px 20px; text-align: center; background: #f8fafc; border-radius: 10px;">
                                    <h3 style="color: #6b7280; margin-bottom: 16px;">📈 积分历史记录</h3>
                                    <p style="color: #9ca3af; margin-bottom: 20px;">
                                        查看账号的积分获得和消耗历史，了解积分变化趋势
                                    </p>
                                    <button class="btn" onclick="loadHistoryData()">加载历史数据</button>
                                </div>
                            </div>
                        </div>

                        <!-- 趋势分析Tab -->
                        <div id="trend-tab" class="tab-content">
                            <div id="history-chart-container">
                                <div style="padding: 40px 20px; text-align: center; background: #f8fafc; border-radius: 10px;">
                                    <h3 style="color: #6b7280; margin-bottom: 16px;">📊 趋势图表</h3>
                                    <p style="color: #9ca3af; margin-bottom: 20px;">
                                        积分获得和消耗的时间趋势图表，帮助分析使用模式
                                    </p>
                                    <canvas id="historyChart" style="max-height: 400px;"></canvas>
                                </div>
                            </div>
                        </div>

                        <!-- 来源分布Tab -->
                        <div id="sources-tab" class="tab-content">
                            <div class="sources-container">
                                <div class="chart-container">
                                    <div style="padding: 20px; text-align: center; background: #f8fafc; border-radius: 10px;">
                                        <h3 style="color: #6b7280; margin-bottom: 16px;">🎯 来源分布</h3>
                                        <canvas id="sourcesChart" style="max-height: 350px;"></canvas>
                                    </div>
                                </div>
                                <div id="sources-details">
                                    <div style="padding: 20px; background: #f8fafc; border-radius: 10px;">
                                        <h4>💰 积分获得来源统计</h4>
                                        <p style="color: #6b7280; margin-top: 10px;">
                                            显示各种积分获得方式的统计信息，点击上方tab切换后自动加载数据
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 日志查看页面 -->
                <div id="logs-page" class="page-content">
                    <div class="card">
                        <h2 class="card-title">
                            <span class="card-title-icon">📋</span>
                            系统日志
                        </h2>
                        <div style="margin-bottom: 20px;">
                            <button class="btn btn-secondary" onclick="loadLogs()">刷新日志</button>
                            <button class="btn btn-secondary" onclick="loadStats()">加载统计</button>
                        </div>
                        <div class="tabs">
                            <button class="tab-btn active" onclick="switchLogTab('logs')">签到日志</button>
                            <button class="tab-btn" onclick="switchLogTab('stats')">统计信息</button>
                        </div>

                        <div id="logs-tab" class="tab-content active">
                            <div id="logs-content">
                                <div style="padding: 20px; background: #f8fafc; border-radius: 10px; text-align: center;">
                                    <h3 style="color: #6b7280; margin-bottom: 16px;">📋 今日签到记录</h3>
                                    <p style="color: #9ca3af; margin-bottom: 20px;">
                                        查看今天的签到日志和操作记录
                                    </p>
                                    <button class="btn btn-secondary" onclick="loadLogs()">点击加载日志</button>
                                </div>
                            </div>
                        </div>

                        <div id="stats-tab" class="tab-content">
                            <div id="stats-content">
                                <div style="padding: 20px; background: #f8fafc; border-radius: 10px; text-align: center;">
                                    <h3 style="color: #6b7280; margin-bottom: 16px;">📊 统计信息</h3>
                                    <p style="color: #9ca3af; margin-bottom: 20px;">
                                        显示签到成功率、积分获得等统计数据
                                    </p>
                                    <button class="btn btn-secondary" onclick="loadStats()">点击加载统计</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 系统设置页面 -->
                <div id="settings-page" class="page-content">
                    <div class="card">
                        <h2 class="card-title">
                            <span class="card-title-icon">⚙️</span>
                            系统设置
                        </h2>

                        <!-- 定时签到设置 -->
                        <div class="settings-section">
                            <div class="settings-toggle active" onclick="toggleSettingsSection('schedule')">
                                <div>
                                    <h3>⏰ 定时签到设置</h3>
                                    <p style="color: #6b7280; font-size: 14px; margin-top: 4px;">配置自动签到时间</p>
                                </div>
                                <span class="toggle-icon">▶</span>
                            </div>
                            <div id="schedule-settings" class="settings-content active">
                                <div class="form-group">
                                    <label class="checkbox-label">
                                        <input type="checkbox" id="schedule-enabled" checked>
                                        <span>启用定时签到</span>
                                    </label>
                                </div>
                                <div class="form-group">
                                    <label>签到时间（可多选，24小时制）</label>
                                    <div id="schedule-times">
                                        <div class="time-input-group">
                                            <input type="time" class="time-input" value="09:00" style="width: 140px;">
                                            <button class="btn-small" onclick="removeTime(this)">删除</button>
                                        </div>
                                    </div>
                                    <button class="btn-small" onclick="addTimeInput()">添加时间</button>
                                </div>
                                <button class="btn" onclick="saveSchedule()">保存设置</button>
                                <div id="schedule-result"></div>
                            </div>
                        </div>

                        <!-- 域名设置 -->
                        <div class="settings-section">
                            <div class="settings-toggle" onclick="toggleSettingsSection('domain')">
                                <div>
                                    <h3>🌐 域名设置</h3>
                                    <p style="color: #6b7280; font-size: 14px; margin-top: 4px;">配置主域名和备用域名</p>
                                </div>
                                <span class="toggle-icon">▶</span>
                            </div>
                            <div id="domain-settings" class="settings-content">
                                <div class="form-group">
                                    <label>主域名</label>
                                    <select id="primary-domain">
                                        <option value="gptgod.work">gptgod.work</option>
                                        <option value="gptgod.online">gptgod.online</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>备用域名</label>
                                    <select id="backup-domain">
                                        <option value="">不使用备用域名</option>
                                        <option value="gptgod.online">gptgod.online</option>
                                        <option value="gptgod.work">gptgod.work</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="checkbox-label">
                                        <input type="checkbox" id="auto-switch" checked>
                                        <span>自动切换域名（当主域名失败时）</span>
                                    </label>
                                </div>
                                <button class="btn" onclick="saveDomains()">保存设置</button>
                                <div id="domain-result"></div>
                            </div>
                        </div>

                        <!-- SMTP邮件设置 -->
                        <div class="settings-section">
                            <div class="settings-toggle" onclick="toggleSettingsSection('smtp')">
                                <div>
                                    <h3>📧 SMTP邮件设置</h3>
                                    <p style="color: #6b7280; font-size: 14px; margin-top: 4px;">配置邮件通知功能</p>
                                </div>
                                <span class="toggle-icon">▶</span>
                            </div>
                            <div id="smtp-settings" class="settings-content">
                                <div class="form-group">
                                    <label class="checkbox-label">
                                        <input type="checkbox" id="smtp-enabled">
                                        <span>启用邮件通知</span>
                                    </label>
                                </div>
                                <div class="form-group">
                                    <label>SMTP服务器</label>
                                    <input type="text" id="smtp-server" placeholder="smtp.gmail.com">
                                </div>
                                <div class="form-group">
                                    <label>端口</label>
                                    <input type="number" id="smtp-port" value="587">
                                </div>
                                <div class="form-group">
                                    <label>发件人邮箱</label>
                                    <input type="email" id="sender-email" placeholder="your-email@gmail.com">
                                </div>
                                <div class="form-group">
                                    <label>发件人密码</label>
                                    <input type="password" id="sender-password" placeholder="应用专用密码">
                                </div>
                                <div class="form-group">
                                    <label>收件人邮箱（每行一个）</label>
                                    <textarea id="receiver-emails" rows="3" placeholder="receiver1@example.com
receiver2@example.com"></textarea>
                                </div>
                                <button class="btn" onclick="saveSmtp()">保存设置</button>
                                <div id="smtp-result"></div>
                            </div>
                        </div>

                        <!-- 账号管理 -->
                        <div class="settings-section">
                            <div class="settings-toggle" onclick="toggleSettingsSection('accounts')">
                                <div>
                                    <h3>👥 账号管理</h3>
                                    <p style="color: #6b7280; font-size: 14px; margin-top: 4px;">管理GPT-GOD账号</p>
                                </div>
                                <span class="toggle-icon">▶</span>
                            </div>
                            <div id="accounts-settings" class="settings-content">
                                <div id="accounts-list">
                                    <!-- 账号列表将在这里动态加载 -->
                                </div>
                                <h4>添加新账号</h4>
                                <div class="form-group">
                                    <label>邮箱</label>
                                    <input type="email" id="new-account-email" placeholder="new@example.com">
                                </div>
                                <div class="form-group">
                                    <label>密码</label>
                                    <input type="password" id="new-account-password" placeholder="密码">
                                </div>
                                <button class="btn" onclick="addAccount()">添加账号</button>
                                <div id="accounts-result"></div>
                            </div>
                        </div>

                        <!-- 配置管理 -->
                        <div class="settings-section">
                            <div class="settings-toggle" onclick="toggleSettingsSection('config-manage')">
                                <div>
                                    <h3>🔧 配置管理</h3>
                                    <p style="color: #6b7280; font-size: 14px; margin-top: 4px;">备份、导入和重置配置</p>
                                </div>
                                <span class="toggle-icon">▶</span>
                            </div>
                            <div id="config-manage-settings" class="settings-content">
                                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                                    <button class="btn btn-secondary" onclick="exportConfig()">导出配置</button>
                                    <button class="btn btn-secondary" onclick="migrateConfig()">迁移配置</button>
                                    <button class="btn btn-danger" onclick="resetConfig()">重置配置</button>
                                </div>
                                <div id="config-manage-result"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 修改密码模态框 -->
    <div id="passwordModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">修改密码</h2>
                <span class="close" onclick="closePasswordModal()">&times;</span>
            </div>
            <form id="passwordForm">
                <div class="form-group">
                    <label for="old-password">当前密码</label>
                    <input type="password" id="old-password" autocomplete="current-password" required>
                </div>
                <div class="form-group">
                    <label for="new-password">新密码</label>
                    <input type="password" id="new-password" autocomplete="new-password" required>
                </div>
                <div class="form-group">
                    <label for="confirm-password">确认新密码</label>
                    <input type="password" id="confirm-password" autocomplete="new-password" required>
                </div>
                <button type="submit" class="btn">更新密码</button>
                <div id="password-result"></div>
            </form>
        </div>
    </div>

    <script>
        let currentPage = 'dashboard';

        // 页面切换功能
        function switchPage(pageName) {
            console.log('Switching to page:', pageName);

            // 更新菜单状态
            document.querySelectorAll('.menu-link').forEach(link => {
                link.classList.remove('active');
            });

            // 找到被点击的菜单项并添加active类
            const clickedLink = event.target.closest('.menu-link');
            if (clickedLink) {
                clickedLink.classList.add('active');
            }

            // 隐藏所有页面
            document.querySelectorAll('.page-content').forEach(page => {
                page.classList.remove('active');
                console.log('Hiding page:', page.id);
            });

            // 显示目标页面
            const targetPage = document.getElementById(pageName + '-page');
            if (targetPage) {
                targetPage.classList.add('active');
                console.log('Showing page:', targetPage.id);
            } else {
                console.error('Target page not found:', pageName + '-page');
            }

            // 更新页面标题
            const pageTitles = {
                'dashboard': '仪表盘',
                'checkin': '签到管理',
                'redeem': '兑换码',
                'points': '积分管理',
                'logs': '日志查看',
                'settings': '系统设置'
            };
            const titleElement = document.getElementById('pageTitle');
            if (titleElement) {
                titleElement.textContent = pageTitles[pageName] || '未知页面';
            }

            // 移动端自动关闭侧边栏
            if (window.innerWidth <= 768) {
                toggleMobileSidebar();
            }

            currentPage = pageName;

            // 加载页面数据
            loadPageData(pageName);
        }

        // 移动端侧边栏切换
        function toggleMobileSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.querySelector('.mobile-overlay');

            if (sidebar.classList.contains('mobile-visible')) {
                sidebar.classList.remove('mobile-visible');
                sidebar.classList.add('mobile-hidden');
                overlay.classList.remove('active');
            } else {
                sidebar.classList.remove('mobile-hidden');
                sidebar.classList.add('mobile-visible');
                overlay.classList.add('active');
            }
        }

        // 设置项展开/收起
        function toggleSettingsSection(sectionName) {
            const toggle = event.currentTarget;
            const content = document.getElementById(sectionName + '-settings');

            toggle.classList.toggle('active');
            content.classList.toggle('active');
        }

        // 加载页面数据
        function loadPageData(pageName) {
            console.log('Loading data for page:', pageName);

            switch(pageName) {
                case 'dashboard':
                    loadDashboardData();
                    break;
                case 'points':
                    loadPointsStatistics();
                    break;
                case 'logs':
                    loadLogs();
                    break;
                case 'settings':
                    loadSchedule();
                    loadDomains();
                    loadSmtp();
                    loadAccounts();
                    break;
                default:
                    // 其他页面不需要自动加载数据
                    break;
            }
        }

        // 签到功能
        async function triggerCheckin() {
            document.getElementById('checkin-loading').style.display = 'block';
            document.getElementById('checkin-result').innerHTML = '';

            try {
                const response = await fetch('/api/checkin', {
                    method: 'POST'
                });
                const data = await response.json();

                if (data.success) {
                    showResults('checkin-result', data.results, 'success');
                } else {
                    showMessage('checkin-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('checkin-result', '签到失败：' + error.message, 'error');
            } finally {
                document.getElementById('checkin-loading').style.display = 'none';
                // 刷新仪表盘数据
                if (currentPage === 'dashboard') {
                    setTimeout(() => loadDashboardData(), 1000);
                }
            }
        }

        // 兑换码功能
        async function redeemCodes() {
            const codes = document.getElementById('redeem-codes').value.trim().split('\\n').filter(c => c);
            const account = document.getElementById('account-select').value;

            if (codes.length === 0) {
                showMessage('redeem-result', '请输入兑换码', 'error');
                return;
            }

            document.getElementById('redeem-loading').style.display = 'block';
            document.getElementById('redeem-result').innerHTML = '';

            try {
                const response = await fetch('/api/redeem', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        codes: codes,
                        account: account
                    })
                });
                const data = await response.json();

                if (data.success) {
                    showResults('redeem-result', data.results, 'success');
                } else {
                    showMessage('redeem-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('redeem-result', '兑换失败：' + error.message, 'error');
            } finally {
                document.getElementById('redeem-loading').style.display = 'none';
            }
        }

        // 工具函数
        function showMessage(elementId, message, type) {
            document.getElementById(elementId).innerHTML =
                `<div class="status ${type}">${message}</div>`;
        }

        function showResults(elementId, results, type) {
            let html = '<ul class="result-list" style="list-style: none; padding: 0;">';
            results.forEach(result => {
                html += `<li style="padding: 12px; margin: 8px 0; border-left: 3px solid #007AFF; background: #f8fafc; border-radius: 8px; font-size: 14px;">${result}</li>`;
            });
            html += '</ul>';
            document.getElementById(elementId).innerHTML = html;
        }

        // Tab切换功能（积分管理页面内）
        function switchTab(tabName) {
            // 获取当前页面
            if (currentPage === 'points') {
                // 隐藏所有tab内容
                const tabs = document.querySelectorAll('#points-page .tab-content');
                tabs.forEach(tab => tab.classList.remove('active'));

                // 移除所有按钮的active类
                const buttons = document.querySelectorAll('#points-page .tab-btn');
                buttons.forEach(btn => btn.classList.remove('active'));

                // 显示目标tab
                document.getElementById(tabName + '-tab').classList.add('active');
                // 添加对应按钮的active类
                event.target.classList.add('active');

                // 根据tab类型加载相应数据
                if (tabName === 'statistics') {
                    loadPointsStatistics();
                } else if (tabName === 'history') {
                    // 历史记录tab不自动加载，需要用户点击按钮
                } else if (tabName === 'trend') {
                    loadHistoryData();
                } else if (tabName === 'sources') {
                    loadSourcesData();
                }
            }
        }

        // 日志Tab切换功能
        function switchLogTab(tabName) {
            // 隐藏所有tab内容
            document.querySelectorAll('#logs-page .tab-content').forEach(tab => {
                tab.classList.remove('active');
            });

            // 移除所有按钮的active类
            document.querySelectorAll('#logs-page .tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });

            // 显示目标tab
            document.getElementById(tabName + '-tab').classList.add('active');
            // 添加对应按钮的active类
            event.target.classList.add('active');

            // 加载相应数据
            if (tabName === 'logs') {
                loadLogs();
            } else if (tabName === 'stats') {
                loadStats();
            }
        }

        // 加载日志
        async function loadLogs() {
            try {
                const response = await fetch('/api/logs');
                const data = await response.json();

                if (data.success) {
                    let html = '<h3>今日签到记录</h3><ul style="list-style: none; padding: 0;">';
                    data.logs.forEach(log => {
                        html += `<li style="padding: 12px; margin: 8px 0; border-left: 3px solid #007AFF; background: #f8fafc; border-radius: 8px;">`;
                        html += `<strong>时间:</strong> ${log.start_time}<br>`;
                        html += `<strong>触发方式:</strong> ${log.trigger_type}<br>`;
                        html += `<strong>账号数:</strong> ${log.total_accounts}<br>`;
                        html += `<strong>成功:</strong> ${log.success_count}, <strong>失败:</strong> ${log.failed_count}<br>`;
                        if (log.accounts && log.accounts.length > 0) {
                            html += '<details><summary style="cursor: pointer; color: #007AFF;">详细信息</summary><ul style="margin-top: 10px;">';
                            log.accounts.forEach(acc => {
                                html += `<li style="padding: 4px 0;">${acc.email} - ${acc.status} ${acc.points ? '(+' + acc.points + '积分)' : ''}</li>`;
                            });
                            html += '</ul></details>';
                        }
                        html += `</li>`;
                    });
                    html += '</ul>';
                    document.getElementById('logs-content').innerHTML = html;
                } else {
                    document.getElementById('logs-content').innerHTML = '<p class="error">获取日志失败</p>';
                }
            } catch (error) {
                document.getElementById('logs-content').innerHTML = `<p class="error">错误: ${error.message}</p>`;
            }
        }

        // 加载统计信息
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();

                if (data.success) {
                    let html = '<div class="stats-grid">';
                    html += '<div class="stat-item"><h4>总计</h4>';
                    html += `<p>签到次数: ${data.stats.all_time.total_checkins}</p>`;
                    html += `<p>成功次数: ${data.stats.all_time.successful_checkins}</p>`;
                    html += `<p>失败次数: ${data.stats.all_time.failed_checkins}</p>`;
                    html += `<p>总积分: ${data.stats.all_time.total_points_earned}</p>`;
                    html += '</div>';

                    html += '<div class="stat-item"><h4>今日</h4>';
                    html += `<p>签到批次: ${data.stats.today.sessions}</p>`;
                    html += `<p>账号数: ${data.stats.today.accounts}</p>`;
                    html += `<p>成功: ${data.stats.today.success}</p>`;
                    html += `<p>失败: ${data.stats.today.failed}</p>`;
                    html += '</div>';
                    html += '</div>';

                    document.getElementById('stats-content').innerHTML = html;
                } else {
                    document.getElementById('stats-content').innerHTML = '<p class="error">获取统计失败</p>';
                }
            } catch (error) {
                document.getElementById('stats-content').innerHTML = `<p class="error">错误: ${error.message}</p>`;
            }
        }

        // 页面初始化
        window.onload = function() {
            // 确保桌面端侧边栏正常显示
            const sidebar = document.getElementById('sidebar');
            if (window.innerWidth > 768) {
                sidebar.classList.remove('mobile-hidden', 'mobile-visible');
            } else {
                sidebar.classList.add('mobile-hidden');
            }

            loadDashboardData();

            // 监听窗口大小变化，自动适配移动端
            window.addEventListener('resize', function() {
                const sidebar = document.getElementById('sidebar');
                const overlay = document.querySelector('.mobile-overlay');

                if (window.innerWidth > 768) {
                    // 桌面端，确保侧边栏显示
                    sidebar.classList.remove('mobile-visible', 'mobile-hidden');
                    overlay.classList.remove('active');
                } else {
                    // 移动端，默认隐藏侧边栏
                    if (!sidebar.classList.contains('mobile-visible')) {
                        sidebar.classList.add('mobile-hidden');
                    }
                }
            });
        }

        // 仪表盘数据加载
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/schedule');
                const data = await response.json();

                if (data.success) {
                    const status = data.enabled && data.times.length > 0 ? '已启用' : '已禁用';
                    const times = data.enabled ? data.times.join('、') : '无';

                    document.getElementById('schedule-status').textContent = status;
                    document.getElementById('schedule-info').textContent = data.enabled ? `定时时间: ${times}` : '定时签到已禁用';
                }

                // 加载快速统计
                try {
                    const pointsResponse = await fetch('/api/points');
                    const pointsData = await pointsResponse.json();

                    if (pointsData.success) {
                        let html = '<div class="stats-grid">';
                        html += '<div class="stat-item">';
                        html += '<h4>总积分</h4>';
                        html += `<p class="stat-value">${pointsData.total_points.toLocaleString()}</p>`;
                        html += '</div>';
                        html += '<div class="stat-item">';
                        html += '<h4>活跃账号</h4>';
                        html += `<p class="stat-value">${pointsData.statistics?.active_accounts || '加载中...'}</p>`;
                        html += '</div>';
                        html += '</div>';

                        document.getElementById('quick-stats').innerHTML = html;
                    }
                } catch (error) {
                    console.log('积分数据加载失败，使用默认显示');
                }
            } catch (error) {
                console.error('加载仪表盘数据失败:', error);
            }
        }
    </script>
    <script>
        // 加载积分统计
        async function loadPointsStatistics() {
            try {
                const response = await fetch('/api/points');
                const data = await response.json();

                if (data.success) {
                    let html = '<div class="stats-grid">';

                    // 总积分
                    html += '<div class="stat-item">';
                    html += '<h4>总积分</h4>';
                    html += `<p class="stat-value">${data.total_points.toLocaleString()}</p>`;
                    html += '</div>';

                    // 活跃账号
                    html += '<div class="stat-item">';
                    html += '<h4>账号统计</h4>';
                    html += `<p>总账号: ${data.statistics.total_accounts}</p>`;
                    html += `<p>活跃: ${data.statistics.active_accounts}</p>`;
                    html += '</div>';

                    html += '</div>';

                    // 各账号积分分布
                    if (data.accounts_detail && data.accounts_detail.accounts) {
                        html += '<h3 style="margin-top: 30px;">📊 各账号积分分布</h3>';
                        html += '<div style="overflow-x: auto;"><table style="width: 100%; margin-top: 10px; border-collapse: collapse;">';
                        html += '<tr style="background: #f8fafc;"><th style="padding: 12px; border: 1px solid #e5e7eb;">账号</th><th style="padding: 12px; border: 1px solid #e5e7eb;">积分</th><th style="padding: 12px; border: 1px solid #e5e7eb;">占比</th><th style="padding: 12px; border: 1px solid #e5e7eb;">进度条</th></tr>';

                        for (const acc of data.accounts_detail.accounts.slice(0, 20)) {
                            html += '<tr>';
                            html += `<td style="padding: 12px; border: 1px solid #e5e7eb;">${acc.email}</td>`;
                            html += `<td style="padding: 12px; border: 1px solid #e5e7eb; text-align: right;">${acc.points.toLocaleString()}</td>`;
                            html += `<td style="padding: 12px; border: 1px solid #e5e7eb; text-align: right;">${acc.percentage}%</td>`;
                            html += '<td style="padding: 12px; border: 1px solid #e5e7eb;">';
                            html += `<div style="background: #f3f4f6; border-radius: 4px; overflow: hidden; height: 20px;">`;
                            html += `<div style="background: linear-gradient(90deg, #007AFF, #5856D6); height: 100%; width: ${acc.percentage}%; transition: width 0.3s;"></div>`;
                            html += '</div>';
                            html += '</td>';
                            html += '</tr>';
                        }
                        html += '</table></div>';
                    }

                    document.getElementById('points-statistics').innerHTML = html;
                } else {
                    document.getElementById('points-statistics').innerHTML = '<p class="error">加载失败</p>';
                }
            } catch (error) {
                document.getElementById('points-statistics').innerHTML = `<p class="error">错误: ${error.message}</p>`;
            }
        }

        // 加载历史记录数据
        async function loadHistoryData() {
            try {
                const accountFilter = document.getElementById('account-filter') ? document.getElementById('account-filter').value : '';
                const daysFilter = document.getElementById('days-filter') ? document.getElementById('days-filter').value : 30;

                let url = `/api/points/history/daily?days=${daysFilter}`;
                if (accountFilter) {
                    url += `&email=${encodeURIComponent(accountFilter)}`;
                }

                const response = await fetch(url);
                const data = await response.json();

                if (data.success && data.daily_summary.length > 0) {
                    displayHistoryRecords(data.daily_summary);
                    displayTrendChart(data.daily_summary);
                } else {
                    document.getElementById('history-records').innerHTML = '<p>没有找到历史记录</p>';
                }
            } catch (error) {
                document.getElementById('history-records').innerHTML = `<p class="error">加载失败: ${error.message}</p>`;
            }
        }

        function displayHistoryRecords(dailyData) {
            let html = '<h4>每日汇总</h4>';
            html += '<div>';

            dailyData.slice(0, 10).forEach(day => {
                html += `<div style="padding: 12px; margin: 8px 0; background: #f8fafc; border-radius: 8px; border-left: 4px solid #007AFF;">`;
                html += `<strong>${day.date}</strong>: `;
                html += `获得 ${day.earned}, 消耗 ${day.spent}, `;
                html += `净收入 ${day.net} (${day.transactions}笔交易)`;
                html += '</div>';
            });

            html += '</div>';
            document.getElementById('history-records').innerHTML = html;
        }

        function displayTrendChart(dailyData) {
            const canvas = document.getElementById('historyChart');
            if (!canvas || dailyData.length === 0) return;

            // 如果已存在图表，先销毁
            if (window.historyChartInstance) {
                window.historyChartInstance.destroy();
            }

            const ctx = canvas.getContext('2d');

            // 准备图表数据 (按日期排序)
            const sortedData = dailyData.sort((a, b) => new Date(a.date) - new Date(b.date));
            const labels = sortedData.map(day => {
                const date = new Date(day.date);
                return `${date.getMonth() + 1}/${date.getDate()}`;
            });

            const earnedData = sortedData.map(day => parseInt(day.earned) || 0);
            const spentData = sortedData.map(day => parseInt(day.spent) || 0);
            const netData = sortedData.map(day => parseInt(day.net) || 0);

            window.historyChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '获得积分',
                        data: earnedData,
                        borderColor: '#34C759',
                        backgroundColor: 'rgba(52, 199, 89, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    }, {
                        label: '消耗积分',
                        data: spentData,
                        borderColor: '#FF3B30',
                        backgroundColor: 'rgba(255, 59, 48, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    }, {
                        label: '净收入',
                        data: netData,
                        borderColor: '#007AFF',
                        backgroundColor: 'rgba(0, 122, 255, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: '日期'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: '积分数量'
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
        }

        // 加载来源分布数据
        async function loadSourcesData() {
            try {
                const response = await fetch('/api/points/history/overview');
                const data = await response.json();

                if (data.success) {
                    displaySourcesDetails(data.overview.total_stats.earned_sources);
                }
            } catch (error) {
                document.getElementById('sources-details').innerHTML = `<p class="error">加载失败: ${error.message}</p>`;
            }
        }

        function displaySourcesDetails(sourcesData) {
            // 显示统计详情
            let html = '<h4>积分获得来源统计</h4>';
            html += '<div>';

            const sortedSources = Object.entries(sourcesData).sort((a, b) => b[1].earned - a[1].earned);

            sortedSources.forEach(([source, data]) => {
                html += `<div style="background: #f8fafc; padding: 16px; border-radius: 8px; border-left: 4px solid #007AFF; margin-bottom: 12px;">`;
                html += `<h5 style="margin: 0 0 8px 0; color: #007AFF; font-weight: 600;">${source}</h5>`;
                html += `<p style="margin: 4px 0; font-size: 14px; color: #6b7280;">记录数: ${data.count}</p>`;
                html += `<p style="margin: 4px 0; font-size: 14px; color: #6b7280;">获得积分: ${data.earned.toLocaleString()}</p>`;
                html += '</div>';
            });

            html += '</div>';
            document.getElementById('sources-details').innerHTML = html;

            // 创建饼状图
            const canvas = document.getElementById('sourcesChart');
            if (canvas && sortedSources.length > 0) {
                // 如果已存在图表，先销毁
                if (window.sourcesChartInstance) {
                    window.sourcesChartInstance.destroy();
                }

                const ctx = canvas.getContext('2d');

                // 准备图表数据
                const labels = sortedSources.map(([source]) => source);
                const dataValues = sortedSources.map(([, data]) => data.earned);

                // 生成颜色
                const colors = [
                    '#007AFF', '#5856D6', '#34C759', '#FF9500',
                    '#FF3B30', '#FF2D92', '#A2845E', '#8E8E93'
                ];

                window.sourcesChartInstance = new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: dataValues,
                            backgroundColor: colors.slice(0, labels.length),
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 20,
                                    font: {
                                        size: 12
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed;
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${label}: ${value.toLocaleString()} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }

        // 设置功能
        async function loadSchedule() {
            try {
                const response = await fetch('/api/schedule');
                const data = await response.json();

                if (data.success) {
                    document.getElementById('schedule-enabled').checked = data.enabled;

                    const timesContainer = document.getElementById('schedule-times');
                    timesContainer.innerHTML = '';

                    data.times.forEach(time => {
                        const div = document.createElement('div');
                        div.className = 'time-input-group';
                        div.innerHTML = `
                            <input type="time" class="time-input" value="${time}" style="width: 140px;">
                            <button class="btn-small" onclick="removeTime(this)">删除</button>
                        `;
                        timesContainer.appendChild(div);
                    });
                }
            } catch (error) {
                console.error('加载定时设置失败:', error);
            }
        }

        function addTimeInput() {
            const timesContainer = document.getElementById('schedule-times');
            const div = document.createElement('div');
            div.className = 'time-input-group';
            div.innerHTML = `
                <input type="time" class="time-input" value="09:00" style="width: 140px;">
                <button class="btn-small" onclick="removeTime(this)">删除</button>
            `;
            timesContainer.appendChild(div);
        }

        function removeTime(button) {
            const group = button.parentElement;
            const container = group.parentElement;
            if (container.children.length > 1) {
                group.remove();
            } else {
                showMessage('schedule-result', '至少保留一个时间', 'error');
            }
        }

        async function saveSchedule() {
            const enabled = document.getElementById('schedule-enabled').checked;
            const timeInputs = document.querySelectorAll('.time-input');
            const times = Array.from(timeInputs).map(input => input.value).filter(v => v);

            if (times.length === 0) {
                showMessage('schedule-result', '请至少设置一个时间', 'error');
                return;
            }

            try {
                const response = await fetch('/api/schedule', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        enabled: enabled,
                        times: times
                    })
                });

                const data = await response.json();
                if (data.success) {
                    showMessage('schedule-result', '设置保存成功', 'success');
                } else {
                    showMessage('schedule-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('schedule-result', '保存失败: ' + error.message, 'error');
            }
        }

        async function loadDomains() {
            try {
                const response = await fetch('/api/domains');
                const data = await response.json();

                if (data.success) {
                    document.getElementById('primary-domain').value = data.primary;
                    document.getElementById('backup-domain').value = data.backup || '';
                    document.getElementById('auto-switch').checked = data.auto_switch;
                }
            } catch (error) {
                console.error('加载域名配置失败:', error);
            }
        }

        async function saveDomains() {
            const primary = document.getElementById('primary-domain').value;
            const backup = document.getElementById('backup-domain').value;
            const autoSwitch = document.getElementById('auto-switch').checked;

            if (primary === backup && backup !== '') {
                showMessage('domain-result', '主域名和备用域名不能相同', 'error');
                return;
            }

            try {
                const response = await fetch('/api/domains', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        primary: primary,
                        backup: backup,
                        auto_switch: autoSwitch
                    })
                });

                const data = await response.json();
                if (data.success) {
                    showMessage('domain-result', '域名设置保存成功', 'success');
                } else {
                    showMessage('domain-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('domain-result', '保存失败: ' + error.message, 'error');
            }
        }

        // SMTP配置管理
        async function loadSmtp() {
            try {
                const response = await fetch('/api/config/smtp');
                const data = await response.json();

                if (data.success && data.config) {
                    document.getElementById('smtp-enabled').checked = data.config.enabled || false;
                    document.getElementById('smtp-server').value = data.config.server || 'smtp.gmail.com';
                    document.getElementById('smtp-port').value = data.config.port || 587;
                    document.getElementById('sender-email').value = data.config.sender_email || '';
                    document.getElementById('sender-password').value = data.config.sender_password || '';
                    document.getElementById('receiver-emails').value = (data.config.receiver_emails || []).join('\\n');
                } else {
                    console.error('SMTP配置加载失败:', data.message || '未知错误');
                }
            } catch (error) {
                console.error('加载SMTP配置失败:', error);
            }
        }

        async function saveSmtp() {
            const enabled = document.getElementById('smtp-enabled').checked;
            const server = document.getElementById('smtp-server').value;
            const port = parseInt(document.getElementById('smtp-port').value);
            const senderEmail = document.getElementById('sender-email').value;
            const senderPassword = document.getElementById('sender-password').value;
            const receiverEmails = document.getElementById('receiver-emails').value
                .split('\\n').map(email => email.trim()).filter(email => email);

            try {
                const response = await fetch('/api/config/smtp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        enabled, server, port, sender_email: senderEmail,
                        sender_password: senderPassword, receiver_emails: receiverEmails
                    })
                });

                const data = await response.json();
                if (data.success) {
                    showMessage('smtp-result', 'SMTP配置保存成功', 'success');
                } else {
                    showMessage('smtp-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('smtp-result', '保存失败: ' + error.message, 'error');
            }
        }

        // 账号管理
        async function loadAccounts() {
            try {
                const response = await fetch('/api/config/accounts');
                const data = await response.json();

                if (data.success && data.accounts) {
                    let html = '<h4>当前账号 (' + data.accounts.length + '个)</h4>';
                    if (data.accounts.length > 0) {
                        data.accounts.forEach((account, index) => {
                            const email = account.mail || account.email || '未知邮箱';
                            html += `<div style="display: flex; align-items: center; justify-content: space-between; padding: 12px; background: #f8fafc; border-radius: 8px; margin-bottom: 8px;">`;
                            html += `<span><strong>${email}</strong></span>`;
                            html += `<button class="btn btn-danger btn-small" onclick="removeAccount('${email}')">删除</button>`;
                            html += `</div>`;
                        });
                    } else {
                        html += '<p style="color: #6b7280; text-align: center; padding: 20px;">暂无账号</p>';
                    }
                    document.getElementById('accounts-list').innerHTML = html;
                } else {
                    document.getElementById('accounts-list').innerHTML = '<p style="color: #ef4444;">加载账号失败: ' + (data.message || '未知错误') + '</p>';
                }
            } catch (error) {
                console.error('加载账号列表失败:', error);
                document.getElementById('accounts-list').innerHTML = '<p style="color: #ef4444;">网络错误: ' + error.message + '</p>';
            }
        }

        async function addAccount() {
            const email = document.getElementById('new-account-email').value.trim();
            const password = document.getElementById('new-account-password').value;

            if (!email || !password) {
                showMessage('accounts-result', '请填写完整的账号信息', 'error');
                return;
            }

            try {
                const response = await fetch('/api/config/accounts/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();
                if (data.success) {
                    showMessage('accounts-result', '账号添加成功', 'success');
                    document.getElementById('new-account-email').value = '';
                    document.getElementById('new-account-password').value = '';
                    loadAccounts(); // 重新加载账号列表
                } else {
                    showMessage('accounts-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('accounts-result', '添加失败: ' + error.message, 'error');
            }
        }

        async function removeAccount(email) {
            if (!confirm('确认删除账号: ' + email + '?')) return;

            try {
                const response = await fetch('/api/config/accounts/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });

                const data = await response.json();
                if (data.success) {
                    showMessage('accounts-result', '账号删除成功', 'success');
                    loadAccounts(); // 重新加载账号列表
                } else {
                    showMessage('accounts-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('accounts-result', '删除失败: ' + error.message, 'error');
            }
        }

        // 配置管理
        async function exportConfig() {
            try {
                const response = await fetch('/api/config/export');
                const data = await response.json();

                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `gptgod_config_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                showMessage('config-manage-result', '配置导出成功', 'success');
            } catch (error) {
                showMessage('config-manage-result', '导出失败: ' + error.message, 'error');
            }
        }

        async function migrateConfig() {
            if (!confirm('确认从YAML文件重新迁移配置？这将覆盖当前数据库配置。')) return;

            try {
                const response = await fetch('/api/config/migrate', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    showMessage('config-manage-result', '配置迁移成功', 'success');
                    // 重新加载所有配置
                    setTimeout(() => {
                        loadSchedule();
                        loadDomains();
                        loadSmtp();
                        loadAccounts();
                    }, 1000);
                } else {
                    showMessage('config-manage-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('config-manage-result', '迁移失败: ' + error.message, 'error');
            }
        }

        async function resetConfig() {
            if (!confirm('确认重置所有配置？这将删除所有数据库配置并恢复默认值。')) return;

            try {
                const response = await fetch('/api/config/reset', { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    showMessage('config-manage-result', '配置重置成功', 'success');
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                } else {
                    showMessage('config-manage-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('config-manage-result', '重置失败: ' + error.message, 'error');
            }
        }
        function openPasswordModal() {
            document.getElementById('passwordModal').style.display = 'block';
        }

        function closePasswordModal() {
            document.getElementById('passwordModal').style.display = 'none';
            document.getElementById('passwordForm').reset();
            document.getElementById('password-result').innerHTML = '';
        }

        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('passwordModal');
            if (event.target == modal) {
                closePasswordModal();
            }
        }

        // 处理密码修改表单
        document.getElementById('passwordForm').onsubmit = async function(e) {
            e.preventDefault();

            const oldPassword = document.getElementById('old-password').value;
            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;

            if (newPassword !== confirmPassword) {
                showMessage('password-result', '两次输入的新密码不一致', 'error');
                return;
            }

            if (newPassword.length < 6) {
                showMessage('password-result', '新密码长度不能小于6位', 'error');
                return;
            }

            try {
                const response = await fetch('/api/change-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        old_password: oldPassword,
                        new_password: newPassword
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showMessage('password-result', '密码修改成功！请重新登录', 'success');
                    setTimeout(() => {
                        window.location.href = '/logout';
                    }, 2000);
                } else {
                    showMessage('password-result', data.message, 'error');
                }
            } catch (error) {
                showMessage('password-result', '修改失败: ' + error.message, 'error');
            }
        }
    </script>
</body>
</html>
'''

def load_config():
    """加载配置文件 - 优先使用数据库配置"""
    try:
        config_manager = ConfigManager()
        return config_manager.get_all_config()
    except:
        # 回退到YAML配置
        try:
            with open('account.yml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"加载配置失败: {e}")
            return {}

def perform_checkin(trigger_type='api', trigger_by=None):
    """执行签到任务"""
    from main import main as checkin_main
    try:
        logging.info("开始执行定时签到任务")
        checkin_main(trigger_type, trigger_by)
        task_status['last_checkin'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return True
    except Exception as e:
        logging.error(f"签到任务失败: {e}")
        return False

def redeem_code(code, account_email, driver):
    """兑换单个兑换码"""
    try:
        # 导航到兑换页面
        driver.get('https://gptgod.work/#/token')
        time.sleep(8)

        # 查找兑换码输入框
        code_input = driver.ele('xpath://input[@placeholder="请输入您的积分兑换码, 点击兑换"]', timeout=10)
        if not code_input:
            return {'success': False, 'message': '找不到兑换码输入框'}

        # 输入兑换码
        code_input.clear()
        code_input.input(code)
        time.sleep(1)

        # 点击兑换按钮
        redeem_button = driver.ele('xpath://button[.//span[@aria-label="gift"] or contains(., "兑换")]', timeout=5)
        if redeem_button and not redeem_button.attr('disabled'):
            redeem_button.click()
            time.sleep(3)

            # 检查结果（可能有弹窗提示）
            # 这里需要根据实际页面反馈调整
            return {'success': True, 'message': f'兑换码 {code} 兑换成功'}
        else:
            return {'success': False, 'message': '兑换按钮不可用或未找到'}

    except Exception as e:
        logging.error(f"兑换失败: {e}")
        return {'success': False, 'message': str(e)}

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next', '/')

        # 验证用户名和密码
        password_hash = hashlib.md5(password.encode()).hexdigest()
        if username == AUTH_CONFIG['username'] and password_hash == AUTH_CONFIG['password_hash']:
            session['authenticated'] = True
            session['username'] = username
            session.permanent = True
            logging.info(f"用户 {username} 登录成功")
            return redirect(next_url)
        else:
            return render_template_string(LOGIN_TEMPLATE, error='用户名或密码错误', next_url=next_url)

    next_url = request.args.get('next', '/')
    show_token = request.args.get('show_token') == 'true'
    return render_template_string(LOGIN_TEMPLATE,
                                 next_url=next_url,
                                 show_token=show_token,
                                 api_token=AUTH_CONFIG.get('api_token', ''))

@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/api/change-password', methods=['POST'])
@require_auth
def api_change_password():
    """修改密码"""
    try:
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({'success': False, 'message': '请提供完整信息'})

        # 验证旧密码
        old_password_hash = hashlib.md5(old_password.encode()).hexdigest()
        if old_password_hash != AUTH_CONFIG['password_hash']:
            return jsonify({'success': False, 'message': '当前密码错误'})

        # 验证新密码长度
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '新密码长度不能小于6位'})

        # 更新密码
        new_password_hash = hashlib.md5(new_password.encode()).hexdigest()
        AUTH_CONFIG['password_hash'] = new_password_hash

        # 更新到数据库配置
        try:
            config_manager = ConfigManager()
            config_manager.update_web_auth_config(
                enabled=AUTH_CONFIG['enabled'],
                username=AUTH_CONFIG['username'],
                password=new_password,
                api_token=AUTH_CONFIG['api_token']
            )
        except:
            # 回退到YAML配置保存
            config = load_config()
            if 'web_auth' not in config:
                config['web_auth'] = {}
            config['web_auth']['password'] = new_password

            with open('account.yml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        logging.info(f"用户 {session.get('username', 'unknown')} 修改了密码")

        return jsonify({'success': True, 'message': '密码修改成功'})

    except Exception as e:
        logging.error(f"修改密码失败: {e}")
        return jsonify({'success': False, 'message': str(e)})

# 配置管理API
@app.route('/api/config/smtp', methods=['GET', 'POST'])
@require_auth
def api_config_smtp():
    """SMTP配置管理"""
    config_manager = ConfigManager()

    if request.method == 'GET':
        try:
            smtp_config = config_manager.get_smtp_config()
            return jsonify({'success': True, 'config': smtp_config})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    else:  # POST
        try:
            data = request.json
            config_manager.update_smtp_config(
                enabled=data.get('enabled', False),
                server=data.get('server', 'smtp.gmail.com'),
                port=data.get('port', 587),
                sender_email=data.get('sender_email', ''),
                sender_password=data.get('sender_password', ''),
                receiver_emails=data.get('receiver_emails', [])
            )
            return jsonify({'success': True, 'message': 'SMTP配置更新成功'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/accounts', methods=['GET'])
@require_auth
def api_config_accounts():
    """获取账号列表"""
    try:
        config_manager = ConfigManager()
        accounts = config_manager.get_accounts()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/accounts/add', methods=['POST'])
@require_auth
def api_config_accounts_add():
    """添加账号"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'success': False, 'message': '请提供完整的账号信息'})

        config_manager = ConfigManager()
        config_manager.add_account(email, password)
        return jsonify({'success': True, 'message': f'账号 {email} 添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/accounts/remove', methods=['POST'])
@require_auth
def api_config_accounts_remove():
    """删除账号"""
    try:
        data = request.json
        email = data.get('email')

        if not email:
            return jsonify({'success': False, 'message': '请提供账号邮箱'})

        config_manager = ConfigManager()
        config_manager.remove_account(email)
        return jsonify({'success': True, 'message': f'账号 {email} 删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/export')
@require_auth
def api_config_export():
    """导出配置"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_all_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/migrate', methods=['POST'])
@require_auth
def api_config_migrate():
    """迁移配置"""
    try:
        config_manager = ConfigManager()
        if config_manager.migrate_from_yaml('account.yml'):
            return jsonify({'success': True, 'message': '配置迁移成功'})
        else:
            return jsonify({'success': False, 'message': '配置迁移失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/reset', methods=['POST'])
@require_auth
def api_config_reset():
    """重置配置"""
    try:
        config_manager = ConfigManager()
        # 删除配置数据库文件
        import os
        db_file = config_manager.data_dir / 'config.db'
        if db_file.exists():
            os.remove(db_file)

        # 重新初始化
        config_manager = ConfigManager()
        return jsonify({'success': True, 'message': '配置重置成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/')
@require_auth
def index():
    """Web界面"""
    config = load_config()
    accounts = [acc['mail'] for acc in config.get('account', [])]
    schedule_config = config.get('schedule', {'enabled': True, 'times': ['09:00']})

    return render_template_string(HTML_TEMPLATE,
                                 accounts=accounts,
                                 start_time=app.config.get('start_time', 'N/A'),
                                 checkin_status='运行中',
                                 last_checkin=task_status['last_checkin'] or '未执行',
                                 schedule_times=schedule_config.get('times', ['09:00']))

@app.route('/api/checkin', methods=['POST'])
@require_auth
def api_checkin():
    """手动触发签到"""
    try:
        # 获取触发者信息
        trigger_by = session.get('username', 'api')
        result = perform_checkin('api', trigger_by)
        if result:
            return jsonify({'success': True, 'message': '签到任务已完成', 'results': task_status['checkin_results']})
        else:
            return jsonify({'success': False, 'message': '签到任务执行失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/redeem', methods=['POST'])
@require_auth
def api_redeem():
    """兑换码接口"""
    try:
        data = request.json
        codes = data.get('codes', [])
        account_filter = data.get('account', 'all')

        if not codes:
            return jsonify({'success': False, 'message': '请提供兑换码'})

        config = load_config()
        accounts = config.get('account', [])

        if account_filter != 'all':
            accounts = [acc for acc in accounts if acc['mail'] == account_filter]

        results = []
        browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")
        arguments = [
            "--incognito",
            "--lang=zh-CN",
            "--accept-lang=zh-CN,zh;q=0.9",
            "--disable-gpu",
            "--disable-dev-tools"
        ]

        for account in accounts:
            email = account['mail']
            password = account['password']

            driver = None
            try:
                # 创建浏览器实例
                options = get_chromium_options(browser_path, arguments)
                driver = ChromiumPage(addr_or_opts=options)
                driver.set.window.full()

                # 登录
                driver.get('https://gptgod.work/#/login')
                time.sleep(8)

                # 登录流程（简化版）
                email_input = driver.ele('xpath://input[@placeholder="请输入邮箱"]', timeout=10)
                password_input = driver.ele('xpath://input[@type="password"]', timeout=10)

                if email_input and password_input:
                    email_input.clear()
                    email_input.input(email)
                    password_input.clear()
                    password_input.input(password)

                    login_button = driver.ele('xpath://button[contains(@class, "ant-btn-primary")]', timeout=5)
                    if login_button:
                        login_button.click()
                        time.sleep(8)

                        # 兑换每个码
                        for code in codes:
                            result = redeem_code(code, email, driver)
                            results.append(f"{email}: {code} - {result['message']}")

            except Exception as e:
                results.append(f"{email}: 兑换失败 - {str(e)}")
            finally:
                if driver:
                    driver.quit()

        task_status['last_redeem'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_status['redeem_results'] = results

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/status')
@require_auth
def api_status():
    """获取服务状态"""
    return jsonify({
        'status': 'running',
        'last_checkin': task_status['last_checkin'],
        'last_redeem': task_status['last_redeem']
    })

# 数据库日志API
@app.route('/api/logs')
@require_auth
def api_logs():
    """获取签到日志"""
    try:
        logger_db = CheckinLoggerDB()
        recent_sessions = logger_db.get_recent_sessions(10)

        # 转换格式以兼容前端
        logs = []
        for session in recent_sessions:
            logs.append({
                'id': session['id'],
                'start_time': session['start_time'],
                'end_time': session['end_time'],
                'trigger_type': session['trigger_type'],
                'total_accounts': session['total_accounts'],
                'success_count': session['success_count'],
                'failed_count': session['failed_count'],
                'status': session['status'],
                'accounts': []  # 详细账号信息需要额外查询
            })

        return jsonify({'success': True, 'logs': logs, 'source': 'database'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stats')
@require_auth
def api_stats():
    """获取统计信息"""
    try:
        logger_db = CheckinLoggerDB()
        stats = logger_db.get_statistics()
        return jsonify({'success': True, 'stats': stats, 'source': 'database'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/schedule', methods=['GET', 'POST'])
@require_auth
def api_schedule():
    """管理定时任务 - 使用数据库配置"""
    config_manager = ConfigManager()

    if request.method == 'GET':
        try:
            schedule_config = config_manager.get_schedule_config()
            return jsonify({
                'success': True,
                'enabled': schedule_config.get('enabled', True),
                'times': schedule_config.get('times', ['09:00']),
                'current_times': task_status['schedule_times']
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    else:  # POST
        try:
            data = request.json
            enabled = data.get('enabled', True)
            times = data.get('times', ['09:00'])

            # 验证时间格式
            import re
            time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
            for time_str in times:
                if not time_pattern.match(time_str):
                    return jsonify({'success': False, 'message': f'无效的时间格式: {time_str}'})

            # 更新数据库配置
            config_manager.update_schedule_config(enabled, times)

            # 重新加载定时任务
            reload_schedule()

            return jsonify({
                'success': True,
                'message': '定时任务已更新',
                'enabled': enabled,
                'times': times
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

@app.route('/api/domains', methods=['GET', 'POST'])
@require_auth
def api_domains():
    """管理域名配置 - 使用数据库配置"""
    config_manager = ConfigManager()

    if request.method == 'GET':
        try:
            domain_config = config_manager.get_domain_config()
            return jsonify({
                'success': True,
                'primary': domain_config.get('primary', 'gptgod.work'),
                'backup': domain_config.get('backup', 'gptgod.online'),
                'auto_switch': domain_config.get('auto_switch', True)
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    else:  # POST
        try:
            data = request.json
            primary = data.get('primary', 'gptgod.work')
            backup = data.get('backup', '')
            auto_switch = data.get('auto_switch', True)

            # 验证域名
            valid_domains = ['gptgod.work', 'gptgod.online']
            if primary not in valid_domains:
                return jsonify({'success': False, 'message': f'无效的主域名: {primary}'})

            if backup and backup not in valid_domains:
                return jsonify({'success': False, 'message': f'无效的备用域名: {backup}'})

            if primary == backup and backup:
                return jsonify({'success': False, 'message': '主域名和备用域名不能相同'})

            # 更新数据库配置
            config_manager.update_domain_config(primary, backup, auto_switch)

            return jsonify({
                'success': True,
                'message': '域名配置已更新',
                'primary': primary,
                'backup': backup,
                'auto_switch': auto_switch
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

def reload_schedule():
    """重新加载定时任务"""
    # 清除所有现有任务
    schedule.clear()

    # 使用数据库配置管理器加载配置
    try:
        config_manager = ConfigManager()
        schedule_config = config_manager.get_schedule_config()
    except:
        # 回退到YAML配置
        config = load_config()
        schedule_config = config.get('schedule', {'enabled': True, 'times': ['09:00']})

    if schedule_config.get('enabled', True):
        times = schedule_config.get('times', ['09:00'])
        task_status['schedule_times'] = times

        for time_str in times:
            schedule.every().day.at(time_str).do(lambda: perform_checkin('scheduled', 'system'))
            logging.info(f"已设置定时任务: {time_str}")
    else:
        task_status['schedule_times'] = []
        logging.info("定时任务已禁用")

@app.route('/api/points')
@require_auth
def api_points():
    """获取积分统计信息 - 使用数据库"""
    try:
        from points_history_manager import PointsHistoryManager
        history_manager = PointsHistoryManager()

        # 获取统计信息
        stats = history_manager.get_statistics()

        return jsonify({
            'success': True,
            'total_points': stats.get('total_points', 0),
            'statistics': {
                'total_accounts': stats.get('total_accounts', 0),
                'active_accounts': stats.get('total_accounts', 0)
            },
            'distribution': {},
            'accounts_detail': {'accounts': []},
            'top_accounts': [],
            'last_update': None
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/points/trend')
@require_auth
def api_points_trend():
    """获取积分趋势"""
    try:
        days = request.args.get('days', 7, type=int)
        # 功能已移除
        return jsonify({'success': True, 'trend': []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/points/export')
@require_auth
def api_points_export():
    """导出积分数据"""
    try:
        export_type = request.args.get('type', 'summary')
        # 功能已移除
        return jsonify({'success': False, 'message': '导出功能暂不可用'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/points/history/stats')
@require_auth
def api_points_history_stats():
    """获取积分历史统计 - 包括来源分布"""
    try:
        email = request.args.get('email')
        uid = request.args.get('uid', type=int)

        history_manager = PointsHistoryManager()
        stats = history_manager.get_statistics(email=email, uid=uid)

        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/points/history/daily')
@require_auth
def api_points_history_daily():
    """获取每日积分汇总"""
    try:
        email = request.args.get('email')
        uid = request.args.get('uid', type=int)
        days = request.args.get('days', 30, type=int)

        history_manager = PointsHistoryManager()
        daily_summary = history_manager.get_daily_summary(email=email, uid=uid, days=days)

        return jsonify({
            'success': True,
            'daily_summary': daily_summary
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/points/history/records')
@require_auth
def api_points_history_records():
    """获取积分历史记录"""
    try:
        email = request.args.get('email')
        uid = request.args.get('uid', type=int)
        days = request.args.get('days', 30, type=int)
        source = request.args.get('source')  # 可选的来源过滤

        history_manager = PointsHistoryManager()

        # 处理来源过滤
        source_filter = None
        if source:
            source_filter = source.split(',') if ',' in source else source

        records = history_manager.get_account_history(
            email=email,
            uid=uid,
            days=days,
            source_filter=source_filter
        )

        return jsonify({
            'success': True,
            'records': records,
            'total': len(records)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/points/history/overview')
@require_auth
def api_points_history_overview():
    """获取所有账号的积分历史概览"""
    try:
        history_manager = PointsHistoryManager()

        # 获取所有账号的统计信息
        all_stats = history_manager.get_statistics()

        # 获取账号映射
        conn = sqlite3.connect('accounts_data/points_history.db')
        cursor = conn.cursor()
        cursor.execute('SELECT uid, email FROM account_mapping ORDER BY last_update DESC')
        accounts = [{'uid': row[0], 'email': row[1]} for row in cursor.fetchall()]
        conn.close()

        # 为每个账号获取统计
        account_stats = []
        for account in accounts:
            stats = history_manager.get_statistics(uid=account['uid'])
            account_stats.append({
                'uid': account['uid'],
                'email': account['email'],
                'stats': stats
            })

        return jsonify({
            'success': True,
            'overview': {
                'total_stats': all_stats,
                'account_stats': account_stats,
                'total_accounts': len(accounts)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ========== 账号添加页面（无需登录） ==========

@app.route('/add-account')
def add_account_page():
    """账号添加页面（无需登录）"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>添加GPT-GOD账号</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 500px;
            width: 100%;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo {
            font-size: 48px;
            margin-bottom: 10px;
        }

        h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 14px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }

        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }

        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }

        .progress-container {
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }

        .progress-title {
            color: #333;
            font-weight: 600;
            margin-bottom: 15px;
        }

        .progress-log {
            max-height: 200px;
            overflow-y: auto;
            background: white;
            padding: 10px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        .log-entry {
            margin-bottom: 8px;
            padding: 5px;
            border-left: 3px solid #e0e0e0;
            padding-left: 10px;
        }

        .log-entry.info {
            border-color: #4CAF50;
            background: #f1f8e9;
        }

        .log-entry.warning {
            border-color: #ff9800;
            background: #fff3e0;
        }

        .log-entry.error {
            border-color: #f44336;
            background: #ffebee;
        }

        .log-entry.success {
            border-color: #4CAF50;
            background: #e8f5e9;
            font-weight: 600;
        }

        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(0,0,0,.3);
            border-radius: 50%;
            border-top-color: #667eea;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            display: none;
        }

        .result.success {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #4CAF50;
        }

        .result.error {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #f44336;
        }

        .back-link {
            display: block;
            text-align: center;
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
        }

        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🎯</div>
            <h1>添加GPT-GOD账号</h1>
            <p class="subtitle">输入账号信息，系统将自动验证并保存</p>
        </div>

        <form id="addAccountForm">
            <div class="form-group">
                <label for="email">邮箱地址</label>
                <input type="email" id="email" name="email" placeholder="example@gmail.com" required>
            </div>

            <div class="form-group">
                <label for="password">账号密码</label>
                <input type="password" id="password" name="password" placeholder="输入密码" required>
            </div>

            <button type="submit" class="btn" id="submitBtn">
                验证并添加账号
            </button>
        </form>

        <div class="progress-container" id="progressContainer">
            <div class="progress-title">
                <span class="spinner"></span>
                验证进度
            </div>
            <div class="progress-log" id="progressLog"></div>
        </div>

        <div class="result" id="result"></div>

        <a href="/" class="back-link">← 返回主页</a>
    </div>

    <script>
        let eventSource = null;

        document.getElementById('addAccountForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const submitBtn = document.getElementById('submitBtn');
            const progressContainer = document.getElementById('progressContainer');
            const progressLog = document.getElementById('progressLog');
            const resultDiv = document.getElementById('result');

            // 重置状态
            submitBtn.disabled = true;
            submitBtn.textContent = '验证中...';
            progressContainer.style.display = 'block';
            progressLog.innerHTML = '';
            resultDiv.style.display = 'none';

            // 关闭之前的连接
            if (eventSource) {
                eventSource.close();
            }

            // 建立SSE连接
            eventSource = new EventSource(`/api/account/verify-stream?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addLogEntry(data.type, data.message);

                if (data.type === 'complete') {
                    eventSource.close();
                    submitBtn.disabled = false;
                    submitBtn.textContent = '验证并添加账号';

                    if (data.success) {
                        showResult('success', '✅ 账号添加成功！');
                        // 清空表单
                        document.getElementById('email').value = '';
                        document.getElementById('password').value = '';
                    } else {
                        showResult('error', '❌ ' + data.message);
                    }
                }
            };

            eventSource.onerror = (error) => {
                console.error('SSE Error:', error);
                eventSource.close();
                submitBtn.disabled = false;
                submitBtn.textContent = '验证并添加账号';
                addLogEntry('error', '连接中断，请重试');
                showResult('error', '验证过程出错，请重试');
            };
        });

        function addLogEntry(type, message) {
            const progressLog = document.getElementById('progressLog');
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;

            const timestamp = new Date().toLocaleTimeString();
            entry.innerHTML = `[${timestamp}] ${message}`;

            progressLog.appendChild(entry);
            progressLog.scrollTop = progressLog.scrollHeight;
        }

        function showResult(type, message) {
            const resultDiv = document.getElementById('result');
            resultDiv.className = `result ${type}`;
            resultDiv.textContent = message;
            resultDiv.style.display = 'block';
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/account/verify-stream')
def verify_account_stream():
    """SSE接口：验证并添加账号"""
    email = request.args.get('email')
    password = request.args.get('password')

    def generate():
        """生成SSE事件流"""
        try:
            # 发送开始消息
            yield f"data: {json.dumps({'type': 'info', 'message': '开始验证账号...'})}\n\n"

            # 检查账号是否已存在
            config_manager = ConfigManager()
            existing_accounts = config_manager.get_accounts()
            for account in existing_accounts:
                if account['mail'] == email:
                    yield f"data: {json.dumps({'type': 'warning', 'message': '账号已存在于系统中'})}\n\n"
                    yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': '账号已存在'})}\n\n"
                    return

            yield f"data: {json.dumps({'type': 'info', 'message': '账号不存在，继续验证...'})}\n\n"

            # 获取配置
            config = load_config()
            domain_config = config.get('domains', {})
            primary_domain = domain_config.get('primary', 'gptgod.online')

            yield f"data: {json.dumps({'type': 'info', 'message': f'使用域名: {primary_domain}'})}\n\n"

            # 创建浏览器实例
            yield f"data: {json.dumps({'type': 'info', 'message': '启动浏览器...'})}\n\n"

            browser_config = config.get('browser', {})
            browser_path = browser_config.get('path', "/usr/bin/google-chrome")
            arguments = browser_config.get('arguments', [
                "--disable-blink-features=AutomationControlled",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "--window-size=1920,1080",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ])

            options = get_chromium_options(browser_path, arguments)
            driver = ChromiumPage(addr_or_opts=options)

            yield f"data: {json.dumps({'type': 'info', 'message': '浏览器启动成功'})}\n\n"

            # 访问登录页面
            yield f"data: {json.dumps({'type': 'info', 'message': '访问登录页面...'})}\n\n"
            driver.get(f'https://{primary_domain}/#/login')
            time.sleep(3)

            # 输入账号密码
            yield f"data: {json.dumps({'type': 'info', 'message': '输入账号信息...'})}\n\n"
            email_input = driver.ele('xpath://input[@placeholder="请输入邮箱"]', timeout=10)
            password_input = driver.ele('xpath://input[@type="password"]', timeout=10)

            if not email_input or not password_input:
                yield f"data: {json.dumps({'type': 'error', 'message': '无法找到登录表单'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': '页面加载失败'})}\n\n"
                driver.quit()
                return

            email_input.clear()
            email_input.input(email)
            password_input.clear()
            password_input.input(password)

            # 点击登录
            yield f"data: {json.dumps({'type': 'info', 'message': '尝试登录...'})}\n\n"
            login_button = driver.ele('xpath://button[contains(@class, "ant-btn-primary")]', timeout=5)
            if login_button:
                login_button.click()
                time.sleep(5)

            # 检查登录结果
            yield f"data: {json.dumps({'type': 'info', 'message': '检查登录结果...'})}\n\n"

            # 检查是否有错误提示
            error_msg = driver.ele('xpath://div[contains(@class, "ant-message-error")]', timeout=2)
            if error_msg:
                yield f"data: {json.dumps({'type': 'error', 'message': '登录失败：账号或密码错误'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': '账号验证失败'})}\n\n"
                driver.quit()
                return

            # 检查是否成功进入主页
            success_indicator = driver.ele('xpath://div[contains(text(), "今日签到")]', timeout=10)
            if not success_indicator:
                # 可能需要处理Cloudflare验证
                yield f"data: {json.dumps({'type': 'warning', 'message': '可能需要处理验证码...'})}\n\n"
                cf_bypasser = CloudflareBypasser(driver, max_retries=3)
                cf_bypasser.bypass()
                time.sleep(3)

                success_indicator = driver.ele('xpath://div[contains(text(), "今日签到")]', timeout=10)

            if success_indicator:
                yield f"data: {json.dumps({'type': 'success', 'message': '登录成功！'})}\n\n"

                # 保存账号到数据库
                yield f"data: {json.dumps({'type': 'info', 'message': '保存账号信息...'})}\n\n"
                config_manager.add_account(email, password)

                yield f"data: {json.dumps({'type': 'success', 'message': '账号已成功添加到系统'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': '账号添加成功'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': '无法验证账号有效性'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': '账号验证失败'})}\n\n"

            driver.quit()

        except Exception as e:
            logging.error(f"账号验证错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'验证过程出错: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': '验证失败'})}\n\n"

            try:
                driver.quit()
            except:
                pass

    return Response(generate(), mimetype='text/event-stream')

def run_schedule():
    """运行定时任务"""
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # 加载认证配置
    load_auth_config()

    # 加载并设置定时任务
    reload_schedule()

    # 启动定时任务线程
    schedule_thread = threading.Thread(target=run_schedule, daemon=True)
    schedule_thread.start()

    # 记录启动时间
    app.config['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 启动Web服务
    logging.info("Web服务启动在 http://localhost:8739")
    app.run(host='0.0.0.0', port=8739, debug=False)