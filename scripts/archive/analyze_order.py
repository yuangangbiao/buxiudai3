# -*- coding: utf-8 -*-
"""
分析订单的工序计算过程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection
from models.process_calc_rule import ProcessCalcRuleDAO, ProcessCalcEngine
import json

def analyze_order(order_number):
    """分析指定订单的工序计算"""
    print("=" * 70)
    print(f"分析订单: {order_number}")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_no = %s", (order_number,))
    order = cursor.fetchone()

    if not order:
        print(f"订单 {order_number} 不存在!")
        cursor.close()
        conn.close()
        return

    print("\n【1. 订单基本信息】")
    print(f"  订单ID: {order.get('id')}")
    print(f"  订单号: {order.get('order_no')}")
    print(f"  产品类型: {order.get('product_type')}")
    print(f"  数量: {order.get('quantity')}")

    print("\n【2. extra_params 尺寸参数】")
    extra_params = order.get('extra_params') or "{}"
    try:
        if isinstance(extra_params, str):
            extra = json.loads(extra_params)
        else:
            extra = extra_params
        if extra:
            for k, v in extra.items():
                print(f"  {k}: {v} (type: {type(v).__name__})")
        else:
            print("  (无)")
    except Exception as e:
        print(f"  解析失败: {e}")
        extra = {}

    cursor.execute("SELECT id FROM production_orders WHERE order_id = %s", (order.get('id'),))
    prod_row = cursor.fetchone()
    production_id = prod_row.get('id') if prod_row else None
    print(f"\n【3. 生产单ID: {production_id}】")

    print("\n【4. 构建 order_data 用于计算】")
    calc_data = {
        "order_id": order.get('id'),
        "quantity": order.get('quantity') or 0,
        "product_type": order.get('product_type') or "",
        "产品类型": order.get('product_type') or "",
        "specs": order.get('mesh_size') or "",
        "customer": order.get('customer_name') or "",
    }
    calc_data.update(extra)
    for k, v in calc_data.items():
        print(f"  {k}: {v}")

    print("\n【5. 工序规则与计算结果】")
    rules = ProcessCalcRuleDAO.get_all()
    print(f"  数据库共有 {len(rules)} 条规则\n")

    for rule in rules:
        process_name = rule.get('process_name')
        condition_expr = rule.get('condition_expr') or ""
        formula = rule.get('planned_qty_formula') or ""

        print(f"  ┌─ 工序: {process_name}")
        print(f"  │  生效条件: '{condition_expr}'")
        print(f"  │  计划数量公式: '{formula}'")

        should_include = ProcessCalcEngine.should_include_process(process_name, calc_data, rules)
        print(f"  │  是否包含: {'✓ 是' if should_include else '✗ 否'}")

        if should_include and formula:
            planned_qty = ProcessCalcEngine.calculate_planned_qty(formula, calc_data)
            print(f"  │  计算结果: {planned_qty}")

        print()

    if production_id:
        print("【6. 当前数据库中的工序记录】")
        cursor.execute("""
            SELECT id, process_name, planned_qty, status
            FROM process_records
            WHERE production_id = %s
            ORDER BY id
        """, (production_id,))
        proc_records = cursor.fetchall()
        print(f"  共有 {len(proc_records)} 道工序:\n")
        for rec in proc_records:
            print(f"    ID={rec.get('id')}, 工序={rec.get('process_name')}, 计划数量={rec.get('planned_qty')}, 状态={rec.get('status')}")
    else:
        print("【6. 该订单尚未排产】")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    import sys
    order_num = sys.argv[1] if len(sys.argv) > 1 else "ORD-202604290001"
    analyze_order(order_num)