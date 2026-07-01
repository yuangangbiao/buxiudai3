# -*- coding: utf-8 -*-
"""
独立调度中心服务器 (端口 5003)
- 注册 dispatch_center blueprint
- 内置企业架构缓存代理（自包含，不依赖 container_center_api）
"""
import os
import sys
import json
import logging
import threading
import atexit
from datetime import datetime
from threading import Lock

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from dotenv import load_dotenv
_env_path = os.path.join(BASE_DIR, '.env')
_parent_env = os.path.join(_PROJECT_ROOT, '.env')
if os.path.exists(_parent_env):
    load_dotenv(_parent_env)
elif os.path.exists(_env_path):
    load_dotenv(_env_path)

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('dispatch_server')

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.cors_config import init_cors
from dispatch_center import dispatch_center_bp

# ── 企业架构缓存（本地文件，替代 container_center_api） ──
ENTERPRISE_STRUCTURE_PATH = os.environ.get('ENTERPRISE_STRUCTURE_PATH',
    os.path.join(BASE_DIR, 'data', 'enterprise_structure.json'))
_enterprise_lock = Lock()

def _load_enterprise_structure():
    with _enterprise_lock:
        if os.path.exists(ENTERPRISE_STRUCTURE_PATH):
            try:
                with open(ENTERPRISE_STRUCTURE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f'加载企业架构文件失败: {e}')
        return {'departments': [], 'users': [], 'updated_at': ''}

def _save_enterprise_structure(data):
    with _enterprise_lock:
        try:
            data['updated_at'] = datetime.now().isoformat()
            with open(ENTERPRISE_STRUCTURE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f'企业架构已保存: {len(data.get("departments", []))} 部门, {len(data.get("users", []))} 用户')
        except Exception as e:
            logger.error(f'保存企业架构文件失败: {e}')



