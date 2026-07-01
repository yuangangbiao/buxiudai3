# -*- coding: utf-8 -*-
"""
容器中心可视化模块
实时监控、数据分析、流程可视化
"""
import logging
import os
import time
import threading
import requests as http_requests
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

_cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')

container_dashboard_bp = Blueprint('container_dashboard', __name__)

_cached_packages = None
_cache_timestamp = 0
_cache_ttl = 5
_cache_lock = threading.Lock()


def _get_cached_packages(container_center, ttl=_cache_ttl):
    """获取缓存的数据包（避免重复查询数据库）"""
    global _cached_packages, _cache_timestamp
    current_time = time.time()

    with _cache_lock:
        if _cached_packages is None or (current_time - _cache_timestamp) > ttl:
            try:
                _cached_packages = container_center.storage.get_packages()
                _cache_timestamp = current_time
                logger.debug(f"[Dashboard] 缓存更新，包数量: {len(_cached_packages)}")
            except Exception as e:
                logger.error(f"[Dashboard] 获取数据包失败: {e}")
                _cached_packages = []
                _cache_timestamp = current_time

    return _cached_packages


def invalidate_cache():
    """手动失效缓存（当数据变化时调用）"""
    global _cached_packages, _cache_timestamp
    with _cache_lock:
        _cached_packages = None
        _cache_timestamp = 0

def _is_container_center_valid(cc) -> bool:
    """检查容器中心实例的存储是否可用"""
    if cc is None:
        return False
    try:
        return cc.storage is not None and hasattr(cc.storage, '_conn') and cc.storage._pool is not None
    except Exception:
        return False

def get_container_center():
    """获取容器中心实例（延迟导入避免循环引用）"""
    try:
        from container_center_api import container_center as cc
        if _is_container_center_valid(cc):
            return cc
    except (ImportError, AttributeError):
        pass
    try:
        from wechat_server import container_center as cc
        if _is_container_center_valid(cc):
            return cc
    except (ImportError, AttributeError):
        pass
    try:
        from container_api_server import container_center as cc
        if _is_container_center_valid(cc):
            return cc
    except (ImportError, AttributeError):
        pass
    try:
        from container_center_v5 import ContainerCenter
        return ContainerCenter()
    except Exception as e:
        logger.error(f"容器中心初始化失败: {e}")
        return None

def get_container_stats():
    """获取容器中心统计数据"""
    container_center = get_container_center()
    if not container_center:
        return {
            'total': 0,
            'pending': 0,
            'distributed': 0,
            'acknowledged': 0,
            'completed': 0,
            'error': '容器中心未初始化'
        }

    all_packages = _get_cached_packages(container_center)

    stats = {
        'total': len(all_packages),
        'pending': 0,
        'distributed': 0,
        'acknowledged': 0,
        'completed': 0,
        'expired': 0,
        'cancelled': 0
    }

    for pkg in all_packages:
        status = pkg.get('status', 'pending')
        if status == 'pending':
            stats['pending'] += 1
        elif status == 'distributed':
            stats['distributed'] += 1
        elif status == 'acknowledged':
            stats['acknowledged'] += 1
        elif status == 'completed':
            stats['completed'] += 1
        elif status == 'expired':
            stats['expired'] += 1
        elif status == 'cancelled':
            stats['cancelled'] += 1

    return stats

def get_hourly_trend(hours=24):
    """获取小时级趋势数据（基于实际数据计算）"""
    container_center = get_container_center()
    if not container_center:
        return [{'time': '', 'hour': 0, 'created': 0, 'completed': 0} for _ in range(hours)]

    all_packages = _get_cached_packages(container_center)

    trend = {}
    now = datetime.now()

    for pkg in all_packages:
        created_at = pkg.get('created_at', '')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue

        pkg_hour = created_at.replace(minute=0, second=0, microsecond=0)
        hour_key = pkg_hour.strftime('%H:%M')

        if hour_key not in trend:
            trend[hour_key] = {'time': hour_key, 'hour': created_at.hour, 'created': 0, 'completed': 0}

        trend[hour_key]['created'] += 1

        if pkg.get('status') == 'completed':
            trend[hour_key]['completed'] += 1

    result = []
    for i in range(hours, 0, -1):
        hour_time = now - timedelta(hours=i)
        hour_key = hour_time.strftime('%H:%M')
        if hour_key in trend:
            result.append(trend[hour_key])
        else:
            result.append({'time': hour_key, 'hour': hour_time.hour, 'created': 0, 'completed': 0})

    return result

