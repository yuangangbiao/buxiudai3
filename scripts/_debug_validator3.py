"""调试 pytest.raises 对 ValidationException 的匹配"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

import pytest
import re

from core.exceptions import ValidationException
from utils.validators import CommonValidators

def test_match_pattern():
    """测试 pytest.raises 如何匹配"""
    pattern = "不能为空"
    with pytest.raises(ValidationException, match=pattern):
        CommonValidators.required(None, "customer_name")

if __name__ == '__main__':
    import pytest as p
    result = p.main(['-xvs', __file__])
    print(f"Exit: {result}")
