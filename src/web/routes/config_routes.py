"""
配置管理相关路由
包括：SMTP配置、账号管理、域名配置、定时任务配置
"""
from flask import Blueprint, request, jsonify
import logging
from src.data.repositories.config_repository import ConfigManager

# 创建蓝图
config_bp = Blueprint('config', __name__, url_prefix='/api/config')


@config_bp.route('/smtp', methods=['GET', 'POST'])
def smtp_config():
    """SMTP配置管理 - 需要在主app中添加@require_auth装饰器"""
    config_manager = ConfigManager()

    if request.method == 'GET':
        try:
            smtp_config = config_manager.get_smtp_config()
            return jsonify({'success': True, 'config': smtp_config})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    elif request.method == 'POST':
        try:
            data = request.json
            config_manager.update_smtp_config(
                enabled=data.get('enabled', False),
                server=data.get('server', ''),
                port=data.get('port', 587),
                sender_email=data.get('sender_email', ''),
                sender_password=data.get('sender_password', ''),
                receiver_emails=data.get('receiver_emails', [])
            )
            return jsonify({'success': True, 'message': 'SMTP配置已更新'})
        except Exception as e:
            logging.error(f"更新SMTP配置失败: {e}")
            return jsonify({'success': False, 'message': str(e)})


@config_bp.route('/accounts', methods=['GET'])
def get_accounts():
    """获取账号列表"""
    try:
        config_manager = ConfigManager()
        accounts = config_manager.get_accounts()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@config_bp.route('/accounts/add', methods=['POST'])
def add_account():
    """添加账号"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'success': False, 'message': '请提供完整信息'})

        config_manager = ConfigManager()
        config_manager.add_account(email, password)

        return jsonify({'success': True, 'message': f'账号 {email} 已添加'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@config_bp.route('/accounts/remove', methods=['POST'])
def remove_account():
    """删除账号"""
    try:
        data = request.json
        email = data.get('email')

        if not email:
            return jsonify({'success': False, 'message': '请提供账号邮箱'})

        config_manager = ConfigManager()
        config_manager.remove_account(email)

        return jsonify({'success': True, 'message': f'账号 {email} 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@config_bp.route('/accounts/email-notification', methods=['POST'])
def update_email_notification():
    """更新账号邮件通知设置"""
    try:
        data = request.json
        email = data.get('email')
        send_notification = data.get('send_notification', False)

        if not email:
            return jsonify({'success': False, 'message': '请提供账号邮箱'})

        config_manager = ConfigManager()
        config_manager.update_account_email_notification(email, send_notification)

        status = '启用' if send_notification else '禁用'
        return jsonify({'success': True, 'message': f'账号 {email} 已{status}邮件通知'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@config_bp.route('/export')
def export_config():
    """导出配置"""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_all_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@config_bp.route('/reset', methods=['POST'])
def reset_config():
    """重置配置"""
    try:
        config_manager = ConfigManager()
        config_manager.reset_config()
        return jsonify({'success': True, 'message': '配置已重置'})
    except Exception as e:
        logging.error(f"重置配置失败: {e}")
        return jsonify({'success': False, 'message': str(e)})
