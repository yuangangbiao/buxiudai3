# -*- coding: utf-8 -*-
"""
调度中心管理员记录管理 API

包含:
- report_record: 报工记录（list/update/withdraw/history_full）
- quality_record: 质检记录（list/update/withdraw/history_full）
- material_record: 物料记录（list/update/withdraw/history_full）
- outsource_record: 外协记录（list/update/withdraw/history_full）
- schedule_record: 排产记录（list/update/withdraw/history_full）

所有写操作接口均需管理员/操作员 JWT 认证 + 每分钟 10 次频率限制

[Phase 1 Refactor] 所有 pymysql.connect() 直连 → MySQLStorage.get_connection()
连接池复用，autocommit=False（与 pymysql.connect 默认行为一致）。
"""
from flask import Blueprint, request, jsonify
import json
import logging

from .decorators import require_admin
from .limiter import limiter
from storage.mysql_storage import MySQLStorage

logger = logging.getLogger(__name__)
bp = Blueprint('report_record_admin', __name__, url_prefix='/api')


def _sync_completed_qty_to_package(order_no, step_name, cur):
    """[v3.8.1] 重算并回写 completed_qty 到 process_sub_steps（SSOT）
    
    修复前: UPDATE process_sub_steps.completed_qty（死代码，无读者）
    修复后: UPDATE process_sub_steps.completed_qty（前端展示唯一真值源）
    """
    try:
        cur.execute(
            "SELECT COALESCE(SUM(quantity),0) FROM process_sub_steps "
            "WHERE order_no=%s AND step_name=%s AND quantity>0",
            (order_no, step_name))
        row = cur.fetchone()
        total = float(row[0] or 0) if row else 0
        cur.execute(
            "UPDATE process_sub_steps SET completed_qty=%s "
            "WHERE order_no=%s AND step_name=%s",
            (total, order_no, step_name))
        return total
    except Exception as e:
        logger.warning('_sync_completed_qty_to_package 失败: order=%s step=%s err=%s',
                       order_no, step_name, type(e).__name__)
        return None


# ─── report_record ────────────────────────────────────────────────────────────

