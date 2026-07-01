# -*- coding: utf-8 -*-
"""库存管理 — 核心业务路由：入库/出库/批次/库存调整

TASK-008 实施：
- inbound_do / outbound_do: FOR UPDATE 行级锁
- batch_do: items 按 product_id 排序（防死锁）+ FOR UPDATE
- 锁等待超时 SET SESSION innodb_lock_wait_timeout = 5
- try-except-rollback 事务模式

TASK-013 实施：所有写操作调用 log_operation 埋点
TASK-014 实施：使用 validate_qty 校验数量
"""
import logging
from datetime import datetime
from flask import request, jsonify, render_template, session

from .db_utils import (
    execute, get_conn, validate_required, validate_qty, log_operation
)
from .admin_auth import admin_required, require_csrf  # CRITICAL Fix C2 + A3
# C-2 修复：包级 import 失败不阻断路由加载，改为 try/except 兜底
try:
    from .feature_flags import safe_require_feature as require_feature  # TODO-T6 灰度开关（兜底）
except Exception:  # noqa: BLE001
    # feature_flags 模块自身失败时，提供 no-op 装饰器
    from functools import wraps
    def require_feature(name):  # type: ignore
        def _d(f):
            @wraps(f)
            def _w(*a, **kw):
                return f(*a, **kw)
            return _w
        return _d
    import logging
    logging.getLogger(__name__).exception('[C-2] feature_flags 加载失败，已降级为 no-op')

logger = logging.getLogger(__name__)


