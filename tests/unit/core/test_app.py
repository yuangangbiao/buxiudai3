# Phase 1: 覆盖 0% 模块 — core/app.py 单元测试
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestGetVersion:
    def test_get_version_returns_string(self):
        """get_version() 返回版本号字符串"""
        from core.app import get_version
        with patch('version.VERSION', '3.0.1'):
            assert get_version() == '3.0.1'


class TestGetBuildInfo:
    def test_get_build_info_contains_keys(self):
        """get_build_info() 包含所有必需的键"""
        from core.app import get_build_info
        with patch('core.app.get_version', return_value='3.0.0'):
            info = get_build_info()
        assert info['version'] == '3.0.0'
        assert 'arch' in info
        assert 'features' in info
        assert isinstance(info['features'], list)


class TestInitializeApp:
    def test_initialize_app_full_flow(self):
        """initialize_app() 执行完整初始化流程"""
        from core.app import initialize_app

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.database.init_db') as mock_init_db:
            with patch('models.database.get_connection', return_value=mock_conn) as mock_get_conn:
                with patch('core.event_bus.EventBus') as mock_EventBus:
                    with patch('core.app.get_build_info') as mock_build_info:
                        with patch('version.VERSION', '3.0.0'):
                            mock_build_info.return_value = {'version': '3.0.0'}
                            initialize_app()

        # 验证初始化流程
        mock_init_db.assert_called_once()
        # 验证创建 audit_logs 表
        mock_conn.cursor.assert_called()
        # 确保提交
        assert mock_conn.commit.called
        # 确保连接被关闭
        assert mock_conn.close.called
        # 确保发布了 APP_STARTED 事件
        mock_EventBus.publish.assert_called_once()

    def test_initialize_app_db_error_raised(self):
        """initialize_app() 中数据库错误向上传播"""
        from core.app import initialize_app

        with patch('models.database.init_db', side_effect=Exception('DB init failed')):
            with pytest.raises(Exception, match='DB init failed'):
                initialize_app()


class TestCreateSecureFlaskApp:
    def _make_app(self, **kwargs):
        """创建测试 app 的辅助方法"""
        from core.app import create_secure_flask_app
        with patch('core.config.JWT_SECRET_KEY', 'test-key-32-chars-minimum-length-00'):
            return create_secure_flask_app(__name__, **kwargs)

    def test_create_basic_app(self):
        """create_secure_flask_app 创建基础 Flask 应用"""
        app = self._make_app(enable_limiter=False)
        assert app is not None
        assert app.name == __name__

    def test_create_app_with_limiter(self):
        """create_secure_flask_app 启用限流器"""
        app = self._make_app(enable_limiter=True)
        assert app is not None

    def test_create_app_with_blueprints(self):
        """create_secure_flask_app 注册蓝图"""
        from flask import Blueprint
        test_bp = Blueprint('test', __name__)
        app = self._make_app(enable_limiter=False, blueprints=[test_bp])
        assert 'test' in app.blueprints

    def test_favicon_returns_204(self):
        """favicon.ico 返回 204 No Content"""
        app = self._make_app(enable_limiter=False)
        with app.test_client() as client:
            r = client.get('/favicon.ico')
            assert r.status_code == 204

    def test_global_error_handler_returns_500(self):
        """全局异常处理器返回 500"""
        app = self._make_app(enable_limiter=False)

        # 创建一个会抛出异常的 route
        @app.route('/crash')
        def crash():
            raise RuntimeError('Something broke')

        with app.test_client() as client:
            r = client.get('/crash')
            assert r.status_code == 500
            assert r.json['code'] == 500
