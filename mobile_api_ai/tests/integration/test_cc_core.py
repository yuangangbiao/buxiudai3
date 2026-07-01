# -*- coding: utf-8 -*-
"""集成测试: 容器中心核心 API (container_center_api.py).

容器中心 API 模块在模块级直接创建 Flask app + 注册路由/blueprint。
测试策略:
  1) 在 import container_center_api 之前先 patch sys.modules + os.environ,
     确保所有可选依赖(desktop_callback, modules.* 等)被 MagicMock 替代;
  2) 用 patch.object 替换模块级全局变量 (container_center, OPERATORS 等);
  3) 每个 TestClass 通过 reload(container_center_api) 创建干净的测试环境.
"""
import json
import os
import sys
import types
from unittest.mock import MagicMock, PropertyMock, patch, ANY
from datetime import datetime, timedelta

import pytest
from flask import Flask

# ── 模块级 Mock 策略 ──────────────────────────────────────────

_PATCHED_MODULES = {
    'container_dashboard': types.ModuleType('container_dashboard'),
    'container_dashboard.container_dashboard_bp': MagicMock(),
    'inventory_web': types.ModuleType('inventory_web'),
    'container_center.storage': types.ModuleType('container_center.storage'),
    'container_center.api': types.ModuleType('container_center.api'),
    'container_center': types.ModuleType('container_center'),
    'container_center_v5': types.ModuleType('container_center_v5'),
    'integration.desktop_callback': types.ModuleType('integration.desktop_callback'),
    'modules.api_signature': types.ModuleType('modules.api_signature'),
    'modules.health_checker': types.ModuleType('modules.health_checker'),
    'modules.deployment_manager': types.ModuleType('modules.deployment_manager'),
    'modules.enhanced_audit_logger': types.ModuleType('modules.enhanced_audit_logger'),
    'modules.enhanced_backup': types.ModuleType('modules.enhanced_backup'),
    'core.config': types.ModuleType('core.config'),
    'data_integrity': types.ModuleType('data_integrity'),
    'data_boundary': types.ModuleType('data_boundary'),
    'clock_sync': types.ModuleType('clock_sync'),
    'container_config': types.ModuleType('container_config'),
}


