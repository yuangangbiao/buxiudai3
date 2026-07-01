# -*- coding: utf-8 -*-
"""调拨 service - 2 步事务 + 在途
TASK-T2/T6 接口签名遵循 DESIGN v2.0 缺陷 2

并发防护：调出仓扣减：FOR UPDATE on inventory(warehouse_id, product_id)
死信防护：scripts/transfer_reaper.py 扫描 in_transit > 24h 自动取消
"""
import logging
import os
from typing import Tuple, List
from ..db_utils import execute, log_operation, _direct_conn

# 修复 H-3：service 层灰度防护（防止被 view 绕过）
# 默认 24h（DESIGN v2.0 缺陷 1.2）
# M-4 修复：通过环境变量配置超时时间，业务可调
DEFAULT_STALE_HOURS = int(os.getenv('INVENTORY_TRANSFER_STALE_HOURS', '24'))

# 修复 H-3：service 层灰度（防止被 view 绕过 cron 直接调用）
# 注意：feature_flags 可能导入失败，try/except 兜底
try:
    from ..feature_flags import is_enabled as _feature_enabled
except Exception:  # noqa: BLE001
    def _feature_enabled(_name):  # type: ignore
        # 兜底：导入失败时全部放行
        return True

logger = logging.getLogger(__name__)


