# QA-013: inventory_api 单元测试
import pytest, json, sys, os
from unittest.mock import patch, MagicMock

# 预先生成一个 CSRF token 值（所有 auth_client 实例共享）
_CSRF_TOKEN = 'test-csrf-token-' + 'x' * 32


def _make_app():
    """在 fixture 内延迟导入，确保环境变量由 monkeypatch 安全设置"""
    from mobile_api_ai.inventory_api_server import app
    return app


@pytest.fixture
def client(monkeypatch):
    """未登录客户端（通过 monkeypatch 安全设置环境变量，不污染全局 os.environ）"""
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-secret-key-for-pytest-at-least-32-chars!!')
    monkeypatch.setenv('MYSQL_USER', 'test_user')
    monkeypatch.setenv('INVENTORY_DB_NAME', 'test_inventory')
    monkeypatch.setenv('INVENTORY_ADMIN_PASSWORD_HASH', '00' * 16 + '$' + '00' * 64)
    monkeypatch.setenv('INVENTORY_MAX_STOCK', '99999')
    app = _make_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture
def auth_client(monkeypatch):
    """已登录管理员客户端（满足 admin_required + require_csrf）"""
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-secret-key-for-pytest-at-least-32-chars!!')
    monkeypatch.setenv('MYSQL_USER', 'test_user')
    monkeypatch.setenv('INVENTORY_DB_NAME', 'test_inventory')
    monkeypatch.setenv('INVENTORY_ADMIN_PASSWORD_HASH', '00' * 16 + '$' + '00' * 64)
    monkeypatch.setenv('INVENTORY_MAX_STOCK', '99999')
    app = _make_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['logged_in'] = True
            sess['is_admin'] = True
            sess['_csrf_token'] = _CSRF_TOKEN
        yield c


def _csrf_headers():
    """构造带 CSRF token 的请求头"""
    return {'X-CSRF-Token': _CSRF_TOKEN, 'Content-Type': 'application/json'}


class TestInventoryHealth:
    def test_health_returns_200(self, client):
        r = client.get('/api/health')
        assert r.status_code == 200
        assert r.json['code'] == 0


class TestInventoryQuery:
    def test_query_returns_200(self, auth_client):
        """真实 API: GET /inventory/api/stock/list"""
        # CRITICAL: 必须用短名 inventory_web.routes_core.execute 而非
        # mobile_api_ai.inventory_web.routes_core.execute，因为 inventory_api_server
        # 使用 from inventory_web import web_bp 导入（非完整包路径），
        # 导致 inventory_web.routes_core 和 mobile_api_ai.inventory_web.routes_core
        # 是两个不同的模块实例（globals 不同）
        with patch('inventory_web.routes_core.execute', return_value=[]):
            r = auth_client.get('/inventory/api/stock/list')
            assert r.status_code == 200

    def test_query_db_error_handled(self, auth_client):
        with patch('inventory_web.routes_core.execute', side_effect=Exception('DB down')):
            r = auth_client.get('/inventory/api/stock/list')
            assert r.status_code == 500


class TestInventoryInbound:
    def test_inbound_missing_fields(self, auth_client):
        headers = _csrf_headers()
        r = auth_client.post('/inventory/api/inbound/do',
                             data=json.dumps({}),
                             content_type='application/json',
                             headers=headers)
        assert r.status_code == 400

    def test_inbound_zero_qty_rejected(self, auth_client):
        headers = _csrf_headers()
        r = auth_client.post('/inventory/api/inbound/do',
                             data=json.dumps({'product_id': 1, 'warehouse_id': 1, 'qty': 0}),
                             content_type='application/json',
                             headers=headers)
        assert r.status_code == 400

    def test_inbound_negative_qty_rejected(self, auth_client):
        headers = _csrf_headers()
        r = auth_client.post('/inventory/api/inbound/do',
                             data=json.dumps({'product_id': 1, 'warehouse_id': 1, 'qty': -5}),
                             content_type='application/json',
                             headers=headers)
        assert r.status_code == 400


class TestInventoryOutbound:
    def test_outbound_missing_fields(self, auth_client):
        headers = _csrf_headers()
        r = auth_client.post('/inventory/api/outbound/do',
                             data=json.dumps({}),
                             content_type='application/json',
                             headers=headers)
        assert r.status_code == 400

    def test_outbound_insufficient_stock(self, auth_client):
        headers = _csrf_headers()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'current_qty': 3}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_conn_ctx = MagicMock()
        mock_get_conn_ctx.__enter__.return_value = mock_conn
        with patch('inventory_web.routes_core.get_conn', return_value=mock_get_conn_ctx):
            r = auth_client.post('/inventory/api/outbound/do',
                                 data=json.dumps({'product_id': 1, 'warehouse_id': 1, 'qty': 10}),
                                 content_type='application/json',
                                 headers=headers)
            assert r.status_code == 409

    def test_outbound_product_not_found(self, auth_client):
        headers = _csrf_headers()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # 库存记录不存在
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_get_conn_ctx = MagicMock()
        mock_get_conn_ctx.__enter__.return_value = mock_conn
        with patch('inventory_web.routes_core.get_conn', return_value=mock_get_conn_ctx):
            r = auth_client.post('/inventory/api/outbound/do',
                                 data=json.dumps({'product_id': 99, 'warehouse_id': 1, 'qty': 5}),
                                 content_type='application/json',
                                 headers=headers)
            assert r.status_code == 404
