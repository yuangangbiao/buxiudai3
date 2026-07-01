# -*- coding: utf-8 -*-
"""集成测试: 移动端登录功能 (v3.5.5)

测试本次修复:
1. /api/login 兼容路由 (支持前端 username 字段)
2. 姓名/工号双模式登录
3. connection-manager.js 脚本加载
4. 登录时实时检查操作员状态

依赖:
- mobile_api_ai.api.auth
- mobile_api_ai.app
"""
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

_MOBILE_API_PATH = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(os.path.dirname(_MOBILE_API_PATH))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)
if _MOBILE_API_PATH not in sys.path:
    sys.path.append(_MOBILE_API_PATH)


class TestApiLoginCompatRoute:
    """测试 /api/login 兼容路由 (支持前端 username 字段)"""

    @pytest.fixture
    def client(self):
        with patch('mobile_api_ai.storage.mysql_storage.MySQLStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_instance.fetch_all.return_value = [
                {
                    'enterprise_id': 'YuanGangBiao',
                    'name': '苑岗彪',
                    'role': '员工',
                    'department': '宁津晨圣输送机械有限公司',
                    'status': 'active'
                }
            ]
            mock_instance.fetch_one.return_value = {'status': 'active'}
            mock_storage.return_value = mock_instance

            from mobile_api_ai.app import create_app
            app = create_app()
            app.config['TESTING'] = True
            return app.test_client()

    def test_login_with_username_field(self, client):
        """前端使用 username 字段登录"""
        resp = client.post('/api/login', json={'username': '苑岗彪'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['operator']['name'] == '苑岗彪'
        assert 'token' in result['data']

    def test_login_with_operator_id_field(self, client):
        """使用 operator_id 字段登录"""
        resp = client.post('/api/login', json={'operator_id': 'YuanGangBiao'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['operator']['id'] == 'YuanGangBiao'

    def test_login_with_name_field(self, client):
        """使用 name 字段登录"""
        resp = client.post('/api/login', json={'name': '苑岗彪'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_login_invalid_operator(self, client):
        """无效操作员"""
        resp = client.post('/api/login', json={'username': '不存在的用户'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002
        assert '操作员不存在' in result['message']

    def test_login_empty_fields_returns_error(self, client):
        """空字段时返回操作员不存在（符合业务逻辑）"""
        resp = client.post('/api/login', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_login_method_not_post(self, client):
        """非 POST 方法应返回 405"""
        resp = client.get('/api/login')
        assert resp.status_code == 405


class TestAuthBlueprintLogin:
    """测试 /api/auth/login 原始路由"""

    @pytest.fixture
    def client(self):
        with patch('mobile_api_ai.storage.mysql_storage.MySQLStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_instance.fetch_all.return_value = [
                {
                    'enterprise_id': 'YuanGangBiao',
                    'name': '苑岗彪',
                    'role': '员工',
                    'department': '宁津',
                    'status': 'active'
                }
            ]
            mock_instance.fetch_one.return_value = {'status': 'active'}
            mock_storage.return_value = mock_instance

            from mobile_api_ai.api.auth import bp
            from flask import Flask
            app = Flask(__name__)
            app.config['TESTING'] = True
            app.register_blueprint(bp)
            return app.test_client()

    def test_auth_login_with_operator_id(self, client):
        """原始 /api/auth/login 使用 operator_id"""
        resp = client.post('/api/auth/login', json={'operator_id': 'YuanGangBiao'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'token' in result['data']

    def test_auth_login_with_name(self, client):
        """原始 /api/auth/login 也支持 name"""
        resp = client.post('/api/auth/login', json={'name': '苑岗彪'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0


class TestLoginResponseFormat:
    """测试登录响应格式"""

    @pytest.fixture
    def client(self):
        with patch('mobile_api_ai.storage.mysql_storage.MySQLStorage') as mock_storage:
            mock_instance = MagicMock()
            mock_instance.fetch_all.return_value = [
                {
                    'enterprise_id': 'YuanGangBiao',
                    'name': '苑岗彪',
                    'role': '员工',
                    'department': '宁津晨圣输送机械有限公司',
                    'status': 'active'
                }
            ]
            mock_instance.fetch_one.return_value = {'status': 'active'}
            mock_storage.return_value = mock_instance

            from mobile_api_ai.app import create_app
            app = create_app()
            app.config['TESTING'] = True
            return app.test_client()

    def test_response_contains_required_fields(self, client):
        """响应包含所有必需字段"""
        resp = client.post('/api/login', json={'username': '苑岗彪'})
        result = resp.get_json()

        assert 'code' in result
        assert 'message' in result
        assert 'data' in result

        data = result['data']
        assert 'token' in data
        assert 'operator' in data

        operator = data['operator']
        assert 'id' in operator
        assert 'name' in operator
        assert 'role' in operator
        assert 'team_name' in operator

    def test_token_is_valid_jwt(self, client):
        """Token 是有效的 JWT 格式"""
        import jwt
        resp = client.post('/api/login', json={'username': '苑岗彪'})
        token = resp.get_json()['data']['token']

        parts = token.split('.')
        assert len(parts) == 3

        secret = os.getenv('JWT_SECRET_KEY', 'default-secret')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        assert 'operator_id' in payload
        assert 'name' in payload
        assert 'exp' in payload


class TestConnectionManagerJsLoad:
    """测试 connection-manager.js 能否正确加载"""

    @pytest.fixture
    def client(self):
        from mobile_api_ai.app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()

    def test_connection_manager_js_loadable(self, client):
        """connection-manager.js 可以被加载且包含 CONN 和 detectMode"""
        resp = client.get('/static/js/connection-manager.js')
        assert resp.status_code == 200
        assert b'CONN' in resp.data
        assert b'detectMode' in resp.data

    def test_mobile_unified_page_without_defer(self):
        """mobile_unified.html 中 connection-manager.js 不使用 defer"""
        html_path = os.path.join(_PROJ_ROOT, 'templates', 'mobile_unified.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        assert 'connection-manager.js' in html_content
        lines_before = html_content.split('connection-manager.js')[0].split('\n')
        last_line = lines_before[-1] if lines_before else ''
        assert 'defer' not in last_line, "connection-manager.js 不应使用 defer"


class TestGzipDirectPassthrough:
    """测试 GZIP 压缩对流式响应的处理"""

    @pytest.fixture
    def client(self):
        from mobile_api_ai.app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()

    def test_gzip_compress_normal_response(self, client):
        """正常响应可以被 GZIP 压缩"""
        resp = client.get('/', headers={'Accept-Encoding': 'gzip'})
        assert resp.status_code == 200

    def test_gzip_no_crash_on_streaming(self, client):
        """流式响应不导致 GZIP 崩溃 (测试无 500 错误)"""
        resp = client.get('/', headers={'Accept-Encoding': 'gzip'})
        assert resp.status_code == 200
        assert 'html' in resp.content_type or 'text/html' in str(resp.content_type)


class TestLoginOperatorStatusCheck:
    """测试登录时实时检查操作员状态"""

    @pytest.fixture
    def storage(self):
        from mobile_api_ai.storage.mysql_storage import MySQLStorage
        return MySQLStorage()

    def test_disabled_operator_returns_code_1003(self, storage):
        """禁用操作员返回 code=1003"""
        import requests

        operator_id = 'YuanGangBiao'
        operator_name = '苑岗彪'

        original_status = storage.fetch_one(
            'SELECT status FROM workers WHERE enterprise_id=%s',
            (operator_id,)
        )

        try:
            storage.execute(
                'UPDATE workers SET status=%s WHERE enterprise_id=%s',
                ('inactive', operator_id)
            )

            resp = requests.post(
                'http://localhost:5008/api/auth/login',
                json={'name': operator_name},
                timeout=5
            )
            assert resp.status_code == 200
            result = resp.json()
            assert result['code'] == 1003
            assert '已被禁用' in result['message']
        finally:
            storage.execute(
                'UPDATE workers SET status=%s WHERE enterprise_id=%s',
                (original_status['status'], operator_id)
            )
            storage.disconnect()

    def test_active_operator_login_succeeds(self):
        """活跃操作员可以正常登录"""
        import requests

        resp = requests.post(
            'http://localhost:5008/api/auth/login',
            json={'name': '苑岗彪'},
            timeout=5
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result['code'] == 0
        assert 'token' in result['data']
        assert result['data']['operator']['name'] == '苑岗彪'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
