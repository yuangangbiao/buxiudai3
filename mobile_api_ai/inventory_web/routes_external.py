# -*- coding: utf-8 -*-
"""库存管理 — 防腐层 API（供桌面端 HTTP 调用）

提供 3 个 API，替代旧版 InventoryDAO 的桌面端直接调用：
- GET /api/external/inventory/dashboard  → 替代 get_dashboard_overview()
- GET /api/external/inventory/alerts     → 替代 get_low_inventory_alerts()
- GET /api/external/inventory/search     → 替代 search_by_material()
"""
import logging

from flask import Blueprint, jsonify, request

from .db_utils import execute

logger = logging.getLogger(__name__)

# 创建独立的 Blueprint，带 url_prefix，桌面端可独立调用
inventory_external_bp = Blueprint('inventory_external', __name__,
                                  url_prefix='/api/external/inventory')


def register_routes_external(bp):
    """注册防腐层路由（兼容传入外部 bp 的形式）"""

    @bp.route('/dashboard', methods=['GET'])
    def dashboard():
        """替代 InventoryDAO.get_dashboard_overview()
        返回 [{material_name, quantity, unit, safe_stock}]
        """
        try:
            rows = execute(
                """SELECT p.name AS material_name,
                          i.current_qty AS quantity,
                          p.unit,
                          i.safety_stock AS safe_stock
                   FROM products p
                   LEFT JOIN inventory i ON p.id = i.product_id
                   WHERE p.deleted_at IS NULL
                   ORDER BY p.name ASC""",
                fetch='all'
            ) or []
            return jsonify({'ok': True, 'data': rows})
        except Exception:
            logger.exception('[external/dashboard] 查询失败')
            return jsonify({'ok': True, 'data': []})

    @bp.route('/alerts', methods=['GET'])
    def alerts():
        """替代 InventoryDAO.get_low_inventory_alerts(limit=3)
        返回 [{material_name, quantity, unit, warning_qty}]
        """
        try:
            limit = request.args.get('limit', 3, type=int)
            rows = execute(
                """SELECT p.name AS material_name,
                          i.current_qty AS quantity,
                          p.unit,
                          i.safety_stock AS warning_qty
                   FROM products p
                   JOIN inventory i ON p.id = i.product_id
                   WHERE p.deleted_at IS NULL
                     AND i.current_qty < i.safety_stock
                   ORDER BY (i.current_qty / i.safety_stock) ASC
                   LIMIT %s""",
                params=(limit,),
                fetch='all'
            ) or []
            return jsonify({'ok': True, 'data': rows})
        except Exception:
            logger.exception('[external/alerts] 查询失败')
            return jsonify({'ok': True, 'data': []})

    @bp.route('/search', methods=['GET'])
    def search():
        """替代 InventoryDAO.search_by_material(name, spec)
        返回 [{material_name, specification, quantity, unit, warehouse, remark}]
        """
        try:
            keyword = request.args.get('keyword', '').strip()
            spec = request.args.get('spec', '').strip() or None

            if not keyword:
                return jsonify({'ok': True, 'data': []})

            sql = """SELECT p.name AS material_name,
                            p.spec AS specification,
                            i.current_qty AS current_qty,
                            p.unit,
                            w.name AS warehouse,
                            w.name AS warehouse_name,
                            p.remark
                     FROM products p
                     LEFT JOIN inventory i ON p.id = i.product_id
                     LEFT JOIN warehouses w ON i.warehouse_id = w.id
                     WHERE p.deleted_at IS NULL
                       AND (p.name LIKE %s OR p.spec LIKE %s)"""
            params = [f'%{keyword}%', f'%{keyword}%']

            if spec:
                sql += " AND p.spec LIKE %s"
                params.append(f'%{spec}%')

            sql += " ORDER BY p.name ASC"
            rows = execute(sql, params=params, fetch='all') or []
            return jsonify({'ok': True, 'data': rows})
        except Exception:
            logger.exception('[external/search] 查询失败')
            return jsonify({'ok': True, 'data': []})


# 自身注册（当 bp 作为独立蓝图使用时）
register_routes_external(inventory_external_bp)
