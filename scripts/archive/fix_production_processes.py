# -*- coding: utf-8 -*-
"""
修复生产工单的工序生成脚本
按照数据库中的规则重新生成工序
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection
from models.process_calc_rule import ProcessCalcEngine
from config import PROCESSES
from constants import ProcessStatus
import json


def regenerate_processes(production_id, order_id):
    """重新为生产工单生成工序"""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT quantity, product_type, customer_name FROM orders WHERE id=%s", (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            print(f"订单 {order_id} 不存在!")
            return False

        order_data = {
            "order_id": order_id,
            "quantity": order_row["quantity"] if order_row["quantity"] else 0,
            "product_type": order_row["product_type"] or "",
            "产品类型": order_row["product_type"] or "",
        }

        cursor.execute("SELECT extra_params FROM orders WHERE id=%s", (order_id,))
        extra_row = cursor.fetchone()
        if extra_row and extra_row.get("extra_params"):
            try:
                extra_params = json.loads(extra_row["extra_params"]) if isinstance(extra_row["extra_params"], str) else extra_row["extra_params"]
                if isinstance(extra_params, dict):
                    order_data.update(extra_params)
            except Exception as e:
                print(f"[fix_production_processes] 解析订单extra_params失败: {e}")

        print("=" * 60)
        print(f"订单ID: {order_id}")
        print(f"生产工单ID: {production_id}")
        print("=" * 60)
        print("\n订单数据:")
        for k, v in order_data.items():
            print(f"  {k}: {v}")

        generated_processes = ProcessCalcEngine.generate_processes_from_order(order_data, list(PROCESSES))
        print(f"\n根据规则将生成 {len(generated_processes)} 道工序:")

        for i, proc in enumerate(generated_processes, 1):
            print(f"  {i}. {proc['process_name']}: planned_qty = {proc['planned_qty']}")

        cursor.execute("DELETE FROM process_records WHERE production_id=%s", (production_id,))
        deleted_count = cursor.rowcount
        print(f"\n已删除 {deleted_count} 道旧工序")

        for i, proc_info in enumerate(generated_processes, 1):
            cursor.execute("""
                INSERT INTO process_records (order_id, production_id, process_name, process_seq, planned_qty, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (order_id, production_id, proc_info["process_name"], i, proc_info["planned_qty"], ProcessStatus.PENDING.value))

        conn.commit()
        print(f"\n✓ 成功创建 {len(generated_processes)} 道新工序")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        import traceback
        conn.rollback()
        print(f"\n✗ 错误: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python fix_production_processes.py <production_id> <order_id>")
        print("示例: python fix_production_processes.py 5 9")
        sys.exit(1)

    prod_id = int(sys.argv[1])
    order_id = int(sys.argv[2])
    success = regenerate_processes(prod_id, order_id)
    sys.exit(0 if success else 1)