# -*- coding: utf-8 -*-
"""测试自定义工序自动编号逻辑"""
import sys
import os
import re

proj = r"d:\yuan\不锈钢网带跟单3.0"
sys.path.insert(0, proj)

print("=" * 50)
print("测试字母转换函数（直接实现）")
print("=" * 50)

def letter_to_value(letter: str) -> int:
    """字母转数值：A=1, B=2, Z=26, AA=27..."""
    value = 0
    for i, c in enumerate(reversed(letter.upper())):
        value += (ord(c) - ord('A') + 1) * (26 ** i)
    return value

def value_to_letter(value: int) -> str:
    """数值转字母：1=A, 2=B, 26=Z, 27=AA..."""
    if value <= 26:
        return chr(ord('A') + value - 1)
    result = ""
    v = value - 1
    while v >= 0:
        result = chr(ord('A') + v % 26) + result
        v = v // 26 - 1
    return result

# 测试 letter_to_value
tests = [
    ("A", 1),
    ("B", 2),
    ("Z", 26),
    ("AA", 27),
    ("AB", 28),
    ("AZ", 52),
    ("BA", 53),
]

for letter, expected in tests:
    result = letter_to_value(letter)
    status = "✓" if result == expected else "✗"
    print(f"{status} letter_to_value('{letter}') = {result}, expected {expected}")

# 测试 value_to_letter
print()
tests2 = [
    (1, "A"),
    (2, "B"),
    (26, "Z"),
    (27, "AA"),
    (28, "AB"),
    (52, "AZ"),
    (53, "BA"),
]

for value, expected in tests2:
    result = value_to_letter(value)
    status = "✓" if result == expected else "✗"
    print(f"{status} value_to_letter({value}) = '{result}', expected '{expected}'")

print()
print("=" * 50)
print("测试 generate_process_code 逻辑")
print("=" * 50)

# 测试 generate_process_code 逻辑（模拟）
def simulate_generate(used_codes, deleted_codes):
    """模拟 generate_process_code 的核心逻辑"""
    max_letter_value = 1  # 从 A=1 开始
    for code in used_codes:
        m = re.match(r'^[A-Z]+\d+-([A-Z]+)(\d*)$', code)
        if m:
            letter = m.group(1)
            letter_value = letter_to_value(letter)
            if letter_value > max_letter_value:
                max_letter_value = letter_value

    # 优先从删除池中找
    for code in sorted(deleted_codes):
        if code not in used_codes:
            return f"重用 {code}"

    new_letter = value_to_letter(max_letter_value + 1)
    return f"新编号 P03-{new_letter}"

# 场景1: 无现有编号，无删除编号
result = simulate_generate([], [])
print(f"场景1: 无现有编号 → {result} (应为 P03-B)")

# 场景2: 有 P03-B，无删除编号
result = simulate_generate(["P03-B"], [])
print(f"场景2: 有 P03-B → {result} (应为 P03-C)")

# 场景3: 有 P03-B, P03-C，无删除编号
result = simulate_generate(["P03-B", "P03-C"], [])
print(f"场景3: 有 P03-B,P03-C → {result} (应为 P03-D)")

# 场景4: P03-B 被软删除（is_deleted_code=1），应该被重用
result = simulate_generate([], ["P03-B"])
print(f"场景4: P03-B 已删除可回收，无使用中 → {result} (应为重用 P03-B)")

# 场景5: P03-C 在使用中，P03-B 被删除可回收
result = simulate_generate(["P03-C"], ["P03-B"])
print(f"场景5: P03-C使用中，P03-B已删除 → {result} (应为重用 P03-B)")

print()
print("测试完成!")
