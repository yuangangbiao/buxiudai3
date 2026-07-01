# -*- coding: utf-8 -*-
"""
sync_bp 蓝图
============================================================
云端去除调度中心功能 — 16 端点迁移
原 wechat_server.py:15003 中 22 个 /api/sync/* 业务 API 中
16 个真新增端点的本地 5003 实现，3 个真重复不迁移，1 个
云端微信回调（/report/wechat）不迁移。

实现路径（按数据流）:
  - 业务操作类 (5):   调容器中心 V5 SDK
  - 业务配置类 (6):   内存计算 + 读容器中心 + 读 MySQL
  - 熔断/队列类 (4):  内存单例
  - 数据落库/读类 (4): 走 8008 桥 + 直读 MySQL

F1 阻塞项 (operation_logs.direction 列缺失):
  - task/<order>/status  (AC-10)
  - reports             (AC-10)
  - logs                (AC-10)
  - report/requests     (AC-10)
  - report/confirm      (AC-10, 走 8008 桥)
修复由云端负责，本地端点先建（返 500 而非 404）。
"""
import os
import re
import time
import json
import hashlib
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

logger = logging.getLogger('sync_bp')

# ── 蓝图定义 ──
sync_bp = Blueprint('sync_bp', __name__, url_prefix='/api/sync')

# ── 订单号正则 ──
ORDER_NO_PATTERN = re.compile(r'^ORD-\d{8,}$')


# ═════════════════════════════════════════════════════════════
#  辅助: 容器中心客户端
# ═════════════════════════════════════════════════════════════

def _get_container_client():
    """获取 V5 兼容容器中心客户端 (复用 DispatchContext 单例)
    Returns:
        V5CompatibleClient 或 None
    """
    try:
        from dispatch_center import DispatchContext
        return DispatchContext.get_instance().get_client()
    except Exception as e:
        logger.exception('[sync_bp] 容器中心客户端初始化失败: %s', e)
        return None


def _find_order(client, order_no: str) -> Optional[Dict]:
    """按 order_no 查 order 文档 (A1: 用订单号对齐)
    ---
    三级回退链:
      1) V5 客户端索引直查 (get_documents_by_index)
      2) V5 客户端全表扫 (get_packages doc_type='order')
      3) 直连容器中心 5002 HTTP API (绕过 V5 HTTP 回退分支的 work_order 硬编码)
    Returns:
        命中返回 order 文档 dict，未命中返回 None
    """
    if client is None or not order_no:
        return None
    # 1) 索引直查
    for method_name in ('get_documents_by_index', 'query_documents_by_index'):
        method = getattr(client, method_name, None)
        if method is None:
            continue
        try:
            resp = method('order', 'order_no', order_no)
            items = resp.get('items', resp.get('data', [])) if isinstance(resp, dict) else (resp or [])
            for it in items:
                if isinstance(it, dict) and it.get('order_no') == order_no:
                    return it
        except Exception as e:
            logger.debug('[sync_bp] _find_order 索引直查失败 %s: %s', method_name, e)
    # 2) V5 客户端全表扫
    try:
        all_orders = client.get_packages(doc_type='order', limit=5000) or []
        for o in all_orders:
            if isinstance(o, dict) and o.get('order_no') == order_no:
                return o
    except Exception as e:
        logger.warning('[sync_bp] _find_order V5 get_packages 失败: %s', e)
    # 3) 直连容器中心 5002 HTTP API (绕过 V5 客户端 HTTP 回退对 'order' 的硬编码跳过)
    #    注意: 5002 端点返回的 item 结构是 {created_at, doc_data:{...}, doc_type, id}
    #          order_no 字段在嵌套 doc_data 内, 不在 item 顶层
    import os
    import json as _json
    from urllib import request as _urlreq
    from urllib.error import URLError, HTTPError
    cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002').rstrip('/')
    url = f'{cc_url}/api/v4/documents/order?limit=5000&q={order_no}'
    try:
        req = _urlreq.Request(url, headers={'Accept': 'application/json'})
        with _urlreq.urlopen(req, timeout=5) as resp:
            payload = _json.loads(resp.read().decode('utf-8'))
            data = payload.get('data', {}) if isinstance(payload, dict) else {}
            items = data.get('data', data.get('items', [])) if isinstance(data, dict) else (data or [])
            for it in items:
                if not isinstance(it, dict):
                    continue
                # 兼容两种 item 结构: order_no 可能在顶层, 也可能在 doc_data 内
                _ono = it.get('order_no') or (it.get('doc_data') or {}).get('order_no')
                if _ono == order_no:
                    return it
            logger.warning(
                '[sync_bp] _find_order HTTP 5002 直连: url=%s, items=%d, 未匹配 order_no=%s',
                url, len(items) if isinstance(items, list) else 0, order_no,
            )
    except (URLError, HTTPError, Exception) as e:
        logger.warning(f'[sync_bp] _find_order HTTP 5002 直连失败: {type(e).__name__}: {e}')
    return None


