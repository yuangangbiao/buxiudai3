from flask import Blueprint, request, jsonify, render_template
import json
import logging

from .decorators import success, fail
from services.factory import get_stats_service, get_scheduler_service

logger = logging.getLogger(__name__)

bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@bp.route('/page')
def page():
    """报表中心页面"""
    return render_template('reports_dashboard.html')


def _get_engine():
    return get_stats_service()


# ── 报表定义管理 ──

@bp.route('/definitions', methods=['GET'])
def list_definitions():
    """列表所有报表定义，可选按 category 筛选"""
    engine = _get_engine()
    category = request.args.get('category')
    reports = engine.list_reports(category)
    return success(data=reports)


@bp.route('/definitions/<report_id>', methods=['GET'])
def get_definition(report_id):
    """获取单个报表定义详情"""
    engine = _get_engine()
    report = engine.get_report(report_id)
    if not report:
        return fail(404, '报表定义不存在')
    return success(data=report)


@bp.route('/definitions', methods=['POST'])
def create_definition():
    """创建报表定义"""
    data = request.get_json(silent=True)
    if not data or not data.get('name') or not data.get('sql_template'):
        return fail(400, '缺少必填字段: name, sql_template')
    engine = _get_engine()
    ok = engine.save_report(data)
    if not ok:
        return fail(500, '保存失败')
    return success(message='报表定义已创建')


@bp.route('/definitions/<report_id>', methods=['PUT'])
def update_definition(report_id):
    """更新报表定义"""
    data = request.get_json(silent=True)
    if not data:
        return fail(400, '缺少请求体')
    engine = _get_engine()
    existing = engine.get_report(report_id)
    if not existing:
        return fail(404, '报表定义不存在')
    data['id'] = report_id
    ok = engine.save_report(data)
    if not ok:
        return fail(500, '保存失败')
    return success(message='报表定义已更新')


@bp.route('/definitions/<report_id>', methods=['DELETE'])
def delete_definition(report_id):
    """删除报表定义"""
    engine = _get_engine()
    ok = engine.delete_report(report_id)
    if not ok:
        return fail(500, '删除失败')
    return success(message='报表定义已删除')


@bp.route('/definitions/<report_id>/execute', methods=['GET', 'POST'])
def execute_definition(report_id):
    """执行报表定义并返回数据"""
    engine = _get_engine()
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        params = body.get('params', {})
    else:
        params = request.args.to_dict()
    result = engine.execute_report(report_id, params)
    if 'error' in result:
        return fail(404, result['error'])
    return jsonify({'code': 0, 'message': 'success', 'data': result})


# ── 导出配置管理 ──

@bp.route('/profiles', methods=['GET'])
def list_profiles():
    """列表导出配置"""
    engine = _get_engine()
    profiles = engine.list_export_profiles()
    return success(data=profiles)


@bp.route('/profiles/<profile_id>', methods=['GET'])
def get_profile(profile_id):
    """获取单个导出配置"""
    engine = _get_engine()
    profile = engine.get_export_profile(profile_id)
    if not profile:
        return fail(404, '导出配置不存在')
    return success(data=profile)


@bp.route('/profiles', methods=['POST'])
def create_profile():
    """创建导出配置"""
    data = request.get_json(silent=True)
    if not data or not data.get('name'):
        return fail(400, '缺少必填字段: name')
    engine = _get_engine()
    ok = engine.save_export_profile(data)
    if not ok:
        return fail(500, '保存失败')
    return success(message='导出配置已创建')


@bp.route('/profiles/<profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """更新导出配置"""
    data = request.get_json(silent=True)
    if not data:
        return fail(400, '缺少请求体')
    engine = _get_engine()
    existing = engine.get_export_profile(profile_id)
    if not existing:
        return fail(404, '导出配置不存在')
    data['id'] = profile_id
    ok = engine.save_export_profile(data)
    if not ok:
        return fail(500, '保存失败')
    return success(message='导出配置已更新')


@bp.route('/profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    """删除导出配置"""
    engine = _get_engine()
    ok = engine.delete_export_profile(profile_id)
    if not ok:
        return fail(500, '删除失败')
    return success(message='导出配置已删除')


# ── 定时计划管理 ──

@bp.route('/schedules', methods=['GET'])
def list_schedules():
    """列表定时计划"""
    engine = _get_engine()
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    schedules = engine.list_schedules(enabled_only)
    return success(data=schedules)


@bp.route('/schedules/<schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """获取单个定时计划"""
    engine = _get_engine()
    schedule = engine.get_schedule(schedule_id)
    if not schedule:
        return fail(404, '定时计划不存在')
    return success(data=schedule)


@bp.route('/schedules', methods=['POST'])
def create_schedule():
    """创建定时计划"""
    data = request.get_json(silent=True)
    if not data or not data.get('name') or not data.get('report_id'):
        return fail(400, '缺少必填字段: name, report_id')
    engine = _get_engine()
    ok = engine.save_schedule(data)
    if not ok:
        return fail(500, '保存失败')
    return success(message='定时计划已创建')


@bp.route('/schedules/<schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """更新定时计划"""
    data = request.get_json(silent=True)
    if not data:
        return fail(400, '缺少请求体')
    engine = _get_engine()
    existing = engine.get_schedule(schedule_id)
    if not existing:
        return fail(404, '定时计划不存在')
    data['id'] = schedule_id
    ok = engine.save_schedule(data)
    if not ok:
        return fail(500, '保存失败')
    return success(message='定时计划已更新')


@bp.route('/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """删除定时计划"""
    engine = _get_engine()
    ok = engine.delete_schedule(schedule_id)
    if not ok:
        return fail(500, '删除失败')
    return success(message='定时计划已删除')


# ── 输出记录 ──

@bp.route('/outputs', methods=['GET'])
def list_outputs():
    """列表报表输出记录"""
    engine = _get_engine()
    report_id = request.args.get('report_id')
    limit = request.args.get('limit', 50, type=int)
    outputs = engine.list_outputs(report_id, limit)
    return success(data=outputs)


# ── 调度器控制 ──

@bp.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    """查看调度器运行状态"""
    scheduler = get_scheduler_service()
    if scheduler and scheduler.is_running():
        return success(data={'running': True, 'check_interval': scheduler.check_interval})
    return success(data={'running': False})


@bp.route('/scheduler/start', methods=['POST'])
def start_scheduler_api():
    """启动定时调度器"""
    engine = _get_engine()
    scheduler = get_scheduler_service()
    scheduler.start()
    return success(data={'running': True})


@bp.route('/scheduler/stop', methods=['POST'])
def stop_scheduler_api():
    """停止定时调度器"""
    scheduler = get_scheduler_service()
    if scheduler:
        scheduler.stop()
    return success(data={'running': False})
