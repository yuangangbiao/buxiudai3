# -*- coding: utf-8 -*-
"""
日志清理工具 - 自动清理过期日志
保留周期：订单完成后180天
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.operation_log import OperationLogDAO
from models.order_log import OrderLogDAO
from models.database import get_connection
from datetime import datetime, timedelta

def cleanup_expired_logs():
    """清理所有过期日志"""
    print("=" * 60)
    print("日志清理任务开始")
    print("=" * 60)
    
    # 清理操作日志
    op_deleted = OperationLogDAO.clean_expired_logs()
    print(f"操作日志清理完成，删除 {op_deleted} 条记录")
    
    # 清理订单日志（同样使用180天保留周期）
    print("\n订单日志清理（保留订单完成后180天）")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 获取所有已完成订单
        cursor.execute("SELECT id, updated_at FROM orders WHERE status = '已完成'")
        completed_orders = cursor.fetchall()
        
        deleted_count = 0
        for order in completed_orders:
            order_id = order['id']
            completed_at = order['updated_at']
            
            if isinstance(completed_at, str):
                completed_at = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S")
            
            expire_date = completed_at + timedelta(days=180)
            if datetime.now() > expire_date:
                cursor.execute("DELETE FROM order_logs WHERE order_id = %s", (order_id,))
                deleted_count += cursor.rowcount
        
        conn.commit()
        print(f"订单日志清理完成，删除 {deleted_count} 条记录")
        
    except Exception as e:
        print(f"订单日志清理失败: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    print("=" * 60)
    print("日志清理任务完成")
    print("=" * 60)

if __name__ == "__main__":
    cleanup_expired_logs()