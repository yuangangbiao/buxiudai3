# -*- coding: utf-8 -*-
"""
swagger 单元测试

覆盖：
- API_DOCS 文档结构
- Blueprint 创建
- 文档渲染
"""
import pytest


class TestSwaggerBlueprint:
    """Swagger Blueprint 测试"""

    def test_blueprint_exists(self):
        from api.swagger import bp
        assert bp is not None
        assert bp.name == 'docs'

    def test_blueprint_url_prefix(self):
        from api.swagger import bp
        assert bp.url_prefix == '/api/docs'

    def test_api_docs_structure(self):
        from api.swagger import API_DOCS
        assert API_DOCS['openapi'] == '3.0.0'
        assert 'info' in API_DOCS
        assert 'paths' in API_DOCS
        assert 'servers' in API_DOCS

    def test_info_section(self):
        from api.swagger import API_DOCS
        assert 'title' in API_DOCS['info']
        assert 'version' in API_DOCS['info']

    def test_paths_have_endpoints(self):
        from api.swagger import API_DOCS
        assert len(API_DOCS['paths']) > 0

    def test_login_endpoint(self):
        from api.swagger import API_DOCS
        assert '/auth/login' in API_DOCS['paths']


class TestSwaggerRoutes:
    """Swagger 路由测试"""

    def setup_method(self):
        from flask import Flask
        from api.swagger import bp
        self.app = Flask(__name__)
        self.app.register_blueprint(bp)
        self.client = self.app.test_client()

    def test_docs_json(self):
        resp = self.client.get('/api/docs/openapi.json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['openapi'] == '3.0.0'

    def test_docs_html(self):
        resp = self.client.get('/api/docs/')
        assert resp.status_code == 200
        assert b'swagger' in resp.data.lower() or b'API' in resp.data
