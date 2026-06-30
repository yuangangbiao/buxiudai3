# -*- coding: utf-8 -*-
"""
发货数据模型 (DAO)
"""
import json
import os
from models.database import get_connection, generate_shipment_no, log_status_change
from constants import OrderStatus, ShipmentStatus, FinishedGoodsStatus


class ShipmentDAO:

    @staticmethod
    def create(data: dict) -> int:
        conn = get_connection()
        shipment_no = generate_shipment_no()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO shipments (
                shipment_no, order_id, finished_goods_id, warehouse,
                ship_quantity, unit, logistics_company, tracking_no,
                ship_date, recipient, recipient_phone, recipient_address,
                freight, status, remark
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            shipment_no,
            data.get("order_id"),
            data.get("finished_goods_id"),
            data.get("warehouse", "成品仓库"),
            float(data.get("ship_quantity", 0)),
            data.get("unit", "米"),
            data.get("logistics_company", ""),
            data.get("tracking_no", ""),
            data.get("ship_date", ""),
            data.get("recipient", ""),
            data.get("recipient_phone", ""),
            data.get("recipient_address", ""),
            float(data.get("freight", 0)),
            ShipmentStatus.PENDING.value,
            data.get("remark", "")
        ))
        new_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        return new_id

    @staticmethod
    def confirm_ship(shipment_id: int, operator: str = "系统") -> bool:
        """确认发货"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT order_id, finished_goods_id FROM shipments WHERE id=%s", (shipment_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            conn.close()
            return False
        order_id = row[0]
        fg_id = row[1]

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE shipments SET status=%s, ship_date=COALESCE(NULLIF(ship_date,''), DATE(NOW())), updated_at=NOW() WHERE id=%s",
            (ShipmentStatus.COMPLETED.value, shipment_id)
        )
        cursor.close()
        if fg_id:
            cursor = conn.cursor()
            cursor.execute("UPDATE finished_goods SET status=%s WHERE id=%s", (FinishedGoodsStatus.OUTBOUND.value, fg_id))
            cursor.close()
        if order_id:
            # 先查询订单当前真实状态
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
            old_order_status = cursor.fetchone()
            old_order_status = old_order_status[0] if old_order_status else "未知"
            cursor.close()
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (OrderStatus.SHIPPED.value, order_id))
            cursor.close()
            conn.commit()  # 先提交当前事务，再写日志（避免数据库锁冲突）
            log_status_change("orders", order_id, old_order_status, OrderStatus.SHIPPED.value, operator, "发货确认")
        conn.commit()
        log_status_change("shipments", shipment_id, ShipmentStatus.PENDING.value, ShipmentStatus.COMPLETED.value, operator)
        return True

    @staticmethod
    def get_all(filters: dict = None, limit: int = 200) -> list:
        conn = get_connection()
        try:
            sql = """
                SELECT s.*, o.order_no, o.customer_name, o.product_type,
                       o.material, o.width, o.length,
                       (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                        FROM production_orders po WHERE po.order_id = s.order_id) as order_no
                FROM shipments s
                JOIN orders o ON s.order_id = o.id
                WHERE o.status IN (%s, %s)
                AND s.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            """
            params = [OrderStatus.PENDING_SHIP.value, OrderStatus.SHIPPED.value]
            if filters:
                if filters.get("status") and filters["status"] != "全部":
                    sql += " AND s.status=%s"
                    params.append(filters["status"])
                if filters.get("keyword"):
                    kw = f"%{filters['keyword']}%"
                    sql += " AND (o.order_no LIKE %s OR o.customer_name LIKE %s OR s.shipment_no LIKE %s)"
                    params.extend([kw, kw, kw])
                if filters.get("date_from"):
                    sql += " AND s.ship_date >= %s"
                    params.append(filters["date_from"])
                if filters.get("date_to"):
                    sql += " AND s.ship_date <= %s"
                    params.append(filters["date_to"])
            sql += " ORDER BY s.created_at DESC LIMIT %s"
            params.append(limit)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_all_shipments(filters: dict = None, limit: int = 200) -> list:
        """获取所有发货单（不限订单状态，用于物流追踪）"""
        conn = get_connection()
        try:
            sql = """
                SELECT s.*, o.order_no, o.customer_name, o.product_type,
                       o.material, o.width, o.length,
                       (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                        FROM production_orders po WHERE po.order_id = s.order_id) as order_no
                FROM shipments s
                JOIN orders o ON s.order_id = o.id
                WHERE 1=1
                AND s.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            """
            params = []
            if filters:
                if filters.get("status") and filters["status"] != "全部":
                    sql += " AND s.status=%s"
                    params.append(filters["status"])
                if filters.get("keyword"):
                    kw = f"%{filters['keyword']}%"
                    sql += " AND (o.order_no LIKE %s OR o.customer_name LIKE %s OR s.shipment_no LIKE %s OR s.tracking_no LIKE %s)"
                    params.extend([kw, kw, kw, kw])
                if filters.get("date_from"):
                    sql += " AND s.ship_date >= %s"
                    params.append(filters["date_from"])
                if filters.get("date_to"):
                    sql += " AND s.ship_date <= %s"
                    params.append(filters["date_to"])
            sql += " ORDER BY s.created_at DESC LIMIT %s"
            params.append(limit)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(shipment_id: int) -> dict:
        """根据ID获取发货单"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, o.order_no, o.customer_name, o.product_type,
                       (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                        FROM production_orders po WHERE po.order_id = s.order_id) as order_no
                FROM shipments s
                JOIN orders o ON s.order_id = o.id
                WHERE s.id = %s
            """, (shipment_id,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_shipment_no(shipment_no: str) -> dict:
        """根据发货单号获取发货单"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, o.order_no, o.customer_name, o.product_type,
                       (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                        FROM production_orders po WHERE po.order_id = s.order_id) as order_no
                FROM shipments s
                JOIN orders o ON s.order_id = o.id
                WHERE s.shipment_no = %s
            """, (shipment_no,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def save_tracking(shipment_id: int, tracking_no: str, state: str,
                      state_text: str, traces: list, company_code: str) -> bool:
        """保存物流追踪查询结果"""
        conn = get_connection()
        try:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            traces_json = json.dumps(traces, ensure_ascii=False)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shipment_tracks
                (shipment_id, tracking_no, state, state_text, traces, company_code, query_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (shipment_id, tracking_no, state, state_text, traces_json, company_code, now))
            conn.commit()
            cursor.close()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_tracking_history(shipment_id: int, limit: int = 10) -> list:
        """获取发货单的物流追踪历史"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, shipment_id, tracking_no, state, state_text,
                       traces, company_code, query_time
                FROM shipment_tracks
                WHERE shipment_id = %s
                ORDER BY query_time DESC
                LIMIT %s
            """, (shipment_id, limit))
            rows = cursor.fetchall()
            cursor.close()
            results = []
            for row in rows:
                r = dict(row) if isinstance(row, dict) else {}
                if not r and isinstance(row, (list, tuple)):
                    r = {
                        "id": row[0], "shipment_id": row[1], "tracking_no": row[2],
                        "state": row[3], "state_text": row[4], "traces": row[5],
                        "company_code": row[6], "query_time": row[7],
                    }
                try:
                    r["traces"] = json.loads(r.get("traces", "[]")) if isinstance(r.get("traces"), str) else r.get("traces", [])
                except (json.JSONDecodeError, TypeError):
                    r["traces"] = []
                results.append(r)
            return results
        finally:
            conn.close()

    @staticmethod
    def get_latest_tracking(shipment_id: int) -> dict:
        """获取发货单的最新一次追踪结果"""
        history = ShipmentDAO.get_tracking_history(shipment_id, limit=1)
        return history[0] if history else None

    @staticmethod
    def get_all_with_latest_tracking(filters: dict = None) -> list:
        """获取发货单列表，附带最新物流状态（单SQL LEFT JOIN，消除N+1）"""
        conn = get_connection()
        try:
            sql = """
                SELECT s.*, o.order_no, o.customer_name, o.product_type,
                       o.material, o.width, o.length,
                       (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                        FROM production_orders po WHERE po.order_id = s.order_id) as order_no,
                       st.state_text AS track_state,
                       st.query_time AS track_time
                FROM shipments s
                JOIN orders o ON s.order_id = o.id
                LEFT JOIN shipment_tracks st ON st.id = (
                    SELECT t.id FROM shipment_tracks t
                    WHERE t.shipment_id = s.id
                    ORDER BY t.query_time DESC
                    LIMIT 1
                )
                WHERE 1=1
            """
            params = []
            if filters:
                if filters.get("status") and filters["status"] != "全部":
                    sql += " AND s.status=%s"
                    params.append(filters["status"])
                if filters.get("keyword"):
                    kw = f"%{filters['keyword']}%"
                    sql += " AND (o.order_no LIKE %s OR o.customer_name LIKE %s OR s.shipment_no LIKE %s OR s.tracking_no LIKE %s)"
                    params.extend([kw, kw, kw, kw])
                if filters.get("date_from"):
                    sql += " AND s.ship_date >= %s"
                    params.append(filters["date_from"])
                if filters.get("date_to"):
                    sql += " AND s.ship_date <= %s"
                    params.append(filters["date_to"])
            sql += " ORDER BY s.created_at DESC LIMIT 200"
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_finished_goods(order_id: int = None, days_limit: int = 60) -> list:
        """获取成品库存（优化：支持60天时间范围限制）

        Args:
            order_id: 订单ID筛选
            days_limit: 限制最近N天的数据，None表示不限制
        """
        conn = get_connection()
        try:
            if order_id:
                cursor = conn.cursor()
                if days_limit:
                    cursor.execute("""
                        SELECT fg.*, o.order_no, o.customer_name, o.product_type,
                               (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                                FROM production_orders po WHERE po.order_id = fg.order_id) as order_no
                        FROM finished_goods fg
                        JOIN orders o ON fg.order_id = o.id
                        WHERE fg.order_id=%s AND fg.status=%s AND fg.in_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    """, (order_id, FinishedGoodsStatus.IN_STOCK.value, days_limit))
                else:
                    cursor.execute("""
                        SELECT fg.*, o.order_no, o.customer_name, o.product_type,
                               (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                                FROM production_orders po WHERE po.order_id = fg.order_id) as order_no
                        FROM finished_goods fg
                        JOIN orders o ON fg.order_id = o.id
                        WHERE fg.order_id=%s AND fg.status=%s
                    """, (order_id, FinishedGoodsStatus.IN_STOCK.value))
                rows = cursor.fetchall()
                cursor.close()
            else:
                cursor = conn.cursor()
                if days_limit:
                    cursor.execute("""
                        SELECT fg.*, o.order_no, o.customer_name, o.product_type,
                               (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                                FROM production_orders po WHERE po.order_id = fg.order_id) as order_no
                        FROM finished_goods fg
                        JOIN orders o ON fg.order_id = o.id
                        WHERE fg.status=%s AND fg.in_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                        ORDER BY fg.in_date DESC
                    """, (FinishedGoodsStatus.IN_STOCK.value, days_limit))
                else:
                    cursor.execute("""
                        SELECT fg.*, o.order_no, o.customer_name, o.product_type,
                               (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                                FROM production_orders po WHERE po.order_id = fg.order_id) as order_no
                        FROM finished_goods fg
                        JOIN orders o ON fg.order_id = o.id
                        WHERE fg.status=%s
                        ORDER BY fg.in_date DESC
                    """, (FinishedGoodsStatus.IN_STOCK.value,))
                rows = cursor.fetchall()
                cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_finished_goods_by_id(fg_id: int) -> dict:
        """根据ID获取成品库存（消除N+1查询）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fg.*, o.order_no, o.customer_name, o.product_type,
                       (SELECT GROUP_CONCAT(DISTINCT po.order_no SEPARATOR ', ')
                        FROM production_orders po WHERE po.order_id = fg.order_id) as order_no
                FROM finished_goods fg
                JOIN orders o ON fg.order_id = o.id
                WHERE fg.id=%s LIMIT 1
            """, (fg_id,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Dashboard 大屏专用方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_recent_for_dashboard(limit: int = 10) -> list:
        """获取最近发货记录（大屏用）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    s.shipment_no,
                    o.order_no,
                    o.customer_name,
                    s.ship_quantity,
                    s.unit,
                    s.logistics_company,
                    s.status,
                    s.ship_date
                FROM shipments s
                LEFT JOIN orders o ON s.order_id = o.id
                ORDER BY s.ship_date DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()
