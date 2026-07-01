# -*- coding: utf-8 -*-
"""库存 service - 入库/出库/批量/库存查询
TASK-T2 接口签名遵循 DESIGN v2.0 缺陷 2
"""
import logging
from typing import Tuple, List
from ..db_utils import execute, log_operation, _direct_conn, _get_max_stock

logger = logging.getLogger(__name__)


class InventoryService:
    """库存核心操作 service"""

    @staticmethod
    def inbound(product_id: int, warehouse_id: int, qty: float,
                operator: str, remark: str = '', unit_price: float = None) -> Tuple[int, dict]:
        """入库 - FOR UPDATE 行级锁 + 事务 + max_stock 校验

        TODO-T5: unit_price 可选 - 若传入则更新 products.last_purchase_price

        Returns:
            (200, {"id": tx_id, "current_qty": ..., "inbound_qty": ...})
            (400, {"msg": "..."}) 参数错
            (422, {"msg": "..."}) 业务规则违反
            (404, {"msg": "..."}) 产品/仓库不存在
        """
        if qty <= 0:
            return 400, {'msg': '入库数量必须 > 0'}

        # 修复 M-2：unit_price 类型校验（前端可能传字符串）
        if unit_price is not None:
            try:
                unit_price = float(unit_price)
            except (TypeError, ValueError):
                return 400, {'msg': f'unit_price 必须是数字，收到: {unit_price!r}'}
            if unit_price < 0:
                return 400, {'msg': '入库单价不能为负'}

        # 产品存在性 + max_stock
        product = execute(
            'SELECT id, max_stock, code, name FROM products WHERE id=%s AND deleted_at IS NULL',
            (product_id,), fetch='one'
        )
        if not product:
            return 404, {'msg': '产品不存在'}

        # 仓库存在性
        wh = execute(
            'SELECT id, name FROM warehouses WHERE id=%s AND deleted_at IS NULL',
            (warehouse_id,), fetch='one'
        )
        if not wh:
            return 404, {'msg': '仓库不存在'}

        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    # FOR UPDATE 锁库存行
                    c.execute(
                        'SELECT current_qty, inbound_qty FROM inventory '
                        'WHERE product_id=%s AND warehouse_id=%s FOR UPDATE',
                        (product_id, warehouse_id)
                    )
                    row = c.fetchone()
                    if not row:
                        # 新建库存行
                        max_stock = product.get('max_stock', 0) or _get_max_stock()
                        if qty > max_stock:
                            return 422, {'msg': f'入库后 {qty} 超过 max_stock={max_stock}'}
                        c.execute(
                            'INSERT INTO inventory (product_id, warehouse_id, current_qty, inbound_qty) '
                            'VALUES (%s, %s, %s, %s)',
                            (product_id, warehouse_id, qty, qty)
                        )
                        new_qty = qty
                    else:
                        new_qty = (row['current_qty'] or 0) + qty
                        max_stock = product.get('max_stock', 0) or _get_max_stock()
                        if max_stock > 0 and new_qty > max_stock:
                            return 422, {
                                'msg': f'入库后 {new_qty} 超过 max_stock={max_stock}',
                                'current': row['current_qty'] or 0,
                                'incoming': qty
                            }
                        c.execute(
                            'UPDATE inventory SET current_qty=%s, inbound_qty=inbound_qty+%s, '
                            'updated_at=NOW() WHERE product_id=%s AND warehouse_id=%s',
                            (new_qty, qty, product_id, warehouse_id)
                        )

                    # 写入 transactions
                    c.execute(
                        'INSERT INTO inventory_transactions '
                        '(product_id, warehouse_id, type, qty, ref_no, operator, remark) '
                        'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (product_id, warehouse_id, 'inbound', qty, '', operator, remark)
                    )
                    tx_id = c.lastrowid

                    # 修复 T5 / L-2：更新 last_purchase_price + 时间戳
                    if unit_price is not None and unit_price > 0:
                        c.execute(
                            'UPDATE products SET last_purchase_price=%s, last_purchase_price_at=NOW() WHERE id=%s',
                            (unit_price, product_id)
                        )
                conn.commit()

            # 审计
            try:
                log_operation(
                    op_type='inbound', entity='inventory',
                    entity_id=tx_id, operator=operator,
                    detail={'product_id': product_id, 'warehouse_id': warehouse_id, 'qty': qty, 'remark': remark}
                )
            except Exception:
                logger.exception('[入库] 审计失败')

            return 200, {'id': tx_id, 'current_qty': new_qty, 'inbound_qty': qty}
        except Exception:
            logger.exception('[入库] 失败')
            return 500, {'msg': '入库失败'}

    @staticmethod
    def outbound(product_id: int, warehouse_id: int, qty: float,
                 operator: str, remark: str = '') -> Tuple[int, dict]:
        """出库 - FOR UPDATE 行级锁 + 库存校验

        Returns:
            (200, {"id": tx_id, "current_qty": ..., "outbound_qty": ...})
            (400, {"msg": "..."}) 参数错
            (422, {"msg": "..."}) 库存不足
            (404, {"msg": "..."}) 产品/仓库/库存不存在
        """
        if qty <= 0:
            return 400, {'msg': '出库数量必须 > 0'}

        # 产品/仓库存在性
        product = execute(
            'SELECT id, code, name FROM products WHERE id=%s AND deleted_at IS NULL',
            (product_id,), fetch='one'
        )
        if not product:
            return 404, {'msg': '产品不存在'}
        wh = execute(
            'SELECT id, name FROM warehouses WHERE id=%s AND deleted_at IS NULL',
            (warehouse_id,), fetch='one'
        )
        if not wh:
            return 404, {'msg': '仓库不存在'}

        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    c.execute(
                        'SELECT current_qty, outbound_qty FROM inventory '
                        'WHERE product_id=%s AND warehouse_id=%s FOR UPDATE',
                        (product_id, warehouse_id)
                    )
                    row = c.fetchone()
                    if not row:
                        return 404, {'msg': '该产品在此仓库无库存'}
                    if (row['current_qty'] or 0) < qty:
                        return 422, {
                            'msg': f'库存不足：当前 {row["current_qty"]}，需出库 {qty}',
                            'current': row['current_qty'] or 0,
                            'required': qty
                        }
                    new_qty = row['current_qty'] - qty
                    c.execute(
                        'UPDATE inventory SET current_qty=%s, outbound_qty=outbound_qty+%s, '
                        'updated_at=NOW() WHERE product_id=%s AND warehouse_id=%s',
                        (new_qty, qty, product_id, warehouse_id)
                    )
                    c.execute(
                        'INSERT INTO inventory_transactions '
                        '(product_id, warehouse_id, type, qty, ref_no, operator, remark) '
                        'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (product_id, warehouse_id, 'outbound', qty, '', operator, remark)
                    )
                    tx_id = c.lastrowid
                conn.commit()

            try:
                log_operation(
                    op_type='outbound', entity='inventory',
                    entity_id=tx_id, operator=operator,
                    detail={'product_id': product_id, 'warehouse_id': warehouse_id, 'qty': qty, 'remark': remark}
                )
            except Exception:
                logger.exception('[出库] 审计失败')

            return 200, {'id': tx_id, 'current_qty': new_qty, 'outbound_qty': qty}
        except Exception:
            logger.exception('[出库] 失败')
            return 500, {'msg': '出库失败'}

    @staticmethod
    def list_stock(filters: dict, page: int = 1, page_size: int = 20) -> Tuple[int, dict]:
        """库存查询 - 多条件 + 分页

        Args:
            filters: {product_code, product_name, warehouse_id, category_id, min_qty, max_qty, low_stock_only}
        """
        where = ['1=1']
        params = []

        if filters.get('product_code'):
            where.append('p.code LIKE %s')
            params.append(f'%{filters["product_code"]}%')
        if filters.get('product_name'):
            where.append('p.name LIKE %s')
            params.append(f'%{filters["product_name"]}%')
        if filters.get('warehouse_id'):
            where.append('i.warehouse_id = %s')
            params.append(int(filters['warehouse_id']))
        if filters.get('category_id'):
            where.append('p.category_id = %s')
            params.append(int(filters['category_id']))
        if filters.get('min_qty') is not None:
            where.append('i.current_qty >= %s')
            params.append(float(filters['min_qty']))
        if filters.get('max_qty') is not None:
            where.append('i.current_qty <= %s')
            params.append(float(filters['max_qty']))
        if filters.get('low_stock_only'):
            where.append('i.current_qty < p.safety_stock')

        where_sql = ' AND '.join(where)
        offset = (page - 1) * page_size

        # 总数
        total = execute(
            f'SELECT COUNT(*) AS cnt FROM inventory i '
            f'JOIN products p ON i.product_id = p.id AND p.deleted_at IS NULL '
            f'WHERE {where_sql}',
            tuple(params), fetch='one'
        )['cnt'] or 0

        items = execute(
            f'SELECT i.id, i.product_id, p.code, p.name, p.spec, p.unit, '
            f'i.warehouse_id, w.name AS warehouse_name, '
            f'i.current_qty, i.inbound_qty, i.outbound_qty, '
            f'p.safety_stock, p.max_stock, i.updated_at '
            f'FROM inventory i '
            f'JOIN products p ON i.product_id = p.id AND p.deleted_at IS NULL '
            f'JOIN warehouses w ON i.warehouse_id = w.id '
            f'WHERE {where_sql} ORDER BY i.id DESC LIMIT %s OFFSET %s',
            tuple(params) + (page_size, offset), fetch='all'
        ) or []

        return 200, {'items': items, 'total': total, 'page': page, 'page_size': page_size}
