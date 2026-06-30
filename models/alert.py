# -*- coding: utf-8 -*-
"""
逾期预警模型
"""
from models.database import get_connection
from datetime import datetime, timedelta


class AlertDAO:
    """逾期预警数据访问"""

    @staticmethod
    def get_overdue_orders(days: int = 0) -> list:
        """获取逾期订单"""
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().date()
        warning_date = today + timedelta(days=days)

        # 逾期订单（已过交货日期但未完成）
        # 只获取有交货日期且状态正常的订单，在Python中进一步过滤
        overdue_sql = """
            SELECT o.*,
                   po.status as production_status,
                   po.order_no
            FROM orders o
            LEFT JOIN production_orders po ON o.id = po.order_id
            WHERE o.delivery_date IS NOT NULL
              AND o.status NOT IN ('已完成', '已取消', '已关闭')
            ORDER BY o.delivery_date ASC
        """
        cursor.execute(overdue_sql)
        overdue_rows = cursor.fetchall()

        # 过滤并计算逾期天数（Python计算，数据库无关）
        overdue = []
        for row in overdue_rows:
            row_dict = dict(row)
            delivery_date = row_dict.get('delivery_date')
            if hasattr(delivery_date, 'date'):
                dlv_date = delivery_date.date()
            elif isinstance(delivery_date, str) and delivery_date and delivery_date[:4] != '0000':
                try:
                    dlv_date = datetime.strptime(delivery_date[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
            else:
                continue

            overdue_days = (today - dlv_date).days
            if overdue_days > 0:
                row_dict['overdue_days'] = overdue_days
                overdue.append(row_dict)

        # 即将到期订单（提前N天预警）
        warning_sql = """
            SELECT o.*,
                   po.status as production_status,
                   po.order_no
            FROM orders o
            LEFT JOIN production_orders po ON o.id = po.order_id
            WHERE o.delivery_date IS NOT NULL
              AND o.status NOT IN ('已完成', '已取消', '已关闭', '待确认')
            ORDER BY o.delivery_date ASC
        """
        cursor.execute(warning_sql)
        warning_rows = cursor.fetchall()

        warning = []
        for row in warning_rows:
            row_dict = dict(row)
            delivery_date = row_dict.get('delivery_date')
            if hasattr(delivery_date, 'date'):
                dlv_date = delivery_date.date()
            elif isinstance(delivery_date, str) and delivery_date:
                try:
                    dlv_date = datetime.strptime(delivery_date[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
            else:
                continue

            remain_days = (dlv_date - today).days
            if 0 <= remain_days <= days:
                row_dict['remain_days'] = remain_days
                warning.append(row_dict)

        cursor.close()
        conn.close()

        return {
            "overdue": overdue,
            "warning": warning
        }

    @staticmethod
    def get_overdue_processes(days: int = 0) -> list:
        """获取逾期工序"""
        conn = get_connection()
        cursor = conn.cursor()
        today = datetime.now().date()

        sql = """
            SELECT pr.*,
                   o.order_no, o.customer_name, o.product_type,
                   o.delivery_date
            FROM process_records pr
            JOIN orders o ON pr.order_id = o.id
            WHERE pr.status = '待开始'
            ORDER BY pr.planned_date ASC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()

        result = []
        for row in rows:
            row_dict = dict(row)
            planned_date = row_dict.get('planned_date')
            if planned_date:
                if hasattr(planned_date, 'date'):
                    plan_date = planned_date.date()
                elif isinstance(planned_date, str) and planned_date:
                    try:
                        plan_date = datetime.strptime(planned_date[:10], "%Y-%m-%d").date()
                    except Exception:
                        plan_date = None
                else:
                    plan_date = None

                if plan_date and plan_date < today:
                    overdue_days = (today - plan_date).days
                    row_dict['overdue_days'] = overdue_days
                    result.append(row_dict)

        cursor.close()
        conn.close()
        return result

    @staticmethod
    def get_low_inventory_alerts() -> list:
        """获取库存预警（低于安全库存的材料）"""
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            SELECT i.*,
                   CASE
                       WHEN i.quantity <= 0 THEN '库存不足'
                       WHEN i.quantity <= i.warning_qty THEN '库存预警'
                       ELSE '正常'
                   END as alert_level
            FROM inventory i
            WHERE i.quantity <= i.warning_qty
            ORDER BY (i.warning_qty - i.quantity) / NULLIF(i.warning_qty, 0) DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_all_alerts(days: int = 3) -> dict:
        """获取所有预警信息"""
        alerts = {
            "overdue_orders": AlertDAO.get_overdue_orders(0)["overdue"],
            "warning_orders": AlertDAO.get_overdue_orders(days)["warning"],
            "low_inventory": AlertDAO.get_low_inventory_alerts(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return alerts


def init_alert_table():
    """初始化预警表（用于存储已读/未读状态）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            alert_type TEXT NOT NULL,
            record_id INT NOT NULL,
            is_read INT DEFAULT 0,
            is_dismissed INT DEFAULT 0,
            created_at DATETIME DEFAULT NOW()
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()