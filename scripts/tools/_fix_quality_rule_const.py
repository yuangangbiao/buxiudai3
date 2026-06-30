# -*- coding: utf-8 -*-
"""修复 test_quality_rule.py 中重复的常量名"""
FILE = r"d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_quality_rule.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("SAMPLE_SAMPLE_ITEM_TUPLE_ROW", "SAMPLE_ITEM_TUPLE_ROW")
content = content.replace("SAMPLE_SAMPLE_ITEM_DICT_ROW", "SAMPLE_ITEM_DICT_ROW")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 修复完成")