def get_data_type_distribution():
    """获取数据类型分布"""
    container_center = get_container_center()
    if not container_center:
        return []

    all_packages = _get_cached_packages(container_center)
    distribution = {}

    for pkg in all_packages:
        data_type = pkg.get('data_type', 'other')
        distribution[data_type] = distribution.get(data_type, 0) + 1

    type_names = {
        'report': '报工',
        'quality': '质检',
        'material': '领料',
        'approval': '审批',
        'order': '订单',
        'process': '工序'
    }

    return [
        {'name': type_names.get(k, k), 'value': v, 'type': k}
        for k, v in distribution.items()
    ]

def get_recent_activities(limit=10):
    """获取最近活动"""
    container_center = get_container_center()
    if not container_center:
        return []

    all_packages = _get_cached_packages(container_center)

    activities = []
    for pkg in all_packages:
        created_at = pkg.get('created_at', '')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, TypeError) as e:
                logger.warning(f"时间格式解析失败: {e}")
                created_at = datetime.now()

        activities.append({
            'id': pkg.get('id', ''),
            'title': pkg.get('title', ''),
            'type': pkg.get('data_type', 'other'),
            'status': pkg.get('status', 'pending'),
            'time': created_at.strftime('%Y-%m-%d %H:%M') if isinstance(created_at, datetime) else str(created_at),
            'order_no': pkg.get('related_order', '')
        })

    activities.sort(key=lambda x: x['time'], reverse=True)
    return activities[:limit]

@container_dashboard_bp.route('/')
def show_dashboard():
    """容器中心统一仪表盘页面"""
    return render_template('unified_container.html')

@container_dashboard_bp.route('/config')
def show_config():
    """重定向到统一页面-配置管理标签"""
    return redirect(url_for('container_dashboard.show_dashboard') + '?tab=config')

@container_dashboard_bp.route('/alert-rules')
def show_alert_rules():
    """重定向到统一页面-告警规则标签"""
    return redirect(url_for('container_dashboard.show_dashboard') + '?tab=alerts')