def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static'),
    )
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    init_cors(app, default_origins='http://localhost:5000,http://localhost:3000,http://localhost:5008')

    # [P0 修复 2026-06-23 小钰] mobile_login role 字段修复:
    # - SQL 增加 role 列查询
    # - 移除硬编码 role='worker', 改用 row[4] or 'worker'
    # - 测试用户兜底 role='admin' (便于 admin 路径测试)
    @app.route('/api/login', methods=['POST'])
    def mobile_login():
        from flask import request, jsonify
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        import pymysql
        body = request.get_json(silent=True) or {}
        username = (body.get('username') or '').strip()
        if not username:
            return jsonify({'code': 400, 'message': '用户名不能为空'})

        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                import pymysql
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            # [P0 修复] 增加 role 列查询
            cur.execute("SELECT id, name, department, wechat_userid, role FROM operators_local WHERE name=%s AND is_active=1 LIMIT 1", (username,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return jsonify({'code': 0, 'data': {
                    'id': row[0], 'name': row[1],
                    'department': row[2] or '', 'username': row[1],
                    'wechat_userid': row[3] or '', 'role': row[4] or 'worker',
                }})
            return jsonify({'code': 401, 'message': '用户不存在或已停用'})
        except Exception as e:
            return jsonify({'code': 500, 'message': str(e)})

    app.secret_key = os.getenv('JWT_SECRET_KEY')
    if not app.secret_key:
        logger.warning('JWT_SECRET_KEY 未设置，使用随机密钥（重启后会话失效）')
        app.secret_key = os.urandom(32).hex()
    Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=os.getenv('DEFAULT_RATE_LIMITS', '1000 per day, 300 per hour').split(', '),
        storage_uri=os.getenv('LIMITER_STORAGE_URI', 'memory://'),
    )

    app.register_blueprint(dispatch_center_bp)

    # 排程/工单蓝图 (云端去除调度中心功能, TASK-8)
    try:
        from dispatch_center.schedule_routes import schedule_bp, workorder_bp
        app.register_blueprint(schedule_bp)
        app.register_blueprint(workorder_bp)
        logger.info('[调度中心] schedule_bp (/api/schedule) + workorder_bp (/api/workorder) 已注册')
    except Exception as e:
        logger.warning(f'[调度中心] schedule_bp/workorder_bp 注册失败: {e}')

    # [Q2 修复 2026-06-18] 发货管理路由 (9 端点: pending/list/create/confirm-ship/confirm-receive/finished-goods/tracking-list/query-tracking/subscribe-tracking)
    try:
        from dispatch_center.shipment_routes import shipment_bp
        app.register_blueprint(shipment_bp)
        logger.info('[调度中心] shipment_bp (/api/dispatch-center/shipping/*) 已注册 (Q2 修复)')
    except Exception as e:
        logger.warning(f'[调度中心] shipment_bp 注册失败: {e}')

    # 同步桥蓝图 (云端去除调度中心功能, TASK-8) — 16 端点本地 5003 入口
    try:
        from sync_bp import sync_bp as sync_blueprint
        app.register_blueprint(sync_blueprint)
        logger.info('[调度中心] sync_bp (/api/sync/*) 已注册, 共 16 端点本地化')
    except Exception as e:
        logger.warning(f'[调度中心] sync_bp 注册失败: {e}')

    # 企业微信机器人蓝图（群hook、应用回调、消息代理）
    try:
        from wechat_work_bot_bp import wechat_bot_bp, init_module
        app.register_blueprint(wechat_bot_bp)
        init_module()
        logger.info('[调度中心] 企业微信机器人蓝图已注册')
    except Exception as e:
        logger.warning(f'[调度中心] 企业微信机器人蓝图注册失败: {e}')

    # 系统配置蓝图
    try:
        from config_center import config_center_bp
        app.register_blueprint(config_center_bp)
        logger.info('[调度中心] 系统配置蓝图已注册: /api/config-center')
    except Exception as e:
        logger.warning(f'[调度中心] 系统配置蓝图注册失败: {e}')

    # 启动后台调度线程（幂等，重复调用不会重复启动）
    _ensure_background_scheduler()

    # F1 自检: operation_logs.direction 列缺失则自动加 (TASK-10 方案A)
    _ensure_operation_logs_direction()

    # 启动 Outbox 消费者（质检报告回写桌面端）
    try:
        from dispatch_center import start_outbox_worker
        start_outbox_worker(interval=15)
        logger.info('[调度中心] Outbox消费者已启动')
    except Exception as e:
        logger.warning(f'[调度中心] Outbox消费者启动失败: {e}')

    # ── 404 专用处理器 ──
    @app.errorhandler(404)
    def handle_404(e):
        logger.warning('[404] %s %s: 资源不存在', request.method, request.path)
        return jsonify({'code': 404, 'message': '请求的资源不存在'}), 404

    # ── 全局异常处理器 ──
    @app.errorhandler(Exception)
    def handle_global_exception(e):
        logger.exception('[全局异常] %s %s: %s', request.method, request.path, e)
        return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    @app.route('/')
    def root():
        from flask import redirect
        return redirect('/api/dispatch-center/', code=302)

    # ── 内置企业架构 API（替代 container_center_api） ──
    @app.route('/api/enterprise/structure', methods=['GET'])
    def get_enterprise_structure():
        """返回缓存的企业微信架构数据"""
        data = _load_enterprise_structure()
        return jsonify({'code': 0, 'data': data})

    # ════════════════════════════════════════════════════════════════
    # 同步队列 API（从 app.py 5008 搬过来的，消灭跨端口依赖）
    # ════════════════════════════════════════════════════════════════
    @app.route('/api/sync-queue/list', methods=['GET'])
    def sync_queue_list():
        """查看 report_queue 中的失败/待重试记录"""
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        status = request.args.get('status', 'failed,retry')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        status_list = [s.strip() for s in status.split(',') if s.strip()]
        placeholders = ','.join(['%s'] * len(status_list))
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                f"SELECT COUNT(*) FROM report_queue WHERE status IN ({placeholders})",
                status_list)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT * FROM report_queue WHERE status IN ({placeholders}) "
                f"ORDER BY enqueued_at DESC LIMIT %s OFFSET %s",
                status_list + [page_size, offset])
            col = [d[0] for d in cur.description]
            rows = [dict(zip(col, r)) for r in cur.fetchall()]
            for r in rows:
                for k in ('enqueued_at', 'processed_at'):
                    if r.get(k):
                        r[k] = r[k].isoformat() if hasattr(r[k], 'isoformat') else str(r[k])
                r['quantity'] = float(r.get('quantity', 0) or 0)
            conn.close()
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            logger.exception('sync-queue/list 异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/sync-queue/retry', methods=['POST'])
    def sync_queue_retry():
        """手动重推一条 report_queue 记录到 8008，成功后标记已完成"""
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        qid = body.get('id')
        if not qid:
            return jsonify({'code': 400, 'message': '缺少 id'}), 400
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM report_queue WHERE id=%s", (qid,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            item = dict(zip(col, row))
            order_no = item['order_no']
            step_name = item['step_name']
            quantity = float(item['quantity'])
            operator = item['operator'] or ''
            from bridge.sync_client import send as sync_send
            ok = sync_send('sub-step-report', {
                'order_no': order_no, 'step_name': step_name,
                'quantity': quantity, 'operator': operator})
            if ok:
                cur.execute("UPDATE report_queue SET status='completed', processed_at=NOW(), retry_count=retry_count+1 WHERE id=%s", (qid,))
                conn.commit()
                conn.close()
                logger.info(f'[手动重推] 成功 qid={qid} {order_no}/{step_name} +{quantity}')
                return jsonify({'code': 0, 'message': f'同步成功 {order_no}/{step_name} +{quantity}'})
            else:
                cur.execute("UPDATE report_queue SET retry_count=retry_count+1, last_error='手动重推失败', enqueued_at=NOW() WHERE id=%s", (qid,))
                conn.commit()
                conn.close()
                logger.warning(f'[手动重推] 失败 qid={qid} {order_no}/{step_name}')
                return jsonify({'code': 500, 'message': '8008 不可达，同步失败'})
        except Exception as e:
            logger.exception('sync-queue/retry 异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/enterprise/structure', methods=['POST'])
    def save_enterprise_structure():
        """保存企业微信架构数据"""
        body = request.get_json(silent=True) or {}
        depts = body.get('departments', [])
        users = body.get('users', [])
        if isinstance(depts, str):
            try: depts = json.loads(depts)
            except Exception: depts = []
        if isinstance(users, str):
            try: users = json.loads(users)
            except Exception: users = []
        if isinstance(depts, dict):
            depts = depts.get('departments', depts.get('data', []))
        if isinstance(users, dict):
            users = users.get('operators', users.get('users', users.get('data', [])))
        if not isinstance(depts, list):
            depts = []
        if not isinstance(users, list):
            users = []
        if not depts and not users:
            return jsonify({'code': 1, 'message': '数据为空'})
        _save_enterprise_structure({'departments': depts, 'users': users})
        return jsonify({'code': 0, 'message': '企业架构已保存', 'data': {'updated_at': _load_enterprise_structure().get('updated_at', '')}})

    @app.route('/health')
    def health():
        import dispatch_center as _dc
        thread_info = {}
        if hasattr(_dc, '_cost_checker_thread') and _dc._cost_checker_thread:
            thread_info['cost_checker'] = 'alive' if _dc._cost_checker_thread.is_alive() else 'dead'
            thread_info['cost_checker_running'] = getattr(_dc, '_cost_checker_running', False)
        if hasattr(_dc, '_alert_engine') and _dc._alert_engine:
            thread_info['alert_engine'] = 'alive' if _dc._alert_engine._thread and _dc._alert_engine._thread.is_alive() else 'dead'
        return jsonify({
            'code': 0,
            'service': 'dispatch-center',
            'time': datetime.now().isoformat(),
            'threads': thread_info,
        })

    # ── 报工/外协记录管理 API（从 app.py 搬来，消灭跨端口依赖） ──
    _register_report_mgmt_routes(app)
    return app


