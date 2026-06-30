"""深度调试 pytest.raises 对 ValidationException 的 match 行为"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

import pytest
import re

from core.exceptions import ValidationException

print("=== 实际用 pytest.raises 测试 ===")
try:
    with pytest.raises(ValidationException, match="不能为空"):
        raise ValidationException("customer_name不能为空", field="customer_name")
    print("  -> pytest.raises 成功!")
except pytest.raises.Exception as e:
    print(f"  -> pytest.raises 失败: {e}")
except Exception as e:
    print(f"  -> 其他异常: {type(e).__name__}: {e}")
