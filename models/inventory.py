# -*- coding: utf-8 -*-
"""
原材料库存数据模型 (DAO)
"""
import os
from models.database import get_connection
from config import STOCK_WARNING_THRESHOLD


class InventoryDAO:

    @staticmethod
    def create(data: dict) -> int:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (material_name, material_type, specification,
                    quantity, unit, unit_price, warehouse, warning_qty, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get("material_name", ""),
                data.get("material_type", ""),
                data.get("specification", ""),
                float(data.get("quantity", 0)),
                data.get("unit", "kg"),
                float(data.get("unit_price", 0)),
                data.get("warehouse", "主仓库"),
                float(data.get("warning_qty", STOCK_WARNING_THRESHOLD)),
                data.get("remark", "")
            ))
            new_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            return new_id
        finally:
            conn.close()

    @staticmethod
    def update(inv_id: int, data: dict) -> bool:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inventory SET
                    material_name=%s, material_type=%s, specification=%s,
                    unit=%s, unit_price=%s, warehouse=%s, warning_qty=%s,
                    remark=%s, updated_at=NOW()
                WHERE id=%s
            """, (
                data.get("material_name", ""),
                data.get("material_type", ""),
                data.get("specification", ""),
                data.get("unit", "kg"),
                float(data.get("unit_price", 0)),
                data.get("warehouse", "主仓库"),
                float(data.get("warning_qty", STOCK_WARNING_THRESHOLD)),
                data.get("remark", ""),
                inv_id
            ))
            conn.commit()
            cursor.close()
            return True
        finally:
            conn.close()

    @staticmethod
    def stock_in(inv_id: int, qty: float, order_id=None, operator="", remark="") -> bool:
        """入库操作"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM inventory WHERE id=%s", (inv_id,))
            row = cursor.fetchone()
            before_qty = row[0] if row else 0
            cursor.close()
            after_qty = before_qty + qty
            cursor = conn.cursor()
            cursor.execute("UPDATE inventory SET quantity=%s, updated_at=NOW() WHERE id=%s",
                         (after_qty, inv_id))
            cursor.close()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory_records (inventory_id, order_id, record_type, quantity,
                    before_qty, after_qty, operator, remark)
                VALUES (%s, %s, '入库', %s, %s, %s, %s, %s)
            """, (inv_id, order_id, qty, before_qty, after_qty, operator, remark))
            cursor.close()
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def stock_out(inv_id: int, qty: float, order_id=None, operator="", remark="") -> bool:
        """出库（领料）操作"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM inventory WHERE id=%s", (inv_id,))
            row = cursor.fetchone()
            before_qty = row[0] if row else 0
            cursor.close()
            if before_qty < qty:
                return False  # 库存不足
            after_qty = before_qty - qty
            cursor = conn.cursor()
            cursor.execute("UPDATE inventory SET quantity=%s, updated_at=NOW() WHERE id=%s",
                         (after_qty, inv_id))
            cursor.close()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory_records (inventory_id, order_id, record_type, quantity,
                    before_qty, after_qty, operator, remark)
                VALUES (%s, %s, '出库', %s, %s, %s, %s, %s)
            """, (inv_id, order_id, qty, before_qty, after_qty, operator, remark))
            cursor.close()
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_all(filters: dict = None) -> list:
        conn = get_connection()
        try:
            sql = "SELECT * FROM inventory WHERE 1=1"
            params = []
            if filters:
                if filters.get("material_type") and filters["material_type"] != "全部":
                    sql += " AND material_type=%s"
                    params.append(filters["material_type"])
                if filters.get("keyword"):
                    kw = f"%{filters['keyword']}%"
                    sql += " AND (material_name LIKE %s OR specification LIKE %s)"
                    params.extend([kw, kw])
                if filters.get("warning_only"):
                    sql += " AND quantity <= warning_qty"
            sql += " ORDER BY material_type, material_name"
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_records(inv_id: int = None, limit: int = 50) -> list:
        """获取出入库记录"""
        conn = get_connection()
        try:
            if inv_id:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ir.*, i.material_name, o.order_no
                    FROM inventory_records ir
                    JOIN inventory i ON ir.inventory_id = i.id
                    LEFT JOIN orders o ON ir.order_id = o.id
                    WHERE ir.inventory_id=%s
                    ORDER BY ir.record_date DESC LIMIT %s
                """, (inv_id, limit))
                rows = cursor.fetchall()
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ir.*, i.material_name, o.order_no
                    FROM inventory_records ir
                    JOIN inventory i ON ir.inventory_id = i.id
                    LEFT JOIN orders o ON ir.order_id = o.id
                    ORDER BY ir.record_date DESC LIMIT %s
                """, (limit,))
                rows = cursor.fetchall()
                cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_warning_items() -> list:
        """获取库存预警项"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM inventory WHERE quantity <= warning_qty ORDER BY quantity ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Dashboard 大屏专用方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_dashboard_overview() -> list:
        """获取大屏库存概览（所有物料）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT material_name, quantity, unit, warning_qty as safe_stock "
                "FROM inventory ORDER BY material_name ASC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_low_inventory_alerts(limit: int = 3) -> list:
        """获取低库存告警项（大屏用）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT material_name, quantity, unit, warning_qty "
                "FROM inventory "
                "WHERE quantity < warning_qty "
                "ORDER BY (CAST(quantity AS DECIMAL(12,2)) / warning_qty) ASC "
                "LIMIT %s",
                (limit,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # 兼容旧 inventory_db_complete API
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def search_by_material(material_name: str, spec: str = None, unit: str = None) -> list:
        """按物料名称搜索库存（兼容 inventory_db_complete.inv_db.search_by_material）

        @param material_name: 物料名称（模糊匹配）
        @param spec: 规格（可选，模糊匹配）
        @param unit: 单位（可选）
        @return: 库存列表 [{"material_name", "current_qty", "warehouse", ...}, ...]
        """
        conn = get_connection()
        try:
            sql = "SELECT material_name, specification, quantity AS current_qty, unit, warehouse, remark FROM inventory WHERE 1=1"
            params = []
            if material_name:
                sql += " AND material_name LIKE %s"
                params.append(f"%{material_name}%")
            if spec:
                sql += " AND specification LIKE %s"
                params.append(f"%{spec}%")
            if unit:
                sql += " AND unit=%s"
                params.append(unit)
            sql += " ORDER BY material_name"
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows] if rows else []
        finally:
            conn.close()
