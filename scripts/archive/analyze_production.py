# -*- coding: utf-8 -*-
"""
工序生成分析脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection
from config import PROCESSES
from models.process_calc_rule import ProcessCalcRuleDAO, ProcessCalcEngine
import json

def analyze_production(production_id):
    """分析指定生产工单的工序生成情况"""
    print("=" * 70)
    print(f"分析生产订单: production_id={production_id}")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM production_orders WHERE id=%s", (production_id,))
    prod = cursor.fetchone()
    if not prod:
        print(f"生产工单 {production_id} 不存在!")
        cursor.close()
        conn.close()
        return

    print(f"\n生产工单信息:")
    print(f"  ID: {prod.get('id')}")
    print(f"  订单号: {prod.get('order_no')}")
    print(f"  订单ID: {prod.get('order_id')}")

    order_id = prod.get('order_id')
    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()
    if not order:
        print(f"订单 {order_id} 不存在!")
        cursor.close()
        conn.close()
        return

    print(f"\n订单信息:")
    print(f"  订单号: {order.get('order_no')}")
    print(f"  产品类型: {order.get('product_type')}")
    print(f"  数量: {order.get('quantity')}")

    extra_params = order.get('extra_params') or "{}"
    try:
        if isinstance(extra_params, str):
            extra = json.loads(extra_params)
        else:
            extra = extra_params
    except Exception as e:
        print(f"[analyze_production] 解析订单extra_params失败: {e}")
        extra = {}

    print(f"\n订单 extra_params:")
    for k, v in extra.items():
        print(f"  {k}: {v}")

    order_data = {
        "order_id": order_id,
        "quantity": order.get('quantity') or 0,
        "product_type": order.get('product_type') or "",
    }
    order_data.update(extra)

    print(f"\n构建的 order_data:")
    for k, v in order_data.items():
        print(f"  {k}: {v}")

    cursor.execute("SELECT id, process_name, planned_qty, status FROM process_records WHERE production_id=%s ORDER BY id", (production_id,))
    db_records = cursor.fetchall()
    db_process_names = set(r.get('process_name') for r in db_records)

    print(f"\n【1. 数据库中现有的工序】({len(db_records)} 道)")
    for r in db_records:
        print(f"  ID={r.get('id')}, {r.get('process_name')}, 计划数量={r.get('planned_qty')}, 状态={r.get('status')}")

    print(f"\n【2. PROCESSES 列表 vs 数据库记录】")
    rules = ProcessCalcRuleDAO.get_all()
    rule_map = {r.get('process_name'): r for r in rules}

    for proc in PROCESSES:
        in_db = "✓" if proc in db_process_names else " "
        rule = rule_map.get(proc)
        has_rule = "有规则" if rule else "无规则"

        if rule:
            cond = rule.get('condition_expr') or '无'
            formula = rule.get('planned_qty_formula') or '无'
            should_include = ProcessCalcEngine.should_include_process(proc, order_data, rules)
            calc_qty = ProcessCalcEngine.calculate_planned_qty_for_process(proc, rules, order_data)
            print(f"  {in_db} {proc} | {has_rule} | 条件={cond[:20]}... | 公式={formula} | 应包含={should_include} | 计算数量={calc_qty}")
        else:
            should_include = True
            print(f"  {in_db} {proc} | {has_rule} | 默认包含={should_include} | 默认数量=1.0")

    print(f"\n【3. 根据规则应该生成的工序】")
    generated = ProcessCalcEngine.generate_processes_from_order(order_data, list(PROCESSES))
    print(f"  将生成 {len(generated)} 道工序:")
    for g in generated:
        print(f"    - {g['process_name']}: planned_qty = {g['planned_qty']}")

    print(f"\n【4. 对比分析】")
    gen_names = set(g['process_name'] for g in generated)
    print(f"  数据库有 {len(db_process_names)} 道，规则应生成 {len(gen_names)} 道")

    only_in_db = db_process_names - gen_names
    only_in_gen = gen_names - db_process_names

    if only_in_db:
        print(f"  数据库有但规则不应生成: {only_in_db}")
    if only_in_gen:
        print(f"  规则应生成但数据库没有: {only_in_gen}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    import sys
    prod_id = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    analyze_production(prod_id)