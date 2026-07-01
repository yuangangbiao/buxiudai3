# -*- coding: utf-8 -*-
"""
health 单元测试

覆盖：
- /api/health 健康检查
- 各组件检查逻辑
- 异常处理
"""
import pytest
from unittest.mock import patch, MagicMock


class TestHealthCheck:
    """健康检查测试"""

    def setup_method(self):
        from flask import Flask
        from api.health import bp
        self.app = Flask(__name__)
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()

    @patch('bots.base.GroupBot', None)
    @patch('core.db.get_db_cursor')
    def test_health_db_error(self, mock_db):
        mock_db.side_effect = Exception('db error')
        resp = self.client.get('/api/health')
        data = resp.get_json()
        assert data['code'] != 0 or 'db' in data.get('data', {}).get('components', {})

    @patch('bots.base.GroupBot', None)
    @patch('core.db.get_db_cursor')
    def test_health_db_ok(self, mock_db):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = (mock_cursor, mock_conn)
        mock_cursor.fetchone.return_value = (1,)
        resp = self.client.get('/api/health')
        assert resp.status_code == 200

    @patch('bots.base.GroupBot', None)
    @patch('core.db.get_db_cursor')
    def test_health_returns_json(self, mock_db):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = (mock_cursor, mock_conn)
        mock_cursor.fetchone.return_value = (1,)
        resp = self.client.get('/api/health')
        data = resp.get_json()
        assert 'code' in data
        assert 'data' in data
