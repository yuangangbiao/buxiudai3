# -*- coding: utf-8 -*-
"""
core/db.py 完整单元测试

覆盖模块:
- ConnectionPool
- PooledConnection
- DB
- 全局函数
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class TestConnectionPool:
    """ConnectionPool 单元测试"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """重置单例状态"""
        from core import db as db_module
        db_module.ConnectionPool._instance = None
        yield
        db_module.ConnectionPool._instance = None

    def test_connection_pool_singleton(self):
        """测试连接池单例模式"""
        from core.db import ConnectionPool

        pool1 = ConnectionPool()
        pool2 = ConnectionPool()

        assert pool1 is pool2, "ConnectionPool 应该是单例"