@bp.route('/report_record/list', methods=['GET'])
def report_record_list():
    try:
        order_no = request.args.get('order_no', '').strip()
        step_name = request.args.get('step_name', '').strip()
        operator = request.args.get('operator', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(100, max(10, int(request.args.get('page_size', 20))))
        where = ["s.quantity > 0"]
        params = []
        if order_no:
            where.append("s.order_no LIKE %s"); params.append(f"%{order_no}%")
        if step_name:
            where.append("s.step_name LIKE %s"); params.append(f"%{step_name}%")
        if operator:
            where.append("s.operator LIKE %s"); params.append(f"%{operator}%")
        if start_date:
            where.append("s.created_at >= %s"); params.append(start_date)
        if end_date:
            where.append("s.created_at <= %s"); params.append(end_date)
        where_sql = " AND ".join(where)
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM process_sub_steps s WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT s.id, s.order_no, s.step_name, s.quantity, s.operator, s.batch_no, s.created_at "
                f"FROM process_sub_steps s WHERE {where_sql} ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        logging.getLogger('report_record_list').exception('查询失败')
        return jsonify({'code': 500, 'message': '查询失败'}), 500


@bp.route('/report_record/update', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def report_record_update():
    body = request.get_json(silent=True) or {}
    sub_step_id = body.get('sub_step_id')
    new_quantity = body.get('new_quantity')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_force')
    remark = body.get('remark', '').strip()
    confirm = body.get('confirm', 0)
    if not sub_step_id or new_quantity is None or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    try:
        new_quantity = float(new_quantity)
    except (ValueError, TypeError):
        return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM process_sub_steps WHERE id=%s FOR UPDATE", (sub_step_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_qty = float(existing.get('quantity', 0) or 0)
        if abs(old_qty - new_quantity) < 0.001:
            conn.rollback(); conn.close()
            return jsonify({'code': 0, 'message': '无变化', 'unchanged': True})
        order_no = existing.get('order_no', '')
        step_name = existing.get('step_name', '')
        batch_no = existing.get('batch_no') or ''
        old_operator = existing.get('operator', '')
        try:
            cur.execute("SELECT quantity FROM process_records WHERE order_no=%s LIMIT 1", (order_no,))
            pr = cur.fetchone()
            order_req = float(pr[0]) if pr else 0
            cur.execute(
                "SELECT SUM(quantity) FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND quantity > 0 AND id<>%s",
                (order_no, step_name, sub_step_id))
            sum_row = cur.fetchone()
            cur_sum = float(sum_row[0] or 0) if sum_row else 0
            if order_req and cur_sum + new_quantity - old_qty > order_req:
                if not confirm:
                    conn.rollback(); conn.close()
                    return jsonify({
                        'code': 300,
                        'message': f'修改后总数量 ({cur_sum + new_quantity - old_qty:.2f}) 超过订单需求 ({order_req:.2f})，请确认',
                        'action': 'prompt',
                        'context': {'current_sum': cur_sum, 'old_qty': old_qty, 'new_qty': new_quantity, 'order_req': order_req}
                    })
        except Exception:
            pass
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE process_sub_steps SET quantity=%s WHERE id=%s", (new_quantity, sub_step_id))
            cur.execute(
                "INSERT INTO process_sub_steps_history (original_id, order_no, step_name, batch_no, operator_before, operator_after, old_quantity, new_quantity, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (sub_step_id, order_no, step_name, batch_no,
                 old_operator, admin_user, old_qty, new_quantity, reason, admin_user))
            cur.execute("UPDATE process_records SET last_reverted_at=NOW() WHERE order_no=%s", (order_no,))
            _sync_completed_qty_to_package(order_no, step_name, cur)
            cur.execute("COMMIT")
            logger.info('[RE-001] sub-steps 修正宽边界 OK: order=%s step=%s qty=%s', order_no, step_name, new_quantity)
        except Exception as e:
            conn.rollback()
            logger.error('[RE-001] sub-steps 修正宽边界回滚: order=%s err=%s', order_no, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        try:
            from notify import notify_admin_modified
            notify_admin_modified(original_operator=old_operator, admin_user=admin_user,
                order_no=order_no, step_name=step_name, old_qty=old_qty, new_qty=new_quantity, remark=remark)
        except Exception as e:
            logging.getLogger('report_record_update').warning(f'通知推送失败: {e}')
        try:
            from bridge.sync_client import send as sync_send
            sync_send('sub-step-report', {'order_no': order_no, 'step_name': step_name,
                                          'quantity': new_quantity - old_qty, 'operator': admin_user})
        except Exception as e:
            logging.getLogger('report_record_update').warning(f'8008同步失败: {e}')
        return jsonify({'code': 0, 'message': f'已修改 {old_qty} → {new_quantity}', 'success': True})
    except Exception as e:
        logging.getLogger('report_record_update').exception('修改失败')
        return jsonify({'code': 500, 'message': '修改失败'}), 500


@bp.route('/report_record/withdraw', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def report_record_admin_withdraw():
    body = request.get_json(silent=True) or {}
    sub_step_id = body.get('sub_step_id')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_withdraw')
    if not sub_step_id or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM process_sub_steps WHERE id=%s FOR UPDATE", (sub_step_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_qty = float(existing.get('quantity', 0) or 0)
        old_operator = existing.get('operator', '')
        order_no = existing.get('order_no', '')
        step_name = existing.get('step_name', '')
        batch_no = existing.get('batch_no', '')
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE process_sub_steps SET quantity=0 WHERE id=%s", (sub_step_id,))
            cur.execute(
                "INSERT INTO process_sub_steps_history (original_id, order_no, step_name, batch_no, operator_before, operator_after, old_quantity, new_quantity, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (sub_step_id, order_no, step_name, batch_no,
                 old_operator, admin_user, old_qty, 0, reason, admin_user))
            _sync_completed_qty_to_package(order_no, step_name, cur)
            cur.execute("COMMIT")
            logger.info('[RE-001] sub-steps 撤回(2)事务 OK: sub_step_id=%s', sub_step_id)
        except Exception as e:
            conn.rollback()
            logger.error('[RE-001] sub-steps 撤回(2)事务回滚: sub_step_id=%s err=%s', sub_step_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        try:
            from notify import notify_admin_withdraw
            notify_admin_withdraw(original_operator=old_operator, admin_user=admin_user,
                order_no=order_no, step_name=step_name, old_qty=old_qty)
        except Exception as e:
            logging.getLogger('admin_withdraw').warning(f'通知推送失败: {e}')
        try:
            from bridge.sync_client import send as sync_send
            sync_send('sub-step-report', {'order_no': order_no, 'step_name': step_name,
                                          'quantity': -old_qty, 'operator': admin_user})
        except Exception as e:
            logging.getLogger('admin_withdraw').warning(f'8008同步失败: {e}')
        return jsonify({'code': 0, 'message': f'已撤回 {old_operator} 的报工 {old_qty}', 'success': True})
    except Exception as e:
        logging.getLogger('admin_withdraw').exception('撤回失败')
        return jsonify({'code': 500, 'message': '撤回失败'}), 500


@bp.route('/report_record/history_full', methods=['GET'])
def report_record_history_full():
    try:
        sub_step_id = request.args.get('sub_step_id', '').strip()
        if not sub_step_id:
            return jsonify({'code': 400, 'message': '缺少 sub_step_id 参数'}), 400
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_sub_steps WHERE id=%s", (sub_step_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM process_sub_steps_history WHERE original_id=%s ORDER BY created_at DESC",
                (sub_step_id,))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
    except Exception as e:
        return jsonify({'code': 500, 'message': '查询失败'}), 500


# ─── quality_record ──────────────────────────────────────────────────────────

@bp.route('/quality_record/list', methods=['GET'])
def quality_record_list():
    try:
        order_no = request.args.get('order_no', '').strip()
        inspection_type = request.args.get('inspection_type', '').strip()
        operator = request.args.get('operator', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(100, max(10, int(request.args.get('page_size', 20))))
        where = ["qr.status IS NULL OR qr.status NOT IN ('withdrawn')"]
        params = []
        if order_no:
            where.append("qr.order_no LIKE %s"); params.append(f"%{order_no}%")
        if inspection_type:
            where.append("qr.inspection_type LIKE %s"); params.append(f"%{inspection_type}%")
        if operator:
            where.append("qr.inspector LIKE %s"); params.append(f"%{operator}%")
        if start_date:
            where.append("qr.record_date >= %s"); params.append(start_date)
        if end_date:
            where.append("qr.record_date <= %s"); params.append(end_date)
        where_sql = " AND ".join(where)
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM container_center.quality_records qr WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT qr.* FROM container_center.quality_records qr WHERE {where_sql} ORDER BY qr.record_date DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            ids = [str(r['id']) for r in rows]
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(
                    f"SELECT record_id, COUNT(*) as cnt FROM container_center.data_regression_history WHERE data_type='quality' AND record_id IN ({placeholders}) GROUP BY record_id",
                    ids)
                hist_counts = {str(r[0]): r[1] for r in cur.fetchall()}
                for row in rows:
                    row['history_count'] = hist_counts.get(str(row.get('id', '')), 0)
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        logging.getLogger('quality_record_list').exception('查询失败')
        return jsonify({'code': 500, 'message': '查询失败'}), 500


@bp.route('/quality_record/update', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def quality_record_update():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    new_result = body.get('new_result', '').strip()
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_force')
    remark = body.get('remark', '').strip()
    if not record_id or not new_result or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    if new_result not in ('合格', '不合格', '待复检', 'pass', 'fail'):
        return jsonify({'code': 400, 'message': '无效的质检结果'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM container_center.quality_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_result = existing.get('result', '')
        if old_result == new_result:
            conn.rollback(); conn.close()
            return jsonify({'code': 0, 'message': '无变化', 'unchanged': True})
        order_no = existing.get('order_no', '')
        step_name = existing.get('process_name', '')
        try:
            with conn.cursor() as c:
                c.execute("START TRANSACTION")
                c.execute("UPDATE container_center.quality_records SET result=%s WHERE id=%s", (new_result, record_id))
                c.execute(
                    "INSERT INTO container_center.data_regression_history "
                    "(data_type, record_id, order_no, step_name, field_before, field_after, "
                    "operator_before, operator_after, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ('quality', str(record_id), order_no, step_name,
                     json.dumps({'result': old_result}), json.dumps({'result': new_result}),
                     existing.get('inspector', ''), admin_user, reason, admin_user))
                c.execute("COMMIT")
                logging.getLogger('quality_record_update').info('[RE-001] quality 修正事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logging.getLogger('quality_record_update').error(
                '[RE-001] quality 修正事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        try:
            from notify import notify_quality_modified
            notify_quality_modified(inspector=existing.get('inspector', ''), admin_user=admin_user,
                order_no=order_no, step_name=step_name, old_result=old_result, new_result=new_result, remark=remark)
        except Exception as e:
            logging.getLogger('quality_record_update').warning(f'通知推送失败: {e}')
        try:
            from bridge.sync_client import send as sync_send
            sync_send('quality-record-update', {'order_no': order_no, 'step_name': step_name,
                                                 'record_id': str(record_id), 'admin_user': admin_user})
        except Exception as e:
            logging.getLogger('quality_record_update').warning(f'8008同步失败: {e}')
        return jsonify({'code': 0, 'message': f'质检结果已修改 {old_result} → {new_result}', 'success': True})
    except Exception as e:
        logging.getLogger('quality_record_update').exception('修改失败')
        return jsonify({'code': 500, 'message': '修改失败'}), 500


@bp.route('/quality_record/withdraw', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def quality_record_admin_withdraw():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_withdraw')
    if not record_id or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM container_center.quality_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_result = existing.get('result', '')
        inspector = existing.get('inspector', '')
        order_no = existing.get('order_no', '')
        step_name = existing.get('process_name', '')
        try:
            with conn.cursor() as c:
                c.execute("START TRANSACTION")
                c.execute("UPDATE container_center.quality_records SET status='withdrawn' WHERE id=%s", (record_id,))
                c.execute(
                    "INSERT INTO container_center.data_regression_history "
                    "(data_type, record_id, order_no, step_name, field_before, field_after, "
                    "operator_before, operator_after, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ('quality', str(record_id), order_no, step_name,
                     json.dumps({'status': 'active', 'result': old_result}),
                     json.dumps({'status': 'withdrawn', 'result': ''}),
                     inspector, admin_user, reason, admin_user))
                c.execute("COMMIT")
                logging.getLogger('quality_withdraw').info('[RE-001] quality 撤回事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logging.getLogger('quality_withdraw').error(
                '[RE-001] quality 撤回事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        try:
            from notify import notify_quality_withdraw
            notify_quality_withdraw(inspector=inspector, admin_user=admin_user,
                order_no=order_no, step_name=step_name, old_result=old_result)
        except Exception as e:
            logging.getLogger('quality_withdraw').warning(f'通知推送失败: {e}')
        try:
            from bridge.sync_client import send as sync_send
            sync_send('quality-record-withdraw', {'order_no': order_no, 'step_name': step_name,
                                                   'record_id': str(record_id), 'admin_user': admin_user})
        except Exception as e:
            logging.getLogger('quality_withdraw').warning(f'8008同步失败: {e}')
        return jsonify({'code': 0, 'message': f'已撤回质检记录 ({old_result})', 'success': True})
    except Exception as e:
        logging.getLogger('quality_withdraw').exception('撤回失败')
        return jsonify({'code': 500, 'message': '撤回失败'}), 500


@bp.route('/quality_record/history_full', methods=['GET'])
def quality_record_history_full():
    try:
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id 参数'}), 400
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM container_center.quality_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='quality' AND record_id=%s ORDER BY reverted_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
    except Exception as e:
        return jsonify({'code': 500, 'message': '查询失败'}), 500


# ─── material_record ─────────────────────────────────────────────────────────

@bp.route('/material_record/list', methods=['GET'])
def material_record_list():
    try:
        order_no = request.args.get('order_no', '').strip()
        material_name = request.args.get('material_name', '').strip()
        operator = request.args.get('operator', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(100, max(10, int(request.args.get('page_size', 20))))
        where = ["dp.source='material_purchase'"]
        params = []
        if order_no:
            where.append("(dp.order_no LIKE %s OR dp.title LIKE %s)")
            params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
        if material_name:
            where.append("dp.title LIKE %s"); params.append(f"%{material_name}%")
        if operator:
            where.append("dp.operator_id LIKE %s"); params.append(f"%{operator}%")
        if start_date:
            where.append("dp.created_at >= %s"); params.append(start_date)
        if end_date:
            where.append("dp.created_at <= %s"); params.append(end_date)
        where_sql = " AND ".join(where)
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM material_records dp WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT dp.* FROM material_records dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        logging.getLogger('material_record_list').exception('查询失败')
        return jsonify({'code': 500, 'message': '查询失败'}), 500


@bp.route('/material_record/update', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def material_record_update():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    new_quantity = body.get('new_quantity')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_force')
    remark = body.get('remark', '').strip()
    if not record_id or new_quantity is None or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    try:
        new_quantity = float(new_quantity)
    except (ValueError, TypeError):
        return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM material_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_qty = float(existing.get('planned_qty', 0) or 0)
        if abs(old_qty - new_quantity) < 0.001:
            conn.rollback(); conn.close()
            return jsonify({'code': 0, 'message': '无变化', 'unchanged': True})
        order_no = existing.get('order_no', '')
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE material_records SET planned_qty=%s, updated_at=NOW() WHERE id=%s", (new_quantity, record_id))
            cur.execute(
                "INSERT INTO container_center.data_regression_history "
                "(data_type, record_id, order_no, step_name, field_before, field_after, "
                "operator_before, operator_after, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ('material', str(record_id), order_no, existing.get('material_name', ''),
                 json.dumps({'planned_qty': old_qty}), json.dumps({'planned_qty': new_quantity}),
                 existing.get('operator_id', ''), admin_user, reason, admin_user))
            cur.execute("COMMIT")
            logging.getLogger('material_record_update').info('[RE-001] material 修正事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logging.getLogger('material_record_update').error(
                '[RE-001] material 修正事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        return jsonify({'code': 0, 'message': '物料记录已修改', 'success': True})
    except Exception as e:
        logging.getLogger('material_record_update').exception('修改失败')
        return jsonify({'code': 500, 'message': '修改失败'}), 500


@bp.route('/material_record/withdraw', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def material_record_admin_withdraw():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_withdraw')
    if not record_id or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM material_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_operator = existing.get('target_operator', '')
        order_no = existing.get('order_no', '')
        old_status = existing.get('status', '')
        if old_status == 'material_withdrawn':
            conn.rollback(); conn.close()
            return jsonify({'code': 409, 'message': '已撤回'}), 409
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE material_records SET status='material_withdrawn', planned_qty=0, updated_at=NOW() WHERE id=%s AND status!='material_withdrawn'", (record_id,))
            if cur.rowcount == 0:
                conn.rollback(); conn.close()
                return jsonify({'code': 409, 'message': '状态已变更'}), 409
            cur.execute(
                "INSERT INTO container_center.data_regression_history "
                "(data_type, record_id, order_no, step_name, field_before, field_after, "
                "operator_before, operator_after, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ('material', record_id, order_no, '',
                 json.dumps({'status': old_status}), json.dumps({'status': 'material_withdrawn'}),
                 old_operator, admin_user, reason, admin_user))
            cur.execute("COMMIT")
            logging.getLogger('material_withdraw').info('[RE-001] material 撤回事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logging.getLogger('material_withdraw').error(
                '[RE-001] material 撤回事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        return jsonify({'code': 0, 'message': f'已撤回物料记录', 'success': True})
    except Exception as e:
        logging.getLogger('material_withdraw').exception('撤回失败')
        return jsonify({'code': 500, 'message': '撤回失败'}), 500


@bp.route('/material_record/history_full', methods=['GET'])
def material_record_history_full():
    try:
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id 参数'}), 400
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM material_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='material' AND record_id=%s ORDER BY reverted_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
    except Exception as e:
        return jsonify({'code': 500, 'message': '查询失败'}), 500


# ─── outsource_record ─────────────────────────────────────────────────────────

@bp.route('/outsource_record/list', methods=['GET'])
def outsource_record_list():
    try:
        order_no = request.args.get('order_no', '').strip()
        operator = request.args.get('operator', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(100, max(10, int(request.args.get('page_size', 20))))
        where = ["dp.type='outsource'"]
        params = []
        if order_no:
            where.append("(dp.order_no LIKE %s OR dp.title LIKE %s)")
            params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
        if operator:
            where.append("dp.operator_id LIKE %s"); params.append(f"%{operator}%")
        if start_date:
            where.append("dp.created_at >= %s"); params.append(start_date)
        if end_date:
            where.append("dp.created_at <= %s"); params.append(end_date)
        where_sql = " AND ".join(where)
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM outsource_records dp WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT dp.* FROM outsource_records dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        logging.getLogger('outsource_record_list').exception('查询失败')
        return jsonify({'code': 500, 'message': '查询失败'}), 500


@bp.route('/outsource_record/update', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def outsource_record_update():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    new_quantity = body.get('new_quantity')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_force')
    remark = body.get('remark', '').strip()
    if not record_id or new_quantity is None or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    try:
        new_quantity = float(new_quantity)
    except (ValueError, TypeError):
        return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM outsource_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_qty = float(existing.get('quantity', 0) or 0)
        if abs(old_qty - new_quantity) < 0.001:
            conn.rollback(); conn.close()
            return jsonify({'code': 0, 'message': '无变化', 'unchanged': True})
        order_no = existing.get('order_no', '')
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE outsource_records SET quantity=%s, updated_at=NOW() WHERE id=%s", (new_quantity, record_id))
            cur.execute(
                "INSERT INTO container_center.data_regression_history "
                "(data_type, record_id, order_no, step_name, field_before, field_after, "
                "operator_before, operator_after, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ('outsource', str(record_id), order_no, '',
                 json.dumps({'quantity': old_qty}), json.dumps({'quantity': new_quantity}),
                 existing.get('operator_id', ''), admin_user, reason, admin_user))
            cur.execute("COMMIT")
            logger.info('[RE-001] outsource 修正事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logger.error('[RE-001] outsource 修正事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        return jsonify({'code': 0, 'message': '外协记录已修改', 'success': True})
    except Exception as e:
        logging.getLogger('outsource_record_update').exception('修改失败')
        return jsonify({'code': 500, 'message': '修改失败'}), 500


@bp.route('/outsource_record/withdraw', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def outsource_record_admin_withdraw():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_withdraw')
    if not record_id or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM outsource_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_operator = existing.get('target_operator', '')
        order_no = existing.get('order_no', '')
        old_status = existing.get('status', '')
        if old_status == 'outsource_withdrawn':
            conn.rollback(); conn.close()
            return jsonify({'code': 409, 'message': '已撤回'}), 409
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE outsource_records SET status='outsource_withdrawn', quantity=0, updated_at=NOW() WHERE id=%s AND status!='outsource_withdrawn'", (record_id,))
            if cur.rowcount == 0:
                conn.rollback(); conn.close()
                return jsonify({'code': 409, 'message': '状态已变更'}), 409
            cur.execute(
                "INSERT INTO container_center.data_regression_history "
                "(data_type, record_id, order_no, step_name, field_before, field_after, "
                "operator_before, operator_after, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ('outsource', record_id, order_no, '',
                 json.dumps({'status': old_status}), json.dumps({'status': 'outsource_withdrawn'}),
                 old_operator, admin_user, reason, admin_user))
            cur.execute("COMMIT")
            logger.info('[RE-001] outsource 撤回事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logger.error('[RE-001] outsource 撤回事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        return jsonify({'code': 0, 'message': '已撤回外协记录', 'success': True})
    except Exception as e:
        logging.getLogger('outsource_withdraw').exception('撤回失败')
        return jsonify({'code': 500, 'message': '撤回失败'}), 500


@bp.route('/outsource_record/history_full', methods=['GET'])
def outsource_record_history_full():
    try:
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id 参数'}), 400
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM outsource_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='outsource' AND record_id=%s ORDER BY reverted_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
    except Exception as e:
        return jsonify({'code': 500, 'message': '查询失败'}), 500


# ─── schedule_record ─────────────────────────────────────────────────────────

@bp.route('/schedule_record/list', methods=['GET'])
def schedule_record_list():
    try:
        order_no = request.args.get('order_no', '').strip()
        operator = request.args.get('operator', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(100, max(10, int(request.args.get('page_size', 20))))
        where = ["1=1"]
        params = []
        if order_no:
            where.append("(dp.order_no LIKE %s OR dp.product_name LIKE %s)")
            params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
        if operator:
            where.append("dp.operator_id LIKE %s"); params.append(f"%{operator}%")
        if start_date:
            where.append("dp.created_at >= %s"); params.append(start_date)
        if end_date:
            where.append("dp.created_at <= %s"); params.append(end_date)
        where_sql = " AND ".join(where)
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM schedule_records dp WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT dp.* FROM schedule_records dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        logging.getLogger('schedule_record_list').exception('查询失败')
        return jsonify({'code': 500, 'message': '查询失败'}), 500


@bp.route('/schedule_record/update', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def schedule_record_update():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    new_quantity = body.get('new_quantity')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_force')
    remark = body.get('remark', '').strip()
    if not record_id or new_quantity is None or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    try:
        new_quantity = float(new_quantity)
    except (ValueError, TypeError):
        return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedule_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_qty = float(existing.get('order_qty', existing.get('plan_qty', 0)) or 0)
        if abs(old_qty - new_quantity) < 0.001:
            conn.rollback(); conn.close()
            return jsonify({'code': 0, 'message': '无变化', 'unchanged': True})
        order_no = existing.get('order_no', '')
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE schedule_records SET order_qty=%s, updated_at=NOW() WHERE id=%s", (new_quantity, record_id))
            cur.execute(
                "INSERT INTO container_center.data_regression_history "
                "(data_type, record_id, order_no, step_name, field_before, field_after, "
                "operator_before, operator_after, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ('schedule', str(record_id), order_no, '',
                 json.dumps({'quantity': old_qty}), json.dumps({'quantity': new_quantity}),
                 existing.get('operator_id', ''), admin_user, reason, admin_user))
            cur.execute("COMMIT")
            logging.getLogger('schedule_record_update').info('[RE-001] schedule 修正事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logging.getLogger('schedule_record_update').error(
                '[RE-001] schedule 修正事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        return jsonify({'code': 0, 'message': '排产记录已修改', 'success': True})
    except Exception as e:
        logging.getLogger('schedule_record_update').exception('修改失败')
        return jsonify({'code': 500, 'message': '修改失败'}), 500


@bp.route('/schedule_record/withdraw', methods=['POST'])
@require_admin
@limiter.limit("10 per minute")
def schedule_record_admin_withdraw():
    body = request.get_json(silent=True) or {}
    record_id = body.get('record_id')
    admin_user = body.get('admin_user', '').strip()
    reason = body.get('reason', 'admin_withdraw')
    if not record_id or not admin_user:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    conn = MySQLStorage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedule_records WHERE id=%s FOR UPDATE", (record_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback(); conn.close()
            return jsonify({'code': 404, 'message': '记录不存在'}), 404
        col = [d[0] for d in cur.description]
        existing = dict(zip(col, row))
        old_operator = existing.get('operator_id', '')
        order_no = existing.get('order_no', '')
        old_status = existing.get('status', '')
        if old_status == 'withdrawn':
            conn.rollback(); conn.close()
            return jsonify({'code': 409, 'message': '已撤回'}), 409
        try:
            cur.execute("START TRANSACTION")
            cur.execute("UPDATE schedule_records SET status='withdrawn', updated_at=NOW() WHERE id=%s AND status!='withdrawn'", (record_id,))
            if cur.rowcount == 0:
                conn.rollback(); conn.close()
                return jsonify({'code': 409, 'message': '状态已变更'}), 409
            cur.execute(
                "INSERT INTO container_center.data_regression_history "
                "(data_type, record_id, order_no, step_name, field_before, field_after, "
                "operator_before, operator_after, revert_reason, reverted_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                ('schedule', record_id, order_no, '',
                 json.dumps({'status': old_status}), json.dumps({'status': 'withdrawn'}),
                 old_operator, admin_user, reason, admin_user))
            cur.execute("COMMIT")
            logger.info('[RE-001] schedule 撤回事务 OK: record_id=%s', record_id)
        except Exception as e:
            conn.rollback()
            logger.error('[RE-001] schedule 撤回事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
            conn.close()
            return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
        conn.close()
        return jsonify({'code': 0, 'message': '已撤回排产记录', 'success': True})
    except Exception as e:
        logging.getLogger('schedule_withdraw').exception('撤回失败')
        return jsonify({'code': 500, 'message': '撤回失败'}), 500


@bp.route('/schedule_record/history_full', methods=['GET'])
def schedule_record_history_full():
    try:
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id 参数'}), 400
        conn = MySQLStorage.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM container_center.process_sub_steps WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='schedule' AND record_id=%s ORDER BY reverted_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
        finally:
            conn.close()
        return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
    except Exception as e:
        return jsonify({'code': 500, 'message': '查询失败'}), 500

