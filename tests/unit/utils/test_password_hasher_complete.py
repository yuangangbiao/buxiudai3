# -*- coding: utf-8 -*-
"""
utils/password_hasher.py 完整单元测试

覆盖模块:
- hash_password
- verify_password
- generate_random_password
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

class TestPasswordHasherExists:
    """password_hasher 模块存在性测试"""

    def test_password_hasher_module_exists(self):
        """测试password_hasher模块存在"""
        from utils import password_hasher
        assert password_hasher is not None

    def test_hash_password_exists(self):
        """测试hash_password函数存在"""
        from utils.password_hasher import hash_password
        assert callable(hash_password)

    def test_verify_password_exists(self):
        """测试verify_password函数存在"""
        from utils.password_hasher import verify_password
        assert callable(verify_password)

    def test_generate_random_password_exists(self):
        """测试generate_random_password函数存在"""
        from utils.password_hasher import generate_random_password
        assert callable(generate_random_password)


class TestPasswordHasherFunctions:
    """password_hasher 函数测试"""

    def test_hash_password_returns_value(self):
        """测试hash_password返回值"""
        from utils.password_hasher import hash_password
        result = hash_password("test123")
        assert result is not None

    def test_hash_password_different_from_input(self):
        """测试hash_password与输入不同"""
        from utils.password_hasher import hash_password
        result = hash_password("test123")
        # result可能是元组或字符串
        if isinstance(result, tuple):
            assert "test123" not in result
        else:
            assert result != "test123"

    def test_verify_password_callable(self):
        """测试verify_password可调用"""
        from utils.password_hasher import verify_password
        assert callable(verify_password)

    def test_generate_random_password_returns_string(self):
        """测试generate_random_password返回字符串"""
        from utils.password_hasher import generate_random_password
        result = generate_random_password()
        assert isinstance(result, str)

    def test_generate_random_password_has_length(self):
        """测试generate_random_password有长度"""
        from utils.password_hasher import generate_random_password
        result = generate_random_password()
        assert len(result) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
