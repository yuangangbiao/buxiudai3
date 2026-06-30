# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection
from models.process_calc_rule import ProcessCalcEngine, ProcessCalcRuleDAO

conn = get_connection()
cursor = conn.cursor()

cursor.execute('SELECT DISTINCT product_type FROM orders WHERE product_type IS NOT NULL AND product_type != ""')
product_types = [r.get('product_type') for r in cursor.fetchall()]
print("=" * 60)
print("Database Order Product Types:")
for pt in product_types:
    print(f"  - {pt}")

print()

rules = ProcessCalcRuleDAO.get_all()
print("Rules and Conditions:")
for r in rules:
    cond = r.get('condition_expr') or '(none)'
    print(f"  {r.get('process_name')}: {cond}")

cursor.close()
conn.close()