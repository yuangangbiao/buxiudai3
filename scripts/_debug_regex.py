"""精确测试 pytest.raises match 对 ValidationException"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

import re

# 模拟 ValidationException 的行为
class TestException(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field

    def __str__(self):
        if self.field:
            return f"字段 [{self.field}]: {self.message}"
        return self.message

# 测试1: match = "不能为空"
exc = TestException("customer_name不能为空", field="customer_name")
actual = str(exc)
pattern = "不能为空"

print(f"str(exc): '{actual}'")
print(f"pattern: '{pattern}'")
print(f"re.search('{pattern}', '{actual}'): {re.search(pattern, actual)}")

# 测试2: 用实际 ValidationException
from core.exceptions import ValidationException
exc2 = ValidationException("customer_name不能为空", field="customer_name")
print(f"\nValidationException str: '{str(exc2)}'")
print(f"re.search match: {re.search(pattern, str(exc2))}")

# 测试3: 验证 pytest.raises 如何使用 match
print("\n=== pytest.raises match 测试 ===")
import pytest

try:
    with pytest.raises(ValidationException, match="不能为空"):
        raise ValidationException("customer_name不能为空", field="customer_name")
    print("PASSED")
except pytest.raises.Exception as e:
    print(f"FAILED: {e}")
except Exception as e:
    print(f"OTHER: {type(e).__name__}: {e}")
