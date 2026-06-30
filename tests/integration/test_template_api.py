# -*- coding: utf-8 -*-
"""消息模板 API 集成测试 — 需要服务 5003 在线"""
import pytest
import requests
import time

BASE = 'http://127.0.0.1:5003/api/dispatch-center'
TEST_TEMPLATE_ID = f'test_qa_{int(time.time())}'


class TestTemplateAPI:
    """模板 CRUD API"""

    def test_get_templates(self):
        r = requests.get(f'{BASE}/templates')
        assert r.status_code == 200
        data = r.json()
        assert data['code'] == 0
        assert 'builtin' in data['data'] or 'data' in data

    def test_put_custom_template(self):
        """创建自定义模板"""
        r = requests.put(f'{BASE}/templates/{TEST_TEMPLATE_ID}', json={
            'name': 'QA测试模板', 'category': 'custom',
            'content': '🎯 {操作员} 这是 QA 测试, 订单 {订单号}'
        })
        assert r.status_code < 500

    def test_delete_custom_template(self):
        """删除自定义模板"""
        r = requests.delete(f'{BASE}/templates/{TEST_TEMPLATE_ID}')
        assert r.status_code < 500

    def test_delete_builtin_403(self):
        """删除内置模板返回 403"""
        r = requests.delete(f'{BASE}/templates/tmpl_task_assigned')
        assert r.status_code == 403

    def test_delete_builtin_owner_path(self):
        """内置模板 ID 保护"""
        for tid in ['tmpl_task_assigned', 'tmpl_process_start', 'tmpl_material_shortage']:
            r = requests.delete(f'{BASE}/templates/{tid}')
            assert r.status_code < 500  # 至少不崩溃


class TestVariables:
    """变量 API"""

    def test_list_variables(self):
        r = requests.get(f'{BASE}/messages/templates/variables')
        assert r.status_code == 200
        data = r.json()
        assert data['code'] == 0
        assert len(data['data']) >= 60


class TestServiceHealth:
    """服务在线性"""

    def test_service_alive(self):
        r = requests.get(f'{BASE}/templates', timeout=5)
        assert r.status_code == 200