def _setup_base_mocks():
    """在 import container_center_api 之前安装所有必要的 sys.modules patch."""
    for mod_name, mod in _PATCHED_MODULES.items():
        sys.modules[mod_name] = mod

    # core.config 提供 DB_PATHS, Config, BASE_DIR
    cfg_mod = sys.modules['core.config']
    cfg_mod.DB_PATHS = {'enterprise_structure': '/tmp/test_enterprise.json'}
    cfg_mod.Config = MagicMock()
    cfg_mod.Config.LOG_DIR = '/tmp'
    cfg_mod.Config.LOG_MAX_BYTES = 1024 * 1024
    cfg_mod.Config.LOG_FORMAT = '%(message)s'
    cfg_mod.Config.LOG_DATE_FORMAT = '%H:%M:%S'
    cfg_mod.Config.LOG_LEVEL = 'WARNING'
    cfg_mod.Config.FLASK_HOST = '0.0.0.0'
    cfg_mod.Config.CONTAINER_CENTER_PORT = 5002
    cfg_mod.Config.DATA_RETENTION_DAYS = 90
    cfg_mod.Config.get_process_code = lambda x: x
    cfg_mod.BASE_DIR = '/tmp'

    # container_center_v5 — ContainerCenter, DataStatus
    cc5 = sys.modules['container_center_v5']

    class FakeDataStatus:
        PENDING = 'pending'
        COMPLETED = 'completed'
        ACKNOWLEDGED = 'acknowledged'

    cc5.DataStatus = FakeDataStatus
    cc5.ContainerCenter = MagicMock

    # data_integrity
    di_mod = sys.modules['data_integrity']
    di_mod.DataIntegrity = MagicMock()
    di_mod.DataIntegrity.calculate_hash = staticmethod(lambda d: 'mockchecksum')

    # data_boundary — DataBoundary, data_boundary
    db_mod = sys.modules['data_boundary']
    db_mod.DataBoundary = MagicMock
    mock_db = MagicMock()
    mock_db.validate_report_request.return_value = (True, None)
    db_mod.data_boundary = mock_db
    db_mod.DataBoundary = MagicMock

    # clock_sync — ClockSync, clock_sync
    cs_mod = sys.modules['clock_sync']
    cs_mod.ClockSync = MagicMock
    cs_mod.clock_sync = MagicMock()

    # container_dashboard
    cd_mod = sys.modules['container_dashboard']
    cd_mod.container_dashboard_bp = MagicMock()

    # inventory_web
    iw_mod = sys.modules['inventory_web']
    iw_mod.web_bp = MagicMock()

    # container_center.api — create_container_api_bp, init_api_bp
    cc_api_mod = sys.modules['container_center.api']
    cc_api_mod.create_container_api_bp = MagicMock(return_value=MagicMock())
    cc_api_mod.init_api_bp = MagicMock()

    # container_center.storage — DocumentStore, IndexStore, ConfigStore, AlertStore
    cc_storage_mod = sys.modules['container_center.storage']
    cc_storage_mod.DocumentStore = MagicMock
    cc_storage_mod.IndexStore = MagicMock
    cc_storage_mod.ConfigStore = MagicMock
    cc_storage_mod.AlertStore = MagicMock

    # container_config
    ccfg_mod = sys.modules['container_config']
    ccfg_mod.container_config = MagicMock()
    ccfg_mod.container_config.get_outsourc_config = MagicMock(return_value=MagicMock())
    mock_outsource_cfg = MagicMock()
    mock_outsource_cfg.enabled = True
    mock_outsource_cfg.default_operator_id = ''
    mock_outsource_cfg.remind_days = 7
    mock_outsource_cfg.overdue_remind_times = 3
    ccfg_mod.container_config.get_outsourc_config.return_value = mock_outsource_cfg


def _setup_storage_mock(mock_storage):
    """给 mock storage 挂上 process_record / package 常用方法."""
    # process records
    mock_storage.get_process_records = MagicMock(return_value=[])
    mock_storage.get_process_record = MagicMock(return_value=None)
    mock_storage.save_process_record = MagicMock(return_value=None)
    mock_storage.delete_process_record = MagicMock(return_value=None)
    mock_storage.get_process_record_by_order = MagicMock(return_value=None)
    mock_storage.get_all_process_records = MagicMock(return_value=[])
    mock_storage.update_process_record_status = MagicMock(return_value=None)
    mock_storage.update_process_record_step = MagicMock(return_value=None)
    mock_storage.update_process_record_task_count = MagicMock(return_value=None)
    mock_storage.assign_template_to_process = MagicMock(return_value=None)

    # packages / tasks
    mock_storage.get_packages = MagicMock(return_value=[])
    mock_storage.get_package = MagicMock(return_value=None)
    mock_storage.insert = MagicMock()
    mock_storage.execute = MagicMock()

    # enterprise structure
    mock_storage.get_enterprise_structure = MagicMock(return_value=None)
    mock_storage.save_enterprise_structure = MagicMock()

    # sub steps
    mock_storage.get_sub_steps_by_process = MagicMock(return_value=[])
    mock_storage.fetch_one = MagicMock(return_value=None)
    mock_storage.fetch_all = MagicMock(return_value=[])

    return mock_storage


def _reload_module():
    """重新加载 container_center_api, 返回模块引用."""
    if 'container_center_api' in sys.modules:
        del sys.modules['container_center_api']
    import container_center_api
    return container_center_api


def _make_mock_container_center():
    """构建 mock ContainerCenter 实例."""
    cc = MagicMock()
    _setup_storage_mock(cc.storage)
    cc.get_pool_status = MagicMock(return_value={
        'total_packages': 0, 'overdue': 0, 'total': 0
    })
    cc.collect_report = MagicMock(return_value=MagicMock())
    cc.distributor = MagicMock()
    cc.distributor.distribute = MagicMock()
    cc.collector = MagicMock()
    cc.acknowledge_task = MagicMock(return_value={'success': True})
    cc.get_unacknowledged_tasks = MagicMock(return_value=[])
    cc.receive_return = MagicMock(return_value={'success': True})
    cc.add_sub_step = MagicMock(return_value=True)
    cc.get_sub_steps = MagicMock(return_value=[])
    cc.get_sub_step_summary = MagicMock(return_value={})
    return cc


