"""
日志和统计相关路由
包括：签到日志查询、统计信息、定时任务配置、域名配置
"""
from flask import Blueprint, request, jsonify
import logging
from src.data.repositories.checkin_repository import CheckinLoggerDB
from src.data.repositories.config_repository import ConfigManager

# 创建蓝图
logs_bp = Blueprint('logs', __name__, url_prefix='/api')


@logs_bp.route('/logs')
def get_logs():
    """获取签到日志"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        logger_db = CheckinLoggerDB()
        logs = logger_db.get_recent_logs(limit=page_size, offset=(page - 1) * page_size)

        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logging.error(f"获取日志失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@logs_bp.route('/stats')
def get_stats():
    """获取统计信息"""
    try:
        logger_db = CheckinLoggerDB()
        stats = logger_db.get_statistics()

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@logs_bp.route('/schedule', methods=['GET', 'POST'])
def schedule_config():
    """定时任务配置"""
    config_manager = ConfigManager()

    if request.method == 'GET':
        try:
            schedule_config = config_manager.get_schedule_config()
            return jsonify({'success': True, 'config': schedule_config})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    elif request.method == 'POST':
        try:
            data = request.json
            config_manager.update_schedule_config(
                enabled=data.get('enabled', False),
                times=data.get('times', [])
            )

            # 重新加载定时任务（需要在主app中实现）
            return jsonify({
                'success': True,
                'message': '定时任务配置已更新（需要重启服务生效）'
            })
        except Exception as e:
            logging.error(f"更新定时任务配置失败: {e}")
            return jsonify({'success': False, 'message': str(e)})


@logs_bp.route('/domains', methods=['GET', 'POST'])
def domains_config():
    """域名配置"""
    config_manager = ConfigManager()

    if request.method == 'GET':
        try:
            domains_config = config_manager.get_domain_config()
            return jsonify({'success': True, 'config': domains_config})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    elif request.method == 'POST':
        try:
            data = request.json
            config_manager.update_domain_config(
                primary=data.get('primary', ''),
                backup=data.get('backup', ''),
                auto_switch=data.get('auto_switch', True)
            )

            return jsonify({'success': True, 'message': '域名配置已更新'})
        except Exception as e:
            logging.error(f"更新域名配置失败: {e}")
            return jsonify({'success': False, 'message': str(e)})
