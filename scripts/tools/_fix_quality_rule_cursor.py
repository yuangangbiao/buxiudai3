# -*- coding: utf-8 -*-
"""修复 test_quality_rule.py 中剩余的 cursor. → self._mock_cursor. 替换"""
import re

FILE = r"d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_quality_rule.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 替换所有剩余的 cursor. → self._mock_cursor. (但避免 self._mock_cursor. 变成 self._mock_mock_cursor.)
# 替换策略：在 cursor. 前添加 self._mock_ 前缀
# 但需要避免 self._mock_cursor. 已经正确的部分

# 第一步：self._mock_cursor. 已经正确的，跳过
# 第二步：self._mock_mock_cursor. 错误的，修复
content = content.replace("self._mock_mock_cursor.", "self._mock_cursor.")

# 第三步：cursor. → self._mock_cursor. (但跳过 self._mock_cursor. 已正确的)
# 简单替换：将所有 self._mock_cursor. 暂时占位，再还原
content = content.replace("self._mock_cursor.", "___MOCK_CURSOR___.")

# 替换所有 cursor. → self._mock_cursor.
content = content.replace("cursor.", "self._mock_cursor.")

# 还原所有 ___MOCK_CURSOR___. → self._mock_cursor.
content = content.replace("___MOCK_CURSOR___.", "self._mock_cursor.")

# 替换 mock_conn. → self._mock_conn.
content = content.replace("mock_conn.", "self._mock_conn.")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 替换完成")
