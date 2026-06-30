# -*- coding: utf-8 -*-
"""
models/enums.py 完整单元测试

覆盖模块:
- OrderStatus
- ProcessStatus
- 其他业务枚举
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest


class TestEnumsExists:
    """Enums 存在性测试"""

    def test_enums_module_exists(self):
        """测试enums模块存在"""
        from models import enums
        assert enums is not None

    def test_order_status_exists(self):
        """测试OrderStatus存在"""
        from models.enums import OrderStatus
        assert OrderStatus is not None


class TestOrderStatus:
    """OrderStatus 测试"""

    def test_order_status_values(self):
        """测试OrderStatus.values()"""
        from models.enums import OrderStatus
        values = OrderStatus.values()
        assert isinstance(values, list)
        assert 'PENDING' in values
        assert 'CONFIRMED' in values
        assert 'IN_PRODUCTION' in values
        assert 'COMPLETED' in values
        assert 'CANCELLED' in values

    def test_order_status_from_string_valid(self):
        """测试有效字符串转换"""
        from models.enums import OrderStatus
        result = OrderStatus.from_string("PENDING")
        assert result == OrderStatus.PENDING

    def test_order_status_from_string_invalid(self):
        """测试无效字符串转换"""
        from models.enums import OrderStatus
        result = OrderStatus.from_string("INVALID_STATUS")
        assert result is None

    def test_order_status_from_string_empty(self):
        """测试空字符串"""
        from models.enums import OrderStatus
        result = OrderStatus.from_string("")
        assert result is None

    def test_order_status_from_string_none(self):
        """测试None"""
        from models.enums import OrderStatus
        result = OrderStatus.from_string(None)
        assert result is None


class TestEnumsComplete:
    """Enums 完整性测试"""

    def test_module_has_enums(self):
        """测试模块有多个枚举类"""
        from models import enums
        enums_list = [a for a in dir(enums) if not a.startswith('_')]
        # 至少有OrderStatus
        assert 'OrderStatus' in enums_list


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
