"""
认证相关路由
包括：登录、登出、修改密码、API Token验证
"""
from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template_string
import hashlib
import logging

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

# 这些变量需要从主app传递过来
LOGIN_TEMPLATE = ""  # 将在主app中注入
AUTH_CONFIG = {}  # 将在主app中注入


def init_auth_routes(login_template, auth_config):
    """初始化认证路由所需的配置"""
    global LOGIN_TEMPLATE, AUTH_CONFIG
    LOGIN_TEMPLATE = login_template
    AUTH_CONFIG = auth_config


@auth_bp.route('/login', methods=['GET', 'POST'])
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


@auth_bp.route('/logout')
def logout():
    """退出登录"""
    session.pop('authenticated', None)
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/change-password', methods=['POST'])
def api_change_password():
    """修改密码 - 需要在主app中添加@require_auth装饰器"""
    from src.data.repositories.config_repository import ConfigManager

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
        config_manager = ConfigManager()
        config_manager.update_web_auth_config(
            enabled=AUTH_CONFIG['enabled'],
            username=AUTH_CONFIG['username'],
            password=new_password,
            api_token=AUTH_CONFIG['api_token']
        )

        logging.info(f"用户 {session.get('username', 'unknown')} 修改了密码")

        return jsonify({'success': True, 'message': '密码修改成功'})

    except Exception as e:
        logging.error(f"修改密码失败: {e}")
        return jsonify({'success': False, 'message': str(e)})