# ══════════════════════════════════════════════════════════════
# Test: 认证模块
# ══════════════════════════════════════════════════════════════

class TestAuth:
    """认证模块 /api/auth/* — login + verify"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        # 替换 after_request 处理器，避免 Content-Type 被覆盖为 text/html
        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', [
                 {'operator_id': 'OP001', 'name': '张三', 'role': '操作员',
                  'team_name': '编织组', 'wechat': 'OP001', 'enabled': True},
             ]), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_login_success(self, setup):
        client, _ = setup
        resp = client.post('/api/auth/login', json={'operator_id': 'OP001'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'token' in result['data']
        assert result['data']['operator']['id'] == 'OP001'

    def test_login_operator_not_found(self, setup):
        client, _ = setup
        resp = client.post('/api/auth/login', json={'operator_id': 'OP999'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002
        assert '操作员不存在' in result['message']

    def test_login_missing_operator_id(self, setup):
        client, _ = setup
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_login_invalid_json(self, setup):
        client, _ = setup
        resp = client.post('/api/auth/login', data='not json', content_type='application/json')
        assert resp.status_code in (200, 400)

    def test_verify_valid_token(self, setup):
        client, mod = setup
        login_resp = client.post('/api/auth/login', json={'operator_id': 'OP001'})
        token = login_resp.get_json()['data']['token']
        resp = client.get('/api/auth/verify', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['valid'] is True

    def test_verify_no_token(self, setup):
        client, _ = setup
        resp = client.get('/api/auth/verify')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_verify_invalid_token(self, setup):
        client, _ = setup
        resp = client.get('/api/auth/verify', headers={'Authorization': 'Bearer invalidtoken123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_verify_expired_token(self, setup):
        client, mod = setup
        import jwt
        expired_payload = {
            'operator_id': 'OP001', 'name': '张三',
            'role': '操作员', 'exp': datetime.utcnow() - timedelta(hours=1)
        }
        token = jwt.encode(expired_payload, 'test-secret-key', algorithm='HS256')
        resp = client.get('/api/auth/verify', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002


# ══════════════════════════════════════════════════════════════
# Test: 流程记录 CRUD
# ══════════════════════════════════════════════════════════════

class TestProcesses:
    """流程记录 /api/processes/* — CRUD 全路径"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_get_processes_empty(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_records.return_value = []
        resp = client.get('/api/processes')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_get_processes_with_data(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_records.return_value = [
            {'id': 'rec001', 'order_no': 'ORD001', 'process_type': 'production',
             'status': 'created', 'quantity': 100}
        ]
        resp = client.get('/api/processes')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']) == 1

    def test_create_process_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.save_process_record = MagicMock()
        resp = client.post('/api/processes', json={
            'order_no': 'ORD001', 'product_name': '不锈钢网带',
            'quantity': 100, 'customer_name': '测试客户'
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['order_no'] == 'ORD001'

    def test_create_process_missing_order_no(self, setup):
        client, _, _ = setup
        resp = client.post('/api/processes', json={
            'product_name': '不锈钢网带'
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1001
        assert '缺少order_no' in result['message']

    def test_get_process_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001', 'status': 'created'
        }
        resp = client.get('/api/processes/rec001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['id'] == 'rec001'

    def test_get_process_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = None
        resp = client.get('/api/processes/rec999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404
        assert '不存在' in result['message']

    def test_update_process_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001', 'status': 'created',
            'quantity': 100
        }
        resp = client.put('/api/processes/rec001', json={
            'quantity': 200, 'status': 'in_production'
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['quantity'] == 200
        assert result['data']['status'] == 'in_production'

    def test_update_process_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = None
        resp = client.put('/api/processes/rec999', json={'quantity': 200})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_update_process_status_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001', 'status': 'created'
        }
        resp = client.put('/api/processes/rec001/status', json={
            'status': 'completed', 'completed_at': '2026-06-03T10:00:00'
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['status'] == 'completed'

    def test_update_process_status_missing(self, setup):
        client, _, _ = setup
        resp = client.put('/api/processes/rec001/status', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1001
        assert '缺少status' in result['message']

    def test_assign_template_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001'
        }
        resp = client.put('/api/processes/rec001/template', json={'template_id': 'tmpl01'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['template_id'] == 'tmpl01'

    def test_assign_template_missing(self, setup):
        client, _, _ = setup
        resp = client.put('/api/processes/rec001/template', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1001

    def test_assign_template_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = None
        resp = client.put('/api/processes/rec999/template', json={'template_id': 'tmpl01'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_update_step_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001', 'current_step': 0
        }
        resp = client.put('/api/processes/rec001/step', json={'current_step': 1})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['current_step'] == 1

    def test_update_step_missing(self, setup):
        client, _, _ = setup
        resp = client.put('/api/processes/rec001/step', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1001

    def test_update_tasks_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001'
        }
        resp = client.put('/api/processes/rec001/tasks', json={
            'task_count': 5, 'completed_task_count': 2
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['task_count'] == 5

    def test_delete_process(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = {
            'id': 'rec001', 'order_no': 'ORD001'
        }
        resp = client.delete('/api/processes/rec001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_delete_process_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record.return_value = None
        resp = client.delete('/api/processes/rec999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0  # delete always returns success

    def test_get_process_by_order_direct(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record_by_order.return_value = {
            'id': 'rec001', 'order_no': 'ORD001'
        }
        resp = client.get('/api/processes/by-order/ORD001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['order_no'] == 'ORD001'

    def test_get_process_by_order_fallback(self, setup):
        """精确匹配失败时走全表扫描兜底."""
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record_by_order.return_value = None
        mock_cc.storage.get_all_process_records.return_value = [
            {'id': 'rec001', 'order_no': 'ORD001'}
        ]
        resp = client.get('/api/processes/by-order/ORD001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['order_no'] == 'ORD001'

    def test_get_process_by_order_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_record_by_order.return_value = None
        mock_cc.storage.get_all_process_records.return_value = []
        resp = client.get('/api/processes/by-order/ORD999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404


# ══════════════════════════════════════════════════════════════
# Test: 任务管理
# ══════════════════════════════════════════════════════════════

class TestTasks:
    """任务管理 /api/tasks/* — 列表、详情、签收、完成"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        mod = _reload_module()
        mock_cc = _make_mock_container_center()
        mock_cc.storage.get_packages = MagicMock(return_value=[
            {'id': 'pkg001', 'title': '测试任务', 'status': 'pending',
             'data_type': 'production', 'related_order': 'ORD001',
             'content': {}, 'target_operator': 'OP001'}
        ])

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', [
                 {'operator_id': 'OP001', 'name': '张三', 'role': '操作员',
                  'team_name': '编织组', 'wechat': 'OP001', 'enabled': True},
             ]), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, 'global_data_boundary', MagicMock()):
            mod.global_data_boundary.validate_report_request.return_value = (True, None)
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def _login_token(self, client, operator_id='OP001'):
        resp = client.post('/api/auth/login', json={'operator_id': operator_id})
        return resp.get_json()['data']['token']

    def test_get_tasks_scan_report(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        resp = client.get('/api/tasks?page_route=scan_report',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'tasks' in result['data']

    def test_get_tasks_unknown_route(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        resp = client.get('/api/tasks?page_route=unknown',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1004

    def test_get_tasks_no_auth(self, setup):
        client, _, _ = setup
        resp = client.get('/api/tasks')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_get_task_found(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mock_cc.storage.get_package.return_value = {
            'id': 'pkg001', 'title': '测试任务', 'status': 'pending'
        }
        resp = client.get('/api/tasks/pkg001',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_get_task_not_found(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mock_cc.storage.get_package.return_value = None
        resp = client.get('/api/tasks/pkg999',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_acknowledge_success(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mock_cc.acknowledge_task.return_value = {'success': True}
        resp = client.post('/api/tasks/pkg001/acknowledge',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '已确认' in result['message']

    def test_acknowledge_fail(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mock_cc.acknowledge_task.return_value = {
            'success': False, 'message': '任务已被其他人签收'
        }
        resp = client.post('/api/tasks/pkg001/acknowledge',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400
        assert '已被其他人' in result['message']

    def test_acknowledge_no_auth(self, setup):
        client, _, _ = setup
        resp = client.post('/api/tasks/pkg001/acknowledge')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_unacknowledged_tasks(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mock_cc.get_unacknowledged_tasks.return_value = [
            {'id': 'pkg001', 'title': '未确认任务'}
        ]
        resp = client.get('/api/tasks/unacknowledged',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['total'] == 1

    def test_unacknowledged_tasks_no_auth(self, setup):
        client, _, _ = setup
        resp = client.get('/api/tasks/unacknowledged')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_complete_task_success(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mock_cc.receive_return.return_value = {'success': True}
        resp = client.post('/api/tasks/pkg001/complete',
                           json={'return_data': {'quantity': 50, 'order_no': 'ORD001'}},
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_complete_task_no_auth(self, setup):
        client, _, _ = setup
        resp = client.post('/api/tasks/pkg001/complete', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1002

    def test_complete_task_boundary_fail(self, setup):
        client, mod, mock_cc = setup
        token = self._login_token(client)
        mod.global_data_boundary.validate_report_request.return_value = (False, '数量超出限制')
        resp = client.post('/api/tasks/pkg001/complete',
                           json={'return_data': {'quantity': 999999, 'order_no': 'ORD001'}},
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400


# ══════════════════════════════════════════════════════════════
# Test: 派工
# ══════════════════════════════════════════════════════════════

class TestDispatch:
    """派工 /api/dispatch + /api/wechat/dispatch"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        # 阻止 dispatch 尝试真正发 HTTP 请求
        os.environ['DISPATCH_CENTER_URL'] = ''
        mod = _reload_module()
        mock_cc = _make_mock_container_center()
        mock_cc.collect_report.return_value = MagicMock()
        mock_collected = MagicMock()
        mock_collected.id = 'pkg-dispatch-001'
        mock_collected.content = {}
        mock_collected.to_dict.return_value = {
            'id': 'pkg-dispatch-001', 'content': {}
        }
        mock_cc.collect_report.return_value = mock_collected

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', [
                 {'operator_id': 'OP001', 'name': '张三', 'role': '操作员',
                  'team_name': '编织组', 'wechat': 'OP001', 'enabled': True},
             ]), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, 'REPORT_SYSTEM_WEBHOOK_URL', ''), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_dispatch_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.return_value = None  # no duplicate
        resp = client.post('/api/dispatch', json={
            'operator_id': 'OP001', 'order_no': 'ORD001',
            'process': '裁剪', 'quantity': 100
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_dispatch_missing_operator(self, setup):
        client, _, _ = setup
        resp = client.post('/api/dispatch', json={
            'order_no': 'ORD001', 'process': '裁剪'
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1001

    def test_dispatch_duplicate(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.return_value = {'id': 'existing-pkg'}
        resp = client.post('/api/dispatch', json={
            'operator_id': 'OP001', 'order_no': 'ORD001',
            'process': '裁剪', 'quantity': 100
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data'].get('duplicate') is True

    def test_wechat_dispatch_wrapper(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.return_value = None
        resp = client.post('/api/wechat/dispatch', json={
            'task_data': {'order_no': 'ORD001', 'process': '裁剪',
                          'quantity': 50},
            'operator_id': 'OP001'
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0


# ══════════════════════════════════════════════════════════════
# Test: 排产发布
# ══════════════════════════════════════════════════════════════

class TestSchedule:
    """排产发布 /api/schedule/publish — 接收主软件排产数据"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        # 阻止 schedule_publish 内尝试真正的 HTTP 请求到调度中心
        os.environ['DISPATCH_CENTER_URL'] = 'http://localhost:1'

        mod = _reload_module()
        mock_cc = _make_mock_container_center()
        # fetch_one 用于去重检查，返回 None 表示新工单
        mock_cc.storage.fetch_one = MagicMock(return_value=None)
        mock_cc.storage.save_process_record = MagicMock()
        mock_cc.storage.insert = MagicMock()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()), \
             patch.object(mod, '_v4_doc_store', MagicMock()):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_schedule_publish_success(self, setup):
        """正常发布排产（production 流程）。"""
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.side_effect = [None, None]  # no duplicate

        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD001',
            'product_type': '不锈钢网带',
            'quantity': 200,
            'customer_name': '某工厂',
            'delivery_date': '2026-07-01',
            'priority': 'high',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0, f"expected 0 got {result}"
        assert result['data']['order_no'] == 'ORD001'
        assert 'record_id' in result['data']

    def test_schedule_publish_no_order_no(self, setup):
        """缺少 order_no 时返回 1001。"""
        client, _, _ = setup
        resp = client.post('/api/schedule/publish', json={
            'product_type': '不锈钢网带', 'quantity': 100
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1001

    def test_schedule_publish_material_purchase(self, setup):
        """material_purchase 流程类型。"""
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.side_effect = [None, None]
        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD-PUR-001',
            'flow_type': 'material_purchase',
            'product_type': '钢丝', 'quantity': 500,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_schedule_publish_quality_flow(self, setup):
        """quality 流程类型。"""
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.side_effect = [None, None]
        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD-QC-001',
            'flow_type': 'quality',
            'product_type': '网带检验', 'quantity': 50,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_schedule_publish_outsource_flow(self, setup):
        """outsource 流程类型（外协）。"""
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.side_effect = [None, None]
        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD-OUT-001',
            'flow_type': 'outsource',
            'product_type': '外协加工', 'quantity': 100,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_schedule_publish_repair_flow(self, setup):
        """repair 流程类型（设备报修）。"""
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.side_effect = [None, None]
        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD-REP-001',
            'flow_type': 'repair',
            'product_type': '设备维修', 'quantity': 1,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_schedule_publish_duplicate_pkg(self, setup):
        """当 data_packages 已存在时返回 duplicate。"""
        client, _, mock_cc = setup
        # 第一个 fetch_one 返回 None(process无重复)，第二个返回记录(pkg有重复)
        existing_pkg = {'id': 'pkg-existing', 'related_order': 'ORD001',
                        'related_process': ''}
        mock_cc.storage.fetch_one.side_effect = [None, existing_pkg]
        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD001', 'product_type': '网带', 'quantity': 100,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data'].get('duplicate') is True

    def test_schedule_publish_product_type_mapping(self, setup):
        """product_type_id 未指定 flow_type 时查 product_flow_map 兜底。"""
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.side_effect = [
            {'flow_type': 'quality'},  # product_flow_map 查询返回 quality
            None,                      # process 去重检查
            None,                      # pkg 去重检查
        ]
        resp = client.post('/api/schedule/publish', json={
            'order_no': 'ORD-MAP-001',
            'product_type_id': 3,
            'product_type': '质检产品', 'quantity': 80,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0


# ══════════════════════════════════════════════════════════════
# Test: 内部发布
# ══════════════════════════════════════════════════════════════

class TestInternalPublish:
    """内部发布 /api/internal/publish — API Key / 完整性校验 / 分类发布"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        os.environ['CONTAINER_API_KEY'] = 'test-api-key-123'
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        mock_collected = MagicMock()
        mock_collected.id = 'task-internal-001'
        mock_cc.collector.collect = MagicMock(return_value=mock_collected)
        mock_cc.distributor.distribute = MagicMock()
        mock_cc.storage.get_process_records_by_work_order = MagicMock(return_value=[])

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, 'global_data_boundary', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()):
            mod.global_data_boundary.validate_report_request.return_value = (True, None)
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_publish_via_api_key(self, setup):
        """使用 X-API-Key 认证发布任务。"""
        client, mod, mock_cc = setup
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report',
            'title': '质检报告',
            'content': {'quantity': 50, 'quality': '合格'},
            'operator_id': 'OP001',
            'related_order': 'ORD001',
            'priority': 'high',
        }, headers={'X-API-Key': 'test-api-key-123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'task_id' in result['data']

    def test_publish_with_checksum(self, setup):
        """带 _checksum 完整性校验发布。"""
        client, mod, mock_cc = setup
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report',
            'title': '带校验任务',
            'content': {'quantity': 30},
            'operator_id': 'OP001',
            '_checksum': 'mockchecksum',  # data_integrity mock 返回固定值
        }, headers={'X-API-Key': 'test-api-key-123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_publish_wrong_checksum(self, setup):
        """_checksum 不匹配时返回 401。"""
        client, mod, mock_cc = setup
        # DataIntegrity.calculate_hash 返回 'mockchecksum'，传入不匹配的值
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report', 'title': '校验失败',
            'content': {'quantity': 10},
            '_checksum': 'WRONGCHECKSUM',
        }, headers={'X-API-Key': 'test-api-key-123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 401
        assert '数据完整性校验失败' in result['message']

    def test_publish_no_api_key(self, setup):
        """缺少 API Key 时仍应正常处理（降级行为）。"""
        client, mod, mock_cc = setup
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report', 'title': '无Key发布',
            'content': {}, 'operator_id': 'OP001',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_publish_boundary_fail(self, setup):
        """数据边界校验失败返回 400。"""
        client, mod, mock_cc = setup
        mod.global_data_boundary.validate_report_request.return_value = (False, '数量超出配额')
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report', 'title': '超量',
            'content': {'quantity': 999999},
        }, headers={'X-API-Key': 'test-api-key-123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400
        assert '数量超出' in result['message']

    def test_publish_from_order_management_no_operator(self, setup):
        """来自主软件_订单管理但未指定操作员时跳过分发（不报错）。"""
        client, mod, mock_cc = setup
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report', 'title': '订单任务',
            'content': {'quantity': 20},
            'source': '主软件_订单管理',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        # distributor.distribute 应未被调用
        mock_cc.distributor.distribute.assert_not_called()

    def test_publish_quantity_fallback(self, setup):
        """content 缺少 quantity 时从订单查询兜底。"""
        client, mod, mock_cc = setup
        mock_cc.storage.get_process_records_by_work_order = MagicMock(return_value=[
            {'quantity': 100, 'planned_qty': 100}
        ])
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report', 'title': '兜底数量',
            'content': {}, 'related_order': 'ORD001',
            'operator_id': 'OP001',
        }, headers={'X-API-Key': 'test-api-key-123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_publish_without_operator_no_distribute(self, setup):
        """指定了 API Key 但未传 operator_id 时不触发 distribute。"""
        client, mod, mock_cc = setup
        resp = client.post('/api/internal/publish', json={
            'task_type': 'report', 'title': '无人任务',
            'content': {'quantity': 10},
        }, headers={'X-API-Key': 'test-api-key-123'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        mock_cc.distributor.distribute.assert_not_called()


# ══════════════════════════════════════════════════════════════
# Test: 内部配置管理
# ══════════════════════════════════════════════════════════════

class TestInternalConfig:
    """内部配置管理 /api/internal/config/* — 部署、版本列表、回滚"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        # _v4_doc_store 用于 _load_config_versions / _save_config_versions
        mock_doc_store = MagicMock()
        mock_doc_store.get.return_value = None  # 首次返回 None（没有存储的配置）

        mock_cc.storage.save_process_record = MagicMock()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'SECRET_KEY', 'test-secret-key'), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()), \
             patch.object(mod, '_v4_doc_store', mock_doc_store):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc, mock_doc_store
        mod.app.after_request_funcs[None] = _orig_after_request

    def _deploy(self, client, config_name='test_config', config_data=None):
        """helper: 部署一条配置。"""
        if config_data is None:
            config_data = {'key1': 'value1', 'timeout': 30}
        return client.post('/api/internal/config/deploy', json={
            'config_name': config_name,
            'config_data': config_data,
        })

    def test_deploy_config_success(self, setup):
        """部署新配置返回 version 信息。"""
        client, mod, mock_cc, mock_doc_store = setup
        mock_doc_store.get.return_value = None
        resp = self._deploy(client)
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['config_name'] == 'test_config'
        assert 'version' in result['data']
        assert len(result['data']['version']) == 14  # %Y%m%d%H%M%S

    def test_deploy_config_missing_name(self, setup):
        """缺少 config_name 时返回 400。"""
        client, _, _, _ = setup
        resp = client.post('/api/internal/config/deploy', json={
            'config_data': {'k': 'v'},
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400
        assert '缺少 config_name' in result['message']

    def test_deploy_config_missing_data(self, setup):
        """缺少 config_data 时返回 400。"""
        client, _, _, _ = setup
        resp = client.post('/api/internal/config/deploy', json={
            'config_name': 'my_config',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400

    def test_get_config_versions_empty(self, setup):
        """获取不存在的配置版本列表返回空数组。"""
        client, _, _, mock_doc_store = setup
        mock_doc_store.get.return_value = None
        resp = client.get('/api/internal/config/versions/nonexistent_config')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['config_name'] == 'nonexistent_config'
        assert result['data']['total'] == 0
        assert result['data']['versions'] == []

    def test_get_config_versions_with_data(self, setup):
        """获取已有版本的配置列表。"""
        client, _, _, mock_doc_store = setup
        mock_doc_store.get.return_value = {
            'doc_data': {
                'my_config': [
                    {'version': '20260603120000', 'config_name': 'my_config',
                     'config_data': {'k': 'v1'}},
                    {'version': '20260603130000', 'config_name': 'my_config',
                     'config_data': {'k': 'v2'}},
                ]
            }
        }
        resp = client.get('/api/internal/config/versions/my_config')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['total'] == 2
        assert len(result['data']['versions']) == 2

    def test_deploy_then_get_versions(self, setup):
        """部署后版本列表中应多出一条。"""
        client, mod, mock_cc, mock_doc_store = setup
        # 首次 get 返回 None → deploy 走 create 分支
        mock_doc_store.get.return_value = None
        resp_deploy = self._deploy(client, 'config_a', {'enable': True})
        assert resp_deploy.status_code == 200

        # 第二次 get 模拟有数据
        mock_doc_store.get.return_value = {
            'doc_data': {
                'config_a': [
                    {'version': resp_deploy.get_json()['data']['version'],
                     'config_name': 'config_a',
                     'config_data': {'enable': True}},
                ]
            }
        }
        resp_versions = client.get('/api/internal/config/versions/config_a')
        assert resp_versions.status_code == 200
        result = resp_versions.get_json()
        assert result['data']['total'] == 1

    def test_rollback_success(self, setup):
        """回滚到指定版本。"""
        client, _, _, mock_doc_store = setup
        mock_doc_store.get.return_value = {
            'doc_data': {
                'my_config': [
                    {'version': 'v1', 'config_name': 'my_config',
                     'config_data': {'key': 'old_value'}},
                    {'version': 'v2', 'config_name': 'my_config',
                     'config_data': {'key': 'new_value'}},
                ]
            }
        }
        resp = client.post('/api/internal/config/rollback', json={
            'config_name': 'my_config',
            'version': 'v1',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['version'] == 'v1'
        assert result['data']['config_data']['key'] == 'old_value'

    def test_rollback_missing_params(self, setup):
        """缺少参数时返回 400。"""
        client, _, _, _ = setup
        resp = client.post('/api/internal/config/rollback', json={
            'config_name': 'my_config',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400

    def test_rollback_version_not_found(self, setup):
        """目标版本不存在时返回 404。"""
        client, _, _, mock_doc_store = setup
        mock_doc_store.get.return_value = {
            'doc_data': {
                'my_config': [
                    {'version': 'v1', 'config_name': 'my_config', 'config_data': {}},
                ]
            }
        }
        resp = client.post('/api/internal/config/rollback', json={
            'config_name': 'my_config',
            'version': 'v999',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404
        assert '不存在' in result['message']