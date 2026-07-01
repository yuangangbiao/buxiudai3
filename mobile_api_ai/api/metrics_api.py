# -*- coding: utf-8 -*-
"""
监控指标API端点
"""
from flask import Blueprint, jsonify, request
from .decorators import success, fail
from metrics import get_stats, reset_metrics, metrics

bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@bp.route('/stats', methods=['GET'])
def stats():
    """获取监控指标统计"""
    minutes = request.args.get('minutes', 60, type=int)
    return success(data=get_stats(minutes=minutes))


@bp.route('/reset', methods=['POST'])
def reset():
    """重置所有指标"""
    reset_metrics()
    return success(message='指标已重置')


@bp.route('/health', methods=['GET'])
def health():
    """健康检查"""
    stats = get_stats(minutes=5)
    api_total = stats['api']['total_requests']
    error_rate = stats['api']['error_rate']
    report_success = stats['reports']['success_rate']

    healthy = error_rate < 5 and report_success > 80

    health_data = {
        'status': 'healthy' if healthy else 'degraded',
        'checks': {
            'error_rate_ok': error_rate < 5,
            'report_success_ok': report_success > 80,
            'error_rate': error_rate,
            'report_success_rate': report_success
        }
    }

    if healthy:
        return success(data=health_data)
    else:
        return fail(503, 'Service degraded', health_data)
