# -*- coding: utf-8 -*-
"""库存管理 — 数据路由：产品/供应商/分类/仓库 CRUD

TASK-006 实施（v2.3 升级 — 强制校验）：
- product_add / supplier_add / category_add / base_add **必须**调用 validate_required
- 字段长度限制生效（code ≤ 50, name ≤ 100）
- code 字符限制（仅字母数字下划线）
- 错误信息聚合 `'; '.join(errors)`
- SQL 参数全部使用 `converted[field]`（非 `data[field]`）

TASK-013 实施：所有写操作调用 log_operation 埋点
"""
import logging
from flask import request, jsonify, render_template, session

from .db_utils import (
    execute, validate_required, log_operation,
    parse_pagination, _do_update, _soft_delete, _restore,
)
from .admin_auth import admin_required, require_csrf  # CRITICAL Fix C2 + A3

logger = logging.getLogger(__name__)

# 字段最大长度（CRITICAL Fix H9: 防止超长输入撑爆数据库）
FIELD_MAX_LEN = {
    'code': 50,
    'name': 100,
    'spec': 200,
    'unit': 20,
    'contact': 50,
    'phone': 30,
    'address': 200,
    'parent_id': 11,
}


def _check_field_lengths(data):
    """CRITICAL Fix H9: 字段长度校验"""
    errs = []
    for k, v in data.items():
        if k in FIELD_MAX_LEN and isinstance(v, str) and len(v) > FIELD_MAX_LEN[k]:
            errs.append(f'{k} 长度超过 {FIELD_MAX_LEN[k]}')
    return errs


def _check_product_ref(eid: int) -> str:
    """TASK-T3: 产品引用检查 - 被 inventory 引用则禁止删除"""
    row = execute('SELECT COUNT(*) AS cnt FROM inventory WHERE product_id=%s', (eid,), fetch='one')
    if row and row['cnt'] > 0:
        return f'该产品被 {row["cnt"]} 条库存记录引用，无法删除'
    return ''


def _check_warehouse_ref(eid: int) -> str:
    """TASK-T3: 仓库引用检查"""
    row = execute('SELECT COUNT(*) AS cnt FROM inventory WHERE warehouse_id=%s', (eid,), fetch='one')
    if row and row['cnt'] > 0:
        return f'该仓库被 {row["cnt"]} 条库存记录引用，无法删除'
    return ''


def _check_category_ref(eid: int) -> str:
    """TASK-T3: 分类引用检查"""
    row = execute(
        'SELECT COUNT(*) AS cnt FROM products WHERE category_id=%s AND deleted_at IS NULL',
        (eid,), fetch='one'
    )
    if row and row['cnt'] > 0:
        return f'该分类被 {row["cnt"]} 个产品引用，无法删除'
    return ''


# CRITICAL Fix L3: 抽取公共 insert 模板
# 5 个 add 端点（product/supplier/category/base/warehouse）原本 90% 代码相同
# 现在只保留各自的 SQL/字段映射/审计 detail 三部分
def _do_create(sql_template, params, entity, audit_detail, data_for_len_check=None):
    """通用新增：长度检查 + 事务 INSERT + 审计

    Args:
        sql_template: INSERT SQL（带 %s 占位符）
        params: SQL 参数元组
        entity: 审计 entity 名（product/supplier/...）
        audit_detail: 审计 detail dict
        data_for_len_check: 需要长度检查的 dict（默认用 data 但可重传）

    Returns:
        (jsonify_response, status_code)
    """
    if data_for_len_check is not None:
        len_errs = _check_field_lengths(data_for_len_check)
        if len_errs:
            return jsonify({'ok': False, 'msg': '; '.join(len_errs)}), 400

    try:
        with _direct_conn() as conn:
            with conn.cursor() as c:
                c.execute(sql_template, params)
                new_id = c.lastrowid
            conn.commit()

        # TASK-013: 审计
        log_operation(
            op_type='create', entity=entity, entity_id=new_id,
            operator=session.get('username', 'admin'),
            detail=audit_detail
        )
        return jsonify({'ok': True, 'id': new_id}), 200
    except Exception:
        logger.exception(f'[{entity} 新增] 失败')
        return jsonify({'ok': False, 'msg': '新增失败'}), 500


