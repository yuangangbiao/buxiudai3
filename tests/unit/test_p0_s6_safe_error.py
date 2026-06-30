# -*- coding: utf-8 -*-
"""
P0-S6 单元测试 - 全局异常脱敏

测试范围: standalone_dispatch_server.py 17 处异常脱敏 + 全局异常处理器
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 项目根目录加入 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'mobile_api_ai'))


class TestSafeErrorResponseImport:
    """测试 _safe_error_response 函数可正常导入"""

    def test_safe_error_msg_constant(self):
        """SAFE_ERROR_MSG 常量存在"""
        from standalone_dispatch_server import SAFE_ERROR_MSG
        assert SAFE_ERROR_MSG == '系统繁忙，请稍后重试'
        # 验证不包含数据库相关字符串
        assert 'MySQL' not in SAFE_ERROR_MSG
        assert 'table' not in SAFE_ERROR_MSG.lower()
        assert 'column' not in SAFE_ERROR_MSG.lower()

    def test_safe_error_response_function_exists(self):
        """_safe_error_response 函数存在"""
        from standalone_dispatch_server import _safe_error_response
        assert callable(_safe_error_response)


class TestSafeErrorResponseBehavior:
    """测试 _safe_error_response 函数行为"""

    @pytest.fixture
    def app(self):
        """创建 Flask 应用 fixture"""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    def test_response_contains_safe_message(self, app):
        """响应包含安全消息"""
        from standalone_dispatch_server import _safe_error_response
        e = Exception("MySQL Connection refused at 10.0.0.5:3306")
        with patch('standalone_dispatch_server.logger') as mock_logger:
            with app.app_context():
                response, code = _safe_error_response(e, code=500)

        # 验证 code
        assert code == 500
        # 验证响应数据
        data = response.get_json()
        assert data['code'] == 500
        assert data['message'] == '系统繁忙，请稍后重试'
        # 验证 message 中不包含原始异常信息
        assert 'MySQL' not in data['message']
        assert '10.0.0.5' not in data['message']
        assert '3306' not in data['message']
        # 验证 logger.exception 被调用
        mock_logger.exception.assert_called_once()

    def test_response_default_code_500(self, app):
        """默认 code=500"""
        from standalone_dispatch_server import _safe_error_response
        e = Exception("test")
        with patch('standalone_dispatch_server.logger'):
            with app.app_context():
                response, code = _safe_error_response(e)
        assert code == 500

    def test_response_custom_code(self, app):
        """自定义 code"""
        from standalone_dispatch_server import _safe_error_response
        e = Exception("test")
        with patch('standalone_dispatch_server.logger'):
            with app.app_context():
                response, code = _safe_error_response(e, code=503)
        assert code == 503
        assert response.get_json()['code'] == 503


class TestNoDatabaseInfoLeak:
    """测试异常响应不泄露数据库信息"""

    @pytest.fixture
    def app(self):
        """创建 Flask 应用 fixture"""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.mark.parametrize("db_error_msg", [
        "MySQL Connection refused at 10.0.0.5:3306",
        "SELECT * FROM orders WHERE id=1 failed",
        "Table 'orders' doesn't exist",
        "Unknown column 'foo' in 'field list'",
        "Duplicate entry 'ORD-001' for key 'order_no'",
    ])
    def test_db_error_not_in_response(self, app, db_error_msg):
        """数据库错误不进入响应"""
        from standalone_dispatch_server import _safe_error_response
        e = Exception(db_error_msg)
        with patch('standalone_dispatch_server.logger'):
            with app.app_context():
                response, _ = _safe_error_response(e, code=500)

        data = response.get_json()
        response_text = str(data)

        # 关键检查：数据库相关信息不进入响应
        assert 'MySQL' not in response_text
        assert 'SELECT' not in response_text
        assert "'orders'" not in response_text
        assert 'column' not in response_text.lower()
        assert '10.0.0.5' not in response_text
        assert '3306' not in response_text


class TestGlobalExceptionHandler:
    """测试全局异常处理器"""

    def test_global_handler_uses_safe_response(self):
        """全局异常处理器使用 _safe_error_response"""
        # 读源码验证
        import inspect
        from standalone_dispatch_server import create_app
        source = inspect.getsource(create_app)

        # 验证全局异常处理器调用 _safe_error_response
        assert '_safe_error_response' in source
        assert 'handle_global_exception' in source
        # 验证 message 使用 SAFE_ERROR_MSG
        assert 'SAFE_ERROR_MSG' in source

    def test_no_str_e_in_message_field(self):
        """JSON 响应 message 字段不含 str(e)"""
        import inspect
        from standalone_dispatch_server import create_app
        source = inspect.getsource(create_app)

        # 查找 'message': str(e) 模式（应该不存在）
        assert "'message': str(e)" not in source, "发现未脱敏的 str(e) 异常响应"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
