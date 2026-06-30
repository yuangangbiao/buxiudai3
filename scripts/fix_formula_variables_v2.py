# -*- coding: utf-8 -*-
"""
公式变量修复脚本 v2
为物料计算和工序计算公式中的中文变量自动添加大括号
确保公式计算时能正确识别中文变量名
"""
import sys
import os
import json
import re

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

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

print("=" * 60)
print("【修复】正确为公式中的中文变量添加大括号")
print("=" * 60)

# 修复逻辑：只对不在大括号内的中文变量添加大括号
def fix_formula(formula):
    """
    修复公式，为中文变量名添加大括号
    
    Args:
        formula: 原始公式字符串
    
    Returns:
        修复后的公式
    """
    if not formula:
        return formula
    
    # 找到所有不在大括号内的中文词（2个字符以上）
    result = []
    i = 0
    while i < len(formula):
        if formula[i] == '{':
            # 找到对应的 }
            j = i + 1
            depth = 1
            while j < len(formula) and depth > 0:
                if formula[j] == '{':
                    depth += 1
                elif formula[j] == '}':
                    depth -= 1
                j += 1
            # 添加整个 {...} 块（保持原样）
            result.append(formula[i:j])
            i = j
        elif formula[i] == '}':
            result.append(formula[i])
            i += 1
        elif '\u4e00' <= formula[i] <= '\u9fa5':
            # 找到连续的中文字符
            j = i
            while j < len(formula) and '\u4e00' <= formula[j] <= '\u9fa5':
                j += 1
            chinese_word = formula[i:j]
            # 如果是2个字符以上的中文词，添加大括号
            if len(chinese_word) >= 2:
                result.append(f'{{{chinese_word}}}')
            else:
                result.append(chinese_word)
            i = j
        else:
            result.append(formula[i])
            i += 1
    
    return ''.join(result)

# 修复物料规则
print("\n--- 修复物料规则 ---")
cursor.execute("SELECT id, product_type, material_name_template, qty_formula FROM material_rules WHERE enabled=1")
material_rules = cursor.fetchall()

for rule in material_rules:
    original = rule['qty_formula'] or ''
    if original:
        fixed = fix_formula(original)
        if fixed != original:
            print(f"修复前: {original}")
            print(f"修复后: {fixed}")
            print(f"  -> 产品类型: {rule['product_type']}, 物料: {rule['material_name_template']}")
            cursor.execute("UPDATE material_rules SET qty_formula = %s, updated_at = NOW() WHERE id = %s",
                          (fixed, rule['id']))

# 修复工序规则
print("\n--- 修复工序规则 ---")
cursor.execute("SELECT id, process_name, planned_qty_formula FROM process_calc_rules WHERE enabled=1")
process_rules = cursor.fetchall()

for rule in process_rules:
    original = rule['planned_qty_formula'] or ''
    if original:
        fixed = fix_formula(original)
        if fixed != original:
            print(f"修复前: {original}")
            print(f"修复后: {fixed}")
            print(f"  -> 工序: {rule['process_name']}")
            cursor.execute("UPDATE process_calc_rules SET planned_qty_formula = %s, updated_at = NOW() WHERE id = %s",
                          (fixed, rule['id']))

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("【修复完成】")
print("=" * 60)