# 表名映射
TABLES = {
    'product': 'products',
    'supplier': 'suppliers',
    'category': 'categories',
    'warehouse': 'warehouses',
    'base': 'bases',
}


def register_routes_data(bp):
    """注册数据管理路由"""

    # ============================================================
    # 产品管理
    # ============================================================
    @bp.route('/inventory/products', methods=['GET'])
    def products_page():
        return render_template('inventory/products.html')

    @bp.route('/inventory/api/product/list', methods=['GET'])
    def product_list():
        """TASK-T4: 增强版 - 分页/筛选/排序/软删除"""
        page, page_size = parse_pagination(request.args)
        filters = {
            'search': request.args.get('search', '').strip(),
            'category_id': request.args.get('category_id'),
        }
        from .services import ProductService
        code, payload = ProductService.list('product', filters, page, page_size)
        return jsonify(payload), code

    @bp.route('/inventory/api/product/add', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def product_add():
        data = request.get_json() or {}

        # TASK-006: 强制校验（v2.3 升级：不强制 → 必须）
        errors, converted = validate_required(
            data,
            fields=['code', 'name', 'unit'],
            types={'safety_stock': int, 'max_stock': int}
        )
        # category_id 可选
        if 'category_id' in data and data['category_id'] is not None:
            errors2, converted2 = validate_required(
                {'category_id': data['category_id']},
                fields=['category_id'],
                types={'category_id': int}
            )
            if errors2:
                errors.extend(errors2)
            else:
                converted['category_id'] = converted2['category_id']

        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400

        # CRITICAL Fix L3: 用 _do_create 统一处理（长度检查 + INSERT + 审计）
        return _do_create(
            sql_template="""INSERT INTO products (code, name, spec, unit, category_id, safety_stock, max_stock)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            params=(
                converted['code'],
                converted['name'],
                converted.get('spec', ''),
                converted['unit'],
                converted.get('category_id'),
                converted.get('safety_stock', 0),
                converted.get('max_stock', 0)
            ),
            entity='product',
            audit_detail={'code': converted['code'], 'name': converted['name']},
            data_for_len_check=data
        )

    @bp.route('/inventory/api/product/<int:pid>/delete', methods=['DELETE'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def product_delete(pid):
        """TASK-T3/T4: 软删除 - 引用检查 + UPDATE deleted_at"""
        return _soft_delete(
            'products', pid, 'product',
            extra_check=lambda eid: _check_product_ref(eid)
        )

    @bp.route('/inventory/api/product/<int:pid>/update', methods=['PATCH'])
    @admin_required
    @require_csrf
    def product_update(pid):
        """TASK-T3: 产品更新"""
        data = request.get_json() or {}
        errors, converted = validate_required(
            data,
            fields=['code', 'name', 'unit'],
            types={'safety_stock': int, 'max_stock': int}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400
        if 'category_id' in data and data['category_id'] is not None:
            try:
                converted['category_id'] = int(data['category_id'])
            except (ValueError, TypeError):
                return jsonify({'ok': False, 'msg': 'category_id 必须是整数'}), 400

        return _do_update(
            table='products', eid=pid,
            sql_template="UPDATE products SET code=%s, name=%s, spec=%s, unit=%s, category_id=%s, safety_stock=%s, max_stock=%s",
            params=(
                converted['code'], converted['name'],
                data.get('spec', ''), converted['unit'],
                converted.get('category_id'),
                converted.get('safety_stock', 0),
                converted.get('max_stock', 0)
            ),
            entity='product',
            audit_detail={'code': converted['code'], 'name': converted['name']},
            data_for_len_check=data
        )

    # ============================================================
    # 供应商管理
    # ============================================================
    @bp.route('/inventory/suppliers', methods=['GET'])
    def suppliers_page():
        return render_template('inventory/suppliers.html')

    @bp.route('/inventory/api/supplier/add', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def supplier_add():
        data = request.get_json() or {}

        errors, converted = validate_required(
            data, fields=['code', 'name'],
            types={}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400

        # CRITICAL Fix L3: 统一处理
        return _do_create(
            sql_template="""INSERT INTO suppliers (code, name, contact, phone, address)
                            VALUES (%s, %s, %s, %s, %s)""",
            params=(
                converted['code'],
                converted['name'],
                converted.get('contact', ''),
                converted.get('phone', ''),
                converted.get('address', '')
            ),
            entity='supplier',
            audit_detail={'code': converted['code'], 'name': converted['name']},
            data_for_len_check=data
        )

    # ============================================================
    # 分类管理
    # ============================================================
    @bp.route('/inventory/api/category/add', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def category_add():
        data = request.get_json() or {}

        errors, converted = validate_required(
            data, fields=['code', 'name'], types={}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400

        # CRITICAL Fix L3: 统一处理
        return _do_create(
            sql_template="""INSERT INTO categories (code, name, parent_id)
                            VALUES (%s, %s, %s)""",
            params=(
                converted['code'],
                converted['name'],
                converted.get('parent_id')
            ),
            entity='category',
            audit_detail={'code': converted['code'], 'name': converted['name']},
            data_for_len_check=data
        )

    # ============================================================
    # 基地/部门管理
    # ============================================================
    @bp.route('/inventory/api/base/add', methods=['POST'])
    @admin_required  # CRITICAL Fix C2
    @require_csrf  # CRITICAL Fix A3
    def base_add():
        data = request.get_json() or {}

        errors, converted = validate_required(
            data, fields=['code', 'name'], types={}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400

        # CRITICAL Fix L3: 统一处理
        return _do_create(
            sql_template="INSERT INTO bases (code, name, address) VALUES (%s, %s, %s)",
            params=(
                converted['code'],
                converted['name'],
                converted.get('address', '')
            ),
            entity='base',
            audit_detail={'code': converted['code'], 'name': converted['name']},
            data_for_len_check=data
        )

    # ============================================================
    # TASK-T3: 通用 list / update / soft_delete（5 实体）
    # ============================================================
    def _make_list_handler(entity_name):
        """工厂：生成通用 list 端点"""
        from .services import ProductService

        def handler():
            page, page_size = parse_pagination(request.args)
            filters = {
                'search': request.args.get('search', '').strip(),
                'is_active': request.args.get('is_active'),
            }
            code, payload = ProductService.list(entity_name, filters, page, page_size)
            return jsonify(payload), code
        handler.__name__ = f'{entity_name}_list'
        return handler

    def _make_update_handler(entity_name, sql_template, field_map):
        """工厂：生成通用 update 端点"""
        from flask import request as _req

        def handler(eid):
            data = _req.get_json() or {}
            # 提取转换后的字段
            params = []
            for field, col in field_map.items():
                val = data.get(field)
                if val is None:
                    # 部分更新：字段可空
                    continue
                params.append(val)
            if not params:
                return jsonify({'ok': False, 'msg': '至少传一个字段'}), 400

            return _do_update(
                table=TABLES[entity_name], eid=eid,
                sql_template=sql_template,
                params=tuple(params),
                entity=entity_name,
                audit_detail={'updated_fields': list(data.keys())},
                data_for_len_check=data
            )
        handler.__name__ = f'{entity_name}_update'
        return handler

    # 注册 5 实体的 list 端点
    bp.add_url_rule('/inventory/api/supplier/list', view_func=_make_list_handler('supplier'), methods=['GET'])
    bp.add_url_rule('/inventory/api/category/list', view_func=_make_list_handler('category'), methods=['GET'])
    bp.add_url_rule('/inventory/api/warehouse/list', view_func=_make_list_handler('warehouse'), methods=['GET'])
    bp.add_url_rule('/inventory/api/base/list', view_func=_make_list_handler('base'), methods=['GET'])

    # 注册 5 实体的 update 端点
    bp.add_url_rule(
        '/inventory/api/supplier/<int:eid>/update', view_func=_make_update_handler(
            'supplier',
            sql_template="UPDATE suppliers SET name=%s, contact=%s, phone=%s, address=%s",
            field_map={'name': 'name', 'contact': 'contact', 'phone': 'phone', 'address': 'address'}
        ), methods=['PATCH']
    )
    bp.add_url_rule(
        '/inventory/api/category/<int:eid>/update', view_func=_make_update_handler(
            'category',
            sql_template="UPDATE categories SET name=%s, parent_id=%s",
            field_map={'name': 'name', 'parent_id': 'parent_id'}
        ), methods=['PATCH']
    )
    bp.add_url_rule(
        '/inventory/api/base/<int:eid>/update', view_func=_make_update_handler(
            'base',
            sql_template="UPDATE bases SET name=%s, address=%s",
            field_map={'name': 'name', 'address': 'address'}
        ), methods=['PATCH']
    )
    bp.add_url_rule(
        '/inventory/api/warehouse/<int:eid>/update', view_func=_make_update_handler(
            'warehouse',
            sql_template="UPDATE warehouses SET name=%s, code=%s, address=%s, is_active=%s, manager=%s, remark=%s",
            field_map={'name': 'name', 'code': 'code', 'address': 'address',
                       'is_active': 'is_active', 'manager': 'manager', 'remark': 'remark'}
        ), methods=['PATCH']
    )

    # 软删除：5 实体
    @bp.route('/inventory/api/supplier/<int:eid>/delete', methods=['DELETE'])
    @admin_required
    @require_csrf
    def supplier_delete(eid):
        return _soft_delete('suppliers', eid, 'supplier')

    @bp.route('/inventory/api/category/<int:eid>/delete', methods=['DELETE'])
    @admin_required
    @require_csrf
    def category_delete(eid):
        return _soft_delete('categories', eid, 'category', extra_check=_check_category_ref)

    @bp.route('/inventory/api/base/<int:eid>/delete', methods=['DELETE'])
    @admin_required
    @require_csrf
    def base_delete(eid):
        return _soft_delete('bases', eid, 'base')

    @bp.route('/inventory/api/warehouse/<int:eid>/delete', methods=['DELETE'])
    @admin_required
    @require_csrf
    def warehouse_delete(eid):
        return _soft_delete('warehouses', eid, 'warehouse', extra_check=_check_warehouse_ref)

    # ============================================================
    # TASK-T2: 仓库管理 add 端点
    # ============================================================
    @bp.route('/inventory/api/warehouse/add', methods=['POST'])
    @admin_required
    @require_csrf
    def warehouse_add():
        """TASK-T2: 仓库新增"""
        data = request.get_json() or {}
        errors, converted = validate_required(
            data, fields=['code', 'name'], types={}
        )
        if errors:
            return jsonify({'ok': False, 'msg': '; '.join(errors)}), 400
        return _do_create(
            sql_template="INSERT INTO warehouses (code, name, address, is_active, manager, remark) VALUES (%s, %s, %s, %s, %s, %s)",
            params=(
                converted['code'], converted['name'],
                data.get('address', ''),
                int(bool(data.get('is_active', 1))),
                data.get('manager', ''),
                data.get('remark', '')
            ),
            entity='warehouse',
            audit_detail={'code': converted['code'], 'name': converted['name']},
            data_for_len_check=data
        )

    # ============================================================
    # TASK-T3: 回收站 list / restore
    # ============================================================
    @bp.route('/inventory/api/recycle-bin/list', methods=['GET'])
    @admin_required
    def recycle_bin_list():
        """回收站 - 列出 5 实体的软删除记录"""
        entity = request.args.get('entity', 'product')
        if entity not in TABLES:
            return jsonify({'ok': False, 'msg': f'未知实体: {entity}'}), 400
        page, page_size = parse_pagination(request.args)
        offset = (page - 1) * page_size

        total = execute(
            f'SELECT COUNT(*) AS cnt FROM {TABLES[entity]} WHERE deleted_at IS NOT NULL',
            fetch='one'
        )['cnt'] or 0
        items = execute(
            f'SELECT * FROM {TABLES[entity]} WHERE deleted_at IS NOT NULL '
            f'ORDER BY deleted_at DESC LIMIT %s OFFSET %s',
            (page_size, offset), fetch='all'
        ) or []
        return jsonify({'ok': True, 'items': items, 'total': total, 'page': page, 'page_size': page_size})

    @bp.route('/inventory/api/recycle-bin/<entity>/<int:eid>/restore', methods=['POST'])
    @admin_required
    @require_csrf
    def recycle_bin_restore(entity, eid):
        """恢复软删除的记录"""
        if entity not in TABLES:
            return jsonify({'ok': False, 'msg': f'未知实体: {entity}'}), 400
        return _restore(TABLES[entity], eid, entity)

    @bp.route('/inventory/recycle-bin', methods=['GET'])
    @admin_required
    def recycle_bin_page():
        """回收站页面"""
        return render_template('inventory/recycle_bin.html')


def _direct_conn():
    """直接获取连接（上下文管理器）"""
    from .db_utils import get_conn
    return get_conn()
