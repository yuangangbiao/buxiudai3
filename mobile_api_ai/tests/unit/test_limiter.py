# -*- coding: utf-8 -*-
"""
limiter 单元测试

覆盖：
- 默认限流器创建
- 限制规则解析
- 应用初始化
"""
import pytest
from unittest.mock import patch


class TestLimiterCreation:
    """限流器创建测试"""

    def test_limiter_default_creation(self):
        from api.limiter import limiter
        assert limiter is not None

    def test_limiter_with_custom_limits(self):
        with patch.dict('os.environ', {'DEFAULT_RATE_LIMITS': '100 per minute, 50 per hour'}):
            import importlib
            import api.limiter
            importlib.reload(api.limiter)
            assert api.limiter.limiter is not None

    def test_limiter_with_custom_storage(self):
        with patch.dict('os.environ', {'LIMITER_STORAGE_URI': 'redis://localhost:6379'}):
            import importlib
            import api.limiter
            importlib.reload(api.limiter)
            assert api.limiter.limiter is not None


class TestLimiterInit:
    """限流器初始化测试"""

    def test_init_app(self):
        from flask import Flask
        from api.limiter import limiter
        app = Flask(__name__)
        limiter.init_app(app)
