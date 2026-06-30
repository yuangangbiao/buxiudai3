# -*- coding: utf-8 -*-
"""修复 test_quality_rule.py 中所有错误的函数签名 (self._mock_conn) 参数"""
import re

FILE = r"d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_quality_rule.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 替换所有 def xxx(self, self._mock_conn): → def xxx(self):
content = re.sub(r"def (test_\w+)\(self, self\._mock_conn\):", r"def \1(self):", content)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

# 统计
count = len(re.findall(r"def (test_\w+)\(self\):", content))
print(f"✅ 修复完成，当前有 {count} 个 test 方法")
