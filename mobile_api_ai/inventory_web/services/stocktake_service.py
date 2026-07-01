# -*- coding: utf-8 -*-
"""抽盘 service - 双重差值判断
TASK-T2/T5 接口签名遵循 DESIGN v2.0 缺陷 2
"""
import logging
from typing import Tuple, List
from ..db_utils import execute, log_operation, _direct_conn

logger = logging.getLogger(__name__)


class StocktakeService:
    """抽盘 service"""

    @staticmethod
    def create(warehouse_id: int, tolerance_pct: float, operator: str,
               remark: str = '') -> Tuple[int, dict]:
        """创建抽盘单 - 自动从 inventory 拉取预期数量

        Returns:
            (200, {"stocktake_id": id, "total_items": N})
            (404, {"msg": "..."}) 仓库不存在
        """
        if tolerance_pct < 0 or tolerance_pct > 100:
            return 400, {'msg': 'tolerance_pct 必须在 0-100 之间'}

        wh = execute(
            'SELECT id, name FROM warehouses WHERE id=%s AND deleted_at IS NULL',
            (warehouse_id,), fetch='one'
        )
        if not wh:
            return 404, {'msg': '仓库不存在'}

        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    # 1. 创建 stocktake 主单
                    c.execute(
                        'INSERT INTO stocktakes (warehouse_id, status, tolerance_pct, operator, remark) '
                        'VALUES (%s, %s, %s, %s, %s)',
                        (warehouse_id, 'draft', tolerance_pct, operator, remark)
                    )
                    stocktake_id = c.lastrowid

                    # 2. 拉取 inventory 中所有产品 + 预期数量
                    c.execute(
                        'SELECT product_id, current_qty FROM inventory WHERE warehouse_id=%s',
                        (warehouse_id,)
                    )
                    items = c.fetchall()

                    # 3. 批量插入 stocktake_items
                    if items:
                        c.executemany(
                            'INSERT INTO stocktake_items (stocktake_id, product_id, expected_qty) '
                            'VALUES (%s, %s, %s)',
                            [(stocktake_id, i['product_id'], i['current_qty']) for i in items]
                        )
                        total_items = len(items)
                    else:
                        total_items = 0

                    # 4. 更新主单 total_items
                    c.execute(
                        'UPDATE stocktakes SET total_items=%s WHERE id=%s',
                        (total_items, stocktake_id)
                    )
                conn.commit()

            try:
                log_operation(
                    op_type='create', entity='stocktake',
                    entity_id=stocktake_id, operator=operator,
                    detail={'warehouse_id': warehouse_id, 'total_items': total_items}
                )
            except Exception:
                logger.exception('[抽盘创建] 审计失败')

            return 200, {'stocktake_id': stocktake_id, 'total_items': total_items}
        except Exception:
            logger.exception('[抽盘创建] 失败')
            return 500, {'msg': '创建抽盘单失败'}

    @staticmethod
    def submit(stocktake_id: int, items: List[dict], operator: str) -> Tuple[int, dict]:
        """提交抽盘结果 - 双重差值判断

        双重判断规则 (DESIGN v2.0 REVIEW 1.8):
            abs(diff_qty) > 1 AND abs(diff_qty) > expected * tolerance% / 100 → abnormal
            否则 → normal

        Args:
            items: [{"product_id": int, "actual_qty": float}, ...]

        Returns:
            (200, {"summary": {total, matched, diff_normal, diff_abnormal}})
        """
        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    # 锁主单
                    c.execute('SELECT tolerance_pct, status FROM stocktakes WHERE id=%s FOR UPDATE', (stocktake_id,))
                    main = c.fetchone()
                    if not main:
                        return 404, {'msg': '抽盘单不存在'}
                    if main['status'] != 'draft':
                        return 422, {'msg': f'抽盘单状态为 {main["status"]}，不能提交'}

                    tol = float(main['tolerance_pct'])

                    matched = diff_normal = diff_abnormal = 0

                    for it in items:
                        pid = it['product_id']
                        actual = float(it['actual_qty'])

                        # 锁明细行
                        c.execute(
                            'SELECT expected_qty FROM stocktake_items '
                            'WHERE stocktake_id=%s AND product_id=%s FOR UPDATE',
                            (stocktake_id, pid)
                        )
                        row = c.fetchone()
                        if not row:
                            continue
                        expected = float(row['expected_qty'])
                        diff = actual - expected
                        abs_diff = abs(diff)

                        # 双重判断
                        if abs_diff < 0.01:
                            status = 'normal'  # 无差异
                            matched += 1
                        elif abs_diff > 1 and abs_diff > expected * tol / 100:
                            status = 'abnormal'  # 容差外
                            diff_abnormal += 1
                        else:
                            status = 'normal'  # 容差内
                            diff_normal += 1

                        c.execute(
                            'UPDATE stocktake_items SET actual_qty=%s, diff_qty=%s, diff_status=%s '
                            'WHERE stocktake_id=%s AND product_id=%s',
                            (actual, diff, status, stocktake_id, pid)
                        )

                    c.execute(
                        'UPDATE stocktakes SET status=%s, submitted_at=NOW(), '
                        'matched_items=%s, diff_normal=%s, diff_abnormal=%s '
                        'WHERE id=%s',
                        ('submitted', matched, diff_normal, diff_abnormal, stocktake_id)
                    )
                conn.commit()

            try:
                log_operation(
                    op_type='submit', entity='stocktake',
                    entity_id=stocktake_id, operator=operator,
                    detail={'matched': matched, 'diff_normal': diff_normal, 'diff_abnormal': diff_abnormal}
                )
            except Exception:
                logger.exception('[抽盘提交] 审计失败')

            return 200, {
                'stocktake_id': stocktake_id,
                'summary': {
                    'total': matched + diff_normal + diff_abnormal,
                    'matched': matched,
                    'diff_normal': diff_normal,
                    'diff_abnormal': diff_abnormal
                }
            }
        except Exception:
            logger.exception('[抽盘提交] 失败')
            return 500, {'msg': '提交抽盘失败'}

    @staticmethod
    def adjust(stocktake_id: int, operator: str,
               confirm_abnormal: bool = False) -> Tuple[int, dict]:
        """确认调整 - 正常项自动调整，异常项需 confirm_abnormal=True

        Returns:
            (200, {"adjusted": N, "abnormal_count": M})
            (422, {"msg": "有 N 项异常未确认"})
        """
        try:
            with _direct_conn() as conn:
                with conn.cursor() as c:
                    c.execute('SELECT warehouse_id, status FROM stocktakes WHERE id=%s FOR UPDATE', (stocktake_id,))
                    main = c.fetchone()
                    if not main:
                        return 404, {'msg': '抽盘单不存在'}
                    if main['status'] != 'submitted':
                        return 422, {'msg': f'状态 {main["status"]} 不能 adjust'}

                    warehouse_id = main['warehouse_id']

                    # 统计异常
                    c.execute(
                        'SELECT COUNT(*) AS cnt FROM stocktake_items '
                        'WHERE stocktake_id=%s AND diff_status="abnormal"',
                        (stocktake_id,)
                    )
                    abnormal_count = c.fetchone()['cnt'] or 0
                    if abnormal_count > 0 and not confirm_abnormal:
                        return 422, {'msg': f'有 {abnormal_count} 项异常未确认'}

                    # 调整 normal 项
                    c.execute(
                        'SELECT product_id, actual_qty, expected_qty FROM stocktake_items '
                        'WHERE stocktake_id=%s AND diff_status IN ("normal","abnormal")',
                        (stocktake_id,)
                    )
                    items = c.fetchall()

                    adjusted = 0
                    for it in items:
                        pid = it['product_id']
                        actual = float(it['actual_qty'])
                        c.execute(
                            'SELECT current_qty FROM inventory '
                            'WHERE product_id=%s AND warehouse_id=%s FOR UPDATE',
                            (pid, warehouse_id)
                        )
                        row = c.fetchone()
                        if row:
                            c.execute(
                                'UPDATE inventory SET current_qty=%s, updated_at=NOW() '
                                'WHERE product_id=%s AND warehouse_id=%s',
                                (actual, pid, warehouse_id)
                            )
                        else:
                            c.execute(
                                'INSERT INTO inventory (product_id, warehouse_id, current_qty, inbound_qty) '
                                'VALUES (%s, %s, %s, 0)',
                                (pid, warehouse_id, actual)
                            )
                        # 写入 transactions（type=adjust）
                        c.execute(
                            'INSERT INTO inventory_transactions '
                            '(product_id, warehouse_id, type, qty, ref_no, operator, remark) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (pid, warehouse_id, 'adjust', actual - float(it['expected_qty']),
                             f'stocktake:{stocktake_id}', operator, '抽盘调整')
                        )
                        c.execute(
                            'UPDATE stocktake_items SET is_adjusted=1 WHERE stocktake_id=%s AND product_id=%s',
                            (stocktake_id, pid)
                        )
                        adjusted += 1

                    c.execute(
                        'UPDATE stocktakes SET status="adjusted", adjusted_at=NOW() WHERE id=%s',
                        (stocktake_id,)
                    )
                conn.commit()

            try:
                log_operation(
                    op_type='adjust', entity='stocktake',
                    entity_id=stocktake_id, operator=operator,
                    detail={'adjusted': adjusted, 'abnormal_count': abnormal_count, 'confirmed': confirm_abnormal}
                )
            except Exception:
                logger.exception('[抽盘调整] 审计失败')

            return 200, {'adjusted': adjusted, 'abnormal_count': abnormal_count}
        except Exception:
            logger.exception('[抽盘调整] 失败')
            return 500, {'msg': '调整失败'}
