# -*- coding: utf-8 -*-
"""
生产统计数据模型 (DAO)
用于收集订单从确认到发货的用时、生产周期、工序用时、合格率、用料差异等数据
"""
import os
from models.database import get_connection
from datetime import datetime, timedelta


class ProductionStatsDAO:
    """生产统计数据访问对象"""

    @staticmethod
    def calculate_order_stats(order_id: int) -> bool:
        """
        计算订单的生产统计数据
        :param order_id: 订单ID
        :return: 是否计算成功
        """
        log("生产统计", "开始计算订单统计数据", f"订单ID={order_id}")
        
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. 获取订单基本信息
            cursor.execute("""
                SELECT order_no, product_type, confirm_time, ship_time, receive_time 
                FROM orders WHERE id=%s
            """, (order_id,))
            order_row = cursor.fetchone()
            if not order_row:
                log_error("生产统计", "计算统计", f"订单 {order_id} 不存在")
                return False
            
            order_no = order_row['order_no']
            product_type = order_row['product_type']
            confirm_time = order_row['confirm_time']
            ship_time = order_row['ship_time']
            receive_time = order_row['receive_time']
            
            # 2. 获取生产订单信息
            cursor.execute("""
                SELECT id, plan_confirm_time, actual_end 
                FROM production_orders WHERE order_id=%s
            """, (order_id,))
            production_row = cursor.fetchone()
            production_id = production_row['id'] if production_row else None
            plan_confirm_time = production_row['plan_confirm_time'] if production_row else None
            production_complete_time = production_row['actual_end'] if production_row else None
            
            # 3. 计算订单周期（按天计算）
            order_cycle_days = None
            if confirm_time and ship_time:
                confirm_dt = datetime.strptime(str(confirm_time), '%Y-%m-%d %H:%M:%S')
                ship_dt = datetime.strptime(str(ship_time), '%Y-%m-%d %H:%M:%S')
                order_cycle_days = (ship_dt - confirm_dt).days
            
            delivery_cycle_days = None
            if ship_time and receive_time:
                ship_dt = datetime.strptime(str(ship_time), '%Y-%m-%d %H:%M:%S')
                receive_dt = datetime.strptime(str(receive_time), '%Y-%m-%d %H:%M:%S')
                delivery_cycle_days = (receive_dt - ship_dt).days
            
            total_cycle_days = None
            if confirm_time and receive_time:
                confirm_dt = datetime.strptime(str(confirm_time), '%Y-%m-%d %H:%M:%S')
                receive_dt = datetime.strptime(str(receive_time), '%Y-%m-%d %H:%M:%S')
                total_cycle_days = (receive_dt - confirm_dt).days
            
            # 4. 计算生产周期
            production_cycle_days = None
            if plan_confirm_time and production_complete_time:
                plan_dt = datetime.strptime(str(plan_confirm_time), '%Y-%m-%d %H:%M:%S')
                complete_dt = datetime.strptime(str(production_complete_time), '%Y-%m-%d %H:%M:%S')
                production_cycle_days = (complete_dt - plan_dt).days
            
            # 5. 获取工序记录统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as process_count,
                    AVG(duration_days) as avg_duration,
                    MAX(duration_days) as max_duration,
                    MIN(duration_days) as min_duration,
                    SUM(completed_qty) as total_qty,
                    SUM(qualified_qty) as total_qualified,
                    SUM(calculated_qty) as total_calculated,
                    SUM(actual_used_qty) as total_actual,
                    SUM(work_hours) as total_work_hours,
                    AVG(efficiency) as avg_efficiency
                FROM process_records 
                WHERE order_id=%s AND status='已完成'
            """, (order_id,))
            process_stats = cursor.fetchone()
            
            total_process_count = process_stats['process_count'] if process_stats else 0
            avg_process_duration_days = process_stats['avg_duration'] if process_stats and process_stats['avg_duration'] else 0
            max_process_duration_days = process_stats['max_duration'] if process_stats and process_stats['max_duration'] else 0
            min_process_duration_days = process_stats['min_duration'] if process_stats and process_stats['min_duration'] else 0
            
            total_qty = process_stats['total_qty'] if process_stats else 0
            qualified_qty = process_stats['total_qualified'] if process_stats else 0
            
            # 计算总合格率
            total_qualified_rate = 0
            if total_qty > 0:
                total_qualified_rate = round((qualified_qty / total_qty) * 100, 2)
            
            # 计算平均工序合格率
            cursor.execute("""
                SELECT AVG(CASE WHEN completed_qty > 0 THEN (qualified_qty / completed_qty) * 100 ELSE 0 END) as avg_rate
                FROM process_records 
                WHERE order_id=%s AND status='已完成'
            """, (order_id,))
            rate_row = cursor.fetchone()
            avg_process_qualified_rate = rate_row['avg_rate'] if rate_row and rate_row['avg_rate'] else 0
            
            # 计算用料差异
            total_calculated_qty = process_stats['total_calculated'] if process_stats else 0
            total_actual_qty = process_stats['total_actual'] if process_stats else 0
            total_material_diff = total_actual_qty - total_calculated_qty if total_calculated_qty else 0
            
            avg_material_diff_rate = 0
            if total_calculated_qty > 0:
                avg_material_diff_rate = round((total_material_diff / total_calculated_qty) * 100, 2)
            
            total_work_hours = process_stats['total_work_hours'] if process_stats else 0
            avg_efficiency = process_stats['avg_efficiency'] if process_stats and process_stats['avg_efficiency'] else 0
            
            # 6. 插入或更新统计记录
            cursor.execute("""
                SELECT id FROM production_stats WHERE order_id=%s
            """, (order_id,))
            existing = cursor.fetchone()
            
            now = datetime.now()
            if existing:
                # 更新现有记录
                cursor.execute("""
                    UPDATE production_stats SET
                        production_id=%s,
                        order_no=%s,
                        product_type=%s,
                        confirm_time=%s,
                        ship_time=%s,
                        receive_time=%s,
                        order_cycle_days=%s,
                        delivery_cycle_days=%s,
                        total_cycle_days=%s,
                        plan_confirm_time=%s,
                        production_complete_time=%s,
                        production_cycle_days=%s,
                        total_process_count=%s,
                        avg_process_duration_days=%s,
                        max_process_duration_days=%s,
                        min_process_duration_days=%s,
                        total_qty=%s,
                        qualified_qty=%s,
                        total_qualified_rate=%s,
                        avg_process_qualified_rate=%s,
                        total_calculated_qty=%s,
                        total_actual_qty=%s,
                        total_material_diff=%s,
                        avg_material_diff_rate=%s,
                        total_work_hours=%s,
                        avg_efficiency=%s,
                        stats_status='已计算',
                        calculated_at=%s,
                        updated_at=%s
                    WHERE order_id=%s
                """, (
                    production_id, order_no, product_type,
                    confirm_time, ship_time, receive_time,
                    order_cycle_days, delivery_cycle_days, total_cycle_days,
                    plan_confirm_time, production_complete_time, production_cycle_days,
                    total_process_count, avg_process_duration_days, max_process_duration_days, min_process_duration_days,
                    total_qty, qualified_qty, total_qualified_rate, avg_process_qualified_rate,
                    total_calculated_qty, total_actual_qty, total_material_diff, avg_material_diff_rate,
                    total_work_hours, avg_efficiency,
                    now, now, order_id
                ))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO production_stats (
                        order_id, production_id, order_no, product_type,
                        confirm_time, ship_time, receive_time,
                        order_cycle_days, delivery_cycle_days, total_cycle_days,
                        plan_confirm_time, production_complete_time, production_cycle_days,
                        total_process_count, avg_process_duration_days, max_process_duration_days, min_process_duration_days,
                        total_qty, qualified_qty, total_qualified_rate, avg_process_qualified_rate,
                        total_calculated_qty, total_actual_qty, total_material_diff, avg_material_diff_rate,
                        total_work_hours, avg_efficiency,
                        stats_status, calculated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id, production_id, order_no, product_type,
                    confirm_time, ship_time, receive_time,
                    order_cycle_days, delivery_cycle_days, total_cycle_days,
                    plan_confirm_time, production_complete_time, production_cycle_days,
                    total_process_count, avg_process_duration_days, max_process_duration_days, min_process_duration_days,
                    total_qty, qualified_qty, total_qualified_rate, avg_process_qualified_rate,
                    total_calculated_qty, total_actual_qty, total_material_diff, avg_material_diff_rate,
                    total_work_hours, avg_efficiency,
                    '已计算', now
                ))
            
            conn.commit()
            cursor.close()
            log("生产统计", "计算完成", f"订单ID={order_id}, 订单号={order_no}")
            return True
            
        except Exception as e:
            log_error("生产统计", "计算统计", f"订单ID={order_id}, 错误: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_order_stats(order_id: int) -> dict:
        """
        获取订单的统计数据
        :param order_id: 订单ID
        :return: 统计数据字典
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM production_stats WHERE order_id=%s
            """, (order_id,))
            result = cursor.fetchone()
            cursor.close()
            return result if result else {}
        except Exception as e:
            log_error("生产统计", "查询统计", f"订单ID={order_id}, 错误: {str(e)}")
            return {}
        finally:
            conn.close()

    @staticmethod
    def get_process_details(order_id: int) -> list:
        """
        获取订单的工序详细统计数据
        :param order_id: 订单ID
        :return: 工序统计列表
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    process_name,
                    process_seq,
                    start_time,
                    end_time,
                    duration_days,
                    completed_qty,
                    qualified_qty,
                    (CASE WHEN completed_qty > 0 THEN (qualified_qty / completed_qty) * 100 ELSE 0 END) as qualified_rate,
                    calculated_qty,
                    actual_used_qty,
                    (actual_used_qty - calculated_qty) as material_diff,
                    (CASE WHEN calculated_qty > 0 THEN ((actual_used_qty - calculated_qty) / calculated_qty) * 100 ELSE 0 END) as material_diff_rate,
                    waste_rate,
                    efficiency,
                    worker,
                    machine_no
                FROM process_records 
                WHERE order_id=%s
                ORDER BY process_seq
            """, (order_id,))
            results = cursor.fetchall()
            cursor.close()
            return results if results else []
        except Exception as e:
            log_error("生产统计", "查询工序详情", f"订单ID={order_id}, 错误: {str(e)}")
            return []
        finally:
            conn.close()

    @staticmethod
    def calculate_all_orders_stats():
        """计算所有已完成订单的统计数据"""
        log("生产统计", "开始批量计算所有订单统计数据", "")
        
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM orders 
                WHERE status='已完成' OR status='已发货' OR status='已签收'
                ORDER BY id
            """)
            order_ids = [row['id'] for row in cursor.fetchall()]
            cursor.close()
            
            success_count = 0
            fail_count = 0
            for order_id in order_ids:
                if ProductionStatsDAO.calculate_order_stats(order_id):
                    success_count += 1
                else:
                    fail_count += 1
            
            log("生产统计", "批量计算完成", f"成功: {success_count}, 失败: {fail_count}")
            return {"success": success_count, "fail": fail_count}
            
        except Exception as e:
            log_error("生产统计", "批量计算", f"错误: {str(e)}")
            return {"success": 0, "fail": 0}
        finally:
            conn.close()

    @staticmethod
    def get_stats_summary(start_date=None, end_date=None) -> dict:
        """
        获取生产统计汇总数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 汇总统计
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    COUNT(*) as order_count,
                    AVG(order_cycle_days) as avg_order_cycle,
                    AVG(production_cycle_days) as avg_production_cycle,
                    AVG(total_cycle_days) as avg_total_cycle,
                    AVG(total_qualified_rate) as avg_qualified_rate,
                    AVG(avg_process_qualified_rate) as avg_process_rate,
                    AVG(avg_material_diff_rate) as avg_material_diff_rate,
                    AVG(avg_efficiency) as avg_efficiency
                FROM production_stats
                WHERE stats_status='已计算'
            """
            params = []
            
            if start_date:
                query += " AND calculated_at >= %s"
                params.append(start_date)
            if end_date:
                query += " AND calculated_at <= %s"
                params.append(end_date)
            
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            cursor.close()
            
            return result if result else {}
        except Exception as e:
            log_error("生产统计", "查询汇总", f"错误: {str(e)}")
            return {}
        finally:
            conn.close()