def _register_report_mgmt_routes(app):
    """注册报工/外协记录管理路由（app.py 中 @app.route，调度中心也需用）"""
    import pymysql
    from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT

    # ========== 报工记录管理 ==========
    @app.route('/api/report_record/list', methods=['GET'])
    def report_record_list_dispatch():
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
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                f"SELECT s.*, (SELECT COUNT(*) FROM process_sub_steps_history h WHERE h.original_id=s.id) as history_count "
                f"FROM process_sub_steps s WHERE {where_sql} ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, (page - 1) * page_size])
            rows = cur.fetchall()
            col = [d[0] for d in cur.description]
            records = [dict(zip(col, r)) for r in rows]
            cur.execute(f"SELECT COUNT(*) FROM process_sub_steps s WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            for r in records:
                for k in ('created_at',):
                    if r.get(k) and hasattr(r[k], 'isoformat'):
                        r[k] = r[k].isoformat()
                r['quantity'] = float(r.get('quantity', 0) or 0)
                r['history_count'] = int(r.get('history_count', 0) or 0)
            conn.close()
            return jsonify({'code': 0, 'data': {'list': records, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            logger.exception('报工记录列表异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/report_record/update', methods=['POST'])
    def report_record_update_dispatch():
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
        try:
            from core.db_compat import get_conn
            conn = get_conn()
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
            batch_no = existing.get('batch_no', '')
            old_operator = existing.get('operator', '')
            # 追加上限校验
            try:
                cur.execute("SELECT quantity FROM process_records WHERE order_no=%s LIMIT 1", (order_no,))
                pr = cur.fetchone()
                order_req = float(pr[0]) if pr else 0
                cur.execute("SELECT SUM(quantity) FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND quantity > 0 AND id<>%s",
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
                # 同步 process_sub_steps.completed_qty (v3.6.1: 已从 data_packages 迁移)
                try:
                    cur.execute(
                        "UPDATE process_sub_steps SET completed_qty = COALESCE(completed_qty, 0) + %s "
                        "WHERE order_no=%s AND step_name=%s",
                        (new_quantity - old_qty, order_no, step_name))
                except Exception:
                    pass
                cur.execute("COMMIT")
                logger.info('[调度中心] 报工修正 OK: order=%s step=%s qty=%s', order_no, step_name, new_quantity)
            except Exception as e:
                conn.rollback()
                logger.error('[调度中心] 报工修正回滚: order=%s err=%s', order_no, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            try:
                from notify import notify_admin_modified
                notify_admin_modified(original_operator=old_operator, admin_user=admin_user,
                                      order_no=order_no, step_name=step_name,
                                      old_qty=old_qty, new_qty=new_quantity, remark=remark)
            except Exception:
                pass
            try:
                from bridge.sync_client import send as sync_send
                sync_send('sub-step-report', {'order_no': order_no, 'step_name': step_name,
                                              'quantity': new_quantity - old_qty, 'operator': admin_user})
            except Exception:
                pass
            return jsonify({'code': 0, 'message': f'已修改 {old_qty} → {new_quantity}', 'success': True})
        except Exception as e:
            logger.exception('报工修正失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/report_record/withdraw', methods=['POST'])
    def report_record_withdraw_dispatch():
        body = request.get_json(silent=True) or {}
        sub_step_id = body.get('sub_step_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not sub_step_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            from core.db_compat import get_conn
            conn = get_conn()
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
                # 同步 process_sub_steps.completed_qty（重算） (v3.6.1: 已从 data_packages 迁移)
                try:
                    cur.execute("SELECT COALESCE(SUM(quantity),0) FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND quantity>0",
                                (order_no, step_name))
                    total = float(cur.fetchone()[0] or 0)
                    cur.execute("UPDATE process_sub_steps SET completed_qty=%s WHERE order_no=%s AND step_name=%s",
                                (total, order_no, step_name))
                except Exception:
                    pass
                cur.execute("COMMIT")
                logger.info('[调度中心] 撤回事务 OK: sub_step_id=%s', sub_step_id)
            except Exception as e:
                conn.rollback()
                logger.error('[调度中心] 撤回事务回滚: sub_step_id=%s err=%s', sub_step_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            try:
                from notify import notify_admin_withdraw
                notify_admin_withdraw(original_operator=old_operator, admin_user=admin_user,
                                      order_no=order_no, step_name=step_name, old_qty=old_qty)
            except Exception:
                pass
            try:
                from bridge.sync_client import send as sync_send
                sync_send('sub-step-report', {'order_no': order_no, 'step_name': step_name,
                                              'quantity': -old_qty, 'operator': admin_user})
            except Exception:
                pass
            return jsonify({'code': 0, 'message': f'已撤回 {old_operator} 的报工 {old_qty}', 'success': True})
        except Exception as e:
            logger.exception('撤回失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/report_record/history_full', methods=['GET'])
    def report_record_history_full_dispatch():
        sub_step_id = request.args.get('sub_step_id', '').strip()
        if not sub_step_id:
            return jsonify({'code': 400, 'message': '缺少 sub_step_id'}), 400
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, original_id, order_no, step_name, batch_no, operator_before, operator_after, "
                "old_quantity, new_quantity, revert_reason, reverted_by, created_at "
                "FROM process_sub_steps_history WHERE original_id=%s ORDER BY created_at DESC LIMIT 50",
                (sub_step_id,))
            rows = cur.fetchall()
            col = [d[0] for d in cur.description]
            records = [dict(zip(col, r)) for r in rows]
            for r in records:
                for k in ('old_quantity', 'new_quantity'):
                    r[k] = float(r.get(k, 0) or 0)
                if r.get('created_at') and hasattr(r['created_at'], 'isoformat'):
                    r['created_at'] = r['created_at'].isoformat()
            conn.close()
            return jsonify({'code': 0, 'data': {'list': records}})
        except Exception as e:
            logger.exception('审计历史查询异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    # ========== 外协记录管理 ==========
    @app.route('/api/outsource_record/list', methods=['GET'])
    def outsource_record_list_dispatch():
        try:
            order_no = request.args.get('order_no', '').strip()
            operator = request.args.get('operator', '').strip()
            start_date = request.args.get('start_date', '').strip()
            end_date = request.args.get('end_date', '').strip()
            page = max(1, int(request.args.get('page', 1)))
            page_size = min(100, max(10, int(request.args.get('page_size', 20))))
            # v3.6.1: 从 outsource_records 表查询
            where = ["status NOT IN ('withdrawn')"]
            params = []
            if order_no:
                where.append("(order_no LIKE %s OR title LIKE %s)")
                params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
            if operator:
                where.append("(supplier_name LIKE %s OR target_operator LIKE %s)")
                params.append(f"%{operator}%"); params.append(f"%{operator}%")
            if start_date:
                where.append("created_at >= %s"); params.append(start_date)
            if end_date:
                where.append("created_at <= %s"); params.append(end_date)
            where_sql = " AND ".join(where)
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                f"SELECT id, order_no, title, supplier_name, target_operator, quantity, completed_qty, status, created_at "
                f"FROM outsource_records WHERE {where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, (page - 1) * page_size])
            rows = cur.fetchall()
            col = [d[0] for d in cur.description]
            records = []
            for r in rows:
                item = dict(zip(col, r))
                item['content'] = {}
                item['quantity'] = float(item.get('quantity', 0) or 0)
                if item.get('created_at') and hasattr(item['created_at'], 'isoformat'):
                    item['created_at'] = item['created_at'].isoformat()
                records.append(item)
            cur.execute(f"SELECT COUNT(*) FROM outsource_records WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            conn.close()
            return jsonify({'code': 0, 'data': {'list': records, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            logger.exception('外协记录列表异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/outsource_record/update', methods=['POST'])
    def outsource_record_update_dispatch():
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id', '').strip()
        admin_user = body.get('admin_user', '').strip()
        new_qty = body.get('new_qty')
        if not record_id or admin_user is None or new_qty is None:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            new_qty = float(new_qty)
        except (ValueError, TypeError):
            return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            # v3.6.1: 从 outsource_records 表查询
            cur.execute("SELECT id, completed_qty FROM outsource_records WHERE id=%s FOR UPDATE", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            existing = dict(zip(col, row))
            old_qty = float(existing.get('completed_qty', 0) or 0)
            try:
                cur.execute("START TRANSACTION")
                cur.execute("UPDATE outsource_records SET completed_qty=%s WHERE id=%s", (new_qty, record_id))
                cur.execute("COMMIT")
                logger.info('[调度中心] 外协修正 OK: id=%s qty=%s', record_id, new_qty)
            except Exception as e:
                conn.rollback()
                logger.error('[调度中心] 外协修正回滚: id=%s err=%s', record_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            return jsonify({'code': 0, 'message': f'已修改 {old_qty} → {new_qty}', 'success': True})
        except Exception as e:
            logger.exception('外协修正失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/outsource_record/withdraw', methods=['POST'])
    def outsource_record_withdraw_dispatch():
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id', '').strip()
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not record_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            # v3.6.1: 从 outsource_records 表查询
            cur.execute("SELECT id, completed_qty FROM outsource_records WHERE id=%s FOR UPDATE", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            existing = dict(zip(col, row))
            old_qty = float(existing.get('completed_qty', 0) or 0)
            try:
                cur.execute("START TRANSACTION")
                cur.execute("UPDATE outsource_records SET status='withdrawn' WHERE id=%s", (record_id,))
                cur.execute("COMMIT")
                logger.info('[调度中心] 外协撤回 OK: id=%s', record_id)
            except Exception as e:
                conn.rollback()
                logger.error('[调度中心] 外协撤回回滚: id=%s err=%s', record_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            return jsonify({'code': 0, 'message': f'已撤回, 旧数量: {old_qty}', 'success': True})
        except Exception as e:
            logger.exception('外协撤回失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/api/outsource_record/history_full', methods=['GET'])
    def outsource_record_history_full_dispatch():
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id'}), 400
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, action, detail, created_at FROM operation_logs "
                "WHERE target_type='outsource' AND target_id=%s ORDER BY created_at DESC LIMIT 50",
                (record_id,))
            rows = cur.fetchall()
            col = [d[0] for d in cur.description]
            records = [dict(zip(col, r)) for r in rows]
            for r in records:
                if r.get('created_at') and hasattr(r['created_at'], 'isoformat'):
                    r['created_at'] = r['created_at'].isoformat()
            conn.close()
            return jsonify({'code': 0, 'data': {'list': records}})
        except Exception as e:
            logger.exception('外协审计历史查询异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    # ========== 质检记录管理 ==========
    @app.route('/api/quality_record/list', methods=['GET'])
    def quality_record_list_dispatch():
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
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
            cur.execute(f"SELECT COUNT(*) FROM container_center.quality_records qr WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT qr.* FROM container_center.quality_records qr WHERE {where_sql} ORDER BY qr.record_date DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            logger.exception('质检记录查询失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    # ========== 物料记录管理 ==========
    @app.route('/api/material_record/list', methods=['GET'])
    def material_record_list_dispatch():
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            order_no = request.args.get('order_no', '').strip()
            material_name = request.args.get('material_name', '').strip()
            operator = request.args.get('operator', '').strip()
            start_date = request.args.get('start_date', '').strip()
            end_date = request.args.get('end_date', '').strip()
            page = max(1, int(request.args.get('page', 1)))
            page_size = min(100, max(10, int(request.args.get('page_size', 20))))
            where = ["(status IS NULL OR status NOT IN ('withdrawn'))"]
            params = []
            if order_no:
                where.append("(order_no LIKE %s OR title LIKE %s)")
                params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
            if material_name:
                where.append("material_name LIKE %s"); params.append(f"%{material_name}%")
            if operator:
                where.append("(target_operator LIKE %s OR supplier LIKE %s)")
                params.append(f"%{operator}%"); params.append(f"%{operator}%")
            if start_date:
                where.append("created_at >= %s"); params.append(start_date)
            if end_date:
                where.append("created_at <= %s"); params.append(end_date)
            where_sql = " AND ".join(where)
            # v3.6.1: 从 material_records 表查询
            cur.execute(f"SELECT COUNT(*) FROM container_center.material_records WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT id, order_no, material_name, target_operator, supplier, quantity, completed_qty, status, created_at "
                f"FROM container_center.material_records WHERE {where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            logger.exception('物料记录查询失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/workorder', methods=['GET'])
    def workorder_api():
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id, order_no, quantity, status, created_at FROM container_center.process_records ORDER BY created_at DESC LIMIT 100")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'items': rows}})
        except Exception as e:
            logger.exception('工单查询失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    @app.route('/production-orders', methods=['GET'])
    def production_orders_api():
        return workorder_api()

    @app.route('/outsource-records', methods=['GET'])
    def outsource_records_api():
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id, order_no, quantity, status, supplier, created_at FROM container_center.outsource_records ORDER BY created_at DESC LIMIT 100")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': rows})
        except Exception as e:
            logger.exception('外协记录查询失败')
            return jsonify({'code': 500, 'message': str(e)}), 500

    # ========== 概览统计 API ==========
    @app.route('/status', methods=['GET'])
    def status_api():
        try:
            from core.db_compat import get_conn
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM container_center.process_sub_steps WHERE status='pending'")
            pending = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM container_center.process_sub_steps WHERE status='in_progress'")
            in_progress = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM container_center.process_sub_steps WHERE status='completed'")
            completed = cur.fetchone()[0]
            conn.close()
            summary = {
                'pending': pending,
                'dispatched': 0,
                'in_progress': in_progress,
                'completed': completed,
                'overdue': 0,
                'completion_rate': int(completed / (pending + in_progress + completed) * 100) if (pending + in_progress + completed) > 0 else 0
            }
            return jsonify({
                'code': 0,
                'data': {
                    'summary': summary,
                    'active_processes': 0,
                    'pending_warehousing': 0,
                    'operators': []
                }
            })
        except Exception as e:
            logger.exception('状态查询失败')
            return jsonify({'code': 0, 'data': {'summary': {'pending': 0, 'dispatched': 0, 'in_progress': 0, 'completed': 0, 'overdue': 0, 'completion_rate': 0}, 'active_processes': 0, 'pending_warehousing': 0, 'operators': []}})


def _ensure_operation_logs_direction():
    """F1 自检: operation_logs.direction 列缺失则自动加 (TASK-10 方案A)
    ---
    触发场景: 云端 DBA 尚未执行 ALTER TABLE 时, 本地 5003 启动主动加列
    幂等保证:
      1. 先查 information_schema, 已存在则 no-op
      2. 多实例并发启动: 仅第一个 ALTER 成功, 其余 catch Duplicate column name 视为已加
    风险: DDL 自动执行 (仅本地 5003 节点, 改的是共享表, 已审批)
    """
    conn = None
    try:
        from db.steelbelt_pool import get_conn
        conn = get_conn()
        with conn.cursor() as c:
            c.execute("""
                SELECT COUNT(*) AS cnt FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'operation_logs'
                  AND column_name = 'direction'
            """)
            row = c.fetchone()
            exists = (row.get('cnt', 0) if isinstance(row, dict) else row[0]) > 0
            if exists:
                logger.info('[F1自检] operation_logs.direction 列已存在, 跳过')
                return

            c.execute("""
                ALTER TABLE operation_logs
                ADD COLUMN direction VARCHAR(16) DEFAULT '上游' AFTER id
            """)
            conn.commit()
            logger.warning('[F1自检] 已自动添加 operation_logs.direction 列')
    except Exception as e:
        err_msg = str(e)
        # 并发场景: 另一实例已加, 捕 "Duplicate column name" 视为成功
        if 'Duplicate column' in err_msg or '1060' in err_msg:
            logger.info('[F1自检] 列已存在(并发加), 跳过: %s', err_msg[:80])
        else:
            logger.error('[F1自检] 失败 (非致命, 4 个读类端点将继续返 500): %s', err_msg)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _ensure_background_scheduler():
    """确保后台调度线程已启动（原子操作）"""
    from dispatch_center import start_background_scheduler
    try:
        from dispatch_center import _alert_engine
    except ImportError:
        _alert_engine = None
    if _alert_engine is None:
        start_background_scheduler()
        logger.info('[启动] 后台调度引擎已启动')
    else:
        logger.info('[启动] 后台调度引擎已在运行')

    _start_log_cleanup()
    # 注册 LogCleaner 到统一管理器（wrapper 适配 SchedulerController 接口）
    try:
        from dispatch_center import _scheduler_manager
        class _LogCleanerWrapper:
            def get_name(self): return 'log_cleaner'
            def get_description(self): return '日志清理 - 定期清理过期日志文件,防止磁盘膨胀'
            def is_available(self): return True
            def get_current_interval(self): return _LOG_CLEANUP_INTERVAL
            def start(self): _start_log_cleanup()
            def stop(self): pass
            def is_running(self): return _log_cleanup_thread is not None and _log_cleanup_thread.is_alive()
        _scheduler_manager.register(_LogCleanerWrapper())
    except Exception:
        pass
    # 启动云端轮询（5006 收发消息）
    _start_cloud_poller()


_LOG_CLEANUP_INTERVAL = 3600 * 6
_log_cleanup_thread = None
_log_cleanup_stop = threading.Event()


class _ResilientLogCleaner(threading.Thread):
    """弹性日志清理线程，异常时自动等待后继续运行"""
    def __init__(self):
        super().__init__(daemon=True, name='log-cleaner')
        self._stop_event = threading.Event()
        self._interval = _LOG_CLEANUP_INTERVAL

    def run(self):
        logger.info(f'[日志清理] 弹性线程已启动, 间隔 {self._interval}s')
        while not self._stop_event.is_set():
            try:
                from logging_setup import cleanup_old_logs
                cleaned = cleanup_old_logs()
                if cleaned:
                    logger.info(f'[日志清理] 已清理 {cleaned} 个过期日志文件')
            except Exception as e:
                logger.warning(f'[日志清理] 异常: {e}')
            self._stop_event.wait(self._interval)
        logger.info('[日志清理] 线程已停止')

    def stop(self):
        self._stop_event.set()

    def set_interval(self, seconds):
        self._interval = seconds
        global _LOG_CLEANUP_INTERVAL
        _LOG_CLEANUP_INTERVAL = seconds


def _start_log_cleanup():
    """按间隔执行日志清理（幂等）"""
    global _log_cleanup_thread
    if _log_cleanup_thread is not None and _log_cleanup_thread.is_alive():
        return
    _log_cleanup_thread = _ResilientLogCleaner()
    _log_cleanup_thread.start()


# ========================================================================
# CloudPoller - 云端消息轮询客户端
# ========================================================================
_CLOUD_POLL_INTERVAL = int(os.getenv('CLOUD_POLL_INTERVAL', '10'))
CLOUD_RELAY_URL = os.getenv('CLOUD_RELAY_URL', '') or os.getenv('WECHAT_CLOUD_HOST', '') or 'http://124.223.57.82:5006'
CLOUD_API_KEY = os.getenv('WECHAT_CLOUD_API_KEY', '')
_cloud_poller_thread = None
_cloud_poller_stop = threading.Event()


def _handle_cloud_message(msg):
    """处理单条云端消息
    当前：日志记录 + ACK（后续可扩展为智能表格删改操作）
    """
    msg_id = msg.get('id', 'unknown')
    user_id = msg.get('user_id', '')
    content = msg.get('content', '')
    event = msg.get('event', '')
    logger.info(f'[CloudPoller] 收到消息: id={msg_id}, user={user_id}, content={content[:100]}')
    if event:
        logger.info(f'[CloudPoller] 事件: {event}')


class _CloudPoller(threading.Thread):
    """云端消息轮询线程"""
    def __init__(self):
        super().__init__(daemon=True, name='cloud-poller')
        self._stop_event = threading.Event()
        self._session = None

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'X-API-Key': CLOUD_API_KEY,
                'Accept': 'application/json',
            })
            self._session.timeout = (15, 30)
        return self._session

    def run(self):
        logger.info(f'[CloudPoller] 线程已启动, 轮询间隔 {_CLOUD_POLL_INTERVAL}s')
        import requests
        first_run = True
        while not self._stop_event.is_set():
            try:
                # 首次立即轮询，后续按间隔等待
                if not first_run:
                    self._stop_event.wait(_CLOUD_POLL_INTERVAL)
                    if self._stop_event.is_set():
                        break
                first_run = False

                poll_url = f'{CLOUD_RELAY_URL}/api/queue/poll'
                sess = self._get_session()
                resp = sess.get(poll_url, params={'limit': 20})
                if resp.status_code != 200:
                    logger.warning(f'[CloudPoller] 轮询返回 {resp.status_code}')
                    continue

                result = resp.json()
                if result.get('code') != 0:
                    logger.warning(f'[CloudPoller] 轮询异常: {result.get("message")}')
                    continue

                messages = result.get('messages', [])
                if not messages:
                    continue

                logger.info(f'[CloudPoller] 拉取到 {len(messages)} 条消息')
                msg_ids = [m['id'] for m in messages if 'id' in m]

                for msg in messages:
                    try:
                        _handle_cloud_message(msg)
                    except Exception as e:
                        logger.error(f'[CloudPoller] 处理消息异常: {e}')

                if msg_ids:
                    ack_url = f'{CLOUD_RELAY_URL}/api/queue/ack'
                    ack_resp = sess.post(ack_url, json={'ids': msg_ids})
                    if ack_resp.status_code == 200:
                        logger.info(f'[CloudPoller] 已确认 {len(msg_ids)} 条消息')
                    else:
                        logger.warning(f'[CloudPoller] ACK失败: {ack_resp.status_code}')

            except requests.exceptions.ConnectionError:
                logger.warning('[CloudPoller] 无法连接到云端中继服务')
            except Exception as e:
                logger.error(f'[CloudPoller] 轮询异常: {e}')

        logger.info('[CloudPoller] 线程已停止')

    def stop(self):
        self._stop_event.set()


def _start_cloud_poller():
    """启动云端轮询线程（幂等）"""
    global _cloud_poller_thread
    if _cloud_poller_thread is not None and _cloud_poller_thread.is_alive():
        return
    if not CLOUD_RELAY_URL:
        logger.info('[CloudPoller] CLOUD_RELAY_URL 未配置，跳过启动')
        return
    _cloud_poller_thread = _CloudPoller()
    _cloud_poller_thread.start()


def _stop_cloud_poller():
    """停止云端轮询线程"""
    global _cloud_poller_thread
    if _cloud_poller_thread:
        _cloud_poller_thread.stop()
        _cloud_poller_thread = None
        logger.info('[CloudPoller] 已停止')


def _shutdown_all():
    """完整关闭所有后台组件"""
    logger.info('[Shutdown] 开始关闭所有组件...')
    try:
        import dispatch_center
        if hasattr(dispatch_center, '_cost_checker_running'):
            dispatch_center._cost_checker_running = False
        if hasattr(dispatch_center, '_alert_engine') and dispatch_center._alert_engine:
            try:
                dispatch_center._alert_engine.stop()
                logger.info('[Shutdown] AlertEngine 已停止')
            except Exception as e:
                logger.warning(f'[Shutdown] AlertEngine 停止异常: {e}')
    except Exception as e:
        logger.warning(f'[Shutdown] 调度中心组件停止异常: {e}')
    global _log_cleanup_thread
    if _log_cleanup_thread:
        _log_cleanup_thread.stop()
        _log_cleanup_thread = None
        logger.info('[Shutdown] 日志清理线程已停止')
    try:
        _stop_cloud_poller()
    except Exception as e:
        logger.warning(f'[Shutdown] 云端轮询停止异常: {e}')

if __name__ == '__main__':
    from flask import request

    host = os.getenv('DISPATCH_HOST', '0.0.0.0')
    port = int(os.getenv('DISPATCH_PORT', '5003'))

    # CONTAINER_CENTER_URL 指向容器中心（端口5002），用于企业架构同步等
    os.environ.setdefault('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')

    atexit.register(_shutdown_all)

    app = create_app()

    # [C3 修复 2026-06-13] 注册 trace_id 中间件
    try:
        from utils.trace import init_trace_middleware
        init_trace_middleware(app)
        logger.info('[TRACE] 5003 调度中心 trace_id 中间件已注册')
    except Exception as e:
        logger.warning(f'[TRACE] 5003 注册中间件失败: {e}')

    def _warmup_mysql():
        """预热 MySQL 连接：启动后对每个关键表做一次查询，触发连接池初始化，避免首请求慢"""
        logger.info('[Warmup] MySQL 连接预热开始...')
        try:
            from storage.mysql_storage import MySQLStorage
            storage = MySQLStorage()
            storage.fetch_one("SELECT 1 AS warmup")
            storage.fetch_one("SELECT COUNT(*) FROM workers")
            storage.fetch_one("SELECT COUNT(*) FROM process_records")
            logger.info('[Warmup] MySQL 连接预热完成')
        except Exception as e:
            logger.warning(f'[Warmup] MySQL 预热失败（非致命）: {e}')

    _warmup_mysql()

    # ── 报工通知路由（供 5008 移动端调用）──────────────────────────
    @app.route('/api/dispatch-center/report-submitted', methods=['POST'])
    def dispatch_report_submitted_notify():
        """5008 移动端报工后，通知 5003 调度中心发微信给操作员"""
        body = request.get_json(force=True, silent=True) or {}
        order_no = body.get('order_no', '')
        step_name = body.get('step_name', '')
        quantity = body.get('quantity', 0)
        operator = body.get('operator', '')
        reported_at = body.get('reported_at', '')
        if not order_no or not step_name:
            return jsonify({'code': 1, 'message': '缺少必要参数'})

        try:
            from template_engine import _render_template
            from dispatch_center._core import _send_wechat_app_message
            content = _render_template('tmpl_report_submitted', {
                '订单号': order_no,
                '工序': step_name,
                '数量': str(int(quantity)),
                '操作员': operator,
                '报工时间': reported_at,
            })
            if not content:
                return jsonify({'code': 2, 'message': '模板渲染失败'})
            ok, err = _send_wechat_app_message(content, None)
            if ok:
                logger.info(f'[报工通知] 已发送给 {operator}，工序={step_name}')
                return jsonify({'code': 0, 'message': '通知已发送'})
            else:
                logger.warning(f'[报工通知] 发送失败: {err}')
                return jsonify({'code': 3, 'message': f'发送失败: {err}'})
        except Exception as e:
            logger.exception('[报工通知] 异常')
            return jsonify({'code': 500, 'message': str(e)}), 500

    # 启用 OpenAI SDK 云端轮询（与 cloud_poller.py 对接）
    try:
        from cloud_poller import init_cloud_poller, start_polling
        init_cloud_poller()
        start_polling()
        logger.info('[调度中心] OpenAI SDK 云端轮询已启动')
    except Exception as e:
        logger.warning(f'[调度中心] 云端轮询启动失败（非致命）: {e}')

    logger.info('=' * 50)
    logger.info('  调度中心服务器启动')
    logger.info(f'  地址: http://{host}:{port}')
    logger.info(f'  页面: http://{host}:{port}/api/dispatch-center/')
    logger.info(f'  CONTAINER_CENTER_URL: {os.environ["CONTAINER_CENTER_URL"]}')
    logger.info(f'  企业架构缓存: {ENTERPRISE_STRUCTURE_PATH}')
    _env_source = _parent_env if os.path.exists(_parent_env) else (_env_path if os.path.exists(_env_path) else '<NONE>')
    _cloud_key = os.getenv('WECHAT_CLOUD_API_KEY', '')
    _cloud_host = os.getenv('WECHAT_CLOUD_HOST', '')
    logger.info(f'  .env 来源: {_env_source}')
    logger.info(f'  WECHAT_CLOUD_HOST: {_cloud_host or "❌ 未配置"}')
    logger.info(f'  WECHAT_CLOUD_API_KEY: {(_cloud_key[:6] + "..." + _cloud_key[-3:]) if _cloud_key else "❌ 未配置"}')
    logger.info('=' * 50)

    try:
        from waitress import serve
        serve(
            app,
            host=host,
            port=port,
            threads=int(os.getenv('DISPATCH_WORKERS', '8')),
            connection_limit=int(os.getenv('DISPATCH_CONN_LIMIT', '100')),
            channel_timeout=int(os.getenv('DISPATCH_CHANNEL_TIMEOUT', '120')),
        )
    except ModuleNotFoundError:
        logger.warning('waitress 未安装，改用 Flask 内置服务器')
        app.run(host=host, port=port, debug=False, threaded=True)
