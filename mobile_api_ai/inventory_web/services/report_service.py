# -*- coding: utf-8 -*-
"""报表 service - 聚合查询
TASK-T2/T7 接口签名遵循 DESIGN v2.0 缺陷 2

修复 L-8：异常协议统一
- 所有方法返回 (status_code: int, data: list|dict)
- status_code: 200=成功，400=参数错，500=服务器错
- 调用方（如 routes_api）负责把 status_code 转换为 HTTP 响应码
"""
import logging
from typing import Tuple
from ..db_utils import execute

logger = logging.getLogger(__name__)


class ReportService:
    """报表聚合 service"""

    @staticmethod
    def stock_trend(months: int = 6) -> Tuple[int, list]:
        """库存价值/数量趋势（按月）

        TODO-T5: 单价口径 - 使用 products.last_purchase_price
        （如未填则用 0，趋势仍能展示数量，价值数据需业务先填采购价）

        Returns:
            (200, [{"month": "2025-12", "total_qty": 12345, "total_value": 67890.5}, ...])
        """
        if months < 1 or months > 24:
            return 400, [{'msg': 'months 必须在 1-24 之间'}]

        try:
            # 修复 H-2：避免在 SQL 中使用 %Y/%m（pymysql mogrify 会做 % 替换，
            # '%%Y' 行为依赖 pymysql 版本，不可靠）
            # 改用 YEAR() + LPAD(MONTH()) 拼接，避免任何 % 字符
            rows = execute(
                """
                SELECT
                    CONCAT(YEAR(i.updated_at), '-', LPAD(MONTH(i.updated_at), 2, '0')) AS month,
                    SUM(i.current_qty) AS total_qty,
                    SUM(i.current_qty * COALESCE(p.last_purchase_price, 0)) AS total_value
                FROM inventory i
                JOIN products p ON i.product_id = p.id AND p.deleted_at IS NULL
                WHERE i.updated_at >= DATE_SUB(NOW(), INTERVAL %s MONTH)
                GROUP BY YEAR(i.updated_at), MONTH(i.updated_at)
                ORDER BY YEAR(i.updated_at) ASC, MONTH(i.updated_at) ASC
                """,
                (months,), fetch='all'
            ) or []
            return 200, rows
        except Exception:
            logger.exception('[报表] 库存趋势失败')
            return 500, []

    @staticmethod
    def inbound_outbound_flow(weeks: int = 12) -> Tuple[int, list]:
        """出入库流量（按周）

        Returns:
            (200, [{"week": "2025-W23", "inbound": 100, "outbound": 80}, ...])
        """
        if weeks < 1 or weeks > 52:
            return 400, [{'msg': 'weeks 必须在 1-52 之间'}]

        try:
            rows = execute(
                """
                SELECT
                    YEARWEEK(t.created_at, 3) AS yw,
                    MIN(DATE(t.created_at)) AS week_start,
                    SUM(CASE WHEN t.type='inbound' THEN t.qty ELSE 0 END) AS inbound,
                    SUM(CASE WHEN t.type='outbound' THEN t.qty ELSE 0 END) AS outbound
                FROM inventory_transactions t
                WHERE t.created_at >= DATE_SUB(NOW(), INTERVAL %s WEEK)
                  AND t.type IN ('inbound','outbound')
                GROUP BY YEARWEEK(t.created_at, 3)
                ORDER BY yw ASC
                """,
                (weeks,), fetch='all'
            ) or []
            return 200, rows
        except Exception:
            logger.exception('[报表] 出入库流量失败')
            return 500, []

    @staticmethod
    def top_low_stock(limit: int = 10) -> Tuple[int, list]:
        """Top 低库存预警

        Returns:
            (200, [{"product_id": 1, "code": "P001", "name": "...", "current_qty": 5, "safety_stock": 20}, ...])
        """
        if limit < 1 or limit > 100:
            return 400, [{'msg': 'limit 必须在 1-100 之间'}]

        try:
            rows = execute(
                """
                SELECT
                    p.id AS product_id, p.code, p.name, p.spec, p.unit,
                    p.safety_stock,
                    COALESCE(SUM(i.current_qty), 0) AS current_qty
                FROM products p
                LEFT JOIN inventory i ON p.id = i.product_id
                WHERE p.deleted_at IS NULL
                GROUP BY p.id
                HAVING current_qty < p.safety_stock
                ORDER BY (p.safety_stock - current_qty) DESC
                LIMIT %s
                """,
                (limit,), fetch='all'
            ) or []
            return 200, rows
        except Exception:
            logger.exception('[报表] Top 低库存失败')
            return 500, []

    @staticmethod
    def category_distribution() -> Tuple[int, list]:
        """分类占比

        Returns:
            (200, [{"category_id": 1, "category_name": "成品", "total_qty": 1000, "count": 50}, ...])
        """
        try:
            rows = execute(
                """
                SELECT
                    c.id AS category_id,
                    c.name AS category_name,
                    COUNT(p.id) AS product_count,
                    COALESCE(SUM(i.current_qty), 0) AS total_qty
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id AND p.deleted_at IS NULL
                LEFT JOIN inventory i ON p.id = i.product_id
                WHERE c.deleted_at IS NULL
                GROUP BY c.id
                ORDER BY total_qty DESC
                """,
                fetch='all'
            ) or []
            return 200, rows
        except Exception:
            logger.exception('[报表] 分类占比失败')
            return 500, []
