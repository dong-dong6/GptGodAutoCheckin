"""
积分相关路由
包括：积分查询、积分趋势、历史统计、每日汇总等
"""
from flask import Blueprint, request, jsonify
import logging
from src.data.repositories.points_repository import PointsHistoryManager

# 创建蓝图
points_bp = Blueprint('points', __name__, url_prefix='/api/points')


@points_bp.route('/')
def get_points():
    """获取所有账号的积分信息"""
    try:
        manager = PointsHistoryManager()

        # 获取所有账号
        accounts = manager.get_all_accounts()

        result = []
        for account_email in accounts:
            # 获取最新记录
            latest_record = manager.get_latest_record(account_email)

            if latest_record:
                result.append({
                    'email': account_email,
                    'current_points': latest_record['current_balance'],
                    'last_updated': latest_record['record_time']
                })
            else:
                result.append({
                    'email': account_email,
                    'current_points': 0,
                    'last_updated': None
                })

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logging.error(f"获取积分信息失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@points_bp.route('/trend')
def get_points_trend():
    """获取积分趋势"""
    try:
        manager = PointsHistoryManager()
        trend_data = manager.get_points_trend(days=30)

        return jsonify({'success': True, 'data': trend_data})
    except Exception as e:
        logging.error(f"获取积分趋势失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@points_bp.route('/history/stats')
def get_history_stats():
    """获取积分历史统计"""
    try:
        email = request.args.get('email')
        days = request.args.get('days', 30, type=int)

        manager = PointsHistoryManager()

        if email:
            stats = manager.get_account_statistics(email, days)
        else:
            stats = manager.get_all_statistics(days)

        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logging.error(f"获取历史统计失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@points_bp.route('/history/daily')
def get_daily_summary():
    """获取每日积分汇总"""
    try:
        email = request.args.get('email')
        days = request.args.get('days', 30, type=int)

        manager = PointsHistoryManager()
        daily_data = manager.get_daily_summary(email, days)

        return jsonify({'success': True, 'data': daily_data})
    except Exception as e:
        logging.error(f"获取每日汇总失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@points_bp.route('/history/records')
def get_history_records():
    """获取积分历史记录"""
    try:
        email = request.args.get('email')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)

        manager = PointsHistoryManager()

        if email:
            records = manager.get_account_records(
                email,
                limit=page_size,
                offset=(page - 1) * page_size
            )
            total = manager.get_account_record_count(email)
        else:
            records = manager.get_all_records(
                limit=page_size,
                offset=(page - 1) * page_size
            )
            total = manager.get_total_record_count()

        return jsonify({
            'success': True,
            'data': records,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
    except Exception as e:
        logging.error(f"获取历史记录失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


@points_bp.route('/history/overview')
def get_points_overview():
    """获取积分概览"""
    try:
        manager = PointsHistoryManager()

        # 获取所有账号的概览信息
        accounts = manager.get_all_accounts()
        overview = []

        for email in accounts:
            stats = manager.get_account_statistics(email, days=30)
            latest = manager.get_latest_record(email)

            overview.append({
                'email': email,
                'current_points': latest['current_balance'] if latest else 0,
                'total_earned': stats.get('total_earned', 0),
                'total_spent': stats.get('total_spent', 0),
                'record_count': stats.get('record_count', 0),
                'last_updated': latest['record_time'] if latest else None
            })

        return jsonify({'success': True, 'data': overview})
    except Exception as e:
        logging.error(f"获取积分概览失败: {e}")
        return jsonify({'success': False, 'message': str(e)})
