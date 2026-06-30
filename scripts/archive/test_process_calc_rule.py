# -*- coding: utf-8 -*-
"""
工序计算规则测试文件
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_process_calc_rule():
    """测试工序计算规则"""
    print("=" * 60)
    print("工序计算规则测试")
    print("=" * 60)
    
    from models.process_calc_rule import ProcessCalcRuleDAO, ProcessCalcEngine
    from models.database import get_connection
    
    # 1. 测试订单数据
    print("\n【1. 测试订单数据构建】")
    
    # 模拟一个订单的 extra_params
    extra_params = {
        "总宽": "1500",
        "网带宽度": "1400", 
        "钢丝直径": "3",
        "总长度": "5000",
        "quantity": "100",
        "product_type": "普货"
    }
    print(f"extra_params: {extra_params}")
    
    # 模拟 order_data
    order_data = {
        "order_id": 1,
        "quantity": 100,
        "product_type": "普货",
        "specs": "",
        "customer": "",
    }
    order_data.update(extra_params)
    print(f"order_data: {order_data}")
    
    # 2. 测试规则评估
    print("\n【2. 测试规则评估】")
    
    rules = ProcessCalcRuleDAO.get_all()
    print(f"数据库中的规则数量: {len(rules)}")
    
    for rule in rules:
        print(f"\n  工序: {rule.get('process_name')}")
        print(f"  生效条件: {rule.get('condition_expr')}")
        print(f"  公式: {rule.get('planned_qty_formula')}")
        print(f"  启用: {rule.get('enabled')}")
        
        # 测试条件评估
        condition = rule.get('condition_expr') or ""
        if condition and condition not in ("所有产品类型", "无", "不限", "默认"):
            result = ProcessCalcEngine.evaluate_condition(condition, order_data)
            print(f"  条件评估结果: {result}")
        
        # 测试数量计算
        formula = rule.get('planned_qty_formula') or ""
        if formula:
            qty = ProcessCalcEngine.calculate_planned_qty(formula, order_data)
            print(f"  数量计算结果: {qty}")
    
    # 3. 测试 should_include_process
    print("\n【3. 测试工序是否应该被包含】")
    
    all_processes = ["织带", "穿杆", "打包", "质检"]
    for proc in all_processes:
        should_include = ProcessCalcEngine.should_include_process(proc, order_data, rules)
        print(f"  {proc}: {'✓ 包含' if should_include else '✗ 不包含'}")
    
    # 4. 测试生成工序列表
    print("\n【4. 测试生成工序列表】")
    
    generated = ProcessCalcEngine.generate_processes_from_order(order_data, all_processes)
    print(f"将创建的工序:")
    for proc in generated:
        print(f"  - {proc['process_name']}: planned_qty = {proc['planned_qty']}")

    # 5. 检查数据库中的规则
    print("\n【5. 数据库中的规则详情】")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, process_name, condition_expr, planned_qty_formula, enabled FROM process_calc_rules")
    rows = cursor.fetchall()
    print(f"数据库共有 {len(rows)} 条规则:")
    for row in rows:
        if isinstance(row, dict):
            print(f"  ID={row.get('id')}, 工序={row.get('process_name')}, 条件={row.get('condition_expr')}, 公式={row.get('planned_qty_formula')}, 启用={row.get('enabled')}")
        elif isinstance(row, (list, tuple)):
            print(f"  ID={row[0]}, 工序={row[1]}, 条件={row[2]}, 公式={row[3]}, 启用={row[4]}")
    cursor.close()
    conn.close()

def test_rule_evaluation():
    """测试规则条件评估"""
    print("\n" + "=" * 60)
    print("规则条件评估测试")
    print("=" * 60)
    
    from models.process_calc_rule import ProcessCalcEngine
    
    test_cases = [
        ("所有产品类型", {"product_type": "普货", "总宽": 1500}),
        ("总宽 > 1000", {"总宽": 1500}),
        ("总宽 > 1000", {"总宽": 500}),
        ("钢丝直径 >= 3", {"钢丝直径": 3}),
        ("钢丝直径 >= 3", {"钢丝直径": 2}),
        ("总宽 > 1000 AND 钢丝直径 >= 3", {"总宽": 1500, "钢丝直径": 3}),
        ("总宽 > 1000 AND 钢丝直径 >= 3", {"总宽": 500, "钢丝直径": 3}),
        ("总宽 > 1000 AND 钢丝直径 >= 3", {"总宽": 1500, "钢丝直径": 2}),
    ]
    
    for condition, data in test_cases:
        result = ProcessCalcEngine.evaluate_condition(condition, data)
        print(f"  条件: {condition}")
        print(f"  数据: {data}")
        print(f"  结果: {'✓' if result else '✗'}")
        print()

def test_formula_calculation():
    """测试公式计算"""
    print("\n" + "=" * 60)
    print("公式计算测试")
    print("=" * 60)
    
    from models.process_calc_rule import ProcessCalcEngine
    
    order_data = {
        "order_id": 1,
        "quantity": 100,
        "product_type": "普货",
        "总宽": 1500,
        "网带宽度": 1400,
        "钢丝直径": 3,
        "总长度": 5000,
    }
    
    formulas = [
        "quantity",
        "总宽 * 0.001 * quantity",
        "总宽 * 总长度 * 0.000001 * quantity",
        "quantity / 2",
        "1",
        "总宽",
        "总宽 + 100",
    ]
    
    for formula in formulas:
        result = ProcessCalcEngine.calculate_planned_qty(formula, order_data)
        print(f"  公式: {formula}")
        print(f"  结果: {result}")
        print()

if __name__ == "__main__":
    test_process_calc_rule()
    test_rule_evaluation()
    test_formula_calculation()
    print("\n测试完成!")