@container_dashboard_bp.route('/api/alert-rules')
def api_get_alert_rules():
    """获取告警规则配置（代理到容器中心API）"""
    try:
        resp = http_requests.get(f'{_cc_url}/api/container/config/alert_rules', timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        return jsonify(resp.json())
    except Exception as e:
        logger.error(f'获取告警规则失败: {e}')
        return jsonify({'code': -1, 'message': f'获取告警规则失败: {e}'})

@container_dashboard_bp.route('/api/alert-rules', methods=['PUT'])
def api_update_alert_rules():
    """更新告警规则配置（代理到容器中心API）"""
    try:
        data = request.get_json()
        resp = http_requests.put(f'{_cc_url}/api/container/config/alert_rules',
                                  json=data, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        return jsonify(resp.json())
    except Exception as e:
        logger.error(f'更新告警规则失败: {e}')
        return jsonify({'code': -1, 'message': f'更新告警规则失败: {e}'})

@container_dashboard_bp.route('/api/stats')
def api_container_stats():
    """获取统计数据"""
    try:
        return jsonify({
            'code': 0,
            'data': get_container_stats()
        })
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return jsonify({'code': 500, 'message': f'获取统计数据失败: {e}'})

@container_dashboard_bp.route('/api/trend')
def api_container_trend():
    """获取趋势数据"""
    try:
        hours = request.args.get('hours', 24, type=int)
        return jsonify({
            'code': 0,
            'data': get_hourly_trend(hours)
        })
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        return jsonify({'code': 500, 'message': f'获取趋势数据失败: {e}'})

@container_dashboard_bp.route('/api/distribution')
def api_container_distribution():
    """获取数据分布"""
    try:
        return jsonify({
            'code': 0,
            'data': get_data_type_distribution()
        })
    except Exception as e:
        logger.error(f"获取分布数据失败: {e}")
        return jsonify({'code': 500, 'message': f'获取分布数据失败: {e}'})

@container_dashboard_bp.route('/api/activities')
def api_container_activities():
    """获取最近活动"""
    try:
        limit = request.args.get('limit', 10, type=int)
        return jsonify({
            'code': 0,
            'data': get_recent_activities(limit)
        })
    except Exception as e:
        logger.error(f"获取活动数据失败: {e}")
        return jsonify({'code': 500, 'message': f'获取活动数据失败: {e}'})

@container_dashboard_bp.route('/api/flow')
def api_container_flow():
    """获取任务流程数据（用于流程图）"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'})

        all_packages = _get_cached_packages(container_center)

        flow_data = {
            'nodes': [
                {'id': 'pending', 'name': '待处理', 'count': 0, 'x': 100, 'y': 200},
                {'id': 'distributed', 'name': '已分配', 'count': 0, 'x': 280, 'y': 200},
                {'id': 'acknowledged', 'name': '已确认', 'count': 0, 'x': 460, 'y': 200},
                {'id': 'completed', 'name': '已完成', 'count': 0, 'x': 640, 'y': 200}
            ],
            'links': [
                {'source': 'pending', 'target': 'distributed', 'count': 0},
                {'source': 'distributed', 'target': 'acknowledged', 'count': 0},
                {'source': 'acknowledged', 'target': 'completed', 'count': 0}
            ]
        }

        status_map = {
            'pending': 0,
            'distributed': 1,
            'acknowledged': 2,
            'completed': 3
        }

        for pkg in all_packages:
            status = pkg.get('status', 'pending')
            idx = status_map.get(status, 0)
            flow_data['nodes'][idx]['count'] += 1

            if idx > 0:
                flow_data['links'][idx - 1]['count'] += 1

        return jsonify({
            'code': 0,
            'data': flow_data
        })
    except Exception as e:
        logger.error(f"获取流程数据失败: {e}")
        return jsonify({'code': 500, 'message': f'获取流程数据失败: {e}'})

@container_dashboard_bp.route('/api/container/operators')
def api_container_operators():
    """获取操作员工作量统计"""
    container_center = get_container_center()
    if not container_center:
        return jsonify({'code': 500, 'message': '容器中心未初始化'})

    all_packages = container_center.storage.get_packages()

    operator_stats = {}
    for pkg in all_packages:
        target = pkg.get('target_operator', 'unknown')
        if target not in operator_stats:
            operator_stats[target] = {
                'operator': target,
                'total': 0,
                'completed': 0,
                'pending': 0,
                'distributed': 0
            }

        operator_stats[target]['total'] += 1
        status = pkg.get('status', 'pending')
        if status == 'completed':
            operator_stats[target]['completed'] += 1
        elif status == 'pending':
            operator_stats[target]['pending'] += 1
        elif status == 'distributed':
            operator_stats[target]['distributed'] += 1

    return jsonify({
        'code': 0,
        'data': list(operator_stats.values())
    })

@container_dashboard_bp.route('/api/container/config')
def api_container_config():
    """获取容器中心配置"""
    try:
        from container_config import container_config
        return jsonify({
            'code': 0,
            'data': {
                'operators': container_config.to_dict()['operators'],
                'processes': container_config.to_dict()['processes'],
                'data_types': container_config.to_dict()['data_types'],
                'notification': container_config.get_notification_config().__dict__
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/config/operator', methods=['POST'])
def api_add_operator():
    """添加操作员"""
    try:
        from container_config import container_config, OperatorConfig

        data = request.get_json()
        operator = OperatorConfig(
            id=data.get('id'),
            name=data.get('name'),
            role=data.get('role', '工人'),
            department=data.get('department', ''),
            enabled=data.get('enabled', True)
        )

        if container_config.add_operator(operator):
            return jsonify({'code': 0, 'message': '添加成功'})
        else:
            return jsonify({'code': 400, 'message': '操作员已存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/config/operator/<operator_id>', methods=['PUT'])
def api_update_operator(operator_id):
    """更新操作员"""
    try:
        from container_config import container_config

        data = request.get_json()
        if container_config.update_operator(operator_id, **data):
            return jsonify({'code': 0, 'message': '更新成功'})
        else:
            return jsonify({'code': 400, 'message': '操作员不存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/config/operator/<operator_id>', methods=['DELETE'])
def api_delete_operator(operator_id):
    """删除操作员"""
    try:
        from container_config import container_config

        if container_config.remove_operator(operator_id):
            return jsonify({'code': 0, 'message': '删除成功'})
        else:
            return jsonify({'code': 400, 'message': '操作员不存在'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/dispatch/commands', methods=['POST'])
def api_create_dispatch_command():
    """创建调度指令"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'})

        data = request.get_json()
        import uuid

        command = {
            'command_id': data.get('command_id', str(uuid.uuid4())[:8].upper()),
            'command_type': data.get('command_type', 'dispatch'),
            'target_type': data.get('target_type', 'operator'),
            'target_id': data.get('target_id'),
            'operator_id': data.get('operator_id'),
            'order_no': data.get('order_no'),
            'process_name': data.get('process_name'),
            'command_data': data.get('command_data', {}),
            'priority': data.get('priority', 'normal'),
            'status': 'pending'
        }

        if container_center.storage.save_dispatch_command(command):
            container_center.storage.log_sync('DISPATCH_CREATE', command['command_id'], f'创建调度指令: {command["command_type"]}')
            return jsonify({
                'code': 0,
                'message': '调度指令创建成功',
                'data': command
            })
        else:
            return jsonify({'code': 500, 'message': '调度指令创建失败'})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/flow/logs')
def api_data_flow_logs():
    """获取数据流转记录列表"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'})

        flow_id = request.args.get('flow_id')
        event_type = request.args.get('event_type')
        order_no = request.args.get('order_no')
        limit = request.args.get('limit', 100, type=int)

        logs = container_center.storage.get_data_flow_logs(
            flow_id=flow_id,
            event_type=event_type,
            order_no=order_no,
            limit=limit
        )

        return jsonify({
            'code': 0,
            'data': logs,
            'total': len(logs)
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/flow/logs/all')
def api_all_data_flow_logs():
    """获取所有数据流转记录"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'})

        logs = container_center.storage.get_all_data_flow_logs()
        return jsonify({
            'code': 0,
            'data': logs,
            'total': len(logs)
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/flow/logs/<flow_id>')
def api_get_flow_log_by_id(flow_id):
    """获取指定数据包的完整流转记录"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'})

        logs = container_center.storage.get_data_flow_logs(flow_id=flow_id, limit=100)

        if not logs:
            return jsonify({'code': 404, 'message': '流转记录不存在'})

        return jsonify({
            'code': 0,
            'data': logs,
            'total': len(logs)
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

@container_dashboard_bp.route('/api/container/flow/stats')
def api_flow_stats():
    """获取流转统计数据（用于分析调度规则）"""
    try:
        container_center = get_container_center()
        if not container_center:
            return jsonify({'code': 500, 'message': '容器中心未初始化'})

        all_logs = container_center.storage.get_all_data_flow_logs()

        stats = {
            'total_events': len(all_logs),
            'by_event_type': {},
            'by_data_type': {},
            'by_operator': {},
            'dispatch_rules': {},
            'avg_duration_ms': 0,
            'total_duration_ms': 0
        }

        durations = []
        for log in all_logs:
            event_type = log.get('event_type', 'unknown')
            stats['by_event_type'][event_type] = stats['by_event_type'].get(event_type, 0) + 1

            data_type = log.get('data_type', 'unknown')
            stats['by_data_type'][data_type] = stats['by_data_type'].get(data_type, 0) + 1

            operator = log.get('target_operator', 'unknown')
            stats['by_operator'][operator] = stats['by_operator'].get(operator, 0) + 1

            rule = log.get('dispatch_rule') or 'unknown'
            stats['dispatch_rules'][rule] = stats['dispatch_rules'].get(rule, 0) + 1

            duration = log.get('duration_ms', 0)
            if duration:
                durations.append(duration)
                stats['total_duration_ms'] += duration

        if durations:
            stats['avg_duration_ms'] = int(sum(durations) / len(durations))

        return jsonify({
            'code': 0,
            'data': stats
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})