# ═════════════════════════════════════════════════════════════
#  辅助: MySQL 连接 (用于读类端点, jgs7 规范: context manager)
# ═════════════════════════════════════════════════════════════

@contextmanager
def _get_mysql_conn():
    """从连接池获取 steel_belt MySQL 连接 (context manager)
    Yields:
        pymysql.connections.Connection
    Raises:
        Exception: 连接失败时记录日志并重新抛出
    """
    try:
        from db.steelbelt_pool import get_conn
        conn = get_conn()
    except Exception as e:
        logger.exception('[sync_bp] MySQL 连接池获取失败: %s', e)
        raise
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════
#  业务操作类 (5 端点, 调容器中心 V5 SDK)
# ═════════════════════════════════════════════════════════════

@sync_bp.route('/report', methods=['POST'])
def sync_report():
    """报工同步 — 改 order 文档 (按 order_no 对齐, 累加 completed_qty)
    ---
    Request:
        order_no   (str, 必填) 订单号
        process    (str, 必填) 工序名
        quantity   (int, 必填) 本次报工数量
        operator   (str, 必填) 操作员 ID
        completed  (bool, 可选) 是否完成, 默认 False
        force      (bool, 可选) 跳过重复报工确认, 默认 False
    Response:
        {code: 200, data: {task_id, completed_qty, planned_qty, remaining}}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        process = str(data.get('process', '')).strip()
        quantity = int(data.get('quantity', 0) or 0)
        operator = str(data.get('operator', '')).strip()
        completed = bool(data.get('completed', False))
        if not all([order_no, process, operator]) or quantity <= 0:
            return jsonify({'code': 400, 'message': 'order_no/process/operator/quantity 必填且 quantity > 0'}), 400

        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500

        # A1: 按 order_no 直接查 order 文档（work_order 已废弃）
        order = _find_order(client, order_no)
        if not order:
            return jsonify({'code': 404, 'message': f'未找到订单 {order_no}'}), 404

        order_id = order.get('id')
        current = client.get_package(pkg_id=order_id, doc_type='order') or order
        current_completed = current.get('completed_qty', 0) or 0
        planned_qty = (current.get('content') or {}).get('planned_qty', 0) or 0
        new_completed = current_completed + quantity
        remaining = max(0, planned_qty - new_completed)
        new_status = 'completed' if (completed or remaining == 0) else current.get('status', 'in_progress')

        client.update_document('order', order_id, {
            'completed_qty': new_completed,
            'actual_qty': new_completed,
            'target_operator': operator,
            'operator_id': operator,
            'status': new_status,
        })
        # RE-002 T4: 报工完成后触发群消息（失败仅 log，不阻断主业务）
        try:
            from bots.factory import get_factory
            from template_engine import _render_template
            _bot = get_factory().get_group_bot()
            if _bot:
                _msg = _render_template('tmpl_report_submitted', {
                    '订单号': order_no,
                    '工序': process,
                    '数量': quantity,
                    '操作员': operator,
                    '报工时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                _bot.send_markdown(_msg)
        except Exception as e:
            logger.warning(f"[sync_bp] /report 报工消息发送失败: {e}")
        return jsonify({
            'code': 200,
            'message': '报工同步成功',
            'data': {
                'task_id': order_id,
                'completed_qty': new_completed,
                'planned_qty': planned_qty,
                'remaining': remaining,
            }
        })
    except Exception as e:
        logger.exception('[sync_bp] /report 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/report/actual', methods=['POST'])
def sync_report_actual():
    """实际报工 — order 文档 completed_qty 累加
    ---
    Request:
        order_no     (str, 必填) 订单号
        process_name (str, 必填) 工序名
        quantity     (int, 必填) 实际报工数量
        operator_id  (str, 必填) 操作员 ID
        completed    (bool, 可选)
    Response:
        {code: 200, data: {task_id, new_completed, remaining}}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        process_name = str(data.get('process_name', '')).strip()
        quantity = int(data.get('quantity', 0) or 0)
        operator_id = str(data.get('operator_id', '')).strip()
        if not all([order_no, process_name, operator_id]) or quantity <= 0:
            return jsonify({'code': 400, 'message': 'order_no/process_name/operator_id/quantity 必填'}), 400

        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500

        # A1: 按 order_no 直接查 order 文档
        order = _find_order(client, order_no)
        if not order:
            return jsonify({'code': 404, 'message': f'未找到订单 {order_no}'}), 404

        order_id = order.get('id')
        current = client.get_package(pkg_id=order_id, doc_type='order') or order
        current_completed = current.get('completed_qty', 0) or 0
        planned_qty = (current.get('content') or {}).get('planned_qty', 0) or 0
        new_completed = current_completed + quantity
        remaining = max(0, planned_qty - new_completed)

        client.update_document('order', order_id, {
            'completed_qty': new_completed,
            'actual_qty': new_completed,
            'operator_id': operator_id,
            'target_operator': operator_id,
        })
        # RE-002 T4: 实际报工完成后触发群消息（失败仅 log，不阻断主业务）
        try:
            from bots.factory import get_factory
            from template_engine import _render_template
            _bot = get_factory().get_group_bot()
            if _bot:
                _msg = _render_template('tmpl_report_actual', {
                    '订单号': order_no,
                    '工序': process_name,
                    '数量': quantity,
                    '累计完成': new_completed,
                    '剩余': remaining,
                    '操作员': operator_id,
                    '报工时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                _bot.send_markdown(_msg)
        except Exception as e:
            logger.warning(f"[sync_bp] /report/actual 报工消息发送失败: {e}")
        return jsonify({
            'code': 200,
            'message': '实际报工成功',
            'data': {'task_id': order_id, 'new_completed': new_completed, 'remaining': remaining}
        })
    except Exception as e:
        logger.exception('[sync_bp] /report/actual 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/outsource/publish', methods=['POST'])
def publish_outsource():
    """外协任务发布 — 调容器中心 create_document('outsource', ...)
    ---
    兼容性: 先 try request.json, 再 try request.form (F3 修复)
    Request:
        order_no         (str, 必填)
        process_name     (str, 必填)
        planned_qty      (int, 必填)
        process_seq      (int, 可选, 默认 1)
        outsource_remark (str, 可选)
        operator_id      (str, 可选)
    Response:
        {code: 200, data: {id, message: '外协任务已发布'}}
    """
    try:
        # 兼容 JSON 和 form
        if request.is_json:
            data = request.get_json(force=True, silent=True) or {}
        else:
            data = request.form.to_dict() if request.form else (request.get_json(force=True, silent=True) or {})

        order_no = str(data.get('order_no', '')).strip()
        process_name = str(data.get('process_name', '')).strip()
        planned_qty = data.get('planned_qty', 0)
        process_seq = int(data.get('process_seq', 1) or 1)
        outsource_remark = str(data.get('outsource_remark', '')).strip()
        operator_id = str(data.get('operator_id', '')).strip()

        try:
            planned_qty = int(planned_qty)
        except (TypeError, ValueError):
            return jsonify({'code': 400, 'message': 'planned_qty 必须是数字'}), 400

        if not order_no or not process_name or planned_qty <= 0:
            return jsonify({'code': 400, 'message': 'order_no/process_name/planned_qty 必填且 planned_qty > 0'}), 400

        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500

        pkg = client.create_document(doc_type='outsource', data={
            'order_no': order_no,
            'process_name': process_name,
            'process_seq': process_seq,
            'planned_qty': planned_qty,
            'outsource_remark': outsource_remark,
            'operator_id': operator_id,
            'status': 'pending',
        })
        pkg_id = (pkg or {}).get('id')
        if pkg_id and operator_id:
            try:
                client.distribute(task_id=pkg_id, operator_id=operator_id)
            except Exception as e:
                logger.warning('[sync_bp] /outsource/publish distribute 失败(忽略): %s', e)
        # RE-002 T5: 外协任务发布后触发群消息（失败仅 log，不阻断主业务）
        try:
            from bots.factory import get_factory
            from template_engine import _render_template
            _bot = get_factory().get_group_bot()
            if _bot:
                _msg = _render_template('tmpl_outsource_send', {
                    '外协单号': pkg_id or f'OUT-{order_no}-{process_seq}',
                    '物料名称': process_name,
                    '数量': planned_qty,
                    '供应商': outsource_remark or '待指派',
                    '发出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '预计返回': '待定',
                })
                _bot.send_markdown(_msg)
        except Exception as e:
            logger.warning(f"[sync_bp] /outsource/publish 外协消息发送失败: {e}")
        return jsonify({
            'code': 200,
            'message': '外协任务已发布',
            'data': {'id': pkg_id, 'order_no': order_no, 'process_name': process_name}
        })
    except Exception as e:
        logger.exception('[sync_bp] /outsource/publish 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/delivery-date-change', methods=['POST'])
def delivery_date_change():
    """改交付日期 — 改 order 文档 (按 order_no 对齐)
    ---
    Request:
        order_no           (str, 必填)
        new_delivery_date  (str, 必填, YYYY-MM-DD)
        reason             (str, 可选)
    Response:
        {code: 200, data: {order_no, delivery_date}}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        new_date = str(data.get('new_delivery_date', '')).strip()
        reason = str(data.get('reason', '')).strip()
        if not order_no or not new_date:
            return jsonify({'code': 400, 'message': 'order_no/new_delivery_date 必填'}), 400

        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500

        order = _find_order(client, order_no)
        if not order:
            return jsonify({'code': 404, 'message': f'未找到订单 {order_no}'}), 404

        client.update_document('order', order.get('id'), {
            'delivery_date': new_date,
            'delivery_date_change_reason': reason,
        })
        return jsonify({
            'code': 200,
            'message': '交付日期已更新',
            'data': {'order_no': order_no, 'delivery_date': new_date}
        })
    except Exception as e:
        logger.exception('[sync_bp] /delivery-date-change 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


# ═════════════════════════════════════════════════════════════
#  业务配置类 (6 端点, 内存计算 + 读容器中心)
# ═════════════════════════════════════════════════════════════

@sync_bp.route('/validate/input', methods=['POST'])
def validate_input():
    """订单号格式校验 (F2 修复: 正则 ^ORD-\\d{8,}$)
    ---
    Request:
        order_no   (str, 必填)
        field_name (str, 可选) 字段名描述
    Response:
        {code: 200, data: {valid, normalized, pattern, message}}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        field_name = str(data.get('field_name', 'order_no')).strip()
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no 必填'}), 400
        is_valid = bool(ORDER_NO_PATTERN.match(order_no))
        return jsonify({
            'code': 200 if is_valid else 400,
            'data': {
                'valid': is_valid,
                'normalized': order_no,
                'pattern': ORDER_NO_PATTERN.pattern,
                'field_name': field_name,
                'message': '格式正确' if is_valid else f'订单号必须符合 {ORDER_NO_PATTERN.pattern}',
            }
        }), 200 if is_valid else 400
    except Exception as e:
        logger.exception('[sync_bp] /validate/input 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/task/<order_no>/status', methods=['GET'])
def get_task_status(order_no):
    """工单状态 — 读 order 文档 + 读 operation_logs (F1 依赖)
    ---
    F1 阻塞项: 读 operation_logs.direction='上游' 报工记录
    AC-10: F1 修复前返 500 而非 404
    Path:
        order_no (str) 订单号
    Response:
        {code: 200, data: {order_no, tasks, reports, progress}}
    """
    try:
        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500

        order = _find_order(client, order_no)
        if not order:
            return jsonify({'code': 404, 'message': f'未找到订单 {order_no}'}), 404
        tasks = [order]

        # F1: 读 operation_logs.direction='上游' 报工记录
        reports: List[Dict] = []
        try:
            with _get_mysql_conn() as conn:
                with conn.cursor() as c:
                    c.execute(
                        """SELECT * FROM operation_logs
                           WHERE direction='上游' AND operation_type='报工回调'
                             AND order_no=%s
                           ORDER BY id DESC LIMIT 100""",
                        (order_no,)
                    )
                    reports = list(c.fetchall())
        except Exception as e:
            # F1 阻塞: 捕获并明确标识
            err_msg = str(e)
            if 'direction' in err_msg or "Unknown column" in err_msg:
                logger.warning('[sync_bp][F1] operation_logs.direction 列缺失, 报工记录无法读取: %s', err_msg)
                return jsonify({
                    'code': 500,
                    'message': '[F1 阻塞] operation_logs.direction 列缺失, 需云端执行: '
                               'ALTER TABLE operation_logs ADD COLUMN direction VARCHAR(16) DEFAULT "上游" AFTER id',
                    'f1_required': True,
                }), 500
            raise

        # 计算进度
        total_planned = sum((t.get('content') or {}).get('planned_qty', 0) or 0 for t in tasks)
        total_completed = sum(t.get('completed_qty', 0) or 0 for t in tasks)
        percentage = round(total_completed / total_planned * 100, 2) if total_planned > 0 else 0.0
        return jsonify({
            'code': 200,
            'data': {
                'order_no': order_no,
                'tasks': tasks,
                'reports': reports,
                'progress': {
                    'completed': total_completed,
                    'total': total_planned,
                    'percentage': percentage,
                }
            }
        })
    except Exception as e:
        logger.exception('[sync_bp] /task/<order>/status 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """任务详情 — 容器中心单文档查询
    ---
    Path:
        task_id (str) 任务 ID
    Response:
        {code: 200|404, data: <work_order 文档>}
    """
    try:
        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500
        task = client.get_package(pkg_id=task_id, doc_type='order')
        if not task:
            return jsonify({'code': 404, 'message': f'未找到订单 {task_id}'}), 404
        return jsonify({'code': 200, 'data': task})
    except Exception as e:
        logger.exception('[sync_bp] /tasks/<id> 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/drift/check', methods=['POST'])
def drift_check():
    """漂移检测 — 比对本地和容器中心数据
    ---
    Request:
        order_no (str, 必填)
        fields   (list, 可选) 待比对字段, 默认 ['completed_qty', 'status', 'operator_id']
    Response:
        {code: 200, data: {drift_detected, drifts}}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        fields = data.get('fields') or ['completed_qty', 'status', 'operator_id']
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no 必填'}), 400

        client = _get_container_client()
        if client is None:
            return jsonify({'code': 500, 'message': '容器中心客户端未初始化'}), 500

        order = _find_order(client, order_no)
        remote_tasks = [order] if order else []
        drifts = []
        for t in remote_tasks:
            for f in fields:
                remote_val = t.get(f)
                # 本地无缓存, 仅报告 remote 值 (后续可扩展本地缓存对比)
                drifts.append({
                    'task_id': t.get('id'),
                    'field': f,
                    'remote_value': remote_val,
                    'local_value': None,
                    'drifted': False,  # 无本地对照, 不算 drift
                })
        return jsonify({
            'code': 200,
            'data': {
                'order_no': order_no,
                'drift_detected': False,  # 单边数据暂不报 drift
                'drifts': drifts,
                'note': '当前为单边报告 (容器中心), 本地缓存对比需后续扩展',
            }
        })
    except Exception as e:
        logger.exception('[sync_bp] /drift/check 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/data/fingerprint', methods=['POST'])
def data_fingerprint():
    """数据指纹 — SHA256(订单+工序+数量+时间)
    ---
    Request:
        order_no  (str, 必填)
        fields    (dict, 必填) {step, quantity, operator, timestamp}
    Response:
        {code: 200, data: {fingerprint}}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        fields = data.get('fields') or {}
        if not order_no or not fields:
            return jsonify({'code': 400, 'message': 'order_no/fields 必填'}), 400
        # 规范化: 排序后 JSON 序列化
        canonical = json.dumps(
            {'order_no': order_no, 'fields': fields},
            sort_keys=True, ensure_ascii=False, separators=(',', ':')
        )
        fp = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        return jsonify({
            'code': 200,
            'data': {
                'fingerprint': f'sha256:{fp}',
                'canonical': canonical,
            }
        })
    except Exception as e:
        logger.exception('[sync_bp] /data/fingerprint 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


# ═════════════════════════════════════════════════════════════
#  熔断/队列类 (4 端点, 内存单例)
# ═════════════════════════════════════════════════════════════

class _CircuitBreaker:
    """轻量熔断器 (单例, 线程安全)"""
    def __init__(self, name: str = 'sync_breaker', threshold: int = 5, reset_seconds: int = 60):
        self.name = name
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self.failure_count = 0
        self.state = 'closed'  # closed / open / half-open
        self.last_failure_at: Optional[float] = None
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = 'closed'

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_at = time.time()
            if self.failure_count >= self.threshold:
                self.state = 'open'

    def can_proceed(self) -> bool:
        with self._lock:
            if self.state == 'closed':
                return True
            if self.state == 'open':
                if self.last_failure_at and (time.time() - self.last_failure_at) > self.reset_seconds:
                    self.state = 'half-open'
                    return True
                return False
            return True  # half-open 放行一次

    def reset(self):
        with self._lock:
            self.failure_count = 0
            self.state = 'closed'
            self.last_failure_at = None

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'name': self.name,
                'state': self.state,
                'failure_count': self.failure_count,
                'last_failure_at': (
                    datetime.fromtimestamp(self.last_failure_at).isoformat()
                    if self.last_failure_at else None
                ),
                'threshold': self.threshold,
                'reset_seconds': self.reset_seconds,
            }


_circuit_breaker = _CircuitBreaker()


class _SyncQueue:
    """轻量同步队列 (单例, 线程安全)"""
    def __init__(self):
        self._items: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.enqueued = 0
        self.consumed = 0
        self.failed = 0
        self.retried = 0

    def enqueue(self, item: Dict[str, Any]):
        with self._lock:
            self._items.append({'data': item, 'enqueued_at': time.time()})
            self.enqueued += 1

    def dequeue(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._items:
                return None
            item = self._items.pop(0)
            self.consumed += 1
            return item

    def record_failure(self):
        with self._lock:
            self.failed += 1

    def record_retry(self):
        with self._lock:
            self.retried += 1

    def status(self) -> Dict[str, Any]:
        with self._lock:
            oldest_age = (time.time() - self._items[0]['enqueued_at']) if self._items else 0
            return {
                'size': len(self._items),
                'oldest_age_seconds': round(oldest_age, 2),
            }

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'enqueued': self.enqueued,
                'consumed': self.consumed,
                'failed': self.failed,
                'retried': self.retried,
                'pending': len(self._items),
            }


_sync_queue = _SyncQueue()


@sync_bp.route('/circuit/status', methods=['GET'])
def circuit_status():
    """熔断器状态
    ---
    Response:
        {code: 200, data: {state, failure_count, last_failure_at, ...}}
    """
    return jsonify({'code': 200, 'data': _circuit_breaker.to_dict()})


@sync_bp.route('/circuit/reset', methods=['POST'])
def circuit_reset():
    """熔断器重置
    ---
    Response:
        {code: 200, data: {state: 'closed'}}
    """
    _circuit_breaker.reset()
    return jsonify({'code': 200, 'message': '熔断器已重置', 'data': _circuit_breaker.to_dict()})


@sync_bp.route('/queue/status', methods=['GET'])
def queue_status():
    """队列状态
    ---
    Response:
        {code: 200, data: {size, oldest_age_seconds}}
    """
    return jsonify({'code': 200, 'data': _sync_queue.status()})


@sync_bp.route('/queue/stats', methods=['GET'])
def queue_stats():
    """队列统计
    ---
    Response:
        {code: 200, data: {enqueued, consumed, failed, retried, pending}}
    """
    return jsonify({'code': 200, 'data': _sync_queue.stats()})


# ═════════════════════════════════════════════════════════════
#  读/数据落库类 (4 端点, 走 8008 桥 + 直读 MySQL)
# ═════════════════════════════════════════════════════════════

@sync_bp.route('/reports', methods=['GET'])
def list_reports():
    """报工记录列表 — 直读 MySQL (F1 阻塞, AC-10)
    ---
    Query:
        order_no    (str, 可选)
        operator_id (str, 可选)
        start_date  (str, 可选, YYYY-MM-DD HH:MM:SS)
        end_date    (str, 可选)
        limit       (int, 可选, 默认 50)
    Response:
        {code: 200, data: {items, total}}
    """
    try:
        order_no = request.args.get('order_no', '').strip()
        operator_id = request.args.get('operator_id', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        limit = int(request.args.get('limit', 50) or 50)

        sql = "SELECT * FROM process_sub_steps WHERE 1=1"
        params: List[Any] = []
        if order_no:
            sql += " AND order_no=%s"
            params.append(order_no)
        if operator_id:
            sql += " AND operator=%s"
            params.append(operator_id)
        if start_date:
            sql += " AND created_at>=%s"
            params.append(start_date)
        if end_date:
            sql += " AND created_at<=%s"
            params.append(end_date)
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        with _get_mysql_conn() as conn:
            with conn.cursor() as c:
                c.execute(sql, params)
                items = list(c.fetchall())
        return jsonify({'code': 200, 'data': {'items': items, 'total': len(items)}})
    except Exception as e:
        err_msg = str(e)
        if 'direction' in err_msg or 'Unknown column' in err_msg:
            logger.warning('[sync_bp][F1] /reports 受 direction 列阻塞: %s', err_msg)
            return jsonify({
                'code': 500,
                'message': '[F1 阻塞] operation_logs.direction 列缺失, 需云端修复',
                'f1_required': True,
            }), 500
        logger.exception('[sync_bp] /reports 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/logs', methods=['GET'])
def list_logs():
    """操作日志 — 直读 MySQL operation_logs (F1 必须, AC-10)
    ---
    Query:
        direction      (str, 可选, 默认 '上游')
        operation_type (str, 可选)
        order_no       (str, 可选)
        start_date     (str, 可选)
        end_date       (str, 可选)
        limit          (int, 可选, 默认 50)
    Response:
        {code: 200, data: {items, total}}
    """
    try:
        direction = request.args.get('direction', '上游').strip()
        operation_type = request.args.get('operation_type', '').strip()
        order_no = request.args.get('order_no', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        limit = int(request.args.get('limit', 50) or 50)

        sql = "SELECT * FROM operation_logs WHERE direction=%s"
        params: List[Any] = [direction]
        if operation_type:
            sql += " AND operation_type=%s"
            params.append(operation_type)
        if order_no:
            sql += " AND order_no=%s"
            params.append(order_no)
        if start_date:
            sql += " AND created_at>=%s"
            params.append(start_date)
        if end_date:
            sql += " AND created_at<=%s"
            params.append(end_date)
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        with _get_mysql_conn() as conn:
            with conn.cursor() as c:
                c.execute(sql, params)
                items = list(c.fetchall())
        return jsonify({'code': 200, 'data': {'items': items, 'total': len(items)}})
    except Exception as e:
        err_msg = str(e)
        if 'direction' in err_msg or 'Unknown column' in err_msg:
            logger.warning('[sync_bp][F1] /logs direction 列缺失: %s', err_msg)
            return jsonify({
                'code': 500,
                'message': '[F1 阻塞] operation_logs.direction 列缺失, '
                           '需云端执行: ALTER TABLE operation_logs ADD COLUMN direction VARCHAR(16) DEFAULT "上游" AFTER id',
                'f1_required': True,
            }), 500
        logger.exception('[sync_bp] /logs 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/report/requests', methods=['GET'])
def list_report_requests():
    """报工请求列表 — 直读 MySQL (F1 关联, AC-10)
    ---
    Query:
        status      (str, 可选) pending/confirmed/rejected
        operator_id (str, 可选)
        limit       (int, 可选, 默认 50)
    Response:
        {code: 200, data: {items, total}}
    """
    try:
        status = request.args.get('status', '').strip()
        operator_id = request.args.get('operator_id', '').strip()
        limit = int(request.args.get('limit', 50) or 50)

        sql = "SELECT * FROM report_request WHERE 1=1"
        params: List[Any] = []
        if status:
            sql += " AND status=%s"
            params.append(status)
        if operator_id:
            sql += " AND operator_id=%s"
            params.append(operator_id)
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        with _get_mysql_conn() as conn:
            with conn.cursor() as c:
                c.execute(sql, params)
                items = list(c.fetchall())
        return jsonify({'code': 200, 'data': {'items': items, 'total': len(items)}})
    except Exception as e:
        err_msg = str(e)
        if 'direction' in err_msg or 'Unknown column' in err_msg:
            logger.warning('[sync_bp][F1] /report/requests 受 direction 列阻塞: %s', err_msg)
            return jsonify({
                'code': 500,
                'message': '[F1 阻塞] operation_logs.direction 列缺失, 关联查询失败',
                'f1_required': True,
            }), 500
        logger.exception('[sync_bp] /report/requests 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


@sync_bp.route('/report/confirm', methods=['POST'])
def sync_report_confirm():
    """报工确认收口 — 走 8008 桥 (REQ-4)
    ---
    Request:
        order_no    (str, 必填)
        operator_id (str, 必填)
        confirmed   (bool, 必填)
        remark      (str, 可选)
    Response:
        {code: 200, data: {request_id, confirmed_at, queue_id}}
    Bridge:
        调 bridge.sync_client.send('report-confirm', payload)
        → 8008 /api/sync/report-confirm (TASK-7 新增)
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = str(data.get('order_no', '')).strip()
        operator_id = str(data.get('operator_id', '')).strip()
        confirmed = bool(data.get('confirmed', False))
        remark = str(data.get('remark', '')).strip()
        if not order_no or not operator_id:
            return jsonify({'code': 400, 'message': 'order_no/operator_id 必填'}), 400

        payload = {
            'order_no': order_no,
            'operator_id': operator_id,
            'confirmed': confirmed,
            'remark': remark,
            'timestamp': datetime.now().isoformat(),
        }
        # 走 8008 桥
        try:
            from bridge.sync_client import send
            ok = send('report-confirm', payload, timeout=5)
        except Exception as e:
            logger.exception('[sync_bp] /report/confirm 8008 桥调用失败: %s', e)
            return jsonify({'code': 502, 'message': f'8008 同步桥不可达: {e}'}), 502

        if not ok:
            return jsonify({'code': 502, 'message': '8008 同步桥返回失败'}), 502

        request_id = f"REQ-{order_no}-{int(time.time())}"
        return jsonify({
            'code': 200,
            'message': '报工确认已入队 8008 桥',
            'data': {
                'request_id': request_id,
                'confirmed_at': payload['timestamp'],
                'order_no': order_no,
            }
        })
    except Exception as e:
        logger.exception('[sync_bp] /report/confirm 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500