class TransferService:
    """调拨 service"""

    @staticmethod
    def create(from_warehouse_id: int, to_warehouse_id: int,
               items: List[dict], operator: str,
               remark: str = '') -> Tuple[int, dict]:
        """创建调拨单 - 调出仓扣减 + 在途

        Args:
            items: [{"product_id": int, "qty": float}, ...]

        Returns:
            (200, {"transfer_id": id, "in_transit": True})
            (400, {"msg": "..."}) 参数错
            (422, {"msg": "..."}) 库存不足
        """
        if from_warehouse_id == to_warehouse_id:
            return 400, {'msg': '调出/调入仓库不能相同'}
        if not items:
            return 400, {'msg': '调拨明细不能为空'}

        # 校验仓库
        wh_from = execute('SELECT id, name FROM warehouses WHERE id=%s AND deleted_at IS NULL',
                          (from_warehouse_id,), fetch='one')
        if not wh_from:
            return 404, {'msg': '调出仓库不存在'}
        wh_to = execute('SELECT id, name FROM warehouses WHERE id=%s AND deleted_at IS NULL',
                        (to_warehouse_id,), fetch='one')
        if not wh_to:
            return 404, {'msg': '调入仓库不存在'}

        # 排序 items 防止死锁（按 product_id 升序）
        items_sorted = sorted(items, key=lambda x: x['product_id'])

        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    # 1. 创建调拨主单
                    c.execute(
                        'INSERT INTO transfers (from_warehouse_id, to_warehouse_id, status, total_items, operator, remark) '
                        'VALUES (%s, %s, %s, %s, %s, %s)',
                        (from_warehouse_id, to_warehouse_id, 'in_transit', len(items), operator, remark)
                    )
                    transfer_id = c.lastrowid

                    # 2. 逐项调出仓扣减（FOR UPDATE）
                    for it in items_sorted:
                        pid = it['product_id']
                        qty = float(it['qty'])
                        if qty <= 0:
                            return 400, {'msg': f'产品 {pid} 数量必须 > 0'}

                        c.execute(
                            'SELECT current_qty FROM inventory '
                            'WHERE product_id=%s AND warehouse_id=%s FOR UPDATE',
                            (pid, from_warehouse_id)
                        )
                        row = c.fetchone()
                        if not row or (row['current_qty'] or 0) < qty:
                            current = row['current_qty'] if row else 0
                            return 422, {
                                'msg': f'产品 {pid} 在调出仓库存不足：当前 {current}，需 {qty}'
                            }
                        c.execute(
                            'UPDATE inventory SET current_qty=current_qty-%s, outbound_qty=outbound_qty+%s, '
                            'updated_at=NOW() WHERE product_id=%s AND warehouse_id=%s',
                            (qty, qty, pid, from_warehouse_id)
                        )
                        c.execute(
                            'INSERT INTO inventory_transactions '
                            '(product_id, warehouse_id, type, qty, ref_no, operator, remark) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (pid, from_warehouse_id, 'transfer_out', qty,
                             f'transfer:{transfer_id}', operator, f'调拨至仓 {to_warehouse_id}')
                        )

                    # 3. 批量插入调拨明细
                    c.executemany(
                        'INSERT INTO transfer_items (transfer_id, product_id, qty) VALUES (%s, %s, %s)',
                        [(transfer_id, it['product_id'], float(it['qty'])) for it in items_sorted]
                    )
                conn.commit()

            try:
                log_operation(
                    op_type='create', entity='transfer',
                    entity_id=transfer_id, operator=operator,
                    detail={'from': from_warehouse_id, 'to': to_warehouse_id, 'items_count': len(items)}
                )
            except Exception:
                logger.exception('[调拨创建] 审计失败')

            return 200, {'transfer_id': transfer_id, 'in_transit': True}
        except Exception:
            logger.exception('[调拨创建] 失败')
            return 500, {'msg': '创建调拨单失败'}

    @staticmethod
    def complete(transfer_id: int, operator: str) -> Tuple[int, dict]:
        """调拨完成 - 调入仓增加 + 在途结束

        业务规则：仅 in_transit 状态可完成
        """
        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    c.execute('SELECT status, from_warehouse_id, to_warehouse_id FROM transfers WHERE id=%s FOR UPDATE',
                              (transfer_id,))
                    t = c.fetchone()
                    if not t:
                        return 404, {'msg': '调拨单不存在'}
                    if t['status'] != 'in_transit':
                        return 422, {'msg': f'状态 {t["status"]} 不能完成'}

                    # 拉取明细
                    c.execute('SELECT product_id, qty FROM transfer_items WHERE transfer_id=%s', (transfer_id,))
                    items = c.fetchall()

                    # 调入仓增加（FOR UPDATE 排序防死锁）
                    for it in sorted(items, key=lambda x: x['product_id']):
                        pid = it['product_id']
                        qty = float(it['qty'])
                        c.execute(
                            'SELECT current_qty FROM inventory '
                            'WHERE product_id=%s AND warehouse_id=%s FOR UPDATE',
                            (pid, t['to_warehouse_id'])
                        )
                        row = c.fetchone()
                        if row:
                            c.execute(
                                'UPDATE inventory SET current_qty=current_qty+%s, inbound_qty=inbound_qty+%s, '
                                'updated_at=NOW() WHERE product_id=%s AND warehouse_id=%s',
                                (qty, qty, pid, t['to_warehouse_id'])
                            )
                        else:
                            c.execute(
                                'INSERT INTO inventory (product_id, warehouse_id, current_qty, inbound_qty) '
                                'VALUES (%s, %s, %s, %s)',
                                (pid, t['to_warehouse_id'], qty, qty)
                            )
                        c.execute(
                            'INSERT INTO inventory_transactions '
                            '(product_id, warehouse_id, type, qty, ref_no, operator, remark) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (pid, t['to_warehouse_id'], 'transfer_in', qty,
                             f'transfer:{transfer_id}', operator, f'调拨入仓 from {t["from_warehouse_id"]}')
                        )

                    c.execute(
                        'UPDATE transfers SET status="completed", completed_at=NOW(), receiver=%s WHERE id=%s',
                        (operator, transfer_id)
                    )
                conn.commit()

            try:
                log_operation(
                    op_type='complete', entity='transfer',
                    entity_id=transfer_id, operator=operator,
                    detail={'from': t['from_warehouse_id'], 'to': t['to_warehouse_id']}
                )
            except Exception:
                logger.exception('[调拨完成] 审计失败')

            return 200, {'transfer_id': transfer_id, 'completed': True}
        except Exception:
            logger.exception('[调拨完成] 失败')
            return 500, {'msg': '完成调拨失败'}

    @staticmethod
    def cancel(transfer_id: int, operator: str, reason: str = '') -> Tuple[int, dict]:
        """调拨取消 - 调出仓回滚

        业务规则：仅 in_transit 状态可取消
        """
        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    c.execute('SELECT status, from_warehouse_id, to_warehouse_id FROM transfers WHERE id=%s FOR UPDATE',
                              (transfer_id,))
                    t = c.fetchone()
                    if not t:
                        return 404, {'msg': '调拨单不存在'}
                    if t['status'] != 'in_transit':
                        return 422, {'msg': f'状态 {t["status"]} 不能取消'}

                    c.execute('SELECT product_id, qty FROM transfer_items WHERE transfer_id=%s', (transfer_id,))
                    items = c.fetchall()

                    # 调出仓回滚
                    for it in sorted(items, key=lambda x: x['product_id']):
                        pid = it['product_id']
                        qty = float(it['qty'])
                        c.execute(
                            'UPDATE inventory SET current_qty=current_qty+%s, '
                            'updated_at=NOW() WHERE product_id=%s AND warehouse_id=%s',
                            (qty, pid, t['from_warehouse_id'])
                        )
                        c.execute(
                            'INSERT INTO inventory_transactions '
                            '(product_id, warehouse_id, type, qty, ref_no, operator, remark) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (pid, t['from_warehouse_id'], 'transfer_cancel', qty,
                             f'transfer:{transfer_id}', operator, f'调拨取消: {reason}')
                        )

                    c.execute(
                        'UPDATE transfers SET status="cancelled", cancelled_at=NOW(), cancel_reason=%s WHERE id=%s',
                        (reason, transfer_id)
                    )
                conn.commit()

            try:
                log_operation(
                    op_type='cancel', entity='transfer',
                    entity_id=transfer_id, operator=operator,
                    detail={'reason': reason}
                )
            except Exception:
                logger.exception('[调拨取消] 审计失败')

            return 200, {'transfer_id': transfer_id, 'cancelled': True}
        except Exception:
            logger.exception('[调拨取消] 失败')
            return 500, {'msg': '取消失败'}

    @staticmethod
    def list_transfers(status: str = None, page: int = 1, page_size: int = 20) -> Tuple[int, dict]:
        """调拨单列表"""
        where = ['1=1']
        params = []
        if status:
            where.append('t.status = %s')
            params.append(status)
        where_sql = ' AND '.join(where)
        offset = (page - 1) * page_size

        total = execute(
            f'SELECT COUNT(*) AS cnt FROM transfers t WHERE {where_sql}',
            tuple(params), fetch='one'
        )['cnt'] or 0

        items = execute(
            f'SELECT t.id, t.from_warehouse_id, t.to_warehouse_id, '
            f'wf.name AS from_name, wt.name AS to_name, '
            f't.status, t.total_items, t.operator, t.receiver, '
            f't.created_at, t.completed_at, t.cancelled_at, t.cancel_reason '
            f'FROM transfers t '
            f'JOIN warehouses wf ON t.from_warehouse_id = wf.id '
            f'JOIN warehouses wt ON t.to_warehouse_id = wt.id '
            f'WHERE {where_sql} ORDER BY t.id DESC LIMIT %s OFFSET %s',
            tuple(params) + (page_size, offset), fetch='all'
        ) or []

        return 200, {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    @staticmethod
    def reap_stale_transfers() -> int:
        """死信清理 - 扫描 in_transit > 24h 自动取消
        由 scripts/transfer_reaper.py 定时调用

        修复 H-3：在 service 层也检查 feature flag（防止绕过 view）
        修复 M-4：超时时间从环境变量 INVENTORY_TRANSFER_STALE_HOURS 读取（默认 24h）
        修复 M-4：异常时返回 -1（非 0），cron 可识别失败
        """
        # 修复 H-3：service 层灰度
        if not _feature_enabled('t6_transfer'):
            logger.info('[调拨死信清理] 跳过：t6_transfer 功能未启用')
            return 0

        # 修复 M-4：超时小时数从环境变量读取
        hours = int(os.getenv('INVENTORY_TRANSFER_STALE_HOURS', str(DEFAULT_STALE_HOURS)))
        if hours < 1 or hours > 168:  # 最多 7 天
            logger.warning(f'[调拨死信清理] 超时小时数 {hours} 超出 [1, 168] 范围，使用默认值 24')
            hours = 24

        try:
            # 找出超时
            stale = execute(
                f"SELECT id FROM transfers WHERE status='in_transit' "
                f"AND created_at < DATE_SUB(NOW(), INTERVAL {int(hours)} HOUR)",
                fetch='all'
            ) or []
            count = 0
            for s in stale:
                code, _ = TransferService.cancel(s['id'], 'system-reaper', f'{hours}h 超时自动取消')
                if code == 200:
                    count += 1
            logger.info(f'[调拨死信清理] 已自动取消 {count} 个超时调拨（>{hours}h）')
            return count
        except Exception:
            # 修复 M-4：异常时返回 -1，让 cron 能识别失败
            logger.exception('[调拨死信清理] 失败')
            return -1
