# -*- coding: utf-8 -*-
"""测试统一排序函数"""
import sys
import os
import re

proj = r"d:\yuan\不锈钢网带跟单3.0"
sys.path.insert(0, proj)
sys.path.insert(0, os.path.join(proj, "mobile_api_ai"))

from mobile_api_ai.core.process_code_classifier import process_code_sort_key

print("=" * 60)
print("测试 process_code_sort_key 排序函数")
print("=" * 60)

# 测试用例 (prefix_priority, num, sub_letter_value, sub_num)
# P=1, M=2, Q=3, STOCK=4
test_cases = [
    ("P01", (1, 1, 0, 0)),
    ("P02", (1, 2, 0, 0)),
    ("P03", (1, 3, 0, 0)),
    ("P03-A1", (1, 3, 1, 1)),  # 特殊位置 A1=1
    ("P03-A", (1, 3, 1, 0)),
    ("P03-B", (1, 3, 2, 0)),   # B=2
    ("P03-C", (1, 3, 3, 0)),   # C=3
    ("P03-D", (1, 3, 4, 0)),   # D=4
    ("P04", (1, 4, 0, 0)),
    ("M01", (2, 1, 0, 0)),
    ("Q01", (3, 1, 0, 0)),
    ("STOCK_IN", (4, 0, 0, 0)),
]

all_pass = True
for code, expected in test_cases:
    result = process_code_sort_key(code)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_pass = False
    print(f"{status} {code:<12} → {result}, expected {expected}")

print()
print("=" * 60)
print("排序顺序测试")
print("=" * 60)

codes = ["P01", "P03", "P03-A1", "P03-B", "P03-C", "P04", "P02", "M01", "Q01", "STOCK_IN"]
sorted_codes = sorted(codes, key=process_code_sort_key)
print("原始:", codes)
print("排序后:", sorted_codes)

# 验证排序结果
expected_order = ["P01", "P02", "P03", "P03-A1", "P03-B", "P03-C", "P04", "M01", "Q01", "STOCK_IN"]
order_ok = sorted_codes == expected_order
status = "✓ 排序正确" if order_ok else "✗ 排序错误"
print(status)
if not order_ok:
    all_pass = False
    print(f"期望: {expected_order}")
    print(f"实际: {sorted_codes}")

print()
if all_pass:
    print("✅ 所有测试通过!")
else:
    print("❌ 有测试失败!")

sys.exit(0 if all_pass else 1)
