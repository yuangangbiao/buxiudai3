# -*- coding: utf-8 -*-
"""
弹簧网公式检查脚本
检查弹簧网物料计算公式是否包含正确的占位符
分析公式结构并验证计算逻辑
"""
import sys
import os

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
    cursor.execute("SELECT qty_field, qty_formula FROM material_rules WHERE product_type = '弹簧网' AND enabled = 1")
    rule = cursor.fetchone()

    print("弹簧网物料规则:")
    print(f"  qty_field: {rule['qty_field']}")
    print(f"  qty_formula: [{rule['qty_formula']}]")

    # 检查公式是否包含 {qty}
    import re
    formula = rule['qty_formula']
    has_qty_placeholder = '{qty}' in formula
    placeholders = re.findall(r'\{([^}]+)\}', formula)

    print(f"\n公式分析:")
    print(f"  包含 {{qty}} 占位符: {has_qty_placeholder}")
    print(f"  所有占位符: {placeholders}")

    # 手动计算验证
    if placeholders:
        print("\n代入参数计算:")
        穿杆直径 = 5
        钢丝直径 = 1.0
        网带宽度 = 95
        螺距 = 4
        链条距 = 9.525
        quantity = 5040

        for p in placeholders:
            print(f"  占位符 {{{p}}}:")

        # 如果没有qty占位符但qty_field是quantity，说明会直接使用公式结果
        if not has_qty_placeholder and rule['qty_field'] == 'quantity':
            print(f"\n警告: qty_field='quantity' 但公式中没有{{qty}}占位符!")
            print(f"这意味着公式会被直接计算为: {formula}")
            print(f"计算结果: {630.5625} (不是 * quantity)")

    conn.close()

if __name__ == "__main__":
    main()