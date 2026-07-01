# -*- coding: utf-8 -*-
"""集成测试: 核心业务 Blueprint (auth, approval, quality, process).

每个测试类创建独立 Flask app 并注册对应 Blueprint，
验证 HTTP 路由、参数处理、返回值结构的正确性。
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

_TEST_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'fixtures', 'api_test_data.json'
)
with open(_TEST_DATA_PATH, 'r', encoding='utf-8') as f:
    API_TEST_DATA = json.load(f)


class TestAuthBlueprint:
    """认证模块 /api/auth/* 集成测试"""

    @pytest.fixture
    def client(self):
        from api.auth import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        return app.test_client()

    def test_login_success(self, client):
        data = API_TEST_DATA['auth']['valid_operator']
        resp = client.post('/api/auth/login', json=data)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'token' in result['data']

    def test_login_fail(self, client):
        data = API_TEST_DATA['auth']['invalid_operator']
        resp = client.post('/api/auth/login', json=data)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002
        assert '操作员不存在' in result['message']

    def test_verify_no_token(self, client):
        resp = client.get('/api/auth/verify')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_verify_valid_token(self, client):
        data = API_TEST_DATA['auth']['valid_operator']
        login_resp = client.post('/api/auth/login', json=data)
        token = login_resp.get_json()['data']['token']
        resp = client.get('/api/auth/verify', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['valid'] is True


class TestApprovalBlueprint:
    """审批模块 /api/approval/* 集成测试"""

    @pytest.fixture
    def client(self):
        from api.approval import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        return app.test_client()

    def test_pending_list(self, client):
        resp = client.get('/api/approval/pending')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'approvals' in result['data']
        assert len(result['data']['approvals']) > 0

    def test_approve_success(self, client):
        resp = client.post('/api/approval/1/approve')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '审批已通过' in result['message']

    def test_reject_success(self, client):
        data = API_TEST_DATA['approval']['reject_reason']
        resp = client.post('/api/approval/2/reject', json=data)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '审批已拒绝' in result['message']

    def test_history_empty(self, client):
        resp = client.get('/api/approval/history')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['total'] == 0


class TestQualityBlueprint:
    """质检模块 /api/quality/* 集成测试"""

    @pytest.fixture
    def client(self):
        from api.quality import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        return app.test_client()

    def test_list(self, client):
        resp = client.get('/api/quality/list')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'records' in result['data']
        assert len(result['data']['records']) > 0

    def test_create_success(self, client):
        data = API_TEST_DATA['quality']['create_data']
        resp = client.post('/api/quality/1/create', json=data)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'quality_id' in result['data']

    def test_create_default_values(self, client):
        resp = client.post('/api/quality/1/create', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'quality_id' in result['data']

    def test_types_list(self, client):
        resp = client.get('/api/quality/types')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'types' in result['data']
        assert 'results' in result['data']


class TestProcessBlueprint:
    """报工模块 /api/process/* 集成测试"""

    @pytest.fixture
    def client(self):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = (mock_cursor, mock_conn)
        mock_get_db = MagicMock(return_value=mock_cm)

        patcher = patch('core.database.get_db_cursor', mock_get_db)
        patcher.start()

        from api.process import bp
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(bp)
        client = app.test_client()

        yield client, mock_cursor, mock_conn

        patcher.stop()

    def test_my_tasks(self, client):
        test_client, mock_cursor, _ = client
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'production_id': 1, 'order_id': 1, 'process_seq': 1,
             'process_name': '裁剪', 'status': '待开始', 'completed_qty': 0,
             'worker': 'OP001', 'quantity': 100, 'order_no': 'ORD001',
             'customer_name': '测试客户', 'product_type': '不锈钢网带',
             'created_at': '2026-05-26 10:00:00', 'updated_at': ''}
        ]
        resp = test_client.get('/api/process/my-tasks?worker_id=OP001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result.get('data', [])) > 0

    def test_my_tasks_empty(self, client):
        test_client, mock_cursor, _ = client
        mock_cursor.fetchall.return_value = []
        resp = test_client.get('/api/process/my-tasks?worker_id=OP999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_submit_report_success(self, client):
        test_client, mock_cursor, _ = client
        mock_cursor.fetchone.return_value = {
            'order_id': 1, 'process_seq': 1,
            'status': '进行中', 'quantity': 100
        }
        data = {'completed_qty': 50, 'status': '进行中'}
        resp = test_client.post('/api/process/1/report', json=data)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '报工' in result.get('message', '')

    def test_submit_report_missing_fields(self, client):
        test_client, mock_cursor, _ = client
        mock_cursor.fetchone.return_value = {
            'order_id': 1, 'process_seq': 1,
            'status': '进行中', 'quantity': 100
        }
        data = API_TEST_DATA['process']['invalid_report']
        resp = test_client.post('/api/process/1/report', json=data)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
