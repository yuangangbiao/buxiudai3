# -*- coding: utf-8 -*-
"""
物料计算诊断脚本 v5 - 完整原始数据
用于诊断物料计算公式的计算过程，查看原始数据和计算步骤
"""
import sys
import os
import json

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_DIR, '.env'))

    import pymysql

    # 建立数据库连接
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
        charset='utf8mb4'
    )

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    print("=" * 70)
    print("1. 订单 ORD-202605050002 的原始数据")
    print("=" * 70)
    cursor.execute("SELECT * FROM orders WHERE order_no = 'ORD-202605050002'")
    order = cursor.fetchone()
    if order:
        for key, value in order.items():
            print(f"{key}: {value}")
    print()

    print("=" * 70)
    print("2. 产品类型'弹簧网'的物料规则原始数据")
    print("=" * 70)
    cursor.execute("SELECT * FROM material_rules WHERE product_type = '弹簧网' AND enabled = 1")
    rules = cursor.fetchall()
    print(f"找到 {len(rules)} 条规则\n")
    for i, r in enumerate(rules, 1):
        print(f"--- 规则 {i} ---")
        for key, value in r.items():
            print(f"{key}: {repr(value)}")
        print()

    print("=" * 70)
    print("3. 订单参数代入公式计算")
    print("=" * 70)

    # 解析订单的额外参数
    extra = order.get("extra_params") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception as e:
            print(f"[diagnose_material_calc_v5] 解析extra_params失败: {e}")
            extra = {}

    # 合并订单参数
    order_params = {
        "product_type": order.get("product_type"),
        "quantity": order.get("quantity", 0),
    }
    order_params.update(extra)

    print("订单参数:")
    for k, v in order_params.items():
        print(f"  {k}: {v}")

    # 逐条规则计算
    for r in rules:
        qty_formula = r.get('qty_formula')
        if qty_formula:
            print(f"\n原始公式: {qty_formula}")

            # 替换运算符为标准Python运算符
            formula = qty_formula.replace('×', '*').replace('÷', '/').replace('X', '*').replace('x', '*')

            import re
            # 提取所有占位符
            placeholders = re.findall(r'\{([^}]+)\}', formula)
            print(f"占位符: {placeholders}")

            # 替换占位符为实际值
            for placeholder in placeholders:
                if placeholder in order_params:
                    value = order_params[placeholder]
                    formula = formula.replace(f'{{{placeholder}}}', str(value))
                    print(f"  替换 {{{placeholder}}} -> {value}")

            print(f"替换后公式: {formula}")

            # 执行计算
            try:
                result = eval(formula)
                print(f"计算结果: {round(result, 2)}")
            except Exception as e:
                print(f"计算错误: {e}")

    conn.close()

if __name__ == "__main__":
    main()