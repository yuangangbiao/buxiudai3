# -*- coding: utf-8 -*-
"""通知 service
TASK-T2/T8 接口签名遵循 DESIGN v2.0 缺陷 2
"""
import logging
from typing import Tuple
from ..db_utils import execute

logger = logging.getLogger(__name__)


class NotificationService:
    """通知 service"""

    @staticmethod
    def create(type_: str, title: str, body: str = '', link: str = None) -> Tuple[int, dict]:
        """创建通知

        Args:
            type_: low_stock/stocktake_diff/transfer_complete/transfer_in_transit/system
        """
        if type_ not in ('low_stock', 'stocktake_diff', 'transfer_complete', 'transfer_in_transit', 'system'):
            return 400, {'msg': f'未知通知类型: {type_}'}

        try:
            nid = execute(
                'INSERT INTO notifications (type, title, body, link) VALUES (%s, %s, %s, %s)',
                (type_, title, body, link), commit=True
            )
            return 200, {'id': nid}
        except Exception:
            logger.exception('[通知] 创建失败')
            return 500, {'msg': '创建通知失败'}

    @staticmethod
    def list_unread(limit: int = 20) -> Tuple[int, list]:
        """列出未读通知"""
        try:
            items = execute(
                'SELECT id, type, title, body, link, is_read, created_at '
                'FROM notifications WHERE is_read=0 '
                'ORDER BY id DESC LIMIT %s',
                (limit,), fetch='all'
            ) or []
            return 200, items
        except Exception:
            logger.exception('[通知] 列表失败')
            return 500, []

    @staticmethod
    def list_all(is_read: int = None, page: int = 1, page_size: int = 20) -> Tuple[int, dict]:
        """分页列出所有通知"""
        where = ['1=1']
        params = []
        if is_read is not None:
            where.append('is_read = %s')
            params.append(int(is_read))
        where_sql = ' AND '.join(where)
        offset = (page - 1) * page_size

        total = execute(
            f'SELECT COUNT(*) AS cnt FROM notifications WHERE {where_sql}',
            tuple(params), fetch='one'
        )['cnt'] or 0

        items = execute(
            f'SELECT id, type, title, body, link, is_read, created_at, read_at '
            f'FROM notifications WHERE {where_sql} ORDER BY id DESC LIMIT %s OFFSET %s',
            tuple(params) + (page_size, offset), fetch='all'
        ) or []
        return 200, {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    @staticmethod
    def mark_read(nid: int) -> Tuple[int, dict]:
        """标记已读"""
        try:
            execute(
                'UPDATE notifications SET is_read=1, read_at=NOW() WHERE id=%s AND is_read=0',
                (nid,), commit=True
            )
            return 200, {'ok': True}
        except Exception:
            logger.exception('[通知] 标记已读失败')
            return 500, {'msg': '标记已读失败'}

    @staticmethod
    def mark_all_read() -> Tuple[int, dict]:
        """全部已读"""
        try:
            rows = execute(
                'UPDATE notifications SET is_read=1, read_at=NOW() WHERE is_read=0',
                commit=True
            )
            return 200, {'marked': rows or 0}
        except Exception:
            logger.exception('[通知] 全部已读失败')
            return 500, {'msg': '全部已读失败'}

    @staticmethod
    def auto_check_low_stock() -> int:
        """自动检查低库存 - 由入库出库后调用

        Returns:
            新建的通知数
        """
        try:
            rows = execute(
                """
                SELECT
                    p.id, p.code, p.name, p.safety_stock,
                    COALESCE(SUM(i.current_qty), 0) AS current_qty
                FROM products p
                LEFT JOIN inventory i ON p.id = i.product_id
                WHERE p.deleted_at IS NULL
                GROUP BY p.id
                HAVING current_qty < p.safety_stock
                """,
                fetch='all'
            ) or []

            count = 0
            for r in rows:
                # 24h 内是否已通知过
                recent = execute(
                    "SELECT id FROM notifications "
                    "WHERE type='low_stock' AND link LIKE %s "
                    "AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1",
                    (f'%product:{r["id"]}%',), fetch='one'
                )
                if recent:
                    continue

                NotificationService.create(
                    type_='low_stock',
                    title=f'低库存预警：{r["code"]} {r["name"]}',
                    body=f'当前库存 {r["current_qty"]} < 安全库存 {r["safety_stock"]}',
                    link=f'/inventory/stock?product_id={r["id"]}'
                )
                count += 1
            return count
        except Exception:
            logger.exception('[通知] 自动检查低库存失败')
            return 0
