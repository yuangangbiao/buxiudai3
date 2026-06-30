# -*- coding: utf-8 -*-
"""
订单日志模型 - 记录所有订单改动信息
"""
import logging
from models.database import get_connection
from datetime import datetime

logger = logging.getLogger(__name__)

class OrderLogDAO:
    """订单日志数据访问对象"""
    
    @staticmethod
    def create(order_id, order_no, action, operator, details=None):
        """
        创建订单操作日志
        
        :param order_id: 订单ID
        :param order_no: 订单编号
        :param action: 操作类型（CREATE, UPDATE, DELETE, CONFIRM, SCHEDULE, PRODUCE, COMPLETE）
        :param operator: 操作人
        :param details: 操作详情（可选）
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO order_logs (order_id, order_no, action, operator, details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (order_id, order_no, action, operator, details, datetime.now()))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"[OrderLog] 创建日志失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_order_id(order_id):
        """获取指定订单的所有日志"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM order_logs 
                WHERE order_id = %s 
                ORDER BY created_at DESC
            """, (order_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[OrderLog] 查询日志失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all(limit=100):
        """获取最近的操作日志"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM order_logs 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[OrderLog] 查询日志失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_operator(operator, limit=100):
        """获取指定操作人的日志"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM order_logs 
                WHERE operator = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (operator, limit))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[OrderLog] 查询日志失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_action(action, limit=100):
        """获取指定操作类型的日志"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM order_logs 
                WHERE action = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (action, limit))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[OrderLog] 查询日志失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def search(keyword, limit=100):
        """搜索日志（按订单号、操作人、详情）"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM order_logs 
                WHERE order_no LIKE %s OR operator LIKE %s OR details LIKE %s
                ORDER BY created_at DESC 
                LIMIT %s
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[OrderLog] 搜索日志失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def count_by_action(action=None):
        """统计操作类型数量"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if action:
                cursor.execute("SELECT COUNT(*) FROM order_logs WHERE action = %s", (action,))
            else:
                cursor.execute("SELECT action, COUNT(*) FROM order_logs GROUP BY action")
            
            result = cursor.fetchone()
            if action:
                return result[0] if result else 0
            return result
        except Exception as e:
            logger.error(f"[OrderLog] 统计失败: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

# 操作类型常量
ORDER_ACTION = {
    "CREATE": "创建订单",
    "UPDATE": "修改订单",
    "DELETE": "删除订单",
    "CONFIRM": "确认订单",
    "SCHEDULE": "排产订单",
    "PRODUCE": "开始生产",
    "COMPLETE": "完成订单",
    "SHIP": "发货",
    "ARCHIVE": "归档订单",
    "CANCEL": "取消订单",
}

def log_order_action(order_id, order_no, action_key, operator="系统", details=None):
    """
    记录订单操作日志（便捷函数）
    
    :param order_id: 订单ID
    :param order_no: 订单编号
    :param action_key: 操作类型键（如 'CREATE', 'UPDATE'）
    :param operator: 操作人（默认系统）
    :param details: 操作详情
    """
    action = ORDER_ACTION.get(action_key, action_key)
    OrderLogDAO.create(order_id, order_no, action, operator, details)