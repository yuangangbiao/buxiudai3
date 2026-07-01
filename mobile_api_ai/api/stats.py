from flask import Blueprint, request
import logging

from .decorators import success, fail
from services.factory import get_stats_service

logger = logging.getLogger(__name__)

bp = Blueprint('stats', __name__, url_prefix='/api/stats')


def _get_engine():
    return get_stats_service()


@bp.route('/dashboard', methods=['GET'])
def dashboard():
    """综合仪表盘 - 今日报工/效率/待审批/亏损订单"""
    engine = _get_engine()
    data = engine.get_dashboard()
    return success(data=data)


@bp.route('/production', methods=['GET'])
def production_stats():
    """生产统计 - 订单状态分布/近7天趋势/产品排行"""
    engine = _get_engine()
    data = engine.get_production_stats()
    return success(data=data)


@bp.route('/cost', methods=['GET'])
def cost_stats():
    """成本统计 - 利润率排行/成本构成/亏损分析"""
    engine = _get_engine()
    data = engine.get_cost_stats()
    return success(data=data)


@bp.route('/worker', methods=['GET'])
def worker_stats():
    """人员效率 - 操作员效率排名/工序完成量"""
    engine = _get_engine()
    data = engine.get_worker_stats()
    return success(data=data)


@bp.route('/worker-stats', methods=['GET'])
def worker_stats_legacy():
    """兼容旧版接口 - 重定向到新接口"""
    engine = _get_engine()
    data = engine.get_worker_stats()
    return success(data=data.get('efficiency', []))


@bp.route('/order-stats', methods=['GET'])
def order_stats_legacy():
    """兼容旧版接口"""
    engine = _get_engine()
    data = engine.get_production_stats()
    overview = data.get('overview', [])
    result = {'total_orders': 0, 'in_production': 0, 'quality_check': 0, 'completed': 0, 'overdue': 0}
    for row in overview:
        status = row.get('状态', '')
        count = row.get('数量', 0)
        if status == 'in_progress':
            result['in_production'] = count
        elif status == 'completed':
            result['completed'] = count
        elif status == 'quality_check':
            result['quality_check'] = count
        elif status == 'overdue':
            result['overdue'] = count
        result['total_orders'] += count
    return success(data=result)


@bp.route('/report/<report_id>', methods=['GET'])
def execute_custom_report(report_id):
    """执行自定义报表（SQL模板）"""
    engine = _get_engine()
    params = request.args.to_dict()
    result = engine.execute_report(report_id, params)
    if 'error' in result:
        return fail(404, result['error'])
    return success(data=result)


@bp.route('/report/<report_id>/export', methods=['GET'])
def export_report(report_id):
    """导出报表文件"""
    engine = _get_engine()
    export_format = request.args.get('format', 'xlsx')
    profile_id = request.args.get('profile_id')
    params = {k: v for k, v in request.args.items() if k not in ('format', 'profile_id')}
    result = engine.export_report(report_id, format=export_format, profile_id=profile_id, params=params)
    if not result.get('success'):
        return fail(400, result.get('error', '导出失败'))
    return success(data={
        'file_path': result.get('file_path'),
        'file_name': result.get('file_name'),
        'row_count': result.get('row_count'),
        'output_id': result.get('output_id')
    })
