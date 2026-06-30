# -*- coding: utf-8 -*-
"""修复 test_quality_rule.py 中的 _self._mock_conn.self._mock_cursor 问题"""
import re

FILE = r"d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_quality_rule.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 修复 self._self._mock_conn.self._mock_cursor. → self._mock_conn.cursor.
# 这发生在 _setup_mock fixture 中
content = content.replace("self._self._mock_conn.self._mock_cursor.", "self._mock_conn.cursor.")

# 修复 self._self._mock_conn.commit → self._mock_conn.commit
content = content.replace("self._self._mock_conn.commit.", "self._mock_conn.commit.")

# 修复 self._self._mock_conn.rollback → self._mock_conn.rollback
content = content.replace("self._self._mock_conn.rollback.", "self._mock_conn.rollback.")

# 修复 self._self._mock_conn.close → self._mock_conn.close
content = content.replace("self._self._mock_conn.close.", "self._mock_conn.close.")

# 修复 self._self._mock_conn.cursor → self._mock_conn.cursor (bare attribute)
content = content.replace("self._self._mock_conn.cursor", "self._mock_conn.cursor")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 修复完成")
