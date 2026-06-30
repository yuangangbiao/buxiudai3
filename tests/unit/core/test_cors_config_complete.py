# -*- coding: utf-8 -*-
"""
core/cors_config.py 完整单元测试

覆盖模块:
- init_cors()
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, MagicMock


class TestCorsConfigExists:
    """cors_config 存在性测试"""

    def test_cors_config_module_exists(self):
        """测试cors_config模块存在"""
        from core import cors_config
        assert cors_config is not None

    def test_init_cors_exists(self):
        """测试init_cors函数存在"""
        from core.cors_config import init_cors
        assert callable(init_cors)


class TestInitCors:
    """init_cors() 测试"""

    @patch.dict(os.environ, {'CORS_ALLOWED_ORIGINS': 'http://localhost:3000'})
    @patch('core.cors_config.CORS')
    def test_init_cors_with_env(self, mock_cors):
        """测试使用环境变量初始化"""
        from core.cors_config import init_cors

        app = MagicMock()
        init_cors(app)

        mock_cors.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch('core.cors_config.CORS')
    def test_init_cors_with_default(self, mock_cors):
        """测试使用默认值初始化"""
        from core.cors_config import init_cors

        app = MagicMock()
        init_cors(app)

        mock_cors.assert_called_once()

    @patch.dict(os.environ, {'CORS_ALLOWED_ORIGINS': 'http://a.com,http://b.com'})
    @patch('core.cors_config.CORS')
    def test_init_cors_with_multiple_origins(self, mock_cors):
        """测试多个origin"""
        from core.cors_config import init_cors

        app = MagicMock()
        init_cors(app)

        mock_cors.assert_called_once()
        call_kwargs = mock_cors.call_args[1]
        assert 'http://a.com' in call_kwargs['resources'][r'/api/*']['origins']
        assert 'http://b.com' in call_kwargs['resources'][r'/api/*']['origins']

    @patch.dict(os.environ, {'CORS_ALLOWED_ORIGINS': '*'})
    @patch('core.cors_config.CORS')
    def test_init_cors_rejects_wildcard(self, mock_cors):
        """测试拒绝通配符"""
        from core.cors_config import init_cors

        app = MagicMock()
        with pytest.raises(ValueError):
            init_cors(app)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
