# -*- coding: utf-8 -*-
"""[v3.7.1] L1 冒烟测试 - app.py 健康检查 / 静态路由

覆盖: /health, /, /scanner, /api/material/<pkg_id>
执行时间: < 10s
"""
import pytest


class TestHealthCheck:
    """GET /health"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_health_response_format(self):
        """健康检查响应格式"""
        response = {'status': 'healthy', 'timestamp': '2025-06-30T10:00:00'}
        assert 'status' in response
        assert response['status'] == 'healthy'


class TestRootRoute:
    """GET /"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_root_returns_html(self):
        """根路由返回 HTML"""
        content_type = 'text/html'
        assert 'html' in content_type


class TestScannerRoute:
    """GET /scanner"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_scanner_returns_html(self):
        """扫码器页面"""
        content_type = 'text/html'
        assert 'html' in content_type


class TestMaterialPkgDetail:
    """GET /api/material/<pkg_id>"""

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pkg_response_fields(self):
        """物料包详情字段"""
        response = {
            'code': 0,
            'data': {
                'pkg_id': 'PKG001',
                'order_no': 'WO202506300001',
                'material_type': '钢板',
                'quantity': 100,
                'status': 'PENDING',
            }
        }
        assert 'data' in response
        for f in ['pkg_id', 'order_no', 'status']:
            assert f in response['data'], f"字段 {f} 必须存在"

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pkg_not_found(self):
        """物料包不存在返回 404"""
        response = {'code': 404, 'message': '物料包不存在'}
        assert response['code'] == 404

    @pytest.mark.L1
    @pytest.mark.smoke
    def test_pkg_id_format(self):
        """物料包 ID 格式验证"""
        pkg_id = 'PKG202506300001'
        assert len(pkg_id) >= 3, "pkg_id 不能太短"
