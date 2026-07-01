# -*- coding: utf-8 -*-
"""
晨圣报工系统 - 旧版 API 兼容路由
为晨圣报工系统前端页面提供所需的 API 端点
"""
import json
import logging
import os
import uuid
from datetime import datetime, date

import requests
from flask import Blueprint, request, jsonify

from sync.event_bus import EventBus
from core.config import SERVICE_URLS, REQUEST_TIMEOUT, SHORT_TIMEOUT, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
from api.step_status_helper import compute_step_statuses

logger = logging.getLogger(__name__)

bp = Blueprint('legacy', __name__)

_DISPATCH_CENTER_URL = SERVICE_URLS.get('dispatch_center', 'http://127.0.0.1:5003')

def _fetch_material_shortages():
    """从 steel_belt.order_materials 直接查询物料缺料数据（不依赖 5003）"""
    import pymysql
    from pymysql.cursors import DictCursor
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT,
            user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE, charset='utf8mb4',
            connect_timeout=5)
        cur = conn.cursor(DictCursor)
        cur.execute("""
            SELECT om.id, om.order_id, om.material_name, om.spec, om.unit,
                   om.required_qty, om.prepared_qty, om.prep_status,
                   om.warehouse, om.remark, om.created_at, om.updated_at,
                   o.order_no
            FROM order_materials om
            LEFT JOIN orders o ON o.id = om.order_id
            WHERE om.prep_status IN ('待备料', '备料中', '已备料')
            ORDER BY om.created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        records = []
        for r in rows:
            order_no = r.get('order_no') or ''
            material_name = r.get('material_name') or '(未命名)'
            spec = r.get('spec') or ''
            unit = r.get('unit') or ''
            try:
                required_qty = float(r.get('required_qty') or 0)
            except (TypeError, ValueError):
                required_qty = 0.0
            try:
                prepared_qty = float(r.get('prepared_qty') or 0)
            except (TypeError, ValueError):
                prepared_qty = 0.0
            shortage_qty = max(0.0, required_qty - prepared_qty)
            updated = r.get('updated_at') or r.get('created_at')
            if hasattr(updated, 'isoformat'):
                updated = updated.isoformat(sep=' ', timespec='minutes')
            else:
                updated = str(updated or '')
            records.append({
                'order_no': order_no,
                'material_name': material_name,
                'spec': spec,
                'required_qty': required_qty,
                'prepared_qty': prepared_qty,
                'shortage_qty': shortage_qty,
                'unit': unit,
                'updated_at': updated,
                'status': r.get('prep_status', ''),
                'task_id': str(r.get('id', '')),
            })
        return [r for r in records if r['shortage_qty'] > 0]
    except Exception as e:
        logger.warning(f'[物料短缺] 查询 steel_belt 失败: {e}')
        return []

def _clean_step_name(sn):
    idx = sn.rfind(' (')
    if idx > 0 and sn.endswith(')'):
        suffix = sn[idx+2:-1]
        if '/' in suffix:
            parts = suffix.split('/')
            if len(parts) == 2 and all(p.replace('.', '', 1).lstrip('-').isdigit() for p in parts):
                return sn[:idx]
    return sn

class _ContainerCenterHolder:
    _instance = None

    @classmethod
    def get(cls):
        if not cls._instance:
            try:
                from container_center_v5 import ContainerCenter
                cls._instance = ContainerCenter()
                logger.info('legacy_routes 容器中心初始化成功 (MySQL)')
            except Exception as e:
                logger.error(f'legacy_routes 容器中心初始化失败: {e}')
        return cls._instance

def get_cc():
    return _ContainerCenterHolder.get()

def success(data=None, message='success'):
    return jsonify({'code': 0, 'data': data, 'message': message, 'success': True})

def fail(code=1, message='操作失败'):
    return jsonify({'code': code, 'message': message})

@bp.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    try:
        today = date.today().isoformat()
        cc = get_cc()
        if not cc:
            raise RuntimeError('容器中心未初始化')

        records = cc.storage.get_all_process_records()
        total = len(records)
        logger.info('[DEBUG] api_dashboard: 获取到 %s 条process_records', total)
        # [P2 修复 2026-06-18 Bug #11] 老板 KPI 改查 production_orders
        # 修复前: pending/processing/completed 算 process_records (7 条) → 全部接近 0
        # 修复后: 查 production_orders 表 (5 条 status='生产中') + steel_belt.orders (16 条)
        try:
            po_records = cc.storage.get_all_production_orders() or []
            pending = sum(1 for o in po_records if o.get('status') in ('待生产', 'pending'))
            processing = sum(1 for o in po_records if o.get('status') in ('生产中', 'processing'))
            completed = sum(1 for o in po_records if o.get('status') in ('已完成', 'completed'))
        except Exception as e:
            logger.warning('[dashboard] production_orders 查询失败, 回退到 process_records: %s', e)
            pending = sum(1 for o in records if o.get('status') == 'pending')
            processing = sum(1 for o in records if o.get('status') == 'processing')
            completed = sum(1 for o in records if o.get('status') == 'completed')

        all_sub_steps = []
        for rec in records:
            try:
                sub_steps = cc.get_sub_steps(rec.get('order_no', ''))
                logger.info('[DEBUG] api_dashboard: process_id=%s 有 %s 条sub_steps', rec.get('id', ''), len(sub_steps))
                all_sub_steps.extend(sub_steps)
            except Exception as e:
                logger.warning('[DEBUG] api_dashboard: process_id=%s get_sub_steps异常: %s', rec.get('id', ''), e)
        today_reports = sum(1 for s in all_sub_steps if s.get('created_at') and str(s['created_at']).startswith(today))
        logger.info('[DEBUG] api_dashboard: 总计 sub_steps=%s today_reports=%s', len(all_sub_steps), today_reports)

        urgent_orders = []
        expected_orders = []
        shortage_orders = []
        for o in records:
            order_no = o.get('order_no', '') or ''
            product_name = o.get('product_name', '') or ''
            # 从 steps/extra 取规格信息
            spec = o.get('spec', '') or ''
            if not spec:
                steps = o.get('steps')
                if steps and isinstance(steps, list):
                    spec = ' | '.join(s.get('name', '') for s in steps if s.get('name'))
            # 计算该订单的完成进度
            order_sub_steps = [s for s in all_sub_steps if s.get('order_no') == order_no]
            completed_qty = sum(float(s.get('quantity', 0) or 0) for s in order_sub_steps)
            total_qty = float(o.get('quantity', 0) or 0)
            order_entry = {
                # [P1 修复 2026-06-18 Bug #14+#13] 输出层去重
                # 修复前: orderId + order_no 重复 / material=name / spec=product_name 重复
                # 修复后: 只保留 orderId, name, spec, material 各自从不同源
                'orderId': order_no,
                'name': product_name,
                'material': o.get('material') or o.get('material_name') or product_name,
                'spec': spec,  # spec 已修：为空时不再降级为 product_name
                'customer_group': o.get('customer_group', '') or o.get('customer_name', ''),
                'quantity': total_qty,
                'completed_qty': completed_qty,
            }

            if o.get('priority') == 'urgent':
                urgent_orders.append(order_entry)

            delivery = o.get('delivery_date')
            if delivery:
                expected_orders.append({**order_entry, 'deliveryDate': delivery})

        # 从调度中心查询真实物料缺料数据
        material_shortages = _fetch_material_shortages()
        # 按订单号聚合物料缺料信息
        shortage_orders_map = {}
        for ms in material_shortages:
            wo = ms.get('order_no', '')
            if wo not in shortage_orders_map:
                shortage_orders_map[wo] = {
                    'orderId': wo,
                    'order_no': wo,
                    'name': ms.get('material_name', ''),
                    'materials': [],
                    'totalShortage': 0
                }
            shortage_orders_map[wo]['materials'].append({
                'material_name': ms.get('material_name', ''),
                'spec': ms.get('spec', ''),
                'required_qty': ms.get('required_qty', 0),
                'prepared_qty': ms.get('prepared_qty', 0),
                'shortage_qty': ms.get('shortage_qty', 0),
                'unit': ms.get('unit', '件'),
                'updated_at': ms.get('updated_at', ''),
            })
            shortage_orders_map[wo]['totalShortage'] += float(ms.get('shortage_qty', 0))
        shortage_orders = list(shortage_orders_map.values())

        today_sub_steps = [s for s in all_sub_steps if s.get('created_at') and str(s['created_at']).startswith(today)]

        recent_records = []
        for s in today_sub_steps:
            recent_records.append({
                'orderId': s.get('order_no', ''),
                'orderName': '',
                'processName': s.get('step_name', ''),
                'worker': s.get('operator', ''),
                'completedQty': float(s.get('quantity', 0) or 0),
                'workHours': 0,
                'equipmentName': s.get('equipment_name', '') or '',
                'time': s.get('created_at') or '',
                'order_no': s.get('order_no', '') or ''
            })
        recent_records.sort(key=lambda r: r['orderId'])

        attendance_list = cc.get_attendance_by_date(today)
        today_checkins = sum(1 for a in attendance_list if a.get('status') == '已签到')

        return jsonify({
            'totalOrders': total,
            'pendingOrders': pending,
            'processingOrders': processing,
            'completedOrders': completed,
            'todayCheckins': today_checkins,
            'todayReports': today_reports,
            'urgentOrders': urgent_orders,
            'expectedOrders': expected_orders,
            'materialShortageOrders': shortage_orders,
            'recentRecords': recent_records
        })
    except Exception as e:
        logger.exception(f'获取看板数据异常: {e}')
        return jsonify({
            'totalOrders': 0, 'pendingOrders': 0, 'processingOrders': 0,
            'completedOrders': 0, 'todayCheckins': 0, 'todayReports': 0,
            'urgentOrders': [], 'expectedOrders': [], 'materialShortageOrders': [],
            'recentRecords': []
        })

# [P2 修复 2026-06-18 Bug #10] 增加 POST 方法支持
# 修复前: methods=['GET'] → POST 返回 405
# 修复后: GET + POST 都支持（前端 fetch 默认 GET, 部分旧代码用 POST）
@bp.route('/api/scan-info', methods=['GET', 'POST'])
def api_scan_info():
    # [P2 修复 2026-06-18 Bug #10] 兼容 GET (?code=X) 和 POST (form/code body)
    if request.method == 'POST':
        code = (request.form.get('code') or request.json.get('code') if request.is_json else request.form.get('code') or '').strip()
        if not code and request.is_json:
            try:
                code = (request.json.get('code') or '').strip()
            except Exception:
                code = ''
    else:
        code = request.args.get('code', '').strip()
    if not code:
        return fail(message='缺少参数: code')
    try:
        cc = get_cc()
        if not cc:
            return fail(message='容器中心未初始化')
        records = cc.storage.get_process_records(search=code, limit=50)
        if not records:
            return _scan_info_fallback(code)
        main_rec = None
        for rec in records:
            steps = rec.get('steps', []) or []
            if isinstance(steps, str):
                try:
                    steps = json.loads(steps)
                except (json.JSONDecodeError, TypeError):
                    steps = []
            if steps:
                main_rec = rec
                break
        if not main_rec:
            main_rec = records[0]
        steps_list = main_rec.get('steps', []) or []
        if isinstance(steps_list, str):
            try:
                steps_list = json.loads(steps_list)
            except (json.JSONDecodeError, TypeError):
                steps_list = []
        all_sub_steps = cc.get_sub_steps(main_rec['order_no'])
        sub_step_qty_map = {}
        sub_step_completed_map = {}  # [2026-06-15 BUG修复] 用 completed_qty 算总进度
        sub_step_latest_map = {}
        for ss in all_sub_steps:
            sn = _clean_step_name(ss.get('step_name', ''))
            qty = ss.get('quantity', 0) or 0
            completed = ss.get('completed_qty', 0) or 0
            sub_step_qty_map[sn] = sub_step_qty_map.get(sn, 0) + qty
            sub_step_completed_map[sn] = sub_step_completed_map.get(sn, 0) + completed
            sub_step_latest_map[sn] = ss
        step_idx = int(main_rec.get('current_step', 0))
        required_qty = float(main_rec.get('quantity', 0) or 0)
        # [2026-06-15 BUG深度修复] 总体进度 = 所有工序完成率的平均数 × required_qty
        # 旧公式错用 quantity(预期量) 导致没报工也显示进度（截图 89/366 错误）
        # 新公式：每个工序的完成率 = min(1.0, completed_qty / required_qty)
        #        所有工序的完成率取平均，再 × required_qty 得到总完成量
        if sub_step_completed_map and required_qty > 0:
            pcts = [min(1.0, cq / required_qty) for cq in sub_step_completed_map.values()]
            total_completed_qty = round((sum(pcts) / len(pcts)) * required_qty)
        else:
            total_completed_qty = 0
        # 统一状态计算（手机端 / 桌面端 / dispatch_center 共用真值源）
        statuses = compute_step_statuses(
            steps_list=steps_list,
            sub_step_qty_map=sub_step_qty_map,
            current_step=step_idx,
            required_qty=required_qty,
            sub_step_latest_map=sub_step_latest_map,
        )
        processes = []
        for i, step_item in enumerate(steps_list):
            step_name = step_item.get('name', str(step_item)) if isinstance(step_item, dict) else str(step_item)
            role = step_item.get('role', '') if isinstance(step_item, dict) else ''
            status_key = step_item.get('status_key', '') if isinstance(step_item, dict) else ''
            st = statuses[i]
            # [2026-06-15] 从 sub_step_latest_map 取 process_code（按工序名匹配）
            matched_pc = ''
            for k, v in sub_step_latest_map.items():
                if _clean_step_name(v.get('step_name', '')) == step_name:
                    matched_pc = v.get('process_code', '') or ''
                    break
            processes.append({
                'process_id': main_rec['order_no'],
                'process_name': step_name,
                'step_name': step_name,
                'process_code': matched_pc,  # [2026-06-15] 添加 process_code
                'role': role,
                'status_key': status_key,
                'step_index': i,
                'is_current': st['is_current'],
                'is_completed': st['is_completed'],
                'required_qty': float(required_qty),
                'completed_qty': round(float(st['completed_qty'])),
                'remaining_qty': float(st['remaining_qty']),
                'unit': main_rec.get('unit', ''),
                'status': st['status'],
                'last_report_operator': st['last_report_operator'],
                'last_report_time': st['last_report_time'],
                'last_report_qty': st['last_report_qty'],
            })
        tasks = _build_tasks_from_packages(cc, code, required_qty, alt_code=main_rec.get('order_no', ''))

        # [2026-06-15] sub_step_summary 按 process_code 升序排序
        import re as _re_summary
        def _summary_sort_key(item):
            latest = item[1] or {}
            code = latest.get('process_code', '') if isinstance(latest, dict) else ''
            m = _re_summary.match(r'^([A-Za-z]+)(\d+)?$', code)
            if m:
                return (m.group(1), int(m.group(2)) if m.group(2) else 0)
            return ('Z', 0)
        sub_step_summary = [
            {'step_name': k, 'total_qty': v, 'latest_record': sub_step_latest_map.get(k)}
            for k, v in sorted(sub_step_qty_map.items(), key=_summary_sort_key)
        ]

        return success({
            'code': code,
            'order_no': main_rec.get('order_no', ''),
            'customer_name': main_rec.get('customer_name', ''),
            'product_name': main_rec.get('product_name', ''),
            'quantity': required_qty,
            'unit': main_rec.get('unit', ''),
            'delivery_date': main_rec.get('delivery_date', ''),
            'priority': main_rec.get('priority', ''),
            'current_step_index': step_idx,
            'total_completed_qty': round(float(total_completed_qty)),
            'total_remaining_qty': max(0.0, float(required_qty) - round(float(total_completed_qty))),
            'processes': processes,
            'tasks': tasks,
            'sub_step_summary': sub_step_summary,
        })
    except Exception as e:
        logger.exception(f'扫码查询异常: {e}')
        return _scan_info_fallback(code)


def _build_tasks_from_packages(cc, code, default_quantity, alt_code=None):
    packages = []
    try:
        packages = cc.storage.get_packages(related_order=code, limit=200)
        if not packages and alt_code:
            packages = cc.storage.get_packages(related_order=alt_code, limit=200)
    except Exception as e:
        logger.warning(f'查询 data_packages 失败(非致命): {e}')
        return []

    tasks = []
    for pkg in packages:
        content = pkg.get('content', {}) or {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {}
        # [2026-06-15] 过滤：工序任务窗口只显示 P 编号（生产工序）
        # 物料 (M 开头) → 物料任务窗口；质检/外协 → 对应窗口
        pc = pkg.get('process_code', '') or ''
        if pc:
            try:
                from mobile_api_ai.core.process_code_classifier import is_production_code
                if not is_production_code(pc):
                    continue  # 跳过物料/质检/入库等非生产类任务
            except ImportError:
                pass
        qty = content.get('quantity', 0) or content.get('target_qty', 0) or default_quantity
        is_public_raw = pkg.get('is_public', 0)
        if isinstance(is_public_raw, bool):
            is_public_int = 1 if is_public_raw else 0
        elif isinstance(is_public_raw, (int, float)):
            is_public_int = 1 if is_public_raw else 0
        elif isinstance(is_public_raw, str):
            is_public_int = 1 if is_public_raw.strip() == '1' else 0
        else:
            is_public_int = 0
        tasks.append({
            'task_id': pkg.get('id', ''),
            'operator': pkg.get('target_operator', '') or '全员',
            'is_public': is_public_int,
            'process_name': pkg.get('related_process', '') or pkg.get('title', ''),
            'process_code': pc,
            'quantity': qty,
            'unit': content.get('unit', ''),
            'completed_qty': pkg.get('completed_qty', 0) or content.get('completed_qty', 0),
            'status': pkg.get('status', ''),
            'created_at': pkg.get('created_at', ''),
            'equipment_name': content.get('equipment_name', ''),
        })
    # [2026-06-15] 按 process_code 编号升序排序
    import re as _re_task
    def _task_sort_key(t):
        code = t.get('process_code', '') or ''
        m = _re_task.match(r'^([A-Za-z]+)(\d+)?$', code)
        if m:
            return (m.group(1), int(m.group(2)) if m.group(2) else 0)
        return ('Z', 0)
    tasks.sort(key=_task_sort_key)
    return tasks


def _scan_info_fallback(code):
    try:
        cc = get_cc()
        if not cc:
            return fail(message='容器中心未初始化')
        records = cc.storage.get_process_records(search=code, limit=20)
        main_rec = None
        code_upper = code.upper()
        is_order_no_query = code_upper.startswith('ORD')
        for rec in records:
            wo = (rec.get('order_no', '') or '').strip()
            on = (rec.get('order_no', '') or '').strip()
            if is_order_no_query:
                if on and on.upper() == code_upper:
                    main_rec = rec
                    break
            else:
                if code_upper in wo.upper():
                    main_rec = rec
                    break
        if not main_rec:
            return fail(code=404, message=f'未找到工单 [{code}]')
        steps_list = main_rec.get('steps', []) or []
        if isinstance(steps_list, str):
            try:
                steps_list = json.loads(steps_list)
            except (json.JSONDecodeError, TypeError):
                steps_list = []
        if not steps_list:
            return fail(code=404, message=f'工单 [{code}] 无工序定义')
        sub_steps = cc.get_sub_steps(main_rec['order_no'])
        default_quantity = float(main_rec.get('quantity', 1000) or 1000)
        # 兜底分支同样走统一真值源（修问题 B：不再硬编码 is_current=(i==0)）
        fb_qty_map = {}
        fb_latest_map = {}
        for s in sub_steps:
            sn = _clean_step_name(s.get('step_name', ''))
            q = float(s.get('quantity', 0) or 0)
            fb_qty_map[sn] = fb_qty_map.get(sn, 0) + q
            fb_latest_map[sn] = s
        fb_statuses = compute_step_statuses(
            steps_list=steps_list,
            sub_step_qty_map=fb_qty_map,
            current_step=0,
            required_qty=default_quantity,
            sub_step_latest_map=fb_latest_map,
        )
        process_list = []
        for i, step_item in enumerate(steps_list):
            step_name = step_item.get('name', str(step_item)) if isinstance(step_item, dict) else str(step_item)
            st = fb_statuses[i]
            process_list.append({
                'process_id': main_rec['order_no'],
                'process_name': step_name,
                'step_name': step_name,
                'step_index': i,
                'is_current': st['is_current'],
                'is_completed': st['is_completed'],
                'required_qty': default_quantity,
                'completed_qty': st['completed_qty'],
                'remaining_qty': st['remaining_qty'],
                'unit': main_rec.get('unit', '件'),
                'status': st['status'],
                'last_report_operator': st['last_report_operator'],
                'last_report_time': st['last_report_time'],
                'last_report_qty': st['last_report_qty'],
            })
        fallback_tasks = _build_tasks_from_packages(cc, code, default_quantity)
        fallback_total_rate = sum(min(p['completed_qty'] / p['required_qty'], 1.0) if p['required_qty'] > 0 else 0 for p in process_list)
        fallback_avg_rate = fallback_total_rate / len(process_list) if process_list else 0
        fallback_avg_completed = round(fallback_avg_rate * default_quantity) if default_quantity > 0 else 0
        return success({
            'code': code,
            'order_no': main_rec.get('order_no', ''),
            'customer_name': main_rec.get('customer_name', ''),
            'product_name': main_rec.get('product_name', ''),
            'quantity': default_quantity,
            'unit': main_rec.get('unit', '件'),
            'delivery_date': main_rec.get('delivery_date', '') or '',
            'priority': main_rec.get('priority', ''),
            'current_step_index': 0,
            'total_completed_qty': fallback_avg_completed,
            'total_remaining_qty': max(0, default_quantity - fallback_avg_completed),
            'processes': process_list,
            'tasks': fallback_tasks,
        })
    except Exception as e:
        logger.exception(f'scan-info fallback 异常: {e}')
        return fail(message=f'查询失败: {e}')

@bp.route('/api/quality', methods=['POST'])
def api_submit_quality():
    try:
        data = request.get_json()
        if not data:
            return fail(message='请求数据为空')
        cc = get_cc()
        if not cc:
            return fail(message='容器中心未初始化')
        order_no = data.get('orderNo', '') or data.get('order_no', '')
        order_id = data.get('orderId', 0) or data.get('order_id', 0)
        inspector = data.get('inspector', '') or data.get('inspector_id', '')
        inspection_type = data.get('inspectionType', '') or data.get('inspection_type', '巡检')
        result = data.get('result', 'pass')
        defect_desc = data.get('defectDescription', '') or data.get('defect_description', '')
        inspection_items = data.get('inspectionItems', []) or data.get('inspection_items', [])
        pkg = cc.collect_quality(
            order_no=order_no,
            order_id=int(order_id) if order_id else 0,
            inspector_id=inspector,
            inspection_type=inspection_type
        )
        pkg.content.update({
            'result': result,
            'defect_description': defect_desc,
            'inspection_items': inspection_items,
            'created_at': datetime.now().isoformat()
        })
        logger.info('质检提交成功: 工单=%s 类型=%s 结果=%s', order_no, inspection_type, result)
        return success({'package_id': pkg.id}, '质检提交成功')
    except Exception as e:
        logger.exception(f'质检提交异常: {e}')
        return fail(message=f'质检提交失败: {e}')

@bp.route('/api/quality', methods=['GET'])
def api_get_quality():
    try:
        cc = get_cc()
        if not cc:
            return jsonify({'code': 0, 'data': [], 'message': '操作成功'})
        order_no = request.args.get('orderNo', '') or request.args.get('order_no', '')
        packages = cc.storage.get_packages(data_type='quality_task', limit=200)
        if order_no:
            packages = [p for p in packages if p.get('related_order', '') == order_no]
        records = []
        for pkg in packages:
            content = pkg.get('content', {}) or {}
            if isinstance(content, str):
                try: content = json.loads(content)
                except Exception: content = {}
            records.append({
                'id': pkg.get('package_id', ''),
                'result': content.get('result', 'pass'),
                'orderId': pkg.get('related_order', ''),
                'order_no': pkg.get('related_order', ''),
                'orderName': content.get('order_name', ''),
                'inspectionType': content.get('inspection_type', ''),
                'inspectionItems': content.get('inspection_items', []),
                'defectDescription': content.get('defect_description', ''),
                'inspector': pkg.get('operator_id', ''),
                'recordDate': pkg.get('created_at', '') or pkg.get('timestamp', '')
            })
        records.reverse()
        return jsonify({'code': 0, 'data': records, 'message': '操作成功'})
    except Exception as e:
        logger.exception(f'获取质检记录异常: {e}')
        return jsonify({'code': 0, 'data': [], 'message': '操作成功'})

def _get_sub_steps(order_no=None, step_name=None, limit=200):
    result = []
    try:
        cc = get_cc()
        if not cc:
            return result
        records = cc.storage.get_all_process_records()
        logger.info('[DEBUG] _get_sub_steps: process_records=%s条 filter_order_no=%s', len(records), order_no)
        for rec in records:
            if order_no and rec.get('order_no') != order_no:
                continue
            try:
                sub_steps = cc.get_sub_steps(rec.get('order_no', ''))
                logger.info('[DEBUG] _get_sub_steps: process_id=%s order_no=%s sub_steps=%s条',
                             rec.get('id', ''), rec.get('order_no', ''), len(sub_steps))
            except Exception as e:
                logger.warning('[DEBUG] _get_sub_steps: process_id=%s异常: %s', rec.get('id', ''), e)
                continue
            for s in sub_steps:
                if step_name and s.get('step_name') != step_name:
                    continue
                result.append(s)
        result.sort(key=lambda x: str(x.get('created_at', '') or ''), reverse=True)
        logger.info('[DEBUG] _get_sub_steps: 最终返回 %s 条', len(result))
        return result[:limit]
    except Exception as e:
        logger.exception('[DEBUG] _get_sub_steps异常: %s', e)
        return result

@bp.route('/api/sub_step_records', methods=['GET'])
def api_get_sub_step_records():
    try:
        order_no = request.args.get('order_no', '') or request.args.get('orderNo', '')
        step_name = request.args.get('step_name', '')

        rows = _get_sub_steps(order_no=order_no, step_name=step_name)
        result = []
        for s in rows:
            result.append({
                'orderId': s.get('order_no', ''),
                'order_no': s.get('order_no', ''),
                'orderName': '',
                'processName': s.get('step_name', ''),
                'status': '',
                'worker': s.get('operator', ''),
                'completedQty': float(s.get('quantity', 0) or 0),
                'workHours': 0,
                'time': s.get('created_at') or '',
                'remark': s.get('remark', ''),
                'equipmentName': s.get('equipment_name', '') or ''
            })
        return jsonify({'code': 0, 'data': result, 'message': '操作成功'})
    except Exception as e:
        logger.exception(f'获取子步骤记录异常: {e}')
        return jsonify({'code': 0, 'data': [], 'message': '操作成功'})

_STATUS_MAP = {
    'pending': '待处理',
    'processing': '进行中',
    'completed': '已完成',
    'cancelled': '已取消',
}

def _fetch_unpublished_tasks(cc, published_order_nos):
    """获取已创建但未排产的任务列表（过渡可见性）"""
    try:
        tasks = cc.get_all_tasks(limit=500)
        if not tasks:
            return []
        result = []
        for t in tasks:
            order_no = t.get('order_no', '') or t.get('related_order', '')
            if not order_no:
                continue
            if order_no in published_order_nos:
                continue
            result.append({
                'workOrderNo': order_no,
                'orderName': t.get('product_name', t.get('name', '待排产任务')),
                'material': '',
                'spec': '',
                'assignedTo': '',
                'status': '待排产',
                'planStart': '',
                'planEnd': '',
                'isPendingTask': True
            })
        return result
    except Exception as e:
        logger.warning(f'[待排产] 获取未排产任务失败: {e}')
        return []


@bp.route('/api/production-orders', methods=['GET'])
def api_get_production_orders():
    try:
        cc = get_cc()
        logger.warning(f'[DEBUG] get_cc() = {type(cc).__name__}, storage={type(getattr(cc, "storage", None)).__name__ if cc else None}')
        if not cc:
            return jsonify({'code': 0, 'data': [], 'message': '操作成功'})
        if not hasattr(cc, 'storage') or cc.storage is None:
            logger.warning('[DEBUG] cc.storage is None, returning []')
            return jsonify({'code': 0, 'data': [], 'message': '操作成功'})

        try:
            raw = cc.storage.get_all_process_records()
            logger.warning(f'[DEBUG] get_all_process_records returned type={type(raw).__name__}, len={len(raw) if isinstance(raw, list) else "N/A"}')
            if raw is not None and not isinstance(raw, list):
                logger.warning(f'[DEBUG] records is not list, converting')
                raw = []
            records = raw if isinstance(raw, list) else []
        except Exception as e:
            logger.warning(f'[DEBUG] get_all_process_records failed: {e}')
            records = []

        operator_map = {}
        broadcast_orders = set()
        try:
            raw_pkgs = cc.storage.get_packages(limit=5000)
            packages = raw_pkgs if isinstance(raw_pkgs, list) else []
            logger.warning(f'[DEBUG] get_packages returned type={type(raw_pkgs).__name__}, len={len(packages)}')
            for pkg in packages:
                if not isinstance(pkg, dict):
                    logger.warning(f'[DEBUG] pkg is {type(pkg).__name__}, skipping')
                    continue
                ono = pkg.get('related_order', '')
                op = pkg.get('target_operator', '') or ''
                if pkg.get('is_public'):
                    broadcast_orders.add(ono)
                if ono and op:
                    operator_map[ono] = op
        except Exception as e:
            logger.warning(f'[DEBUG] get_packages failed: {e}')

        published_nos = set()
        result = []
        # [P1 修复 2026-06-18 Bug #6] 批量预查 production_orders
        # 修复前: material/spec/planStart/flowType/assignedTo 全部硬编码空字符串
        # 修复后: 批量 JOIN production_orders 表补全字段
        po_map = {}
        try:
            po_records = cc.storage.get_all_production_orders(limit=5000) or []
            for po in po_records:
                key = po.get('order_no', '') or ''
                if key:
                    po_map[key] = po
        except Exception as e:
            logger.warning('[production-orders] 批量查 production_orders 失败: %s', e)
        for o in records:
            if not isinstance(o, dict):
                logger.warning(f'[DEBUG] record is {type(o).__name__}, skipping')
                continue
            eng_status = o.get('status', 'pending')
            order_no = o.get('order_no', '')
            if order_no:
                published_nos.add(order_no)
            # [P1 修复 2026-06-18 Bug #6] 补字段
            # 数据源真实情况 (2026-06-18 验证):
            # - production_orders 表: 5 条, 无 material/spec/flow_type 字段
            # - steel_belt.orders 表: 16 条, 无 material/spec 字段
            # - data_packages 旧方案: title/content 字段不存在 → 500
            # 修复策略: 接受 material/spec 字段为 None, 由前端 fallback 到 product_name
            po = po_map.get(order_no, {})
            product_name = o.get('product_name', '') or po.get('order_no', '')
            result.append({
                'workOrderNo': order_no,
                'orderName': product_name,
                'material': po.get('material') or po.get('material_name') or '',
                'spec': po.get('spec', '') or '',
                'assignedTo': operator_map.get(order_no, '') or po.get('assigned_to', ''),
                'isPublic': order_no in broadcast_orders,
                'flowType': o.get('flow_type', '') or po.get('flow_type', ''),
                'status': _STATUS_MAP.get(eng_status, eng_status),
                'planStart': po.get('plan_start', '') or '',
                'planEnd': po.get('plan_end', '') or o.get('delivery_date', '') or ''
            })
        pending = _fetch_unpublished_tasks(cc, published_nos)
        result.extend(pending)
        return jsonify({'code': 0, 'data': result, 'message': '操作成功'})
    except Exception as e:
        logger.exception(f'获取生产工单异常: {e}')
        return jsonify({'code': 0, 'data': [], 'message': '操作成功'})

@bp.route('/api/workers', methods=['GET'])
def api_get_workers():
    try:
        cc = get_cc()
        if not cc:
            return jsonify({'code': 0, 'data': [], 'message': '操作成功'})
        rows = cc.get_all_workers()
        seen = set()
        result = []
        for r in rows:
            name = r.get('name', '') or r.get('username', '')
            if name and name not in seen:
                seen.add(name)
                result.append({
                    'name': name,
                    'username': r.get('username', ''),
                    'role': r.get('role', '操作员'),
                    'createdAt': r.get('created_at', '')
                })
        structure = cc.load_enterprise_structure()
        if structure:
            for u in structure.get('users', []):
                name = u.get('name', '')
                userid = u.get('userid', '')
                if name and name not in seen:
                    seen.add(name)
                    result.append({
                        'name': name,
                        'username': userid,
                        'role': '操作员',
                        'createdAt': ''
                    })
        return jsonify({'code': 0, 'data': result, 'message': '操作成功'})
    except Exception as e:
        logger.exception(f'获取工人列表异常: {e}')
        return jsonify({'code': 0, 'data': [], 'message': '操作成功'})

@bp.route('/api/attendance/<username>', methods=['GET'])
def api_get_attendance(username):
    now = datetime.now()
    today_key = now.strftime('%Y-%m-%d')
    try:
        cc = get_cc()
        r = cc.get_attendance(username, today_key) if cc else None
        if r:
            return jsonify({
                'checkIn': r.get('check_in', ''),
                'checkOut': r.get('check_out', ''),
                'status': r.get('status', '未签到'),
                'date': today_key
            })
    except Exception:
        pass
    return jsonify({
        'checkIn': '',
        'checkOut': '',
        'status': '未签到',
        'date': today_key
    })

@bp.route('/api/attendance', methods=['GET'])
def api_list_attendance():
    now = datetime.now()
    today_key = now.strftime('%Y-%m-%d')
    try:
        cc = get_cc()
        rows = cc.get_attendance_by_date(today_key) if cc else []
    except Exception:
        rows = []
    results = []
    for r in rows:
        results.append({
            'worker': r.get('worker', ''),
            'checkIn': r.get('check_in', ''),
            'checkOut': r.get('check_out', ''),
            'status': r.get('status', '未签到'),
            'date': today_key
        })
    return jsonify(results)

@bp.route('/api/attendance', methods=['POST'])
def api_post_attendance():
    try:
        data = request.get_json() if request.is_json else request.form
        if not data:
            return fail(message='请求数据为空')
        worker = data.get('worker', '') or data.get('username', '')
        action = data.get('action', '')
        if not worker or not action:
            return fail(message='参数不完整: worker, action 必填')
        now = datetime.now()
        today_key = now.strftime('%Y-%m-%d')
        cc = get_cc()
        if action in ('check-in', 'checkin'):
            if cc:
                cc.upsert_attendance(worker, today_key, check_in=now.strftime('%H:%M'), status='已签到')
            logger.info('签到: %s %s', worker, now.isoformat())
            EventBus.get().publish('attendance.created', {
                'worker': worker, 'date': today_key,
                'check_in': now.strftime('%H:%M'), 'status': '已签到', 'action': 'check-in'
            })
            return jsonify({'code': 0, 'action': 'check-in', 'time': now.strftime('%H:%M'), 'message': '签到成功'})
        elif action in ('check-out', 'checkout'):
            if cc:
                cc.upsert_attendance(worker, today_key, check_out=now.strftime('%H:%M'), status='已签退')
            logger.info('签退: %s %s', worker, now.isoformat())
            EventBus.get().publish('attendance.updated', {
                'worker': worker, 'date': today_key,
                'check_out': now.strftime('%H:%M'), 'status': '已签退', 'action': 'check-out'
            })
            return jsonify({'code': 0, 'action': 'check-out', 'time': now.strftime('%H:%M'), 'message': '签退成功'})
        else:
            return fail(message=f'未知操作: {action}')
    except Exception as e:
        logger.exception(f'签到操作异常: {e}')
        return fail(message=f'签到操作失败: {e}')

@bp.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json() if request.is_json else request.form
        if not data:
            return fail(message='请求数据为空')
        username = data.get('username', '').strip()
        if not username:
            return fail(message='请输入人员名称')
        cc = get_cc()
        if not cc:
            return fail(message='服务未初始化')
        worker = cc.get_worker_by_name(username)
        if not worker:
            return fail(code=404, message=f'未找到操作员 [{username}]')
        if worker.get('status') == 'inactive':
            logger.warning('操作员已禁用, 拒登: %s', username)
            return fail(code=403, message=f'操作员 [{username}] 已禁用')
        logger.info('登录成功: %s', worker.get('name', username))
        return success({
            'username': worker.get('enterprise_id', ''),
            'name': worker.get('name', worker.get('enterprise_id', '')),
            'role': worker.get('role', '操作员'),
            'createdAt': worker.get('created_at', '')
        }, '登录成功')
    except Exception as e:
        logger.exception(f'登录异常: {e}')
        return fail(message=f'登录失败: {e}')