def register_routes_core(bp):
    """注册核心业务路由"""

    # ============================================================
    # 仪表盘
    # ============================================================
    @bp.route('/inventory/dashboard', methods=['GET'])
    def dashboard():
        # 修复 500 错误：dashboard.html 使用 total_items/low_items/today_in/today_out/month_in/month_out/warehouse_stats/alerts/recent 9 个变量
        # 之前未传，导致 jinja2.UndefinedError: 'month_in' is undefined
        # 同时加 try/except 兜底：DB 失败时返回空数据，页面仍能渲染
        try:
            _total = execute(
                "SELECT COUNT(*) AS n FROM products WHERE deleted_at IS NULL",
                fetch='one'
            )
            total_items = _total.get('n', 0) if isinstance(_total, dict) else 0
        except Exception:
            total_items = 0

        try:
            _low = execute(
                "SELECT COUNT(*) AS n FROM products WHERE deleted_at IS NULL "
                "AND current_qty IS NOT NULL AND current_qty <= IFNULL(safety_stock, 0) "
                "AND current_qty > 0",
                fetch='one'
            )
            low_items = _low.get('n', 0) if isinstance(_low, dict) else 0
        except Exception:
            low_items = 0

        try:
            _today = execute(
                "SELECT "
                "  COALESCE(SUM(CASE WHEN trans_type='in'  THEN qty ELSE 0 END), 0) AS today_in, "
                "  COALESCE(SUM(CASE WHEN trans_type='out' THEN qty ELSE 0 END), 0) AS today_out "
                "FROM inventory_transactions WHERE DATE(created_at)=CURDATE()",
                fetch='one'
            )
            today_in = _today.get('today_in', 0) if isinstance(_today, dict) else 0
            today_out = _today.get('today_out', 0) if isinstance(_today, dict) else 0
        except Exception:
            today_in = 0
            today_out = 0

        try:
            _month = execute(
                "SELECT "
                "  COALESCE(SUM(CASE WHEN trans_type='in'  THEN qty ELSE 0 END), 0) AS month_in, "
                "  COALESCE(SUM(CASE WHEN trans_type='out' THEN qty ELSE 0 END), 0) AS month_out "
                "FROM inventory_transactions "
                "WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL DAYOFMONTH(CURDATE())-1 DAY)",
                fetch='one'
            )
            month_in = _month.get('month_in', 0) if isinstance(_month, dict) else 0
            month_out = _month.get('month_out', 0) if isinstance(_month, dict) else 0
        except Exception:
            month_in = 0
            month_out = 0

        try:
            warehouse_stats = execute(
                "SELECT w.id, w.name, "
                "  COALESCE(SUM(i.current_qty), 0) AS total_qty, "
                "  COALESCE(SUM(i.current_qty * IFNULL(p.last_purchase_price, 0)), 0) AS total_value, "
                "  COUNT(i.product_id) AS product_count "
                "FROM warehouses w "
                "LEFT JOIN inventory i ON i.warehouse_id = w.id "
                "LEFT JOIN products p ON p.id = i.product_id AND p.deleted_at IS NULL "
                "WHERE w.deleted_at IS NULL "
                "GROUP BY w.id, w.name "
                "ORDER BY w.id LIMIT 10",
                fetch='all'
            ) or []
        except Exception:
            warehouse_stats = []

        try:
            alerts = execute(
                "SELECT id, type AS alert_type, title AS item_name, body, created_at "
                "FROM notifications WHERE is_read=0 ORDER BY created_at DESC LIMIT 5",
                fetch='all'
            ) or []
        except Exception:
            alerts = []

        try:
            recent = execute(
                "SELECT t.trans_type, COALESCE(p.name, t.product_id) AS product_name, "
                "  t.qty, t.created_at "
                "FROM inventory_transactions t "
                "LEFT JOIN products p ON p.id = t.product_id "
                "ORDER BY t.created_at DESC LIMIT 10",
                fetch='all'
            ) or []
        except Exception:
            recent = []

        return render_template(
            'inventory/dashboard.html',
            total_items=total_items,
            low_items=low_items,
            today_in=today_in,
            today_out=today_out,
            month_in=month_in,
            month_out=month_out,
            warehouse_stats=warehouse_stats,
            alerts=alerts,
            recent=recent
        )

    # ============================================================
    # 库存列表
    # ============================================================
    @bp.route('/inventory/stock', methods=['GET'])
    def stock_list():
        # 修复 500 错误：stock_list.html 使用 total_pages/page/keyword/category/alert 5 个变量
        # 之前未传 → jinja2.UndefinedError: 'total_pages' is undefined
        # DB 失败时给空数据兜底
        try:
            keyword = request.args.get('q', '')
            category = request.args.get('category', '')
            alert = request.args.get('alert', '')
            page = max(1, int(request.args.get('page', '1') or 1))
            page_size = 20
            _count = execute(
                "SELECT COUNT(*) AS n FROM products WHERE deleted_at IS NULL",
                fetch='one'
            )
            total = _count.get('n', 0) if isinstance(_count, dict) else 0
            total_pages = max(1, (total + page_size - 1) // page_size)
        except Exception:
            keyword = category = alert = ''
            page = 1
            total_pages = 1
        return render_template(
            'inventory/stock_list.html',
            total_pages=total_pages,
            page=page,
            keyword=keyword,
            category=category,
            alert=alert
        )

    @bp.route('/inventory/api/stock/list', methods=['GET'])
    def stock_api_list():
        try:
            rows = execute(
                """SELECT i.id, i.product_id, p.code, p.name, p.spec, p.unit,
                          i.warehouse_id, w.name AS warehouse_name,
                          i.current_qty, i.safety_stock, i.max_stock, i.unit_price
                   FROM inventory i
                   JOIN products p ON i.product_id = p.id
                   JOIN warehouses w ON i.warehouse_id = w.id
                   ORDER BY i.id DESC""",
                fetch='all'
            )
            return jsonify({'ok': True, 'data': rows or []})
        except Exception:
            logger.exception('[库存列表] 失败')
            return jsonify({'ok': False, 'msg': '查询失败'}), 500

    # ============================================================
    # 入库单
    # ============================================================
    @bp.route('/inventory/inbound', methods=['GET'])
    def inbound_page():
        # 修复 500：inbound.html 需要 items（含 current_qty/safety_stock/warehouse_name/product_name）
        #  + warehouses + categories + mode 变量
        try:
            items = execute(
                "SELECT i.id, i.product_id, i.warehouse_id, i.current_qty, i.safety_stock, "
                "       p.name AS product_name, p.spec, p.unit, p.category_id, "
                "       w.name AS warehouse_name "
                "FROM inventory i "
                "LEFT JOIN products p ON p.id = i.product_id AND p.deleted_at IS NULL "
                "LEFT JOIN warehouses w ON w.id = i.warehouse_id AND w.deleted_at IS NULL "
                "WHERE i.deleted_at IS NULL "
                "ORDER BY p.code, w.id LIMIT 500",
                fetch='all'
            ) or []
        except Exception:
            items = []
        try:
            warehouses = execute(
                "SELECT id, name FROM warehouses WHERE deleted_at IS NULL AND is_active = 1 ORDER BY id",
                fetch='all'
            ) or []
        except Exception:
            warehouses = []
        try:
            categories = execute(
                "SELECT id, name FROM categories WHERE deleted_at IS NULL ORDER BY id",
                fetch='all'
            ) or []
        except Exception:
            categories = []
        return render_template('inventory/inbound.html',
                               items=items, warehouses=warehouses,
                               categories=categories, mode='inbound')

    @bp.route('/inventory/api/inbound/do', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def inbound_do():
        """入库：FOR UPDATE 行级锁 + 事务 + 审计 + max_stock 校验"""
        data = request.get_json() or {}

        # TASK-006/014: 校验
        errors, converted = validate_required(
            data, fields=['product_id', 'warehouse_id', 'qty'],
            types={'product_id': int, 'warehouse_id': int}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400

        qty_err = validate_qty(converted['qty'])
        if qty_err:
            return jsonify({'ok': False, 'msg': qty_err}), 400

        product_id = converted['product_id']
        warehouse_id = converted['warehouse_id']
        qty = float(converted['qty'])

        # TASK-008: 事务 + FOR UPDATE + 锁超时
        try:
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("SET SESSION innodb_lock_wait_timeout = 5")
                    # CRITICAL Fix M2: 查询产品的 max_stock 限制
                    c.execute(
                        "SELECT max_stock FROM products WHERE id=%s",
                        (product_id,)
                    )
                    prod_row = c.fetchone()
                    if not prod_row:
                        conn.rollback()
                        return jsonify({'ok': False, 'msg': '产品不存在'}), 404
                    max_stock = prod_row.get('max_stock') or 0
                    # 锁定现有记录（如有）
                    c.execute(
                        """SELECT current_qty, inbound_qty FROM inventory
                           WHERE product_id=%s AND warehouse_id=%s FOR UPDATE""",
                        (product_id, warehouse_id)
                    )
                    row = c.fetchone()
                    if row:
                        new_qty = row['current_qty'] + qty
                        # CRITICAL Fix M2: max_stock 校验
                        if max_stock > 0 and new_qty > max_stock:
                            conn.rollback()
                            return jsonify({
                                'ok': False,
                                'msg': f'入库后将超过最大库存（当前: {row["current_qty"]}, '
                                       f'入库: {qty}, 最大: {max_stock}）'
                            }), 409
                        c.execute(
                            """UPDATE inventory
                               SET current_qty=current_qty+%s, inbound_qty=inbound_qty+%s
                               WHERE product_id=%s AND warehouse_id=%s""",
                            (qty, qty, product_id, warehouse_id)
                        )
                    else:
                        # CRITICAL Fix M2: 新建时也要校验
                        if max_stock > 0 and qty > max_stock:
                            conn.rollback()
                            return jsonify({
                                'ok': False,
                                'msg': f'入库数量超过最大库存（{qty} > {max_stock}）'
                            }), 409
                        c.execute(
                            """INSERT INTO inventory (product_id, warehouse_id, current_qty, inbound_qty)
                               VALUES (%s, %s, %s, %s)""",
                            (product_id, warehouse_id, qty, qty)
                        )
                    # 写入流水
                    trans_no = f"IN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    c.execute(
                        """INSERT INTO inventory_transactions
                           (trans_no, trans_type, product_id, warehouse_id,
                            qty, order_no, operator, trans_date)
                           VALUES (%s, 'inbound', %s, %s, %s, %s, %s, CURDATE())""",
                        (trans_no, product_id, warehouse_id, qty,
                         data.get('order_no', ''), data.get('operator', ''))
                    )
                conn.commit()

            log_operation('inbound', 'inventory', f"{product_id}_{warehouse_id}",
                          operator=session.get('username', 'admin'),
                          detail={'qty': qty, 'trans_no': trans_no})
            return jsonify({'ok': True, 'msg': '入库成功', 'trans_no': trans_no})
        except Exception:
            logger.exception('[入库] 失败')
            return jsonify({'ok': False, 'msg': '入库失败'}), 500

    # ============================================================
    # 出库单（TASK-008 重点）
    # ============================================================
    @bp.route('/inventory/outbound', methods=['GET'])
    def outbound_page():
        # 修复 500：复用 inbound.html 但必须传 items/warehouses/categories/mode
        try:
            items = execute(
                "SELECT i.id, i.product_id, i.warehouse_id, i.current_qty, i.safety_stock, "
                "       p.name AS product_name, p.spec, p.unit, p.category_id, "
                "       w.name AS warehouse_name "
                "FROM inventory i "
                "LEFT JOIN products p ON p.id = i.product_id AND p.deleted_at IS NULL "
                "LEFT JOIN warehouses w ON w.id = i.warehouse_id AND w.deleted_at IS NULL "
                "WHERE i.deleted_at IS NULL AND i.current_qty > 0 "
                "ORDER BY p.code, w.id LIMIT 500",
                fetch='all'
            ) or []
        except Exception:
            items = []
        try:
            warehouses = execute(
                "SELECT id, name FROM warehouses WHERE deleted_at IS NULL AND is_active = 1 ORDER BY id",
                fetch='all'
            ) or []
        except Exception:
            warehouses = []
        try:
            categories = execute(
                "SELECT id, name FROM categories WHERE deleted_at IS NULL ORDER BY id",
                fetch='all'
            ) or []
        except Exception:
            categories = []
        return render_template('inventory/inbound.html',
                               items=items, warehouses=warehouses,
                               categories=categories, mode='outbound')

    @bp.route('/inventory/api/outbound/do', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def outbound_do():
        """出库：FOR UPDATE 行级锁 + 库存校验 + 事务"""
        data = request.get_json() or {}

        errors, converted = validate_required(
            data, fields=['product_id', 'warehouse_id', 'qty'],
            types={'product_id': int, 'warehouse_id': int}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400

        qty_err = validate_qty(converted['qty'])
        if qty_err:
            return jsonify({'ok': False, 'msg': qty_err}), 400

        product_id = converted['product_id']
        warehouse_id = converted['warehouse_id']
        qty = float(converted['qty'])

        try:
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("SET SESSION innodb_lock_wait_timeout = 5")
                    c.execute(
                        """SELECT current_qty FROM inventory
                           WHERE product_id=%s AND warehouse_id=%s FOR UPDATE""",
                        (product_id, warehouse_id)
                    )
                    row = c.fetchone()
                    if not row:
                        conn.rollback()
                        return jsonify({'ok': False, 'msg': '库存记录不存在'}), 404
                    if row['current_qty'] < qty:
                        conn.rollback()
                        return jsonify({
                            'ok': False,
                            'msg': f'库存不足（当前: {row["current_qty"]}, 需要: {qty}）'
                        }), 409

                    c.execute(
                        """UPDATE inventory
                           SET current_qty=current_qty-%s, outbound_qty=outbound_qty+%s
                           WHERE product_id=%s AND warehouse_id=%s""",
                        (qty, qty, product_id, warehouse_id)
                    )
                    trans_no = f"OUT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    c.execute(
                        """INSERT INTO inventory_transactions
                           (trans_no, trans_type, product_id, warehouse_id,
                            qty, order_no, operator, trans_date)
                           VALUES (%s, 'outbound', %s, %s, %s, %s, %s, CURDATE())""",
                        (trans_no, product_id, warehouse_id, qty,
                         data.get('order_no', ''), data.get('operator', ''))
                    )
                conn.commit()

            log_operation('outbound', 'inventory', f"{product_id}_{warehouse_id}",
                          operator=session.get('username', 'admin'),
                          detail={'qty': qty, 'trans_no': trans_no})
            return jsonify({'ok': True, 'msg': '出库成功', 'trans_no': trans_no})
        except Exception:
            logger.exception('[出库] 失败')
            return jsonify({'ok': False, 'msg': '出库失败'}), 500

    # ============================================================
    # 库存预警（实时从 inventory 表计算，无需触发器）
    # ============================================================
    @bp.route('/inventory/alerts', methods=['GET'])
    def alerts_page():
        """库存预警页：低库存 + 超储 + 零库存 + 已处理标记
        数据来源：inventory 表 LEFT JOIN products/warehouses
        已处理状态：session 中 alerts_resolved 集合（按 inventory.id）
        """
        try:
            rows = execute(
                "SELECT i.id, i.product_id, i.warehouse_id, i.current_qty, i.safety_stock, i.max_stock, "
                "       p.name AS product_name, w.name AS warehouse_name "
                "FROM inventory i "
                "LEFT JOIN products p ON p.id = i.product_id AND p.deleted_at IS NULL "
                "LEFT JOIN warehouses w ON w.id = i.warehouse_id AND w.deleted_at IS NULL "
                "WHERE i.deleted_at IS NULL "
                "  AND (i.current_qty <= i.safety_stock OR i.current_qty = 0 OR i.current_qty > i.max_stock) "
                "ORDER BY i.current_qty ASC, p.code LIMIT 200",
                fetch='all'
            ) or []
        except Exception:
            rows = []

        # 已处理状态（session 内简单集合；生产可改为 inventory_alerts 表）
        resolved = set(session.get('alerts_resolved', []) or [])
        items = []
        for r in rows:
            qty = float(r.get('current_qty') or 0)
            ss = float(r.get('safety_stock') or 0)
            mx = float(r.get('max_stock') or 0)
            if qty == 0:
                atype = 'zero_stock'
            elif qty <= ss:
                atype = 'low_stock'
            elif qty > mx > 0:
                atype = 'over_stock'
            else:
                continue
            items.append({
                'id': r['id'],
                'product_id': r.get('product_id'),
                'product_name': r.get('product_name') or f'#{r.get("product_id")}',
                'warehouse_name': r.get('warehouse_name') or '',
                'current_qty': qty,
                'safety_stock': ss,
                'max_stock': mx,
                'alert_type': atype,
                'is_resolved': r['id'] in resolved,
                'remark': f'仓库: {r.get("warehouse_name") or "-"}',
            })
        return render_template('inventory/alerts.html', items=items)

    @bp.route('/inventory/api/alert/<int:alert_id>/resolve', methods=['POST'])
    def alert_resolve(alert_id):
        """标记预警已处理（写入 session）"""
        resolved = set(session.get('alerts_resolved', []) or [])
        resolved.add(alert_id)
        # 限制 session 大小
        session['alerts_resolved'] = list(resolved)[-500:]
        return jsonify({'ok': True, 'msg': '已标记处理'})

    # ============================================================
    # 5 个缺失页面（warehouses / categories / export / base / settings）
    # ============================================================
    @bp.route('/inventory/warehouses', methods=['GET'])
    def warehouses_page():
        """仓库管理页面：列表 + 新增/编辑/停用/删除"""
        try:
            rows = execute(
                "SELECT w.id, w.code, w.name, w.address, w.manager, w.is_active, "
                "       (SELECT COUNT(*) FROM inventory i WHERE i.warehouse_id = w.id AND i.deleted_at IS NULL) AS product_count "
                "FROM warehouses w "
                "WHERE w.deleted_at IS NULL "
                "ORDER BY w.id",
                fetch='all'
            ) or []
        except Exception:
            rows = []
        # 补 code 字段（兼容老数据缺 code 的情况）
        for r in rows:
            if not r.get('code'):
                r['code'] = f'WH{r["id"]:03d}'
        return render_template('inventory/warehouses.html', warehouses=rows)

    @bp.route('/inventory/warehouses/add', methods=['POST'], endpoint='wh_add_view')
    def warehouse_add():
        """新增仓库"""
        data = request.get_json() or request.form.to_dict() or {}
        code = (data.get('code') or '').strip()
        name = (data.get('name') or '').strip()
        if not code or not name:
            return jsonify({'ok': False, 'msg': '编码和名称必填'}), 400
        try:
            execute(
                "INSERT INTO warehouses (code, name, address, manager, is_active, created_at) "
                "VALUES (%s, %s, %s, %s, 1, NOW())",
                params=(code, name, data.get('address', ''), data.get('manager', ''))
            )
            return jsonify({'ok': True, 'msg': '已添加'})
        except Exception as e:
            logger.exception('[warehouses] add failed')
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/warehouses/edit/<int:wid>', methods=['POST'])
    def warehouse_edit(wid):
        data = request.get_json() or request.form.to_dict() or {}
        try:
            execute(
                "UPDATE warehouses SET name=%s, address=%s, manager=%s WHERE id=%s AND deleted_at IS NULL",
                params=(data.get('name', ''), data.get('address', ''), data.get('manager', ''), wid)
            )
            return jsonify({'ok': True, 'msg': '已修改'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/warehouses/toggle/<int:wid>', methods=['POST'])
    def warehouse_toggle(wid):
        data = request.get_json() or {}
        is_active = 1 if data.get('is_active') in (1, True, '1', 'true') else 0
        try:
            execute(
                "UPDATE warehouses SET is_active=%s WHERE id=%s AND deleted_at IS NULL",
                params=(is_active, wid)
            )
            return jsonify({'ok': True, 'msg': '已更新'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/warehouses/delete/<int:wid>', methods=['POST'], endpoint='warehouse_delete_page')
    def warehouse_delete(wid):
        """软删除仓库（如果有库存则拒绝）"""
        try:
            n = execute(
                "SELECT COUNT(*) AS n FROM inventory WHERE warehouse_id=%s AND deleted_at IS NULL",
                params=(wid,), fetch='one'
            )
            if n and n.get('n', 0) > 0:
                return jsonify({'ok': False, 'msg': '该仓库有库存，无法删除'}), 400
            execute(
                "UPDATE warehouses SET deleted_at=NOW() WHERE id=%s AND deleted_at IS NULL",
                params=(wid,)
            )
            return jsonify({'ok': True, 'msg': '已删除'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/categories', methods=['GET'])
    def categories_page():
        """产品分类页面：分类列表 + 分类下产品 + 供应商下拉"""
        try:
            cats = execute(
                "SELECT c.id, c.code, c.name, "
                "       (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.deleted_at IS NULL) AS product_count "
                "FROM categories c "
                "WHERE c.deleted_at IS NULL "
                "ORDER BY c.code",
                fetch='all'
            ) or []
            # 每个分类下产品（限制 50 个避免数据过大）
            for c in cats:
                c['products'] = execute(
                    "SELECT id, name, spec, unit, price FROM products "
                    "WHERE category_id=%s AND deleted_at IS NULL ORDER BY name LIMIT 50",
                    params=(c['id'],), fetch='all'
                ) or []
        except Exception:
            cats = []
        try:
            suppliers = execute(
                "SELECT id, name FROM suppliers WHERE deleted_at IS NULL ORDER BY name",
                fetch='all'
            ) or []
        except Exception:
            suppliers = []
        return render_template('inventory/categories.html',
                               categories=cats, suppliers=suppliers)

    @bp.route('/inventory/categories/add', methods=['POST'], endpoint='category_add_view')
    def category_add():
        data = request.get_json() or request.form.to_dict() or {}
        code = (data.get('code') or '').strip()
        name = (data.get('name') or '').strip()
        if not code or not name:
            return jsonify({'ok': False, 'msg': '编码和名称必填'}), 400
        try:
            execute(
                "INSERT INTO categories (code, name, created_at) VALUES (%s, %s, NOW())",
                params=(code, name)
            )
            return jsonify({'ok': True, 'msg': '已添加'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/products/add', methods=['POST'], endpoint='product_add_simple')
    def product_add():
        """从 categories.html 添加产品到指定分类（端点别名避免与 routes_data.product_add 冲突）"""
        data = request.get_json() or request.form.to_dict() or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'ok': False, 'msg': '产品名必填'}), 400
        try:
            # 自动生成 code
            import time as _t
            code = data.get('code') or f'PRD-{int(_t.time())}'
            execute(
                "INSERT INTO products (code, name, spec, unit, price, category_id, status, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, 1, NOW())",
                params=(
                    code, name,
                    data.get('spec', ''), data.get('unit', '件'),
                    float(data.get('unit_price') or data.get('price') or 0),
                    int(data.get('category_id') or 0) or None
                )
            )
            return jsonify({'ok': True, 'msg': '已添加'})
        except Exception as e:
            logger.exception('[products] add failed')
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/export', methods=['GET'])
    def export_page():
        """导出/打印页面（无模板变量）"""
        return render_template('inventory/export.html')

    @bp.route('/inventory/print/preview', methods=['GET'])
    def print_preview_page():
        """打印预览（入库单 / 出库单）：从 inventory_transactions 取最近 30 条"""
        trans_type = request.args.get('type', 'inbound')
        if trans_type not in ('inbound', 'outbound'):
            trans_type = 'inbound'
        try:
            transactions = execute(
                "SELECT t.id, t.trans_no, t.qty, t.unit_price, t.total_amount, "
                "       t.operator, t.remark, t.trans_date, t.created_at, "
                "       p.name AS product_name, p.spec, p.unit, "
                "       w.name AS warehouse_name, "
                "       IFNULL(s.name, '-') AS supplier_name "
                "FROM inventory_transactions t "
                "LEFT JOIN products p ON p.id = t.product_id AND p.deleted_at IS NULL "
                "LEFT JOIN warehouses w ON w.id = t.warehouse_id AND w.deleted_at IS NULL "
                "LEFT JOIN suppliers s ON s.id = t.supplier_id AND s.deleted_at IS NULL "
                "WHERE t.trans_type=%s AND t.deleted_at IS NULL "
                "ORDER BY t.created_at DESC LIMIT 30",
                params=(trans_type,), fetch='all'
            ) or []
            # 转换 Decimal → float
            for t in transactions:
                if 'qty' in t and t['qty'] is not None:
                    t['qty'] = float(t['qty'])
                if 'unit_price' in t and t['unit_price'] is not None:
                    t['unit_price'] = float(t['unit_price'])
                if 'total_amount' in t and t['total_amount'] is not None:
                    t['total_amount'] = float(t['total_amount'])
        except Exception:
            transactions = []
        return render_template('inventory/print_preview.html',
                               trans_type=trans_type, transactions=transactions)

    @bp.route('/inventory/base', methods=['GET'])
    def base_page():
        """基础数据合并视图：仓库 + 分类 + 供应商 + 呆滞库存"""
        try:
            warehouses = execute(
                "SELECT code, name FROM warehouses WHERE deleted_at IS NULL ORDER BY code",
                fetch='all'
            ) or []
        except Exception:
            warehouses = []
        try:
            categories = execute(
                "SELECT code, name FROM categories WHERE deleted_at IS NULL ORDER BY code",
                fetch='all'
            ) or []
        except Exception:
            categories = []
        try:
            suppliers = execute(
                "SELECT code, name, contact FROM suppliers WHERE deleted_at IS NULL ORDER BY code",
                fetch='all'
            ) or []
        except Exception:
            suppliers = []
        try:
            # 呆滞库存：90 天内无出入库且 current_qty > 0
            stagnant = execute(
                "SELECT p.name AS product_name, p.spec, i.current_qty, "
                "       IFNULL((SELECT MAX(t.created_at) FROM inventory_transactions t "
                "               WHERE t.product_id=i.product_id AND t.warehouse_id=i.warehouse_id), i.created_at) AS last_trans, "
                "       DATEDIFF(NOW(), IFNULL((SELECT MAX(t.created_at) FROM inventory_transactions t "
                "               WHERE t.product_id=i.product_id AND t.warehouse_id=i.warehouse_id), i.created_at)) AS days_idle "
                "FROM inventory i "
                "LEFT JOIN products p ON p.id = i.product_id AND p.deleted_at IS NULL "
                "WHERE i.deleted_at IS NULL AND i.current_qty > 0 "
                "HAVING days_idle >= 90 "
                "ORDER BY days_idle DESC LIMIT 50",
                fetch='all'
            ) or []
        except Exception:
            stagnant = []
        return render_template('inventory/base_data.html',
                               warehouses=warehouses, categories=categories,
                               suppliers=suppliers, stagnant=stagnant)

    @bp.route('/inventory/base/<kind>/add', methods=['POST'], endpoint='base_add_page')
    def base_add(kind):
        """base_data.html 通用 add API：warehouse / category / supplier"""
        data = request.get_json() or request.form.to_dict() or {}
        code = (data.get('code') or '').strip()
        name = (data.get('name') or '').strip()
        if not code or not name:
            return jsonify({'ok': False, 'msg': '编码和名称必填'}), 400
        try:
            if kind == 'warehouse':
                execute(
                    "INSERT INTO warehouses (code, name, is_active, created_at) VALUES (%s, %s, 1, NOW())",
                    params=(code, name)
                )
            elif kind == 'category':
                execute(
                    "INSERT INTO categories (code, name, created_at) VALUES (%s, %s, NOW())",
                    params=(code, name)
                )
            elif kind == 'supplier':
                execute(
                    "INSERT INTO suppliers (code, name, contact, created_at) VALUES (%s, %s, %s, NOW())",
                    params=(code, name, data.get('contact', ''))
                )
            else:
                return jsonify({'ok': False, 'msg': f'未知类型: {kind}'}), 400
            return jsonify({'ok': True, 'msg': '已添加'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': str(e)[:100]}), 500

    @bp.route('/inventory/settings', methods=['GET'])
    def settings_page():
        """系统设置页面：从环境变量读配置（显示用，不写回）"""
        import os as _os
        config = {
            'MYSQL_HOST': _os.environ.get('MYSQL_HOST', ''),
            'MYSQL_PORT': _os.environ.get('MYSQL_PORT', '3306'),
            'MYSQL_USER': _os.environ.get('MYSQL_USER', ''),
        }
        return render_template('inventory/settings.html', config=config)

    @bp.route('/inventory/api/settings', methods=['POST'])
    @admin_required
    def settings_save():
        """保存配置（仅记录到日志，不直接修改 .env，避免硬编码）"""
        data = request.get_json() or {}
        # 安全：不直接修改 .env，只记录配置变更日志
        try:
            execute(
                "INSERT INTO operation_logs (operator, action, detail, created_at) "
                "VALUES (%s, %s, %s, NOW())",
                params=(
                    session.get('username', 'admin'),
                    'settings_change',
                    f"配置变更: {data}"
                )
            )
        except Exception:
            pass
        logger.info(f'[settings] 管理员请求修改配置: {data}')
        return jsonify({'ok': True, 'msg': '配置变更已记录，重启服务后生效'})


    # ============================================================
    # 批次操作（TASK-008 重点：防死锁排序）
    # ============================================================
    @bp.route('/inventory/batch', methods=['GET'])
    def batch_page():
        # 修复 500：batch.html 用 {{ products | tojson }} 和 {{ warehouses | tojson }}
        try:
            products = execute(
                "SELECT id, code, name, spec, unit FROM products "
                "WHERE deleted_at IS NULL ORDER BY code LIMIT 500",
                fetch='all'
            ) or []
        except Exception:
            products = []
        try:
            warehouses = execute(
                "SELECT id, name FROM warehouses WHERE deleted_at IS NULL AND is_active = 1 ORDER BY id",
                fetch='all'
            ) or []
        except Exception:
            warehouses = []
        return render_template('inventory/batch.html', products=products, warehouses=warehouses)

    @bp.route('/inventory/api/batch/do', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def batch_do():
        """批次入库/出库：items 按 product_id 升序排序（防死锁）"""
        data = request.get_json() or {}
        items = data.get('items', [])
        op_type = data.get('op_type', 'inbound')  # inbound / outbound

        if not isinstance(items, list) or not items:
            return jsonify({'ok': False, 'msg': 'items 必填且为非空数组'}), 400
        if op_type not in ('inbound', 'outbound'):
            return jsonify({'ok': False, 'msg': 'op_type 必须为 inbound 或 outbound'}), 400

        # TASK-008: 按 product_id 升序排序（防死锁）
        try:
            items = sorted(items, key=lambda x: int(x.get('product_id', 0)))
        except (ValueError, TypeError):
            return jsonify({'ok': False, 'msg': 'product_id 必须为整数'}), 400

        try:
            success_count = 0
            with get_conn() as conn:
                with conn.cursor() as c:
                    c.execute("SET SESSION innodb_lock_wait_timeout = 5")
                    for item in items:
                        # 校验每个 item
                        errs, conv = validate_required(
                            item, fields=['product_id', 'warehouse_id', 'qty'],
                            types={'product_id': int, 'warehouse_id': int}
                        )
                        if errs:
                            conn.rollback()
                            return jsonify({
                                'ok': False,
                                'msg': f'item {item} 校验失败: {"; ".join(errs)}'
                            }), 400

                        qe = validate_qty(conv['qty'])
                        if qe:
                            conn.rollback()
                            return jsonify({
                                'ok': False,
                                'msg': f'item {item.get("product_id")} 数量错误: {qe}'
                            }), 400

                        pid = conv['product_id']
                        wid = conv['warehouse_id']
                        q = float(conv['qty'])

                        c.execute(
                            """SELECT current_qty FROM inventory
                               WHERE product_id=%s AND warehouse_id=%s FOR UPDATE""",
                            (pid, wid)
                        )
                        row = c.fetchone()

                        if op_type == 'inbound':
                            if row:
                                c.execute(
                                    """UPDATE inventory
                                       SET current_qty=current_qty+%s, inbound_qty=inbound_qty+%s
                                       WHERE product_id=%s AND warehouse_id=%s""",
                                    (q, q, pid, wid)
                                )
                            else:
                                c.execute(
                                    """INSERT INTO inventory (product_id, warehouse_id, current_qty, inbound_qty)
                                       VALUES (%s, %s, %s, %s)""",
                                    (pid, wid, q, q)
                                )
                        else:  # outbound
                            if not row:
                                conn.rollback()
                                return jsonify({
                                    'ok': False,
                                    'msg': f'产品 {pid} 库存记录不存在'
                                }), 404
                            if row['current_qty'] < q:
                                conn.rollback()
                                return jsonify({
                                    'ok': False,
                                    'msg': f'产品 {pid} 库存不足（{row["current_qty"]} < {q}）'
                                }), 409
                            c.execute(
                                """UPDATE inventory
                                   SET current_qty=current_qty-%s, outbound_qty=outbound_qty+%s
                                   WHERE product_id=%s AND warehouse_id=%s""",
                                (q, q, pid, wid)
                            )

                        success_count += 1
                conn.commit()

            log_operation(f'batch_{op_type}', 'inventory', f'{success_count}_items',
                          operator=session.get('username', 'admin'),
                          detail={'count': success_count, 'op_type': op_type})
            return jsonify({
                'ok': True,
                'msg': f'批次{("入库" if op_type == "inbound" else "出库")}成功',
                'count': success_count
            })
        except Exception:
            logger.exception('[批次操作] 失败')
            return jsonify({'ok': False, 'msg': '批次操作失败'}), 500

    # ============================================================
    # 库存预警
    # ============================================================
    @bp.route('/inventory/api/inventory/alert', methods=['GET'])
    def inventory_alert():
        """低于安全库存的预警"""
        try:
            rows = execute(
                """SELECT i.product_id, p.name, p.code,
                          i.current_qty, i.safety_stock, w.name AS warehouse_name
                   FROM inventory i
                   JOIN products p ON i.product_id = p.id
                   JOIN warehouses w ON i.warehouse_id = w.id
                   WHERE i.current_qty <= i.safety_stock AND i.safety_stock > 0""",
                fetch='all'
            )
            return jsonify({'ok': True, 'data': rows or [], 'count': len(rows or [])})
        except Exception:
            logger.exception('[预警] 失败')
            return jsonify({'ok': False, 'msg': '预警查询失败'}), 500

    # ============================================================
    # TASK-T5: 抽盘
    # ============================================================
    @bp.route('/inventory/stocktake', methods=['GET'])
    @admin_required
    @require_feature('t5_stocktake')
    def stocktake_page():
        return render_template('inventory/stocktake.html')

    @bp.route('/inventory/api/stocktake/create', methods=['POST'])
    @admin_required
    @require_csrf
    @require_feature('t5_stocktake')
    def stocktake_create():
        data = request.get_json() or {}
        try:
            wid = int(data.get('warehouse_id', 0))
            tol = float(data.get('tolerance_pct', 0.5))
        except (ValueError, TypeError):
            return jsonify({'ok': False, 'msg': '参数类型错误'}), 400
        operator = session.get('username', 'admin')
        from .services import StocktakeService
        code, payload = StocktakeService.create(wid, tol, operator, data.get('remark', ''))
        return jsonify(payload), code

    @bp.route('/inventory/api/stocktake/<int:sid>/submit', methods=['POST'])
    @admin_required
    @require_csrf
    @require_feature('t5_stocktake')
    def stocktake_submit(sid):
        data = request.get_json() or {}
        items = data.get('items', [])
        if not items:
            return jsonify({'ok': False, 'msg': '明细不能为空'}), 400
        operator = session.get('username', 'admin')
        from .services import StocktakeService
        code, payload = StocktakeService.submit(sid, items, operator)
        return jsonify(payload), code

    @bp.route('/inventory/api/stocktake/<int:sid>/adjust', methods=['POST'])
    @admin_required
    @require_csrf
    @require_feature('t5_stocktake')
    def stocktake_adjust(sid):
        """TASK-T5: 二次确认 - 需前端输入 "ADJUST" 确认"""
        data = request.get_json() or {}
        confirm = data.get('confirm', '')
        if confirm != 'ADJUST':
            return jsonify({'ok': False, 'msg': '需要输入 ADJUST 确认'}), 400
        operator = session.get('username', 'admin')
        from .services import StocktakeService
        code, payload = StocktakeService.adjust(sid, operator, confirm_abnormal=True)
        return jsonify(payload), code

    @bp.route('/inventory/api/stocktake/list', methods=['GET'])
    @admin_required
    def stocktake_list():
        from .db_utils import parse_pagination
        page, page_size = parse_pagination(request.args)
        offset = (page - 1) * page_size
        total = execute('SELECT COUNT(*) AS cnt FROM stocktakes', fetch='one')['cnt'] or 0
        items = execute(
            'SELECT s.*, w.name AS warehouse_name FROM stocktakes s '
            'JOIN warehouses w ON s.warehouse_id = w.id '
            'ORDER BY s.id DESC LIMIT %s OFFSET %s',
            (page_size, offset), fetch='all'
        ) or []
        return jsonify({'ok': True, 'items': items, 'total': total, 'page': page, 'page_size': page_size})

    @bp.route('/inventory/api/stocktake/<int:sid>/items', methods=['GET'])
    @admin_required
    def stocktake_items(sid):
        items = execute(
            'SELECT si.*, p.code, p.name, p.spec, p.unit FROM stocktake_items si '
            'JOIN products p ON si.product_id = p.id '
            'WHERE si.stocktake_id=%s ORDER BY si.id',
            (sid,), fetch='all'
        ) or []
        return jsonify({'ok': True, 'items': items})

    # ============================================================
    # TASK-T6: 调拨
    # ============================================================
    @bp.route('/inventory/transfer', methods=['GET'])
    @admin_required
    @require_feature('t6_transfer')
    def transfer_page():
        return render_template('inventory/transfer.html')

    @bp.route('/inventory/api/transfer/create', methods=['POST'])
    @admin_required
    @require_csrf
    @require_feature('t6_transfer')
    def transfer_create():
        data = request.get_json() or {}
        try:
            from_w = int(data.get('from_warehouse_id', 0))
            to_w = int(data.get('to_warehouse_id', 0))
        except (ValueError, TypeError):
            return jsonify({'ok': False, 'msg': '仓库 ID 类型错误'}), 400
        items = data.get('items', [])
        if not items:
            return jsonify({'ok': False, 'msg': '明细不能为空'}), 400
        operator = session.get('username', 'admin')
        from .services import TransferService
        code, payload = TransferService.create(from_w, to_w, items, operator, data.get('remark', ''))
        return jsonify(payload), code

    @bp.route('/inventory/api/transfer/<int:tid>/complete', methods=['POST'])
    @admin_required
    @require_csrf
    @require_feature('t6_transfer')
    def transfer_complete(tid):
        operator = session.get('username', 'admin')
        from .services import TransferService
        code, payload = TransferService.complete(tid, operator)
        return jsonify(payload), code

    @bp.route('/inventory/api/transfer/<int:tid>/cancel', methods=['POST'])
    @admin_required
    @require_csrf
    @require_feature('t6_transfer')
    def transfer_cancel(tid):
        data = request.get_json() or {}
        reason = data.get('reason', '')
        operator = session.get('username', 'admin')
        from .services import TransferService
        code, payload = TransferService.cancel(tid, operator, reason)
        return jsonify(payload), code

    @bp.route('/inventory/api/transfer/list', methods=['GET'])
    @admin_required
    def transfer_list():
        from .db_utils import parse_pagination
        page, page_size = parse_pagination(request.args)
        from .services import TransferService
        code, payload = TransferService.list_transfers(
            request.args.get('status'), page, page_size
        )
        return jsonify(payload), code
