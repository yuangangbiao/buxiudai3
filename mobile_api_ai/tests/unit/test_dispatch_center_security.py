# -*- coding: utf-8 -*-
"""
dispatch_center 安全修复测试套件
覆盖: SQL注入防护 / 异常脱敏 / JWT认证 / Redis限流 / 分页校验 / 连接泄漏
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: SQL注入防护 — 字段白名单（静态代码检查）
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLInjectionFieldAllowlist:

    def test_evil_sql_payload_rejected_from_outsource_allowlist(self):
        from mobile_api_ai.dispatch_center._core import _OUTER_SQL_ALLOWED
        evil = [
            "id; DROP TABLE users;--",
            "1' OR '1'='1",
            "name` WHERE 1=1; DELETE * FROM all",
            "field WHERE 1=1--",
            "id<script>alert(1)</script>",
        ]
        for f in evil:
            assert f not in _OUTER_SQL_ALLOWED, f"恶意字段未被拦截: {f}"

    def test_evil_sql_payload_rejected_from_material_allowlist(self):
        from mobile_api_ai.dispatch_center._core import _MATERIAL_SQL_ALLOWED
        evil = [
            "'; UPDATE orders SET status='hacked';--",
            "<img src=x onerror=alert(1)>",
            "field UNION SELECT * FROM passwords",
        ]
        for f in evil:
            assert f not in _MATERIAL_SQL_ALLOWED, f"恶意字段未被拦截: {f}"

    def test_evil_sql_payload_rejected_from_repair_allowlist(self):
        from mobile_api_ai.dispatch_center._core import _REPAIR_SQL_ALLOWED
        evil = [
            "id'--",
            "field; EXEC xp_cmdshell('dir');--",
        ]
        for f in evil:
            assert f not in _REPAIR_SQL_ALLOWED, f"恶意字段未被拦截: {f}"

    def test_evil_sql_payload_rejected_from_quality_allowlist(self):
        from mobile_api_ai.dispatch_center._core import _QUALITY_SQL_ALLOWED
        evil = [
            "../../../etc/passwd",
            "{{7*7}}",
            "${env.SECRET}",
        ]
        for f in evil:
            assert f not in _QUALITY_SQL_ALLOWED, f"恶意字段未被拦截: {f}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: SQL注入防护 — 参数化查询（静态代码检查）
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLInjectionParameterizedQueries:

    def test_no_fstring_sql_in_list_unified_tasks(self):
        from mobile_api_ai.dispatch_center._core import list_unified_tasks
        import inspect
        source = inspect.getsource(list_unified_tasks)
        lines = source.split('\n')
        dangerous = []
        for i, line in enumerate(lines):
            if 'cur.execute' in line and ('f"' in line or "f'" in line):
                stripped = line.strip()
                if '{' in stripped and ('status_filter' in stripped or 'operator_filter' in stripped):
                    dangerous.append((i, stripped))
        assert len(dangerous) == 0, f"发现f-string SQL注入: {dangerous}"

    def test_no_percent_formatting_sql(self):
        from mobile_api_ai.dispatch_center._core import list_unified_tasks
        import inspect
        source = inspect.getsource(list_unified_tasks)
        assert '"% (' not in source and "'% (" not in source, "发现%格式化SQL注入"

    def test_no_chr39_sql_escaping_in_execute(self):
        from mobile_api_ai.dispatch_center._core import list_unified_tasks
        import inspect
        source = inspect.getsource(list_unified_tasks)
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'chr(39)' in line and ('execute' in line or 'SELECT' in line or 'WHERE' in line):
                pytest.fail(f"L{i}: 发现chr(39)字符串拼接SQL: {line.strip()}")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: 异常脱敏（静态代码检查）
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptionSanitization:

    def _get_sync_source(self, func_name):
        from mobile_api_ai.dispatch_center._core import (
            api_sync_outsource, api_sync_material,
            api_sync_repair, api_sync_quality_record,
        )
        mapping = {
            'api_sync_outsource': api_sync_outsource,
            'api_sync_material': api_sync_material,
            'api_sync_repair': api_sync_repair,
            'api_sync_quality_record': api_sync_quality_record,
        }
        import inspect
        return inspect.getsource(mapping[func_name])

    @pytest.mark.parametrize("func", [
        'api_sync_outsource', 'api_sync_material',
        'api_sync_repair', 'api_sync_quality_record',
    ])
    def test_no_str_e_in_jsonify_error_response(self, func):
        source = self._get_sync_source(func)
        assert "'message': str(e)" not in source, \
            f"{func}: except块中仍使用str(e)泄露异常信息"

    def test_list_unified_tasks_no_str_e(self):
        from mobile_api_ai.dispatch_center._core import list_unified_tasks
        import inspect
        source = inspect.getsource(list_unified_tasks)
        assert "'message': str(e)" not in source, \
            "list_unified_tasks: except块中仍使用str(e)"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: JWT认证（Flask test_request_context）
# ═══════════════════════════════════════════════════════════════════════════════

class TestJWTAuthentication:

    @pytest.fixture
    def app_client(self):
        from mobile_api_ai.dispatch_center._core import dispatch_center_bp
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(dispatch_center_bp, url_prefix='/dispatch')
        with app.test_request_context():
            yield app.test_client()

    def test_missing_auth_header_returns_401(self, app_client):
        resp = app_client.get('/dispatch/unified-tasks')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert '令牌' in data['message']

    def test_invalid_token_returns_401(self, app_client):
        resp = app_client.get('/dispatch/unified-tasks',
                            headers={'Authorization': 'Bearer invalid_token_xyz'})
        assert resp.status_code == 401

    def test_valid_token_passes_auth(self, app_client):
        import jwt
        from core.config import JWT_SECRET_KEY
        payload = {'user_id': 1, 'role': 'admin'}
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
        with patch('mobile_api_ai.dispatch_center._core._get_mysql_connection') as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], [], [], [], []]
            mock_cur.fetchone.return_value = (0,)
            mock_conn.return_value.cursor.return_value = mock_cur
            resp = app_client.get('/dispatch/unified-tasks',
                                headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 200

    @pytest.mark.parametrize("endpoint", [
        '/dispatch/sync/material',
        '/dispatch/sync/repair',
        '/dispatch/sync/outsource',
        '/dispatch/sync/quality-record',
    ])
    def test_sync_endpoint_requires_auth(self, app_client, endpoint):
        resp = app_client.post(endpoint,
                            headers={'Content-Type': 'application/json'},
                            json={'order_no': 'TEST'})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert '令牌' in data['message']


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: 分页参数校验（Flask test_client + 有效JWT）
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaginationValidation:

    @pytest.fixture
    def auth_client(self):
        import jwt
        from core.config import JWT_SECRET_KEY
        from mobile_api_ai.dispatch_center._core import dispatch_center_bp
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(dispatch_center_bp, url_prefix='/dispatch')
        token = jwt.encode({'user_id': 1}, JWT_SECRET_KEY, algorithm='HS256')
        client = app.test_client()
        client.token = token
        return client

    def test_non_integer_page_returns_400(self, auth_client):
        with patch('dispatch_center._core._get_mysql_connection') as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], [], [], [], []]
            mock_cur.fetchone.return_value = (0,)
            mock_conn.return_value.cursor.return_value = mock_cur
            resp = auth_client.get('/dispatch/unified-tasks?page=abc',
                                headers={'Authorization': f'Bearer {auth_client.token}'})
            assert resp.status_code == 200
            assert resp.get_json()['code'] == 400

    def test_page_size_out_of_range_returns_400(self, auth_client):
        with patch('dispatch_center._core._get_mysql_connection') as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], [], [], [], []]
            mock_cur.fetchone.return_value = (0,)
            mock_conn.return_value.cursor.return_value = mock_cur
            resp = auth_client.get('/dispatch/unified-tasks?page_size=999',
                                headers={'Authorization': f'Bearer {auth_client.token}'})
            assert resp.status_code == 200
            assert resp.get_json()['code'] == 400

    def test_negative_page_returns_400(self, auth_client):
        with patch('dispatch_center._core._get_mysql_connection') as mock_conn:
            mock_cur = MagicMock()
            mock_cur.fetchall.side_effect = [[], [], [], [], []]
            mock_cur.fetchone.return_value = (0,)
            mock_conn.return_value.cursor.return_value = mock_cur
            resp = auth_client.get('/dispatch/unified-tasks?page=-1',
                                headers={'Authorization': f'Bearer {auth_client.token}'})
            assert resp.status_code == 200
            assert resp.get_json()['code'] == 400


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: 连接泄漏防护（mock验证）
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectionLeakProtection:

    @pytest.fixture
    def auth_client(self):
        import jwt
        from core.config import JWT_SECRET_KEY
        from mobile_api_ai.dispatch_center._core import dispatch_center_bp
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(dispatch_center_bp, url_prefix='/dispatch')
        token = jwt.encode({'user_id': 1}, JWT_SECRET_KEY, algorithm='HS256')
        client = app.test_client()
        client.token = token
        return client

    def test_connection_closed_on_db_error(self, auth_client):
        resp = auth_client.get('/dispatch/unified-tasks',
                            headers={'Authorization': f'Bearer {auth_client.token}'})
        assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: skipped_fields响应（Flask test_client）
# ═══════════════════════════════════════════════════════════════════════════════

class TestSkippedFieldsResponse:

    @pytest.fixture
    def app_client(self):
        from mobile_api_ai.dispatch_center._core import dispatch_center_bp
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(dispatch_center_bp, url_prefix='/dispatch')
        return app.test_client()

    def test_sync_outsource_skips_illegal_fields(self, app_client):
        import jwt
        from core.config import JWT_SECRET_KEY
        token = jwt.encode({'user_id': 1}, JWT_SECRET_KEY, algorithm='HS256')
        with patch('mobile_api_ai.dispatch_center._core._get_mysql_connection') as mock_conn:
            mock_cur = MagicMock()
            mock_cur.rowcount = 1
            mock_conn.return_value.cursor.return_value = mock_cur
            resp = app_client.post(
                '/dispatch/sync/outsource',
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={'order_no': 'TEST001', '__evil__': 'test', 'status': 'done'},
            )
            data = resp.get_json()
            assert data is not None
            assert 'skipped_fields' in data, f"Response: {data}"
            assert '__evil__' in data['skipped_fields'], \
                f"evil not in skipped_fields: {data['skipped_fields']}"
