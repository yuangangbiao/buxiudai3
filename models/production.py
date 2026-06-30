# -*- coding: utf-8 -*-
"""
工单数据模型 (DAO)
"""
import os
import logging
from models.database import get_connection, generate_order_no, log_status_change
from constants import ProductionStatus, OrderStatus, ProcessStatus
from utils.op_logger import log, log_step, log_sql, log_error
from config import PROCESSES


class ProductionDAO:

    @staticmethod
    def create(order_id: int, data: dict) -> int:
        """为订单创建生产工单，同时初始化工序记录"""
        from models.order import OrderDAO
        from models.process_calc_rule import ProcessCalcEngine

        log("排产", "开始创建生产工单", f"订单ID={order_id}")
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT order_no, quantity, product_type, mesh_size, customer_name FROM orders WHERE id=%s", (order_id,))
            order_row = cursor.fetchone()
            cursor.close()

            if not order_row:
                log_error("排产", "查询订单", f"订单 {order_id} 不存在")
                raise ValueError(f"订单 {order_id} 不存在")

            # 统一使用订单号
            order_no = order_row['order_no']
            order_no = order_no

            log("排产", "订单信息", f"产品类型='{order_row['product_type']}', 数量={order_row['quantity']}, 规格={order_row['mesh_size']}")

            log_step("排产", 2, "创建工单记录", f"订单号={order_no}")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO production_orders (
                    order_no, order_id, priority, plan_start, plan_end,
                    assigned_to, status, remark
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order_no, order_id,
                data.get("priority", 5),
                data.get("plan_start") or None,
                data.get("plan_end") or None,
                data.get("assigned_to", ""),
                ProductionStatus.PENDING.value,
                data.get("remark", "")
            ))
            prod_id = cursor.lastrowid
            cursor.close()
            log_sql("排产", "INSERT", "production_orders", f"工单ID={prod_id}, 订单号={order_no}")

            log_step("排产", 3, "组装订单数据", "合并基础信息+扩展参数")
            order_data = {
                "order_id": order_id,
                "quantity": order_row['quantity'] if order_row['quantity'] else 0,
                "product_type": order_row['product_type'] if order_row['product_type'] else "",
                "产品类型": order_row['product_type'] if order_row['product_type'] else "",
                "specs": str(order_row['mesh_size']) if order_row['mesh_size'] else "",
                "customer": order_row['customer_name'] if order_row['customer_name'] else "",
            }
            cursor = conn.cursor()
            cursor.execute("SELECT extra_params FROM orders WHERE id=%s", (order_id,))
            extra_row = cursor.fetchone()
            cursor.close()
            if extra_row and extra_row['extra_params']:
                try:
                    import json
                    extra_params = json.loads(extra_row['extra_params']) if isinstance(extra_row['extra_params'], str) else extra_row['extra_params']
                    if isinstance(extra_params, dict):
                        order_data.update(extra_params)
                        param_names = list(extra_params.keys())
                        log("排产", "扩展参数", f"共{len(extra_params)}个: {', '.join(param_names)}")
                except Exception:
                    pass
            else:
                log("排产", "扩展参数", "⚠️ 无扩展参数，计算公式可能结果为0")

            log("排产", "订单数据汇总", f"product_type='{order_data.get('product_type')}', 产品类型='{order_data.get('产品类型')}', quantity={order_data.get('quantity')}")

            log_step("排产", 4, "根据规则生成工序", f"调用 ProcessCalcEngine.generate_processes_from_order")
            generated_processes = ProcessCalcEngine.generate_processes_from_order(order_data, list(PROCESSES))

            log("排产", "工序生成结果", f"共生成 {len(generated_processes)} 道工序")

            log_step("排产", 5, "写入工序记录", f"写入 process_records 表")
            for proc_info in generated_processes:
                worker = proc_info.get("default_worker", "")
                unit = proc_info.get("unit", "件")
                log("排产", "写入工序", f"{proc_info['process_seq']}. {proc_info['process_name']} = {proc_info['planned_qty']} {unit}" + (f" (负责人: {worker})" if worker else ""))
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO process_records (order_id, production_id, process_name, process_code, process_seq, display_seq, planned_qty, status, worker, unit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (order_id, prod_id, proc_info["process_name"], proc_info.get("process_code", ""), proc_info["process_seq"],
                      proc_info.get("display_seq"), proc_info["planned_qty"], ProcessStatus.PENDING.value,
                      worker, unit))
                cursor.close()

            log_step("排产", 6, "更新订单状态", f"→ 已排产")
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (OrderStatus.SCHEDULED.value, order_id))
            cursor.close()
            log_sql("排产", "UPDATE", "orders", f"订单ID={order_id}, 状态→已排产")

            conn.commit()
            log_status_change("production_orders", prod_id, None, ProductionStatus.PENDING.value)
            log_status_change("orders", order_id, OrderStatus.CONFIRMED.value, OrderStatus.SCHEDULED.value)

            log("排产", "✅ 工单创建完成", f"工单ID={prod_id}, 订单号={order_no}, 工序数={len(generated_processes)}")
            return prod_id
        except Exception as e:
            log_error("排产", "创建工单失败", f"{type(e).__name__}: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update(prod_id: int, data: dict) -> bool:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM production_orders WHERE id=%s", (prod_id,))
            old = cursor.fetchone()
            old_status = old['status'] if old else None
            cursor.close()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE production_orders SET
                    priority=%s, plan_start=%s, plan_end=%s, assigned_to=%s,
                    status=%s, remark=%s,
                    updated_at=NOW()
                WHERE id=%s
            """, (
                data.get("priority", 5),
                data.get("plan_start", ""),
                data.get("plan_end", ""),
                data.get("assigned_to", ""),
                data.get("status", old_status),
                data.get("remark", ""),
                prod_id
            ))
            conn.commit()
            cursor.close()
            new_status = data.get("status")
            if new_status and new_status != old_status:
                log_status_change("production_orders", prod_id, old_status, new_status)
            return True
        finally:
            conn.close()

    @staticmethod
    def update_status(prod_id: int, new_status: str, operator: str = "系统") -> bool:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status, order_id FROM production_orders WHERE id=%s", (prod_id,))
            old = cursor.fetchone()
            old_status = old['status'] if old else None
            order_id = old['order_id'] if old else None
            cursor.close()
            STATUS_ORDERS_MAP = {
                ProductionStatus.IN_PROGRESS.value: OrderStatus.PRODUCTION.value,
                ProductionStatus.COMPLETED.value: '报工完成',
                '报工完成': '报工完成',
                '成品入库': '成品入库',
                '已发货': OrderStatus.SHIPPED.value,
                '已收货': '已收货',
                '订单完成': '订单完成',
            }
            if new_status == ProductionStatus.IN_PROGRESS.value:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE production_orders
                    SET status=%s, actual_start=NOW(),
                        updated_at=NOW()
                    WHERE id=%s
                """, (new_status, prod_id))
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE production_orders SET status=%s, updated_at=NOW() WHERE id=%s",
                    (new_status, prod_id)
                )
                cursor.close()
            if order_id:
                order_status = STATUS_ORDERS_MAP.get(new_status)
                if order_status:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (order_status, order_id))
                    cursor.close()
            conn.commit()
            log_status_change("production_orders", prod_id, old_status, new_status, operator)
            if new_status and order_id:
                try:
                    import requests as _req
                    c = conn.cursor()
                    c.execute("""
                        SELECT po.order_no, o.order_no FROM production_orders po
                        JOIN orders o ON po.order_id = o.id
                        WHERE po.id=%s
                    """, (prod_id,))
                    row = c.fetchone()
                    c.close()
                    status_key_map = {
                        ProductionStatus.IN_PROGRESS.value: 'in_production',
                        ProductionStatus.COMPLETED.value: 'report_complete',
                        '报工完成': 'report_complete',
                        '成品入库': 'warehousing',
                        '已发货': 'shipped',
                        '已收货': 'received',
                        '订单完成': 'order_complete',
                    }
                    status_key = status_key_map.get(new_status, new_status)
                    wo_no = row.get('order_no') if row else None
                    if wo_no:
                        sync_url = os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:5008')
                        _req.post(f'{sync_url}/api/sync/status-change', json={
                            'order_no': wo_no,
                            'status_key': status_key,
                            'source': 'production.update_status'
                        }, timeout=2)
                except Exception:
                    pass
            return True
        finally:
            conn.close()

    @staticmethod
    def confirm_schedule(prod_id: int, plan_start: str, plan_end: str) -> bool:
        """确认排产 - 设置计划开始/结束日期，更新工单状态为生产中"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status, order_id FROM production_orders WHERE id=%s", (prod_id,))
            old = cursor.fetchone()
            old_status = old['status'] if old else None
            order_id = old['order_id'] if old else None
            cursor.close()

            new_status = ProductionStatus.IN_PROGRESS.value
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE production_orders
                SET status=%s, plan_start=%s, plan_end=%s,
                    actual_start=COALESCE(actual_start, NOW()),
                    updated_at=NOW()
                WHERE id=%s
            """, (new_status, plan_start, plan_end, prod_id))
            cursor.close()

            if order_id:
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s",
                               (OrderStatus.PRODUCTION.value, order_id))
                cursor.close()

            conn.commit()
            if old_status and old_status != new_status:
                log_status_change("production_orders", prod_id, old_status, new_status)
            try:
                import requests as _req
                c = conn.cursor()
                c.execute("SELECT order_no FROM production_orders WHERE id=%s", (prod_id,))
                row = c.fetchone()
                c.close()
                if row and row.get('order_no'):
                    sync_url = os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:5008')
                    _req.post(f'{sync_url}/api/sync/status-change', json={
                        'order_no': row['order_no'],
                        'status_key': new_status,
                        'plan_start': plan_start,
                        'plan_end': plan_end,
                        'source': 'production.confirm_schedule'
                    }, timeout=2)
            except Exception:
                pass
            return True
        finally:
            conn.close()

    @staticmethod
    def get_all_with_order(filters: dict = None) -> list:
        """获取生产工单列表（含订单信息）"""
        conn = get_connection()
        try:
            sql = """
                SELECT po.*, o.order_no, o.customer_name, o.customer_group, o.product_type,
                       o.material, o.width, o.length, o.quantity, o.delivery_date,
                       o.status as order_status
                FROM production_orders po
                JOIN orders o ON po.order_id = o.id
                WHERE 1=1
                AND o.status NOT IN (%s, %s)
                AND po.status != '已取消'
                AND COALESCE(o.is_archived, 0) = 0
                AND o.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            """
            params = [OrderStatus.SHIPPED.value, "已取消"]
            if filters:
                if filters.get("status"):
                    status_val = filters["status"]
                    if isinstance(status_val, list) and status_val:
                        placeholders = ",".join(["%s"] * len(status_val))
                        sql += f" AND po.status IN ({placeholders})"
                        params.extend(status_val)
                    elif isinstance(status_val, str) and status_val != "全部":
                        sql += " AND po.status=%s"
                        params.append(status_val)
                if filters.get("keyword"):
                    kw = f"%{filters['keyword']}%"
                    sql += " AND (po.order_no LIKE %s OR o.order_no LIKE %s OR o.customer_name LIKE %s)"
                    params.extend([kw, kw, kw])

            sort_col = filters.get("sort_col", "po.priority") if filters else "po.priority"
            sort_reverse = filters.get("sort_reverse", False) if filters else False
            if sort_reverse:
                sql += f" ORDER BY {sort_col} DESC"
            else:
                sql += f" ORDER BY {sort_col} ASC"

            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(prod_id: int) -> dict:
        """根据工单ID获取工单（含订单信息）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT po.*, o.order_no, o.customer_name, o.product_type,
                       o.material, o.width, o.length, o.quantity, o.delivery_date,
                       o.status as order_status, o.extra_params
                FROM production_orders po
                JOIN orders o ON po.order_id = o.id
                WHERE po.id=%s
            """, (prod_id,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_order_id(order_id: int) -> dict:
        """根据订单ID获取工单（含订单信息）"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT po.*, o.order_no, o.customer_name, o.product_type,
                       o.material, o.width, o.length, o.quantity, o.delivery_date,
                       o.status as order_status, o.extra_params
                FROM production_orders po
                JOIN orders o ON po.order_id = o.id
                WHERE po.order_id=%s
                ORDER BY po.created_at DESC
                LIMIT 1
            """, (order_id,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_order_ids(order_ids: list) -> dict:
        """根据订单ID列表批量获取工单（含订单信息）"""
        if not order_ids:
            return {}
        conn = get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["%s"] * len(order_ids))
            cursor.execute(f"""
                SELECT po.*, o.order_no, o.customer_name, o.product_type,
                       o.material, o.width, o.length, o.quantity, o.delivery_date,
                       o.status as order_status, o.extra_params
                FROM production_orders po
                JOIN orders o ON po.order_id = o.id
                WHERE po.order_id IN ({placeholders})
            """, tuple(order_ids))
            rows = cursor.fetchall()
            cursor.close()
            result = {}
            for row in rows:
                d = dict(row)
                result[d["order_id"]] = d
            return result
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Dashboard 大屏专用方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_dashboard_production_list(limit: int = 20) -> list:
        """获取大屏生产列表（生产工单 + 订单信息 JOIN）

        Returns:
            list: [{
                'prod_id', 'order_no', 'priority',
                'order_no', 'customer_name', 'product_type',
                'quantity', 'unit', 'status', 'delivery_date',
                'mesh_size', 'wire_diameter', 'width', 'length',
                'surface_treatment'
            }, ...]
        """
        from constants import OrderStatus as ConstOrderStatus
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT "
                "  p.id as prod_id, p.order_no, p.priority, "
                "  o.order_no, o.customer_name, o.product_type, "
                "  o.quantity, o.unit, o.status, o.delivery_date, "
                "  o.mesh_size, o.wire_diameter, o.width, o.length, "
                "  o.surface_treatment "
                "FROM production_orders p "
                "LEFT JOIN orders o ON p.order_id = o.id "
                "WHERE o.status IN (%s, %s, %s, %s) "
                "ORDER BY p.priority ASC, o.delivery_date ASC "
                "LIMIT %s",
                (ConstOrderStatus.SCHEDULED.value, ConstOrderStatus.PRODUCTION.value,
                 ConstOrderStatus.QC.value, ConstOrderStatus.PENDING_SHIP.value,
                 limit)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()