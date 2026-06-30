# -*- coding: utf-8 -*-
"""查看所有工序规则的生效条件"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.process_calc_rule import ProcessCalcRuleDAO
from config import PROCESSES

rules = ProcessCalcRuleDAO.get_all()
print("=" * 70)
print(f"共有 {len(rules)} 条规则")
print("=" * 70)

for r in rules:
    print(f"\n工序: {r.get('process_name')}")
    print(f"  生效条件: {r.get('condition_expr') or '(无)'}")
    print(f"  计划数量公式: {r.get('planned_qty_formula') or '(无)'}")

print("\n" + "=" * 70)
print("PROCESSES 列表中的工序（可能没有规则）:")
for p in PROCESSES:
    has_rule = any(r.get('process_name') == p for r in rules)
    status = "" if has_rule else " <-- 无规则"
    print(f"  {p}{status}")