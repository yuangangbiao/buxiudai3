# -*- coding: utf-8 -*-
"""测试条件表达式评估"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.process_calc_rule import ProcessCalcEngine
import json

order_data_平板型 = {
    "product_type": "平板型网带",
    "产品类型": "平板型网带",
    "quantity": 50,
    "总宽度": 300,
}

order_data_螺旋网 = {
    "product_type": "冷冻螺旋网",
    "产品类型": "冷冻螺旋网",
    "quantity": 1000,
}

test_conditions = [
    "所有产品类型",
    "产品类型等于平板型网带",
    "产品类型等于冷冻螺旋网",
    "产品类型不等于平板型网带",
    "产品类型包含螺旋",
]

print("=" * 70)
print("测试条件表达式评估")
print("=" * 70)

for cond in test_conditions:
    print(f"\n条件: {cond}")
    print(f"  平板型网带订单 -> {ProcessCalcEngine.evaluate_condition(cond, order_data_平板型)}")
    print(f"  冷冻螺旋网订单 -> {ProcessCalcEngine.evaluate_condition(cond, order_data_螺旋网)}")