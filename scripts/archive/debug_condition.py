# -*- coding: utf-8 -*-
"""调试条件表达式"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.process_calc_rule import ProcessCalcEngine

order_data = {
    "product_type": "平板型网带",
}

expr = "产品类型等于平板型网带"

print(f"表达式: {expr}")
print(f"order_data: {order_data}")
print()

# 模拟 _eval_expr 的逻辑
all_ops = {}
all_ops.update(ProcessCalcEngine.COND_OPERATORS)
all_ops.update(ProcessCalcEngine.COND_OPERATORS_EN)

print(f"所有操作符: {list(all_ops.keys())}")
print()

sorted_ops = sorted(all_ops.keys(), key=len, reverse=True)
print(f"排序后的操作符: {sorted_ops}")
print()

for op_name in sorted_ops:
    if op_name in expr:
        idx = expr.index(op_name)
        field = expr[:idx].strip()
        value = expr[idx + len(op_name):].strip()
        print(f"找到操作符: '{op_name}'")
        print(f"  idx={idx}")
        print(f"  field='{field}'")
        print(f"  value='{value}'")
        if field in order_data:
            field_val = order_data[field]
            print(f"  field_val='{field_val}'")
            print(f"  field_val 类型: {type(field_val)}")
            result = all_ops[op_name](field_val, value)
            print(f"  结果: {result}")
        else:
            print(f"  字段 '{field}' 不在 order_data 中")
        break