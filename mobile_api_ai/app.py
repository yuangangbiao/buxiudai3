# -*- coding: utf-8 -*-
"""
AI增强版移动报工系统 - Flask应用入口
"""
import os
import sys

# 每次启动清除缓存，避免旧代码残留
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import glob as _glob
for _d in [os.path.dirname(__file__), os.path.dirname(os.path.dirname(__file__))]:
    for _root, _dirs, _files in os.walk(_d):
        if '__pycache__' in _dirs:
            import shutil as _sh; _sh.rmtree(os.path.join(_root, '__pycache__'), ignore_errors=True)
    for _f in _glob.glob(os.path.join(_d, '**', '*.pyc'), recursive=True):
        try: os.remove(_f)
        except Exception: pass

# 强制加载项目 .env，避免 DB 连接分裂
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_PROJECT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from flask import Flask, jsonify, send_from_directory, render_template, request
import json
from core.cors_config import init_cors
import logging

from core.config import JWT_EXPIRE_HOURS, FLASK_HOST, DB_PATHS
from mobile_api_ai.api.limiter import limiter
from mobile_api_ai.api.decorators import require_admin, require_auth

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 静态文件不缓存
    init_cors(app, default_origins='http://localhost:5000,http://localhost:5003,http://localhost:3000')
    limiter.init_app(app)

    # 启动时验证前端JS语法
    def _validate_frontend_js():
        import os as _os
        for _fname in ['cs_report.html', 'mobile_unified.html']:
            _path = _os.path.join(app.root_path, 'templates', _fname)
            try:
                with open(_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                s = content.find('<script>')
                e = content.rfind('</script>')
                if s < 0 or e < 0:
                    logger.error(f'[启动检查] {_fname} 中未找到 <script> 标签')
                    continue
                js = content[s:e]
                brace = 0
                ok = True
                for ln, line in enumerate(js.split('\n'), 1):
                    brace += line.count('{') - line.count('}')
                    if brace < 0:
                        logger.critical(f'[启动检查] ❌ {_fname} JS语法错误！多余的 }} 在第 {ln} 行，系统将无法正常使用！')
                        logger.critical(f'[启动检查]    >> {line.strip()[:100]}')
                        ok = False
                        break
                if ok:
                    if brace != 0:
                        logger.warning(f'[启动检查] ⚠️ {_fname} JS花括号不平衡(diff={brace}), 可能影响功能')
                    else:
                        logger.info(f'[启动检查] ✅ {_fname} JS语法检查通过')
            except FileNotFoundError:
                logger.warning(f'[启动检查] {_fname} 不存在，跳过检查')
            except Exception as exc:
                logger.error(f'[启动检查] {_fname} 检查失败: {exc}')
    _validate_frontend_js()

    # ============================================================
    # 鉴权钩子：所有写操作必须带 X-User-Id header
    # ============================================================
    @app.before_request
    def require_user_for_write():
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return
        user_id = request.headers.get('X-User-Id', '').strip()
        if not user_id:
            from flask import jsonify
            return jsonify({'code': 1, 'message': '未登录: X-User-Id header 必填'}), 401

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.svg', mimetype='image/svg+xml')

    @app.route('/mobile_login.html')
    def mobile_login_page():
        return send_from_directory(app.root_path, 'templates/mobile_login.html')

    app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['JWT_EXPIRE_HOURS'] = JWT_EXPIRE_HOURS

    # 导入已有的蓝图模块
    from mobile_api_ai.api import auth, scan, process, quality, message, approval, health
    app.register_blueprint(auth.bp)
    app.register_blueprint(scan.bp)
    app.register_blueprint(process.bp)
    app.register_blueprint(quality.bp)
    app.register_blueprint(message.bp)
    app.register_blueprint(approval.bp)
    app.register_blueprint(health.bp)
    from mobile_api_ai.api.quality_inspection import bp as qi_bp
    app.register_blueprint(qi_bp)

    # stats 可选（依赖 services.factory）
    try:
        from mobile_api_ai.api import stats
        app.register_blueprint(stats.bp)
    except (ImportError, AttributeError) as e:
        logger.warning(f"[App] 蓝图 stats 注册跳过（依赖未实现）: {e}")

    # 可选蓝图：尚未实现时静默跳过
    for mod_name, bp_attr in [('mobile_api_ai.api.ai', 'bp'), ('mobile_api_ai.api.cost', 'bp'), ('mobile_api_ai.api.reports', 'bp')]:
        try:
            mod = __import__(mod_name, fromlist=[bp_attr])
            app.register_blueprint(getattr(mod, bp_attr))
        except (ImportError, AttributeError) as e:
            logger.warning(f"[App] 蓝图 {mod_name}.{bp_attr} 注册跳过（未实现）: {e}")

    # legacy_routes 可选
    try:
        from mobile_api_ai.api.legacy_routes import bp as legacy_bp
        app.register_blueprint(legacy_bp)
    except ImportError as e:
        logger.warning(f"[App] legacy_routes 蓝图注册跳过: {e}")

    # inventory_external 防腐层 API（桌面端 HTTP 调用）
    try:
        from inventory_web.routes_external import inventory_external_bp
        app.register_blueprint(inventory_external_bp)
        logger.info("[App] 已注册 inventory_external 防腐层蓝图")
    except (ImportError, AttributeError) as e:
        logger.warning(f"[App] inventory_external 蓝图注册跳过: {e}")

    # /api/all-process-tasks — 全部订单工序汇总
    @app.route('/api/all-process-tasks', methods=['GET'])
    def all_process_tasks():
        """
        全部订单工序汇总接口（手机端"工序任务"页面数据源）

        查询参数:
            order_no (str, optional): 按订单号模糊筛选
            page (int, optional): 页码（从 1 开始），与 size 同时传入时分页
            size (int, optional): 每页条数（1~200），与 page 同时传入时分页
            不传 page/size 时向后兼容，返回全量数据

        返回:
            data: 工序任务列表
            count: 当前页条数
            total: 总条数（仅分页时返回）
            page: 当前页码（仅分页时返回）
            size: 每页条数（仅分页时返回）
            total_pages: 总页数（仅分页时返回）

        修复说明：
        1. customer_group / product_name 兜底从 content JSON 字段读取
           （部分历史订单的扩展字段仅存于 content 中，DB 顶层列为空）
        2. processes 数组从 sub_steps 汇总构建，剔除 0 量噪声记录
           （原实现错误返回 workflow 节点 required_qty=0 的占位数据）
        3. total_completed_qty 改用各工序完成率均值 × 订单数量，
           与 /api/scan-info 保持一致，避免超过 quantity 出现"超额完成"显示
        4. 状态判定统一走 api.step_status_helper.compute_sub_step_statuses，
           避免今后与 /api/scan-info / dispatch_center 出现三端漂移
        5. 2026-06-09: 添加 page/size 分页参数（兼容旧客户端）
        """
        try:
            from mobile_api_ai.api.step_status_helper import compute_sub_step_statuses
            from container_center_v5 import ContainerCenter
            cc = ContainerCenter()
            all_records = cc.storage.get_all_process_records()
            filter_order = request.args.get('order_no', '').strip().upper()

            # 分页参数（兼容旧客户端：不传 page/size 时返回全量）
            page_str = request.args.get('page', '').strip()
            size_str = request.args.get('size', '').strip()
            has_pagination = bool(page_str) or bool(size_str)
            page = max(1, int(page_str)) if page_str else 1
            size = min(200, max(1, int(size_str))) if size_str else len(all_records)

            result = []
            for rec in all_records:
                ono = rec.get('order_no', '')
                if filter_order and filter_order not in ono.upper():
                    continue

                # 解析 content JSON（扩展字段兜底来源）
                content_raw = rec.get('content', '') or ''
                content = json.loads(content_raw) if isinstance(content_raw, str) and content_raw else (content_raw or {})

                sub_steps = cc.get_sub_steps(ono)
                required_qty = float(rec.get('quantity', 0) or 0)

                # 按子工序名聚合（过滤 quantity=0 的噪声记录）
                step_completed = {}
                sub_step_latest_map = {}
                for ss in sub_steps:
                    qty = float(ss.get('quantity', 0) or 0)
                    if qty <= 0:
                        continue
                    sn = ss.get('step_name', '')
                    step_completed[sn] = step_completed.get(sn, 0) + qty
                    sub_step_latest_map[sn] = ss

                # 统一真值源：与 /api/scan-info / dispatch_center 共用
                statuses = compute_sub_step_statuses(
                    sub_step_qty_map=step_completed,
                    required_qty=required_qty,
                    sub_step_latest_map=sub_step_latest_map,
                )

                # processes 数组（按工序名汇总，状态来自共享函数）
                processes = []
                items = list(step_completed.items())
                for i, ((sn, _), st) in enumerate(zip(items, statuses)):
                    processes.append({
                        'process_id': f'{ono}::{sn}',
                        'process_name': sn,
                        'required_qty': required_qty,
                        'completed_qty': st['completed_qty'],
                        'remaining_qty': st['remaining_qty'],
                        'status': st['status'],
                    })

                # 总完成量：各工序完成率均值 × 订单数量（与 scan-info 一致）
                if step_completed and required_qty > 0:
                    pcts = [min(1.0, q / required_qty) for q in step_completed.values()]
                    total_completed = round((sum(pcts) / len(pcts)) * required_qty)
                else:
                    total_completed = 0

                result.append({
                    'order_no': ono,
                    'product_name': rec.get('product_name', '') or content.get('product_type', ''),
                    'customer_group': (
                        rec.get('customer_group', '')
                        or rec.get('customer_name', '')
                        or content.get('customer_group', '')
                    ),
                    'quantity': required_qty,
                    'unit': rec.get('unit', ''),
                    'total_completed_qty': total_completed,
                    'total_remaining_qty': max(0, required_qty - total_completed),
                    'processes': processes,
                })

            total = len(result)
            if has_pagination:
                start = (page - 1) * size
                end = start + size
                paged = result[start:end]
            else:
                paged = result

            return jsonify({
                'code': 0,
                'data': paged,
                'count': len(paged),
                'total': total,
                'page': page,
                'size': size,
                'total_pages': max(1, (total + size - 1) // size) if size > 0 else 1,
            })
        except Exception as e:
            logger.exception('all-process-tasks 异常')
            return jsonify({'code': 500, 'message': 'all-process-tasks 查询失败'})

    # /api/process_sub_step — 手机报工入口（v5.0 简化：只做幂等去重，回归/修改统一走调度中心）
    @app.route('/api/process_sub_step', methods=['POST'])
    def process_sub_step():
        _log = logging.getLogger('process_sub_step')
        body = request.get_json(silent=True) or {}
        order_no = body.get('order_no', '').strip()
        # [P2 修复 2026-06-18 Bug #12] 字段名兼容
        # 修复前: 报工需要 step_name + operator → process_code + operator_name 报工失败
        # 修复后: 兼容所有命名 (step_name/process_code, operator/operator_name)
        step_name = (body.get('step_name') or body.get('process_name') or body.get('process_code') or '').strip()
        process_code_input = (body.get('process_code') or '').strip()
        try: quantity = float(body.get('quantity', 0))
        except (ValueError, TypeError): return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
        operator = (body.get('operator') or body.get('operator_name') or body.get('worker') or '').strip()
        batch_no = body.get('batch_no', '') or ''
        if not order_no or not step_name or not operator or quantity <= 0:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        # [P2 修复 2026-06-18] process_code 作为 step_name 时，优先用 process_code
        if process_code_input and not step_name:
            step_name = process_code_input
        # ① 校验订单在 steel_belt 是否存在
        try:
            from db.steelbelt_pool import cursor as sb_cursor
            _conn, _cur = sb_cursor()
            _cur.execute("SELECT 1 FROM orders WHERE order_no=%s LIMIT 1", (order_no,))
            if not _cur.fetchone():
                _conn.close()
                return jsonify({'code': 404, 'message': f'订单 {order_no} 未在桌面端创建'}), 404
            _conn.close()
        except Exception:
            pass
        # ① 同人同批次 → 幂等拦截（防重复点击）
        if batch_no:
            import pymysql
            try:
                from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
                try:
                    from core._db_pools import get_container_connection
                    _dc = get_container_connection(autocommit=True)
                except Exception:
                    _dc = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
                _dc_c = _dc.cursor()
                _dc_c.execute(
                    "SELECT id FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND batch_no=%s AND quantity > 0 LIMIT 1",
                    (order_no, step_name, batch_no))
                if _dc_c.fetchone():
                    _dc.close()
                    return jsonify({'code': 0, 'message': '已报工', 'success': True, 'idempotent': True})
                _dc.close()
            except Exception:
                pass
        # ② v4.0 改造: 改走 save_process_sub_step_with_pkg_update
        # [v3.8.1 修复] 原子化: 3 键去重 + process_sub_steps 写入 + 一次 commit.
        # [v3.8.1 废弃] 不再写 data_packages.completed_qty（SSOT 已切换到 process_sub_steps）
        try:
            from storage.mysql_storage import MySQLStorage
            _storage = MySQLStorage()
            _storage.connect()
            # [F16 T16.1 修复] process_names 表已被 F6 P9 DROP, 改用 core.config.get_process_code() 内存函数
            # (替代原 SELECT process_code FROM process_names, 避免 1146 WARNING)
            try:
                from core.config import get_process_code
                process_code = get_process_code(step_name)
            except Exception:
                process_code = ''
            _storage.save_process_sub_step_with_pkg_update(
                {
                    'order_no': order_no,
                    'step_name': step_name,
                    'process_code': process_code,
                    'operator': operator,
                    'quantity': quantity,
                    'batch_no': batch_no,
                    'status': 'pending',
                },
                pkg_order=order_no,
                pkg_process=step_name,
                qty_delta=quantity,
            )
        except Exception as e:
            _log.exception('写入 process_sub_steps 失败')
            return jsonify({'code': 500, 'message': '写入 process_sub_steps 失败'}), 500
        # ③ 同步桌面端
        from bridge.sync_client import send as sync_send
        sync_ok = sync_send('sub-step-report', {'order_no': order_no, 'step_name': step_name,
                                                'quantity': quantity, 'operator': operator})
        if not sync_ok:
            try:
                from container_center_v5 import ContainerCenter
                cc = ContainerCenter()
                cc.storage.enqueue_report({'order_no': order_no, 'step_name': step_name,
                                           'quantity': quantity, 'operator': operator})
            except Exception:
                pass
        return jsonify({'code': 0, 'message': f'报工已提交 ({step_name} +{quantity})', 'success': True})

    # ============= completed_qty SSOT 同步（v3.8.1 修复） =============
    # SSOT: 所有 completed_qty 均以 process_sub_steps 表为准，data_packages.completed_qty 已废弃
    def _sync_completed_qty_to_package(order_no, step_name, conn, cur):
        """[v3.8.1] 重算并回写 completed_qty 到 process_sub_steps（SSOT）
        
        修复前: UPDATE data_packages.completed_qty（死代码，无读者）
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

    # [v3.8.1 废弃] _add_completed_qty_to_package 函数已删除（从未被调用）

    # ------------- 撤回 -------------
    @app.route('/api/process_sub_step/withdraw', methods=['POST'])
    def withdraw_sub_step():
        body = request.get_json(silent=True) or {}
        sub_step_id = body.get('sub_step_id')
        operator = body.get('operator', '').strip()
        if not sub_step_id or not operator:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_sub_steps WHERE id=%s FOR UPDATE", (sub_step_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            existing = dict(zip(col, row))
            # 24h 时限检查
            from datetime import datetime, timedelta
            created = existing.get('created_at')
            if created and datetime.now() - created > timedelta(hours=24):
                conn.rollback(); conn.close()
                return jsonify({'code': 403, 'message': '超过 24h 修正期限'}), 403
            old_qty = float(existing.get('quantity', 0) or 0)
            # === RE-001: 窄边界事务 START (sub-steps 撤回) ===
            try:
                cur.execute("START TRANSACTION")
                # 1. 软删除 (主表)
                cur.execute("UPDATE process_sub_steps SET quantity=0 WHERE id=%s", (sub_step_id,))
                # 2. 写 history
                cur.execute(
                    "INSERT INTO process_sub_steps_history (original_id, order_no, step_name, batch_no, operator_before, operator_after, old_quantity, new_quantity, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (sub_step_id, existing.get('order_no', ''), existing.get('step_name', ''),
                     existing.get('batch_no', ''), existing.get('operator', ''), operator,
                     old_qty, 0, 'self_withdraw', operator))
                # 3. 同步 data_packages.completed_qty（重算）
                _sync_completed_qty_to_package(
                    existing.get('order_no', ''), existing.get('step_name', ''), conn, cur)
                cur.execute("COMMIT")
                logger.info('[RE-001] sub-steps 撤回事务 OK: sub_step_id=%s', sub_step_id)
                # ④ 同步桌面端（数量归零）
                try:
                    from bridge.sync_client import send as sync_send
                    sync_send('sub-step-report', {'order_no': existing.get('order_no', ''),
                                                  'step_name': existing.get('step_name', ''),
                                                  'quantity': -old_qty, 'operator': operator})
                except Exception:
                    pass
            except Exception as e:
                conn.rollback()
                logger.error('[RE-001] sub-steps 撤回事务回滚: sub_step_id=%s err=%s', sub_step_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            return jsonify({'code': 0, 'message': '已撤回', 'success': True})
        except Exception as e:
            logging.getLogger('withdraw').exception('撤回失败')
            return jsonify({'code': 500, 'message': '撤回失败'}), 500

    @app.route('/api/process_sub_step/history', methods=['GET'])
    def sub_step_history():
        order_no = request.args.get('order_no', '').strip()
        step_name = request.args.get('step_name', '').strip()
        if not order_no:
            return jsonify({'code': 400, 'message': '缺少 order_no'}), 400
        from container_center_v5 import ContainerCenter
        cc = ContainerCenter()
        records = cc.storage.get_history(order_no, step_name)
        return jsonify({'code': 0, 'data': records})

    # ============= 调度中心 · 报工记录管理 =============
    # /api/report_record/list — 报工记录列表（支持筛选/分页）
    @app.route('/api/report_record/list', methods=['GET'])
    def report_record_list():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            # 总数
            cur.execute(f"SELECT COUNT(*) FROM process_sub_steps s WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            # 分页
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT s.id, s.order_no, s.step_name, s.quantity, s.operator, s.batch_no, s.created_at "
                f"FROM process_sub_steps s WHERE {where_sql} ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            _log = logging.getLogger('report_record_list')
            _log.exception('查询失败')
            return jsonify({'code': 500, 'message': '修改失败'}), 500

    # /api/report_record/update — 调度员修改报工记录
    @app.route('/api/report_record/update', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def report_record_update():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        sub_step_id = body.get('sub_step_id')
        new_quantity = body.get('new_quantity')
        admin_user = body.get('admin_user', '').strip()  # 调度员账号
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
            # 追加上限校验
            try:
                cur.execute("SELECT quantity FROM process_records WHERE order_no=%s LIMIT 1", (order_no,))
                pr = cur.fetchone()
                order_req = float(pr[0]) if pr else 0
                # 查询该工序当前累计
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
            # === RE-001: 宽边界事务 START (sub-steps 修正: 3 表) ===
            try:
                cur.execute("START TRANSACTION")
                # 1. UPDATE process_sub_steps (主表)
                cur.execute("UPDATE process_sub_steps SET quantity=%s WHERE id=%s", (new_quantity, sub_step_id))
                # 2. INSERT process_sub_steps_history
                cur.execute(
                    "INSERT INTO process_sub_steps_history (original_id, order_no, step_name, batch_no, operator_before, operator_after, old_quantity, new_quantity, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (sub_step_id, order_no, step_name, batch_no,
                     old_operator, admin_user, old_qty, new_quantity, reason, admin_user))
                # 3. UPDATE process_records (宽边界: 必须一起提交)
                cur.execute("UPDATE process_records SET last_reverted_at=NOW() WHERE order_no=%s", (order_no,))
                # 4. 同步 data_packages.completed_qty（重算）
                _sync_completed_qty_to_package(order_no, step_name, conn, cur)
                cur.execute("COMMIT")
                logger.info('[RE-001] sub-steps 修正宽边界 OK: order=%s step=%s qty=%s',
                            order_no, step_name, new_quantity)
            except Exception as e:
                conn.rollback()
                logger.error('[RE-001] sub-steps 修正宽边界回滚: order=%s err=%s', order_no, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            # 通知原操作员
            try:
                from notify import notify_admin_modified
                notify_admin_modified(
                    original_operator=old_operator, admin_user=admin_user,
                    order_no=order_no, step_name=step_name,
                    old_qty=old_qty, new_qty=new_quantity, remark=remark)
            except Exception as e:
                logging.getLogger('report_record_update').warning(f'通知推送失败: {e}')
            # 同步桌面端
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

    # /api/report_record/withdraw — 调度员撤回报工记录
    @app.route('/api/report_record/withdraw', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def report_record_admin_withdraw():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        sub_step_id = body.get('sub_step_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not sub_step_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
            # === RE-001: 窄边界事务 START (sub-steps 撤回(2)) ===
            try:
                cur.execute("START TRANSACTION")
                # 1. 软删除 (主表)
                cur.execute("UPDATE process_sub_steps SET quantity=0 WHERE id=%s", (sub_step_id,))
                # 2. 写 history
                cur.execute(
                    "INSERT INTO process_sub_steps_history (original_id, order_no, step_name, batch_no, operator_before, operator_after, old_quantity, new_quantity, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (sub_step_id, order_no, step_name, batch_no,
                     old_operator, admin_user, old_qty, 0, reason, admin_user))
                # 3. 同步 data_packages.completed_qty（重算）
                _sync_completed_qty_to_package(order_no, step_name, conn, cur)
                cur.execute("COMMIT")
                logger.info('[RE-001] sub-steps 撤回(2)事务 OK: sub_step_id=%s', sub_step_id)
            except Exception as e:
                conn.rollback()
                logger.error('[RE-001] sub-steps 撤回(2)事务回滚: sub_step_id=%s err=%s', sub_step_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            conn.close()
            # 通知原操作员
            try:
                from notify import notify_admin_withdraw
                notify_admin_withdraw(
                    original_operator=old_operator, admin_user=admin_user,
                    order_no=order_no, step_name=step_name, old_qty=old_qty)
            except Exception as e:
                logging.getLogger('admin_withdraw').warning(f'通知推送失败: {e}')
            # 同步桌面端（数量归零）
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

    # /api/report_record/history_full — 单条记录的完整审计历史
    @app.route('/api/report_record/history_full', methods=['GET'])
    def report_record_history_full():
        sub_step_id = request.args.get('sub_step_id', '').strip()
        if not sub_step_id:
            return jsonify({'code': 400, 'message': '缺少 sub_step_id'}), 400
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_sub_steps WHERE id=%s", (sub_step_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM process_sub_steps_history WHERE original_id=%s ORDER BY reverted_at DESC",
                (sub_step_id,))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # ============= 调度中心 · 质检回归审计 =============
    # /api/quality_record/list — 质检记录列表（支持筛选/分页）
    @app.route('/api/quality_record/list', methods=['GET'])
    def quality_record_list():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM container_center.quality_records qr WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT qr.* FROM container_center.quality_records qr WHERE {where_sql} ORDER BY qr.record_date DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            # 补充审计历史条数（IN 子查询，避免全表 GROUP BY）
            ids = [str(r['id']) for r in rows]
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(
                    f"SELECT record_id, COUNT(*) as cnt FROM container_center.data_regression_history WHERE data_type='quality' AND record_id IN ({placeholders}) GROUP BY record_id",
                    ids)
                hist_counts = {str(r[0]): r[1] for r in cur.fetchall()}
                for row in rows:
                    row['history_count'] = hist_counts.get(str(row.get('id', '')), 0)
            conn.close()
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            _log = logging.getLogger('quality_record_list')
            _log.exception('查询失败')
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # /api/quality_record/update — 调度员修改质检记录
    @app.route('/api/quality_record/update', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def quality_record_update():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
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
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
            # === RE-001: 事务包裹 START (quality 修正) ===
            try:
                with conn.cursor() as c:
                    c.execute("START TRANSACTION")
                    # 1. UPDATE 主表
                    c.execute(
                        "UPDATE container_center.quality_records SET result=%s WHERE id=%s",
                        (new_result, record_id)
                    )
                    # 2. INSERT history
                    c.execute(
                        "INSERT INTO container_center.data_regression_history "
                        "(data_type, record_id, order_no, step_name, field_before, field_after, "
                        "operator_before, operator_after, revert_reason, reverted_by) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        ('quality', str(record_id), order_no, step_name,
                         json.dumps({'result': old_result}), json.dumps({'result': new_result}),
                         existing.get('inspector', ''), admin_user, reason, admin_user)
                    )
                    c.execute("COMMIT")
                    logging.getLogger('quality_record_update').info(
                        '[RE-001] quality 修正事务 OK: record_id=%s', record_id)
            except Exception as e:
                conn.rollback()
                logging.getLogger('quality_record_update').error(
                    '[RE-001] quality 修正事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            # === RE-001: 事务包裹 END ===
            conn.close()
            # 通知原质检员
            try:
                from notify import notify_quality_modified
                notify_quality_modified(
                    inspector=existing.get('inspector', ''), admin_user=admin_user,
                    order_no=order_no, step_name=step_name,
                    old_result=old_result, new_result=new_result, remark=remark)
            except Exception as e:
                logging.getLogger('quality_record_update').warning(f'通知推送失败: {e}')
            # 同步桌面端
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

    # /api/quality_record/withdraw — 调度员撤回质检记录
    @app.route('/api/quality_record/withdraw', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def quality_record_admin_withdraw():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not record_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
            # === RE-001: 事务包裹 START (quality 撤回) ===
            try:
                with conn.cursor() as c:
                    c.execute("START TRANSACTION")
                    # 1. UPDATE 主表 (软删除)
                    c.execute(
                        "UPDATE container_center.quality_records SET status='withdrawn' WHERE id=%s",
                        (record_id,)
                    )
                    # 2. INSERT history
                    c.execute(
                        "INSERT INTO container_center.data_regression_history "
                        "(data_type, record_id, order_no, step_name, field_before, field_after, "
                        "operator_before, operator_after, revert_reason, reverted_by) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        ('quality', str(record_id), order_no, step_name,
                         json.dumps({'status': 'active', 'result': old_result}),
                         json.dumps({'status': 'withdrawn', 'result': ''}),
                         inspector, admin_user, reason, admin_user)
                    )
                    c.execute("COMMIT")
                    logging.getLogger('quality_withdraw').info(
                        '[RE-001] quality 撤回事务 OK: record_id=%s', record_id)
            except Exception as e:
                conn.rollback()
                logging.getLogger('quality_withdraw').error(
                    '[RE-001] quality 撤回事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            # === RE-001: 事务包裹 END ===
            conn.close()
            # 通知原质检员
            try:
                from notify import notify_quality_withdraw
                notify_quality_withdraw(
                    inspector=inspector, admin_user=admin_user,
                    order_no=order_no, step_name=step_name, old_result=old_result)
            except Exception as e:
                logging.getLogger('quality_withdraw').warning(f'通知推送失败: {e}')
            # 同步桌面端
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

    # /api/quality_record/history_full — 单条质检记录的完整审计历史
    @app.route('/api/quality_record/history_full', methods=['GET'])
    def quality_record_history_full():
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id'}), 400
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM container_center.quality_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='quality' AND record_id=%s ORDER BY created_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # ============= 调度中心 · 物料回归审计 =============
    # /api/material_record/list — 物料记录列表
    @app.route('/api/material_record/list', methods=['GET'])
    def material_record_list():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        try:
            order_no = request.args.get('order_no', '').strip()
            material_name = request.args.get('material_name', '').strip()
            operator = request.args.get('operator', '').strip()
            start_date = request.args.get('start_date', '').strip()
            end_date = request.args.get('end_date', '').strip()
            page = max(1, int(request.args.get('page', 1)))
            page_size = min(100, max(10, int(request.args.get('page_size', 20))))
            where = ["dp.source='material_purchase'"]  # material_records 使用 source 字段
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM material_records dp WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT dp.* FROM material_records dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            # [前端兼容 v3.8.1] 字段别名映射
            for row in rows:
                row['type'] = 'material'  # 前端需要
                row['related_order'] = row.get('order_no', '')  # 前端需要
                row['related_process'] = row.get('material_name', '')  # 前端需要
                row['quantity'] = row.get('planned_qty', 0)  # 前端需要
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            _log = logging.getLogger('material_record_list')
            _log.exception('查询失败')
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # /api/material_record/update — 调度员修改物料记录
    @app.route('/api/material_record/update', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def material_record_update():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
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
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
                    ('material', str(record_id), order_no, existing.get('title', ''),
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

    # /api/material_record/withdraw — 调度员撤回物料记录
    @app.route('/api/material_record/withdraw', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def material_record_admin_withdraw():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not record_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM material_records WHERE id=%s FOR UPDATE", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            existing = dict(zip(col, row))
            old_qty = float(existing.get('planned_qty', 0) or 0)
            order_no = existing.get('order_no', '')
            try:
                cur.execute("START TRANSACTION")
                cur.execute("UPDATE material_records SET planned_qty=0, status='material_withdrawn', updated_at=NOW() WHERE id=%s", (record_id,))
                cur.execute(
                    "INSERT INTO container_center.data_regression_history "
                    "(data_type, record_id, order_no, step_name, field_before, field_after, "
                    "operator_before, operator_after, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ('material', str(record_id), order_no, existing.get('title', ''),
                     json.dumps({'planned_qty': old_qty}), json.dumps({'planned_qty': 0}),
                     existing.get('operator_id', ''), admin_user, reason, admin_user))
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

    # /api/material_record/history_full — 单条物料记录的完整审计历史
    @app.route('/api/material_record/history_full', methods=['GET'])
    def material_record_history_full():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id 参数'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM material_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='material' AND record_id=%s ORDER BY created_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # ============= 调度中心 · 外协回归审计 =============
    @app.route('/api/outsource_record/list', methods=['GET'])
    def outsource_record_list():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM outsource_records dp WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT dp.* FROM outsource_records dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            conn.close()
            # [前端兼容 v3.8.1] 字段别名映射
            for row in rows:
                row['type'] = 'outsource'  # 前端需要
                row['related_order'] = row.get('order_no', '')  # 前端需要
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            _log = logging.getLogger('outsource_record_list')
            _log.exception('查询失败')
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    @app.route('/api/outsource_record/update', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def outsource_record_update():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
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
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
                    ('outsource', str(record_id), order_no, existing.get('title', ''),
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

    @app.route('/api/outsource_record/withdraw', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def outsource_record_admin_withdraw():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not record_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM outsource_records WHERE id=%s FOR UPDATE", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            existing = dict(zip(col, row))
            old_qty = float(existing.get('quantity', 0) or 0)
            order_no = existing.get('order_no', '')
            try:
                cur.execute("START TRANSACTION")
                cur.execute("UPDATE outsource_records SET quantity=0, status='outsource_withdrawn', updated_at=NOW() WHERE id=%s", (record_id,))
                cur.execute(
                    "INSERT INTO container_center.data_regression_history "
                    "(data_type, record_id, order_no, step_name, field_before, field_after, "
                    "operator_before, operator_after, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ('outsource', str(record_id), order_no, existing.get('title', ''),
                     json.dumps({'quantity': old_qty}), json.dumps({'quantity': 0}),
                     existing.get('operator_id', ''), admin_user, reason, admin_user))
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

    @app.route('/api/outsource_record/history_full', methods=['GET'])
    def outsource_record_history_full():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id 参数'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM outsource_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='outsource' AND record_id=%s ORDER BY created_at DESC",
                (str(record_id),))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # ============= 调度中心 · 排产回归审计 =============
    @app.route('/api/schedule_record/list', methods=['GET'])
    def schedule_record_list():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        try:
            order_no = request.args.get('order_no', '').strip()
            operator = request.args.get('operator', '').strip()
            start_date = request.args.get('start_date', '').strip()
            end_date = request.args.get('end_date', '').strip()
            page = max(1, int(request.args.get('page', 1)))
            page_size = min(100, max(10, int(request.args.get('page_size', 20))))
            where = ["1=1", "dp.status NOT IN ('withdrawn')"]  # schedule_records 没有 data_type 字段
            params = []
            if order_no:
                where.append("(dp.order_no LIKE %s OR dp.product_name LIKE %s)")
                params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
            if operator:
                where.append("dp.operator_id LIKE %s")
                params.append(f"%{operator}%")
            if start_date:
                where.append("dp.created_at >= %s"); params.append(start_date)
            if end_date:
                where.append("dp.created_at <= %s"); params.append(end_date)
            where_sql = " AND ".join(where)
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM schedule_records dp WHERE {where_sql}", params)
            total = cur.fetchone()[0]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT dp.* FROM schedule_records dp WHERE {where_sql} ORDER BY dp.created_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            ids = [str(r['id']) for r in rows]
            if ids:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(
                    f"SELECT record_id, COUNT(*) as cnt FROM container_center.data_regression_history WHERE data_type='schedule' AND record_id IN ({placeholders}) GROUP BY record_id",
                    ids)
                hist_counts = {str(r[0]): r[1] for r in cur.fetchall()}
                for row in rows:
                    row['history_count'] = hist_counts.get(str(row.get('id', '')), 0)
            conn.close()
            # [前端兼容 v3.8.1] 字段别名映射
            for row in rows:
                row['data_type'] = 'schedule'  # 前端需要
                row['related_order'] = row.get('order_no', '')  # 前端需要
                row['title'] = row.get('product_name', '')  # 前端需要
                row['target_operator'] = row.get('operator_id', '')  # 前端需要
            return jsonify({'code': 0, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})
        except Exception as e:
            _log = logging.getLogger('schedule_record_list')
            _log.exception('查询失败')
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # /api/schedule_record/update — 调度员修改排产记录
    @app.route('/api/schedule_record/update', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def schedule_record_update():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_force')
        updates = {}
        for k in ('title', 'content', 'priority', 'target_operator', 'status'):
            v = body.get(k)
            if v is not None:
                updates[k] = str(v).strip()
        if not record_id or not admin_user or not updates:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM schedule_records WHERE id=%s FOR UPDATE", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            existing = dict(zip(col, row))
            # [安全 v3.8.1] 字段白名单校验：仅允许修改指定字段
            ALLOWED_SCHEDULE_UPDATE_FIELDS = {'title', 'target_operator', 'status', 'priority'}
            invalid_fields = set(updates.keys()) - ALLOWED_SCHEDULE_UPDATE_FIELDS
            if invalid_fields:
                conn.rollback(); conn.close()
                logger.warning('[schedule_record_update] 非法字段: %s', invalid_fields)
                return jsonify({'code': 400, 'message': f'字段不允许修改: {invalid_fields}'}), 400
            existing_mapped = {
                'title': existing.get('product_name', ''),
                'target_operator': existing.get('operator_id', ''),
                'status': existing.get('status', ''),
                'priority': existing.get('priority', ''),
            }
            old_vals = {k: existing_mapped.get(k, '') for k in updates}
            has_change = False
            for k, v in updates.items():
                if str(existing_mapped.get(k, '')) != str(v):
                    has_change = True
                    break
            if not has_change:
                conn.rollback(); conn.close()
                return jsonify({'code': 0, 'message': '无变化', 'unchanged': True})
            # === RE-001: 窄边界事务 START (schedule 修正) ===
            try:
                cur.execute("START TRANSACTION")
                # 字段映射：前端字段 -> 数据库字段
                db_updates = {}
                if 'title' in updates:
                    db_updates['product_name'] = updates['title']
                if 'target_operator' in updates:
                    db_updates['operator_id'] = updates['target_operator']
                if 'status' in updates:
                    db_updates['status'] = updates['status']
                if 'priority' in updates:
                    db_updates['priority'] = updates['priority']
                if db_updates:
                    set_clause = ', '.join([f"{k}=%s" for k in db_updates]) + ", updated_at=NOW()"
                    args = list(db_updates.values()) + [record_id]
                    cur.execute(f"UPDATE schedule_records SET {set_clause} WHERE id=%s", args)
                cur.execute(
                    "INSERT INTO container_center.data_regression_history "
                    "(data_type, record_id, order_no, step_name, field_before, field_after, operator_before, operator_after, revert_reason, reverted_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ('schedule', record_id, existing.get('order_no', ''), '',
                     json.dumps(old_vals), json.dumps(updates),
                     existing.get('operator_id', ''), admin_user, reason, admin_user))
                cur.execute("COMMIT")
                logging.getLogger('schedule_record_update').info(
                    '[RE-001] schedule 修正事务 OK: record_id=%s', record_id)
            except Exception as e:
                conn.rollback()
                logging.getLogger('schedule_record_update').error(
                    '[RE-001] schedule 修正事务回滚: record_id=%s err=%s', record_id, e, exc_info=True)
                conn.close()
                return jsonify({'code': 500, 'message': '事务失败,已回滚'}), 500
            # === RE-001: 事务包裹 END ===
            conn.close()
            return jsonify({'code': 0, 'message': '排产记录已修改', 'success': True})
        except Exception as e:
            logging.getLogger('schedule_record_update').exception('修改失败')
            return jsonify({'code': 500, 'message': '修改失败'}), 500

    # /api/schedule_record/withdraw — 调度员撤回排产记录
    @app.route('/api/schedule_record/withdraw', methods=['POST'])
    @require_admin
    @limiter.limit("10 per minute")
    def schedule_record_admin_withdraw():
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id')
        admin_user = body.get('admin_user', '').strip()
        reason = body.get('reason', 'admin_withdraw')
        if not record_id or not admin_user:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
                return jsonify({'code': 409, 'message': '已撤回，请勿重复操作'}), 409
            # === RE-001: 窄边界事务 START (schedule 撤回) ===
            try:
                cur.execute("START TRANSACTION")
                cur.execute("UPDATE schedule_records SET status='withdrawn', updated_at=NOW() WHERE id=%s AND status!='withdrawn'", (record_id,))
                if cur.rowcount == 0:
                    conn.rollback()
                    conn.close()
                    return jsonify({'code': 409, 'message': '状态已变更，请刷新'}), 409
                cur.execute(
                    "INSERT INTO container_center.data_regression_history "
                    "(data_type, record_id, order_no, step_name, field_before, field_after, operator_before, operator_after, revert_reason, reverted_by) "
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
            # === RE-001: 事务包裹 END ===
            conn.close()
            return jsonify({'code': 0, 'message': '已撤回排产记录', 'success': True})
        except Exception as e:
            logging.getLogger('schedule_withdraw').exception('撤回失败')
            return jsonify({'code': 500, 'message': '撤回失败'}), 500

    # /api/schedule_record/history_full — 单条排产记录的完整审计历史
    @app.route('/api/schedule_record/history_full', methods=['GET'])
    def schedule_record_history_full():
        record_id = request.args.get('record_id', '').strip()
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id'}), 400
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        try:
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            cur = conn.cursor()
            cur.execute("SELECT * FROM schedule_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({'code': 404, 'message': '记录不存在'}), 404
            col = [d[0] for d in cur.description]
            rec = dict(zip(col, row))
            cur.execute(
                "SELECT * FROM container_center.data_regression_history WHERE data_type='schedule' AND record_id=%s ORDER BY reverted_at DESC",
                (record_id,))
            hcol = [d[0] for d in cur.description]
            history = [dict(zip(hcol, r)) for r in cur.fetchall()]
            conn.close()
            return jsonify({'code': 0, 'data': {'record': rec, 'history': history}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    from config_center import config_center_bp
    app.register_blueprint(config_center_bp)

    # sync_bridge 已迁移到 main.py (端口 8008)
    # from sync_bridge import sync_bp
    # app.register_blueprint(sync_bp)

    from dispatch_center.schedule_routes import schedule_bp, workorder_bp
    app.register_blueprint(schedule_bp)
    app.register_blueprint(workorder_bp)

    from wecom_auth import bp as wecom_bp
    app.register_blueprint(wecom_bp)

    # API v1 蓝图始终注册（S5-03: 版本化路由）
    from api_v1 import api_v1_bp
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    logger.info("[App] API v1蓝图已注册（始终启用）")

    if os.getenv('ENABLE_TRACING', 'true') == 'true':
        try:
            from request_tracing import init_tracing
            init_tracing(app)
            logger.info("[App] 请求追踪中间件已启用")
        except Exception as e:
            logger.warning(f"[App] 请求追踪中间件初始化失败: {e}")

    @app.route('/health')
    def health():
        return jsonify({'code': 0, 'message': 'success', 'data': {'service': 'mobile-report-ai', 'mode': 'production'}})

    @app.route('/api/tasks', methods=['GET'])
    def proxy_tasks():
        """手机报工分区分流 - 查询独立业务表"""
        from flask import request
        from models.database import get_connection_context

        page_route = request.args.get('page_route', None)

        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                tasks = []

                if page_route == 'material' or page_route is None:
                    cursor.execute('SELECT * FROM material_records ORDER BY created_at DESC LIMIT 100')
                    for row in cursor.fetchall():
                        col = [d[0] for d in cursor.description]
                        t = dict(zip(col, row))
                        t['data_type'] = 'material'
                        t['completed_qty'] = float(t.get('planned_qty', 0) or 0)
                        t['page_route'] = 'material'
                        if isinstance(t.get('content'), str):
                            try: t['content'] = json.loads(t['content'])
                            except Exception: pass
                        tasks.append(t)

                if page_route == 'outsource' or page_route is None:
                    cursor.execute('SELECT * FROM outsource_records ORDER BY created_at DESC LIMIT 100')
                    for row in cursor.fetchall():
                        col = [d[0] for d in cursor.description]
                        t = dict(zip(col, row))
                        t['data_type'] = 'outsource'
                        t['completed_qty'] = float(t.get('quantity', 0) or 0)
                        t['page_route'] = 'outsource'
                        tasks.append(t)

                if page_route == 'scan_report' or page_route is None:
                    cursor.execute('SELECT * FROM process_sub_steps ORDER BY created_at DESC LIMIT 100')
                    for row in cursor.fetchall():
                        col = [d[0] for d in cursor.description]
                        t = dict(zip(col, row))
                        t['data_type'] = 'report'
                        t['completed_qty'] = float(t.get('quantity', 0) or 0)
                        t['page_route'] = 'scan_report'
                        tasks.append(t)

                return jsonify({'code': 0, 'data': {'tasks': tasks, 'total': len(tasks)}})
        except Exception as e:
            logger.error(f'[分流] 查询失败: {e}')
            return jsonify({'code': -1, 'message': '查询失败'}), 500

    # ─── 物料任务操作 API ───
    MATERIAL_FLOW = [
        {'name': '物料申请', 'key': 'material_requested'},
        {'name': '任务确认', 'key': 'material_confirmed'},
        {'name': '入库通知', 'key': 'material_arrived'},
        {'name': '物料出库', 'key': 'material_delivered'},
    ]

    @app.route('/api/material/confirm', methods=['POST'])
    @require_auth
    def material_confirm():
        from models.database import get_connection_context
        data = request.get_json(silent=True) or {}
        pkg_id = data.get('id', '')
        if not pkg_id:
            return jsonify({'code': -1, 'message': 'id 不能为空'}), 400
        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM material_records WHERE id=%s FOR UPDATE', (pkg_id,))
                pkg = cursor.fetchone()
                if not pkg:
                    return jsonify({'code': -1, 'message': '物料任务不存在'}), 404
                col = [d[0] for d in cursor.description]
                pkg_dict = dict(zip(col, pkg))
                if pkg_dict.get('status') != '缺料':
                    return jsonify({'code': -1, 'message': '只有缺料状态才能确认'}), 400
                content = pkg_dict.get('content', {})
                if isinstance(content, str):
                    try: content = json.loads(content)
                    except: content = {}
                content['deadline'] = data.get('deadline', '')
                content['arrival_date'] = data.get('arrival_date', '')
                content['confirmed_by'] = data.get('operator', '')
                content['confirmed_at'] = __import__('datetime').datetime.now().isoformat()
                cursor.execute('UPDATE material_records SET status=%s, content=%s, updated_at=NOW() WHERE id=%s',
                    ('material_confirmed', json.dumps(content, ensure_ascii=False), pkg_id))
                conn.commit()
                logger.info(f'[物料] 任务已确认: {pkg_id}')
                return jsonify({'code': 0, 'data': {'id': pkg_id, 'status': 'material_confirmed'}})
        except Exception as e:
            logger.error(f'[物料] 确认失败: {type(e).__name__}')
            return jsonify({'code': -1, 'message': '操作失败'}), 500

    def _find_mat_pkg(material_name, order_no=""):
        from models.database import get_connection_context
        clean = material_name.replace("备料-", "").strip()
        with get_connection_context() as conn:
            conn.select_db("container_center")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM material_records WHERE material_name=%s LIMIT 1", (clean,))
            return cursor.fetchone()
    @app.route('/api/material/arrived', methods=['POST'])
    @require_auth
    def material_arrived():

        data = request.get_json(silent=True) or {}
        pkg_id = data.get('id', '')
        if not pkg_id:
            pkg = _find_mat_pkg(data.get('material_name', ''), data.get('order_no', ''))
            if not pkg: return jsonify({'code': -1, 'message': '物料任务不存在'}), 404
            pkg_id = pkg['id']
        from models.database import get_connection_context
        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM material_records WHERE id=%s FOR UPDATE', (pkg_id,))
                existing = cursor.fetchone()
                if not existing:
                    return jsonify({'code': -1, 'message': '物料任务不存在'}), 404
                col = [d[0] for d in cursor.description]
                existing_dict = dict(zip(col, existing))
                if existing_dict.get('status') not in ['material_confirmed', '缺料']:
                    return jsonify({'code': -1, 'message': '状态不是已确认，请刷新'}), 400
                cursor.execute('UPDATE material_records SET status=%s, arrival_date=NOW(), updated_at=NOW() WHERE id=%s AND status IN (%s, %s)',
                    ('material_arrived', pkg_id, 'material_confirmed', '缺料'))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return jsonify({'code': 409, 'message': '状态已变更，请刷新'}), 409
                conn.commit()
                logger.info(f'[物料] 已到货: {pkg_id}')
                return jsonify({'code': 0, 'data': {'id': pkg_id, 'status': 'material_arrived'}})
        except Exception as e:
            logger.error(f'[物料] 到货失败: {e}')
            return jsonify({'code': -1, 'message': '操作失败'}), 500

    @app.route('/api/material/delivered', methods=['POST'])
    @require_auth
    def material_delivered():
        data = request.get_json(silent=True) or request.get_json(force=True, silent=True) or {}
        if not data:
            try: data = __import__('json').loads(request.get_data().decode('gbk'))
            except Exception: data = {}
        pkg_id = data.get('id', '')
        if not pkg_id:
            pkg = _find_mat_pkg(data.get('material_name', ''), data.get('order_no', ''))
            if not pkg: return jsonify({'code': -1, 'message': '物料任务不存在'}), 404
            pkg_id = pkg['id']
        from models.database import get_connection_context
        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM material_records WHERE id=%s FOR UPDATE', (pkg_id,))
                existing = cursor.fetchone()
                if not existing:
                    return jsonify({'code': -1, 'message': '物料任务不存在'}), 404
                col = [d[0] for d in cursor.description]
                existing_dict = dict(zip(col, existing))
                if existing_dict.get('status') not in ['material_confirmed', 'material_arrived', '缺料']:
                    return jsonify({'code': -1, 'message': '状态不是已确认或已到货'}), 400
                cursor.execute('UPDATE material_records SET status=%s, updated_at=NOW() WHERE id=%s AND status IN (%s, %s, %s)',
                    ('material_delivered', pkg_id, 'material_confirmed', 'material_arrived', '缺料'))
                if cursor.rowcount == 0:
                    conn.rollback()
                    return jsonify({'code': 409, 'message': '状态已变更，请刷新'}), 409
                conn.commit()
                logger.info(f'[物料] 已出库: {pkg_id}')
                return jsonify({'code': 0, 'data': {'id': pkg_id, 'status': 'material_delivered'}})
        except Exception as e:
            # [安全 v3.8.1] 不返回 str(e)
            logger.error(f'[物料] 出库失败: {type(e).__name__}')
            return jsonify({'code': -1, 'message': '操作失败'}), 500

    @app.route('/api/material/requirements', methods=['GET'])
    def material_requirements():
        """物料缺料列表 - 直接查 steel_belt.order_materials（不依赖 5003）"""
        try:
            from core._db_pools import get_steel_belt_connection
            conn = get_steel_belt_connection(autocommit=False)
            import pymysql
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("""
                SELECT om.id, om.order_id, om.material_name, om.spec, om.unit,
                       om.required_qty, om.prepared_qty, om.prep_status,
                       om.created_at, om.updated_at,
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
                required_qty = float(r.get('required_qty') or 0)
                prepared_qty = float(r.get('prepared_qty') or 0)
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
            return jsonify({'code': 0, 'data': records})
        except Exception as e:
            return jsonify({'code': -1, 'message': '查询失败'}), 500

    @app.route('/api/material/<pkg_id>', methods=['GET'])
    def material_detail(pkg_id):
        from models.database import get_connection_context
        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM material_records WHERE id=%s', (pkg_id,))
                pkg = cursor.fetchone()
                if not pkg:
                    return jsonify({'code': -1, 'message': '物料任务不存在'}), 404
                if isinstance(pkg.get('content'), str):
                    try: pkg['content'] = json.loads(pkg['content'])
                    except Exception: pass
                current = pkg.get('status', '')
                pkg['flow'] = []
                for i, step in enumerate(MATERIAL_FLOW):
                    cur_idx = next((j for j, s in enumerate(MATERIAL_FLOW) if s['key'] == current), 0)
                    st = 'completed' if i < cur_idx else ('active' if step['key'] == current else 'pending')
                    pkg['flow'].append({**step, 'status': st})
                return jsonify({'code': 0, 'data': pkg})
        except Exception as e:
            return jsonify({'code': -1, 'message': '查询失败'}), 500

    @app.route('/api/material/return', methods=['POST'])
    @require_auth
    def material_return():
        """退料：减少物料数量"""
        import pymysql, json
        from datetime import datetime
        body = request.get_json(silent=True) or {}
        pkg_id = body.get('pkg_id', '')
        try: return_qty = float(body.get('return_qty', 0))
        except (ValueError, TypeError): return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
        operator = body.get('operator', '')
        if not pkg_id or return_qty <= 0:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
            from core.db import get_direct_connection
            conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            c = conn.cursor()
            c.execute("SELECT * FROM material_records WHERE id=%s FOR UPDATE", (pkg_id,))
            pkg = c.fetchone()
            if not pkg:
                conn.close()
                return jsonify({'code': 404, 'message': '任务不存在'}), 404
            ct = json.loads(pkg['content']) if isinstance(pkg.get('content'), str) else (pkg.get('content') or {})
            old_qty = float(ct.get('quantity', pkg.get('planned_qty', 0)))
            new_qty = max(0, old_qty - return_qty)
            ct['quantity'] = new_qty
            ct['return_qty'] = ct.get('return_qty', 0) + return_qty
            ct['return_count'] = ct.get('return_count', 0) + 1
            ct['return_operator'] = operator
            ct['return_time'] = datetime.now().isoformat()
            c.execute("UPDATE material_records SET content=%s, planned_qty=%s, updated_at=NOW() WHERE id=%s",
                      (json.dumps(ct, ensure_ascii=False), new_qty, pkg_id))
            conn.commit()
            conn.close()
            return jsonify({'code': 0, 'message': f'已退料 {return_qty}', 'data': {'new_qty': new_qty}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '操作失败'}), 500

    @app.route('/api/material/replenish', methods=['POST'])
    @require_auth
    def material_replenish():
        """补料：新增物料需求"""
        import pymysql, json
        from datetime import datetime
        body = request.get_json(silent=True) or {}
        pkg_id = body.get('pkg_id', '')
        try: add_qty = float(body.get('add_qty', 0))
        except (ValueError, TypeError): return jsonify({'code': 400, 'message': '数量必须为数字'}), 400
        operator = body.get('operator', '')
        if not pkg_id or add_qty <= 0:
            return jsonify({'code': 400, 'message': '参数不完整'}), 400
        try:
            from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
            from core.db import get_direct_connection
            conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            c = conn.cursor()
            c.execute("SELECT * FROM material_records WHERE id=%s FOR UPDATE", (pkg_id,))
            pkg = c.fetchone()
            if not pkg:
                conn.close()
                return jsonify({'code': 404, 'message': '任务不存在'}), 404
            ct = json.loads(pkg['content']) if isinstance(pkg.get('content'), str) else (pkg.get('content') or {})
            old_qty = float(ct.get('quantity', pkg.get('planned_qty', 0)))
            new_qty = old_qty + add_qty
            ct['quantity'] = new_qty
            ct['replenish_qty'] = ct.get('replenish_qty', 0) + add_qty
            ct['replenish_count'] = ct.get('replenish_count', 0) + 1
            ct['replenish_operator'] = operator
            ct['replenish_time'] = datetime.now().isoformat()
            log = ct.get('replenish_log', [])
            log.append({'qty': add_qty, 'operator': operator, 'time': ct['replenish_time'], 'round': ct['replenish_count']})
            ct['replenish_log'] = log
            c.execute("UPDATE material_records SET content=%s, planned_qty=%s, updated_at=NOW() WHERE id=%s",
                      (json.dumps(ct, ensure_ascii=False), new_qty, pkg_id))
            conn.commit()
            conn.close()
            return jsonify({'code': 0, 'message': f'已补料 {add_qty}', 'data': {'new_qty': new_qty}})
        except Exception as e:
            return jsonify({'code': 500, 'message': '操作失败'}), 500

    @app.route('/api/warehousing/pending', methods=['GET'])
    def warehousing_pending():
        _dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
        try:
            import requests as _http
            resp = _http.get(f'{_dispatch_url}/api/dispatch-center/pending-warehousing', timeout=5)
            return jsonify(resp.json())
        except Exception as e:
            logger.error(f'获取待入库列表失败: {e}')
            return jsonify({'code': 500, 'message': '获取待入库列表失败', 'data': []})

    @app.route('/api/warehousing/confirm', methods=['POST'])
    def warehousing_confirm():
        _data = request.get_json(silent=True) or {}
        _process_id = _data.get('process_id') or _data.get('id')
        if not _process_id:
            return jsonify({'code': 400, 'message': '缺少 process_id 参数'})
        _dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
        try:
            import requests as _http
            resp = _http.post(
                f'{_dispatch_url}/api/dispatch-center/processes/{_process_id}/confirm',
                json={'operator_name': '报工系统'},
                timeout=5
            )
            return jsonify(resp.json())
        except Exception as e:
            logger.error(f'入库确认失败: {e}')
            return jsonify({'code': 500, 'message': '入库确认失败'})



    @app.route('/')
    def index():
        """统一移动端页面（含摄像头扫码报工）"""
        return render_template('mobile_unified.html')

    @app.route('/scanner')
    def scanner_page():
        """扫码页面"""
        return render_template('scanner.html')

    @app.route('/api/wechat/pool/report', methods=['POST'])
    def scanner_report_api():
        """扫码报工 — 直写 process_sub_steps（不再依赖 Worker 队列）"""
        _log = logging.getLogger('scanner_report')
        try:
            _data = request.get_json(silent=True) or {}
            _task_id = _data.get('task_id', '') or _data.get('id', '')
            _order_no = _data.get('order_no', '')
            _process = _data.get('process', '') or _data.get('process_name', '')
            _qty_raw = _data.get('quantity', None)
            if _qty_raw is None:
                _qty_raw = _data.get('completed_qty', 0)
            _quantity = float(_qty_raw) if _qty_raw else 0
            _operator = _data.get('worker', '') or _data.get('operator', '') or _data.get('operator_name', '')
            _batch_no = _data.get('batch_no', '') or ''

            if not _operator:
                return jsonify({'code': 400, 'message': '缺少操作员信息，请重新登录'})
            if not _order_no:
                return jsonify({'code': 400, 'message': '缺少订单号，请扫码或输入工单号'})
            if not _process:
                return jsonify({'code': 400, 'message': '缺少工序名称，请选择工序'})
            if _quantity <= 0:
                return jsonify({'code': 400, 'message': '报工数量必须大于0'})

            # ① 幂等去重（同人同批次）
            if _batch_no:
                import pymysql
                from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
                try:
                    try:
                        from core._db_pools import get_container_connection
                        _dc = get_container_connection(autocommit=True)
                    except Exception:
                        _dc = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
                    _dc_c = _dc.cursor()
                    _dc_c.execute(
                        "SELECT id FROM process_sub_steps WHERE order_no=%s AND step_name=%s AND batch_no=%s AND quantity > 0 LIMIT 1",
                        (_order_no, _process, _batch_no))
                    if _dc_c.fetchone():
                        _dc.close()
                        return jsonify({'code': 0, 'message': '已报工', 'success': True, 'idempotent': True})
                    _dc.close()
                except Exception:
                    pass

            # ② v4.0 改造: 改走 save_process_sub_step_with_pkg_update
            # [v3.8.1 修复] 原子化: 3 键去重 + process_sub_steps 写入 + 一次 commit.
            # [v3.8.1 废弃] 不再写 data_packages.completed_qty（SSOT 已切换到 process_sub_steps）
            try:
                from storage.mysql_storage import MySQLStorage
                _storage = MySQLStorage()
                _storage.connect()
                # [F16 T16.1 修复] process_names 表已被 F6 P9 DROP, 改用 core.config.get_process_code() 内存函数
                # (替代原 SELECT process_code FROM process_names, 避免 1146 WARNING)
                try:
                    from core.config import get_process_code
                    process_code = get_process_code(_process)
                except Exception:
                    process_code = ''
                _storage.save_process_sub_step_with_pkg_update(
                    {
                        'order_no': _order_no,
                        'step_name': _process,
                        'process_code': process_code,
                        'operator': _operator,
                        'quantity': _quantity,
                        'batch_no': _batch_no,
                        'status': 'pending',
                    },
                    pkg_order=_order_no,
                    pkg_process=_process,
                    qty_delta=_quantity,
                )
            except Exception as _e:
                _log.exception('写入 process_sub_steps 失败')
                return jsonify({'code': 500, 'message': str(_e)}), 500

            # ③ 同步桌面端
            from bridge.sync_client import send as sync_send
            sync_ok = sync_send('sub-step-report', {'order_no': _order_no, 'step_name': _process,
                                                    'quantity': _quantity, 'operator': _operator})
            if not sync_ok:
                # 同步失败时入队列兜底（用于调度中心手动重推）
                from container_center_v5 import ContainerCenter
                cc = ContainerCenter()
                cc.storage.enqueue_report({
                    'order_no': _order_no, 'step_name': _process,
                    'quantity': _quantity, 'operator': _operator})
                _log.warning(f'8008同步失败，已入队列兜底: {_order_no}/{_process} +{_quantity}')

            _log.info(f'[扫码报工] 直写成功: {_order_no}/{_process} +{_quantity} op={_operator}')
            return jsonify({
                'code': 0,
                'message': f'报工成功 ({_process} +{_quantity})',
                'success': True,
                'data': {
                    'task_id': _task_id,
                    'order_no': _order_no,
                    'process': _process,
                    'quantity': _quantity,
                    'operator': _operator,
                }
            })

        except Exception as _e:
            _log.exception(f'[扫码报工] 异常: {_e}')
            return jsonify({'code': 500, 'message': f'报工失败: {str(_e)[:100]}'})

    # /api/sync-queue/list — 查看同步失败队列
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
            return jsonify({'code': 500, 'message': '查询失败'}), 500

    # /api/sync-queue/retry — 手动重推一条同步
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
            try:
                from core._db_pools import get_container_connection
                conn = get_container_connection(autocommit=False)
            except Exception:
                conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
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
            # 同步到 8008
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
            return jsonify({'code': 500, 'message': '操作失败'}), 500

    @app.after_request
    def add_cache_headers(response):
        if response.content_type and 'application/json' in response.content_type:
            response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.context_processor
    def inject_conn_config():
        return {
            'LOCAL_HOST': os.environ.get('LOCAL_HOST', ''),
            'CLOUD_HOST': os.environ.get('CLOUD_HOST', '')
        }

    from sync.init import init_sync_engine
    init_sync_engine()

    return app


app = create_app()

if os.getenv('ENABLE_THREAD_MANAGEMENT', 'true') == 'true':
    try:
        from thread_lifecycle import init_graceful_shutdown
        shutdown_timeout = int(os.getenv('SHUTDOWN_TIMEOUT', '10'))
        init_graceful_shutdown(timeout=shutdown_timeout)
        logger.info(f"[App] 线程生命周期管理已启用 (timeout={shutdown_timeout}s)")
    except Exception as e:
        logger.warning(f"[App] 线程生命周期管理初始化失败: {e}")

# 调度中心后台调度器已随服务剥离（端口 5003），报工系统不再启动
# from dispatch_center import start_background_scheduler
# scheduler_interval = int(os.getenv('SCHEDULER_INTERVAL', '60'))
# start_background_scheduler(interval_seconds=scheduler_interval)

from storage_layer import StorageFactory, StorageType, resolve_storage_type
try:
    from services.stats_engine import StatsEngine
    _default_st = resolve_storage_type()
    _report_storage = StorageFactory.get_instance(_default_st)
    if _report_storage is None:
        _report_storage = StorageFactory.create(_default_st)
    if _report_storage:
        _report_engine = StatsEngine(_report_storage)
        _report_engine.seed_builtin_reports()
        from services.scheduler import start_scheduler as start_report_scheduler
        start_report_scheduler(_report_engine, check_interval=60)
except ImportError as e:
    logger.warning(f"[App] 统计引擎初始化跳过（模块未实现）: {e}")
except Exception as e:
    logger.warning(f"[App] 统计引擎初始化失败: {e}")

if os.getenv('ENABLE_CACHE_WARMUP', 'false') == 'true':
    try:
        from cache_warmup import async_warmup_cache
        async_warmup_cache()
        logger.info("[App] 缓存异步预热已启动")
    except Exception as e:
        logger.warning(f"[App] 缓存预热初始化失败: {e}")

# ───── 报工队列后台消费者 ─────
def _start_report_queue_worker():
    """后台线程: 每 10 秒消费 report_queue 中的待处理报工"""
    import threading, time, uuid
    from datetime import datetime

    def _worker():
        from container_center_v5 import ContainerCenter
        from core.config import get_process_code
        cc = ContainerCenter()
        logger.info('[队列Worker] 启动，轮询间隔 10s')
        while True:
            try:
                pending = cc.storage.dequeue_pending_reports(limit=5)
                if pending:
                    for item in pending:
                        qid = item['id']
                        order_no = item['order_no']
                        step_name = item['step_name']
                        quantity = float(item['quantity'])
                        qualified_qty = float(item.get('qualified_qty', quantity))
                        operator = item['operator']
                        process_id = item.get('process_id', '')
                        retry = item['retry_count']

                        try:
                            # 写入 process_sub_steps
                            import uuid as _uuid
                            today = datetime.now().strftime('%Y%m%d')
                            prefix = 'STK' if '入库' in step_name else 'SHP'
                            record = {
                                'id': str(_uuid.uuid4()),
                                'process_id': process_id,
                                'order_no': order_no,
                                'step_name': step_name,
                                'batch_no': f'{prefix}-{today}-{_uuid.uuid4().hex[:6].upper()}',
                                'quantity': quantity,
                                'qualified_qty': qualified_qty,
                                'operator': operator,
                                'created_at': datetime.now().isoformat(),
                            }
                            cc.add_sub_step(record)

                            # [v3.8.1 废弃] 旧: 更新 data_packages.completed_qty
                            # add_sub_step 已写 process_sub_steps（SSOT），不再需要同步到 data_packages
                            cc.storage.mark_report_processed(qid)

                            # 同步到 8008 → steel_belt
                            try:
                                from bridge.sync_client import send as sync_send
                                sync_send('sub-step-report', {'order_no': order_no, 'step_name': step_name,
                                                              'quantity': quantity, 'operator': operator})
                            except Exception:
                                pass
                            logger.info(f'[队列Worker] 处理成功: qid={qid} {order_no}/{step_name} +{quantity}')

                        except Exception as e:
                            logger.warning(f'[队列Worker] 处理失败: qid={qid} {order_no}/{step_name} retry={retry} err={e}')
                            try:
                                cc.storage.mark_report_failed(qid, str(e)[:255], retry + 1)
                            except Exception:
                                pass
                else:
                    pass  # line 699 已 sleep
                time.sleep(10)
            except Exception as e:
                logger.error(f'[队列Worker] 异常: {e}')
                time.sleep(10)

    t = threading.Thread(target=_worker, daemon=True, name='report-queue-worker')
    t.start()
    logger.info('[队列Worker] 线程已启动')

_start_report_queue_worker()

app.jinja_env.globals['static_hash'] = lambda filename: f'/static/{filename}'

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    port = int(os.getenv('PORT', 5008))
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host=FLASK_HOST, port=port, debug=False, use_reloader=False)
