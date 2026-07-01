# -*- coding: utf-8 -*-
"""产品 service - 5 实体通用 CRUD
TASK-T2 接口签名遵循 DESIGN v2.0 缺陷 2
"""
import logging
from typing import Tuple
from ..db_utils import execute, log_operation

logger = logging.getLogger(__name__)

# 实体表映射
TABLES = {
    'product': 'products',
    'supplier': 'suppliers',
    'category': 'categories',
    'warehouse': 'warehouses',
    'base': 'bases',
}

# 实体默认字段（用于 list 通用查询）
LIST_FIELDS = {
    'product': 'id, code, name, spec, unit, category_id, safety_stock, max_stock, created_at',
    'supplier': 'id, name, contact, phone, address, created_at',
    'category': 'id, name, created_at',
    'warehouse': 'id, name, code, address, is_active, manager, remark, created_at',
    'base': 'id, name, code, created_at',
}


class ProductService:
    """产品/分类/供应商/基地/仓库 通用 CRUD
    注: 命名沿用 ProductService 但服务 5 实体（与 routes_data.py 中 TABLES 一致）
    """

    @staticmethod
    def list(entity: str, filters: dict, page: int = 1, page_size: int = 20) -> Tuple[int, dict]:
        """通用 list - 支持分页/筛选/排序/模糊

        Args:
            entity: 'product'/'supplier'/'category'/'warehouse'/'base'
            filters: {'search': str, 'is_active': int, ...}
            page: 页码（从1开始）
            page_size: 每页条数

        Returns:
            (200, {"items": [...], "total": int, "page": int, "page_size": int})
            (400, {"msg": "..."}) 实体名错
        """
        if entity not in TABLES:
            return 400, {'msg': f'未知实体: {entity}'}

        table = TABLES[entity]
        fields = LIST_FIELDS[entity]

        # 构造 WHERE
        where = ['deleted_at IS NULL']
        params = []

        # 模糊搜索
        search = filters.get('search')
        if search:
            if entity == 'product':
                where.append('(code LIKE %s OR name LIKE %s)')
                params.extend([f'%{search}%', f'%{search}%'])
            elif entity == 'supplier':
                where.append('name LIKE %s')
                params.append(f'%{search}%')
            elif entity == 'category':
                where.append('name LIKE %s')
                params.append(f'%{search}%')
            elif entity == 'warehouse':
                where.append('(name LIKE %s OR code LIKE %s)')
                params.extend([f'%{search}%', f'%{search}%'])
            elif entity == 'base':
                where.append('(name LIKE %s OR code LIKE %s)')
                params.extend([f'%{search}%', f'%{search}%'])

        # is_active 筛选（仅 warehouse）
        if entity == 'warehouse' and 'is_active' in filters:
            where.append('is_active = %s')
            params.append(int(filters['is_active']))

        # category_id 筛选（仅 product）
        if entity == 'product' and filters.get('category_id'):
            where.append('category_id = %s')
            params.append(int(filters['category_id']))

        where_sql = ' AND '.join(where)

        # 总数
        total_row = execute(f'SELECT COUNT(*) AS cnt FROM {table} WHERE {where_sql}', tuple(params), fetch='one')
        total = total_row['cnt'] if total_row else 0

        # 分页
        offset = (page - 1) * page_size
        sql = f'SELECT {fields} FROM {table} WHERE {where_sql} ORDER BY id DESC LIMIT %s OFFSET %s'
        items = execute(sql, tuple(params) + (page_size, offset), fetch='all') or []

        return 200, {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        }

    @staticmethod
    def get(entity: str, eid: int) -> Tuple[int, dict]:
        """通用详情"""
        if entity not in TABLES:
            return 400, {'msg': f'未知实体: {entity}'}
        table = TABLES[entity]
        fields = LIST_FIELDS[entity]
        row = execute(f'SELECT {fields} FROM {table} WHERE id=%s AND deleted_at IS NULL', (eid,), fetch='one')
        if not row:
            return 404, {'msg': '记录不存在'}
        return 200, row

    @staticmethod
    def soft_delete(entity: str, eid: int) -> Tuple[int, dict]:
        """软删除 - 检查引用后 UPDATE deleted_at

        Returns:
            (200, {"ok": True}) 成功
            (404, {"msg": "..."}) 不存在
            (409, {"msg": "..."}) 被引用
            (400, {"msg": "..."}) 实体名错
        """
        if entity not in TABLES:
            return 400, {'msg': f'未知实体: {entity}'}
        table = TABLES[entity]

        # 引用检查
        ref_check = _check_references(entity, eid)
        if ref_check:
            return 409, {'msg': ref_check}

        # 软删除
        rows = execute(
            f'UPDATE {table} SET deleted_at=NOW() WHERE id=%s AND deleted_at IS NULL',
            (eid,),
            commit=True
        )
        if not rows:
            return 404, {'msg': '记录不存在或已删除'}

        # 审计
        try:
            log_operation(
                op_type='delete', entity=entity, entity_id=eid,
                operator='admin', detail={'soft_delete': True}
            )
        except Exception:
            logger.exception(f'[{entity} 删除] 审计失败')

        return 200, {'ok': True}

    @staticmethod
    def restore(entity: str, eid: int) -> Tuple[int, dict]:
        """恢复软删除的记录"""
        if entity not in TABLES:
            return 400, {'msg': f'未知实体: {entity}'}
        table = TABLES[entity]

        # 检查 code 冲突
        if entity in ('product', 'supplier', 'category', 'warehouse', 'base'):
            row = execute(
                f'SELECT code FROM {table} WHERE id=%s AND deleted_at IS NOT NULL',
                (eid,),
                fetch='one'
            )
            if not row:
                return 404, {'msg': '记录不存在或未被删除'}
            if row.get('code'):
                conflict = execute(
                    f'SELECT id FROM {table} WHERE code=%s AND deleted_at IS NULL AND id!=%s',
                    (row['code'], eid),
                    fetch='one'
                )
                if conflict:
                    return 409, {'msg': f'code {row["code"]!r} 已被占用，请先修改'}

        # 恢复
        rows = execute(
            f'UPDATE {table} SET deleted_at=NULL WHERE id=%s AND deleted_at IS NOT NULL',
            (eid,),
            commit=True
        )
        if not rows:
            return 404, {'msg': '记录不存在或未被删除'}

        try:
            log_operation(
                op_type='restore', entity=entity, entity_id=eid,
                operator='admin', detail={}
            )
        except Exception:
            logger.exception(f'[{entity} 恢复] 审计失败')

        return 200, {'ok': True}


def _check_references(entity: str, eid: int) -> str:
    """检查实体是否被引用，返回错误消息或空字符串

    引用规则:
      - product: 被 inventory 引用则禁止
      - supplier/category/base: 当前无引用
      - warehouse: 被 inventory 引用则禁止
    """
    if entity == 'product':
        row = execute('SELECT COUNT(*) AS cnt FROM inventory WHERE product_id=%s', (eid,), fetch='one')
        if row and row['cnt'] > 0:
            return f'该产品被 {row["cnt"]} 条库存记录引用，无法删除'
    elif entity == 'warehouse':
        row = execute('SELECT COUNT(*) AS cnt FROM inventory WHERE warehouse_id=%s', (eid,), fetch='one')
        if row and row['cnt'] > 0:
            return f'该仓库被 {row["cnt"]} 条库存记录引用，无法删除'
    elif entity == 'category':
        row = execute('SELECT COUNT(*) AS cnt FROM products WHERE category_id=%s AND deleted_at IS NULL', (eid,), fetch='one')
        if row and row['cnt'] > 0:
            return f'该分类被 {row["cnt"]} 个产品引用，无法删除'
    return ''
