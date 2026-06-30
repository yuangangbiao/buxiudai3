# -*- coding: utf-8 -*-
"""
utils/validators.py 完整单元测试

覆盖模块:
- CommonValidators
- OrderValidator
"""
import os
import sys
import pytest
from datetime import datetime

class TestCommonValidatorsRequired:
    """CommonValidators.required 测试"""

    def test_required_with_valid_value(self):
        """测试有效值"""
        from utils.validators import CommonValidators
        result = CommonValidators.required("test_value", "测试字段")
        assert result == "test_value"

    def test_required_with_none_raises_exception(self):
        """测试None值抛出异常"""
        from utils.validators import CommonValidators
        from core.exceptions import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            CommonValidators.required(None, "测试字段")
        assert "不能为空" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
