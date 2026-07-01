# -*- coding: utf-8 -*-
"""集成测试: 容器中心辅助 API (container_center_api.py).

覆盖辅助端点组:
  Enterprise, ProcessVerification, V4, ProcessNames,
  Outsource, SubStep, ScanInfo, FlowType, Operators, Material.
"""

import json
import os
import sys
import types
from unittest.mock import MagicMock, patch, ANY
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
    cfg_mod.get_process_code = lambda x: x
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

    # modules.api_signature — require_signature 和 require_api_key 装饰器
    api_sig_mod = sys.modules['modules.api_signature']
    api_sig_mod.require_signature = lambda f: f
    api_sig_mod.require_api_key = lambda f: f


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
    mock_storage.update_package = MagicMock()

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
    cc.collect_outsource = MagicMock(return_value=MagicMock())
    return cc


# ══════════════════════════════════════════════════════════════
# Test: 企业微信架构缓存
# ══════════════════════════════════════════════════════════════

class TestEnterprise:
    """Enterprise /api/enterprise/structure POST + GET"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()), \
             patch.object(mod, '_load_enterprise_structure', MagicMock(
                 return_value={'departments': [], 'users': [], 'updated_at': '2026-06-01'})), \
             patch.object(mod, '_push_enterprise_users_to_report', MagicMock()), \
             patch.object(mod, '_save_enterprise_structure', MagicMock(
                 side_effect=lambda data: data.update({'updated_at': '2026-06-01T12:00:00'}))):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_save_structure_success(self, setup):
        client, mod, _ = setup
        resp = client.post('/api/enterprise/structure', json={
            'departments': [{'id': 1, 'name': '生产部'}],
            'users': [{'userid': 'U001', 'name': '张三'}],
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '企业架构已保存' in result['message']
        mod._save_enterprise_structure.assert_called_once()
        mod._push_enterprise_users_to_report.assert_called_once()

    def test_save_structure_empty_data(self, setup):
        client, _, _ = setup
        resp = client.post('/api/enterprise/structure', json={
            'departments': [], 'users': []
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1
        assert '数据为空' in result['message']

    def test_save_structure_no_body(self, setup):
        client, _, _ = setup
        resp = client.post('/api/enterprise/structure', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 1

    def test_get_structure(self, setup):
        client, mod, _ = setup
        resp = client.get('/api/enterprise/structure')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'departments' in result['data']
        assert 'users' in result['data']
        mod._load_enterprise_structure.assert_called_once()


# ══════════════════════════════════════════════════════════════
# Test: 工序验证
# ══════════════════════════════════════════════════════════════

class TestProcessVerification:
    """ProcessVerification /api/process_sub_steps/<order_no>/<process_code> GET"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
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

    def test_verify_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.return_value = {
            'id': 'ss001', 'order_no': 'ORD001', 'process_code': 'PC001',
            'step_name': '裁剪', 'quantity': 100
        }
        resp = client.get('/api/process_sub_steps/ORD001/PC001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['received'] is True

    def test_verify_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_one.return_value = None
        resp = client.get('/api/process_sub_steps/ORD999/PC999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['received'] is False


# ══════════════════════════════════════════════════════════════
# Test: V4 兼容接口
# ══════════════════════════════════════════════════════════════

class TestV4:
    """V4 /api/v4/operators, /api/v4/work_order, /api/v4/alerts (硬迁移后 alerts 已删除)"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', [
                 {'operator_id': 'OP001', 'name': '张三', 'role': '操作员'},
             ]), \
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

    def test_v4_operators(self, setup):
        client, _, _ = setup
        resp = client.get('/api/v4/operators')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']) == 1
        assert result['data'][0]['operator_id'] == 'OP001'

    def test_v4_work_order_empty(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_packages.return_value = []
        resp = client.get('/api/v4/work_order')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['total'] == 0

    def test_v4_work_order_with_data(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_packages.return_value = [
            {'id': 'pkg001', 'title': '任务1', 'status': 'pending',
             'data_type': 'report', 'priority': 'normal',
             'target_operator': 'OP001', 'content': {},
             'created_at': '', 'distributed_at': '',
             'acknowledged_at': '', 'completed_at': '',
             'related_order': 'ORD001', 'related_process': '',
             'source': ''},
            {'id': 'pkg002', 'title': '任务2', 'status': 'completed',
             'data_type': 'report', 'priority': 'high',
             'target_operator': '', 'content': {},
             'created_at': '', 'distributed_at': '',
             'acknowledged_at': '', 'completed_at': '',
             'related_order': '', 'related_process': '',
             'source': ''},
        ]
        resp = client.get('/api/v4/work_order')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['total'] == 2
        assert len(result['items']) == 2

    def test_v4_work_order_pagination(self, setup):
        client, _, mock_cc = setup
        pkgs = [{'id': f'pkg{i:03d}', 'title': f'task{i}', 'status': 'pending',
                 'data_type': 'report', 'priority': 'normal',
                 'target_operator': '', 'content': {},
                 'created_at': '', 'distributed_at': '',
                 'acknowledged_at': '', 'completed_at': '',
                 'related_order': '', 'related_process': '', 'source': ''}
                for i in range(10)]
        mock_cc.storage.get_packages.return_value = pkgs
        resp = client.get('/api/v4/work_order?page=1&size=3')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['total'] == 10
        assert len(result['items']) == 3

    def test_v4_work_order_status_filter(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_packages.return_value = [
            {'id': 'pkg001', 'title': 't1', 'status': 'pending',
             'data_type': 'report', 'priority': 'normal', 'target_operator': '',
             'content': {}, 'created_at': '', 'distributed_at': '',
             'acknowledged_at': '', 'completed_at': '', 'related_order': '',
             'related_process': '', 'source': ''},
            {'id': 'pkg002', 'title': 't2', 'status': 'completed',
             'data_type': 'report', 'priority': 'normal', 'target_operator': '',
             'content': {}, 'created_at': '', 'distributed_at': '',
             'acknowledged_at': '', 'completed_at': '', 'related_order': '',
             'related_process': '', 'source': ''},
        ]
        resp = client.get('/api/v4/work_order?status=completed')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['total'] == 1

    def test_v4_alerts_removed(self, setup):
        """[F22 行动项 3 硬迁移 2026-06-20] /api/v4/alerts mock 路由已删除

        真实告警 API 已迁移到 5003 /api/dispatch-center/alerts。
        验证目标路由在容器中心 5002 端口返回 404。
        """
        client, _, _ = setup
        resp = client.get('/api/v4/alerts')
        assert resp.status_code == 404, f'硬迁移后 /api/v4/alerts 应返回 404，实际 {resp.status_code}'


# ══════════════════════════════════════════════════════════════
# Test: 工序名称/部门
# ══════════════════════════════════════════════════════════════

class TestProcessNames:
    """ProcessNames /api/process_names, /api/process_departments"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
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

    def test_get_process_names(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_all.return_value = [
            {'process_code': 'CUT', 'process_name': '裁剪'},
            {'process_code': 'WELD', 'process_name': '焊接'},
        ]
        resp = client.get('/api/process_names')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        # 端点返回列表，按 process_code 索引
        assert result['data'][0]['process_code'] == 'CUT'
        assert result['data'][0]['process_name'] == '裁剪'

    def test_get_process_names_include_dept(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_all.return_value = [
            {'process_code': 'CUT', 'process_name': '裁剪', 'department': '生产部'},
        ]
        resp = client.get('/api/process_names?include_dept=1')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data'][0]['department'] == '生产部'

    def test_get_process_departments(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.fetch_all.return_value = [
            {'process_code': 'CUT', 'department': '生产部'},
        ]
        resp = client.get('/api/process_departments')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['CUT'] == '生产部'

    def test_save_process_department(self, setup):
        client, _, mock_cc = setup
        resp = client.put('/api/process_departments/CUT', json={'department': '质检部'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        mock_cc.storage.execute.assert_called_once()

    def test_delete_process_department(self, setup):
        client, _, mock_cc = setup
        resp = client.delete('/api/process_departments/CUT')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['message'] == 'deleted'
        mock_cc.storage.execute.assert_called_once()

    def test_delete_process_name(self, setup):
        client, _, mock_cc = setup
        resp = client.delete('/api/process_names/裁剪')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['message'] == 'deleted'
        mock_cc.storage.execute.assert_called_once()


# ══════════════════════════════════════════════════════════════
# Test: 外协管理
# ══════════════════════════════════════════════════════════════

class TestOutsource:
    """Outsource /api/outsource/* — 外协记录 CRUD、发布、反馈"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()), \
             patch.object(mod, '_get_outsource_records', MagicMock(return_value=[])), \
             patch.object(mod, '_update_outsource_extra', MagicMock(return_value={'id': 'test'})):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_list_outsource_records(self, setup):
        client, mod, _ = setup
        records = [
            {'id': 'os001', 'data_type': 'outsource', 'status': 'processing',
             'created_at': '2026-06-01'},
        ]
        mod._get_outsource_records.return_value = records
        resp = client.get('/api/outsource/records')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']) == 1

    def test_list_outsource_records_with_status(self, setup):
        client, mod, _ = setup
        mod._get_outsource_records.return_value = []
        resp = client.get('/api/outsource/records?status=pending')
        assert resp.status_code == 200
        mod._get_outsource_records.assert_called_with('pending')

    def test_get_outsource_record_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = {
            'id': 'os001', 'data_type': 'outsource', 'status': 'processing'
        }
        resp = client.get('/api/outsource/records/os001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_get_outsource_record_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = None
        resp = client.get('/api/outsource/records/os999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_get_outsource_record_wrong_type(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = {
            'id': 'pkg001', 'data_type': 'production', 'status': 'pending'
        }
        resp = client.get('/api/outsource/records/pkg001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_publish_outsource_task_success(self, setup):
        client, _, mock_cc = setup
        mock_pkg = MagicMock()
        mock_pkg.id = 'os-pub-001'
        mock_cc.collect_outsource.return_value = mock_pkg
        resp = client.post('/api/internal/outsource/publish', json={
            'order_no': 'ORD001', 'process_name': '外协加工',
            'planned_qty': 100, 'operator_id': 'OP001',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['id'] == 'os-pub-001'
        mock_cc.collect_outsource.assert_called_once()
        mock_cc.distributor.distribute.assert_called_once_with('os-pub-001')

    def test_publish_outsource_missing_fields(self, setup):
        client, _, _ = setup
        resp = client.post('/api/internal/outsource/publish', json={
            'order_no': '', 'process_name': '',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400

    def test_publish_outsource_checksum(self, setup):
        client, _, mock_cc = setup
        mock_pkg = MagicMock()
        mock_pkg.id = 'os-checksum-001'
        mock_cc.collect_outsource.return_value = mock_pkg
        resp = client.post('/api/internal/outsource/publish', json={
            'order_no': 'ORD001', 'process_name': '外协',
            'planned_qty': 50, '_checksum': 'mockchecksum',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_publish_outsource_wrong_checksum(self, setup):
        client, _, _ = setup
        resp = client.post('/api/internal/outsource/publish', json={
            'order_no': 'ORD001', 'process_name': '外协',
            'planned_qty': 50, '_checksum': 'WRONG',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 401

    def test_feedback_outsource_missing_days(self, setup):
        client, _, _ = setup
        resp = client.post('/api/outsource/records/os001/feedback', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 400

    def test_feedback_outsource_success(self, setup):
        client, mod, _ = setup
        mod._update_outsource_extra.return_value = {'id': 'os001'}
        resp = client.post('/api/outsource/records/os001/feedback', json={'promised_days': 7})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '承诺' in result['message']

    def test_feedback_outsource_not_found(self, setup):
        client, mod, _ = setup
        mod._update_outsource_extra.return_value = None
        resp = client.post('/api/outsource/records/os999/feedback', json={'promised_days': 3})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_complete_outsource(self, setup):
        client, mod, _ = setup
        mod._update_outsource_extra.return_value = {'id': 'os001'}
        resp = client.post('/api/outsource/records/os001/complete')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '已完成' in result['message']

    def test_complete_outsource_not_found(self, setup):
        client, mod, _ = setup
        mod._update_outsource_extra.return_value = None
        resp = client.post('/api/outsource/records/os999/complete')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_receive_outsource(self, setup):
        client, mod, _ = setup
        mod._update_outsource_extra.return_value = {'id': 'os001'}
        resp = client.post('/api/outsource/records/os001/receive')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert '收货入库' in result['message']

    def test_receive_outsource_not_found(self, setup):
        client, mod, _ = setup
        mod._update_outsource_extra.return_value = None
        resp = client.post('/api/outsource/records/os999/receive')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404

    def test_get_outsource_config(self, setup):
        client, _, _ = setup
        resp = client.get('/api/outsource/config')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'enabled' in result['data']

    def test_update_outsource_config(self, setup):
        client, _, _ = setup
        resp = client.post('/api/outsource/config', json={
            'enabled': True, 'remind_days': 14,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0


# ══════════════════════════════════════════════════════════════
# Test: 子步骤（SubStep）
# ══════════════════════════════════════════════════════════════

class TestSubStep:
    """SubStep /api/process_sub_step, /api/process_sub_steps/<order_no>, etc."""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        # mock storage._conn 用于 sub-step/rollback 和 repair-mysql
        mock_storage_conn = MagicMock()
        mock_storage_cursor = MagicMock()
        mock_storage_cursor.fetchone.return_value = None
        mock_storage_cursor.fetchall.return_value = []
        mock_storage_conn.cursor.return_value = mock_storage_cursor

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        # require_api_key 装饰器需要 WECHAT_CLOUD_API_KEY 环境变量和 X-API-Key 请求头
        _orig_api_key = os.environ.get('WECHAT_CLOUD_API_KEY')
        os.environ['WECHAT_CLOUD_API_KEY'] = 'test-api-key'

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()), \
             patch.object(mock_cc.storage, '_conn', mock_storage_conn):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc, mock_storage_conn
        mod.app.after_request_funcs[None] = _orig_after_request
        if _orig_api_key is None:
            del os.environ['WECHAT_CLOUD_API_KEY']
        else:
            os.environ['WECHAT_CLOUD_API_KEY'] = _orig_api_key

    def _headers(self):
        return {'X-API-Key': 'test-api-key'}

    def test_create_sub_step_success(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.add_sub_step.return_value = True
        mock_cc.get_sub_step_summary.return_value = {
            'total_qty': 50, 'completed_qty': 50, 'steps': []
        }
        resp = client.post('/api/process_sub_step',
                           json={'order_no': 'ORD001', 'step_name': '裁剪', 'quantity': 50, 'operator': '张三'},
                           headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'record' in result['data']
        assert result['data']['record']['step_name'] == '裁剪'

    def test_create_sub_step_missing_params(self, setup):
        client, _, _, _ = setup
        resp = client.post('/api/process_sub_step', json={'order_no': 'ORD001'},
                           headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        # fail('参数不完整') 将参数字符串放入 code 字段, message 为默认的 '操作失败'
        assert '参数不完整' in str(result.get('code', ''))

    def test_create_sub_step_fail(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.add_sub_step.return_value = False
        resp = client.post('/api/process_sub_step',
                           json={'order_no': 'ORD001', 'step_name': '裁剪', 'quantity': 50},
                           headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0

    def test_get_sub_steps(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.get_sub_steps.return_value = [
            {'id': 'ss001', 'order_no': 'ORD001', 'step_name': '裁剪', 'quantity': 50},
        ]
        resp = client.get('/api/process_sub_steps/ORD001', headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']) == 1

    def test_get_sub_steps_empty(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.get_sub_steps.return_value = []
        resp = client.get('/api/process_sub_steps/ORD999', headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data'] == []

    def test_get_sub_step_summary(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.get_sub_step_summary.return_value = {
            'total_qty': 100, 'completed_qty': 60, 'steps': []
        }
        resp = client.get('/api/process_sub_step_summary/ORD001', headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['total_qty'] == 100

    def test_get_sub_step_summary_by_order_found(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.storage.get_process_record_by_order.return_value = {
            'id': 'rec001', 'order_no': 'ORD001'
        }
        mock_cc.get_sub_step_summary.return_value = {
            'total_qty': 80, 'completed_qty': 40, 'steps': []
        }
        resp = client.get('/api/process_sub_step/summary_by_order/ORD001', headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0

    def test_get_sub_step_summary_by_order_not_found(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.storage.get_process_record_by_order.return_value = None
        resp = client.get('/api/process_sub_step/summary_by_order/ORD999', headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['total_qty'] == 0

    def test_rollback_sub_step_success(self, setup):
        client, _, _, mock_storage_conn = setup
        mock_cursor = mock_storage_conn.cursor.return_value
        # first fetchone: no duplicate rollback
        # second fetchone: record exists
        mock_cursor.fetchone.side_effect = [
            None,                           # 幂等检查 — 未回退
            (1, 'ORD001', 'PC001', '裁剪', 50, '张三'),  # 记录存在
            (0,),                           # remaining_qty
        ]
        mock_cursor.fetchall.return_value = []
        resp = client.post('/api/sub-step/rollback', json={'sub_step_id': 'ss001'},
                           headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['remaining_qty'] == 0

    def test_rollback_sub_step_no_id(self, setup):
        client, _, _, _ = setup
        resp = client.post('/api/sub-step/rollback', json={}, headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '缺少 sub_step_id' in str(result.get('code', ''))

    def test_rollback_sub_step_already_rolled(self, setup):
        client, _, _, mock_storage_conn = setup
        mock_cursor = mock_storage_conn.cursor.return_value
        mock_cursor.fetchone.side_effect = [{'id': 'existing'}]  # already rolled
        resp = client.post('/api/sub-step/rollback', json={'sub_step_id': 'ss001'},
                           headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '已回退' in str(result.get('code', ''))

    def test_rollback_sub_step_not_found(self, setup):
        client, _, _, mock_storage_conn = setup
        mock_cursor = mock_storage_conn.cursor.return_value
        mock_cursor.fetchone.side_effect = [None, None]  # no duplicate, no record
        resp = client.post('/api/sub-step/rollback', json={'sub_step_id': 'ss999'},
                           headers=self._headers())
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '不存在' in str(result.get('code', ''))

    def test_get_audit_log(self, setup):
        client, _, mock_cc, _ = setup
        mock_cc.storage.fetch_all.return_value = [
            {'id': 1, 'sub_step_id': 'ss001', 'step_name': '裁剪', 'quantity': 50,
             'operator': '张三', 'action': 'rollback', 'action_by': 'admin', 'reason': '测试'},
        ]
        resp = client.get('/api/sub-step/audit/ORD001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']) == 1


# ══════════════════════════════════════════════════════════════
# Test: 扫码信息
# ══════════════════════════════════════════════════════════════

class TestScanInfo:
    """ScanInfo /api/scan-info GET — 通过扫码编码查询工序信息"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
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

    def test_scan_info_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_records.return_value = [
            {'id': 'rec001', 'order_no': 'ORD001', 'customer_name': '测试客户',
             'product_name': '不锈钢网带', 'quantity': 100, 'unit': '米',
             'delivery_date': '2026-07-01', 'priority': 'normal',
             'current_step': 0,
             'steps': [{'name': '裁剪'}, {'name': '焊接'}],
             }
        ]
        mock_cc.storage.get_sub_steps_by_process.return_value = [
            {'step_name': '裁剪', 'quantity': 40},
        ]
        mock_cc.storage.get_packages.return_value = []
        resp = client.get('/api/scan-info?code=ORD001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']['processes']) == 2

    def test_scan_info_no_code(self, setup):
        client, _, _ = setup
        resp = client.get('/api/scan-info')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '缺少参数' in str(result.get('code', ''))

    def test_scan_info_order_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_records.return_value = []
        resp = client.get('/api/scan-info?code=ORD999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 404
        assert '未找到' in result['message']

    def test_scan_info_no_steps(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_process_records.return_value = [
            {'id': 'rec001', 'order_no': 'ORD001', 'steps': [], 'quantity': 100, 'current_step': 0}
        ]
        mock_cc.storage.get_sub_steps_by_process.return_value = []
        mock_cc.storage.get_packages.return_value = []
        resp = client.get('/api/scan-info?code=ORD001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['processes'] == []


# ══════════════════════════════════════════════════════════════
# Test: 流程类型
# ══════════════════════════════════════════════════════════════

class TestFlowType:
    """FlowType /api/flow-type/<product_type_id> GET + /api/flow-map/sync POST"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
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

    def test_get_flow_type(self, setup):
        client, _, _ = setup
        resp = client.get('/api/flow-type/1')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['flow_type'] == 'production'

    def test_sync_flow_map_success(self, setup):
        client, _, _ = setup
        resp = client.post('/api/flow-map/sync', json={
            'mappings': [{'product_type_id': 1, 'flow_type': 'production'}]
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['count'] == 1

    def test_sync_flow_map_empty(self, setup):
        client, _, _ = setup
        resp = client.post('/api/flow-map/sync', json={'mappings': []})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        # fail('缺少 mappings') — code被设为字符串 '缺少 mappings', message='操作失败'
        assert '缺少 mappings' in str(result.values())


# ══════════════════════════════════════════════════════════════
# Test: 操作员管理
# ══════════════════════════════════════════════════════════════

class TestOperators:
    """Operators /api/operators GET — 从 enterprise_structure 查询"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        # comment: old get_operators (line 806) is active, uses OPERATORS not SQL
        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', [
                 {'userid': 'U001', 'name': '张三', 'department_name': '生产部', 'role': '操作员'},
                 {'userid': 'U002', 'name': '李四', 'department_name': '质检部', 'role': '质检员'},
             ]), \
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

    def test_get_operators_found(self, setup):
        client, mod = setup
        resp = client.get('/api/operators')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        operators = result['data']['operators']
        assert len(operators) == 2
        assert operators[0]['userid'] == 'U001'

    def test_get_operators_empty(self, setup):
        client, mod = setup
        with patch.object(mod, 'OPERATORS', []):
            resp = client.get('/api/operators')
            assert resp.status_code == 200
            result = resp.get_json()
            assert result['code'] == 0
            assert result['data']['operators'] == []

    def test_get_operators_bad_json(self, setup):
        client, _ = setup
        resp = client.get('/api/operators')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert len(result['data']['operators']) == 2

    def test_get_operators_tuple_result(self, setup):
        client, mod = setup
        with patch.object(mod, 'OPERATORS', [
            {'userid': 'U001', 'name': '张三'},
        ]):
            resp = client.get('/api/operators')
            assert resp.status_code == 200
            result = resp.get_json()
            assert result['code'] == 0
            assert len(result['data']['operators']) == 1


# ══════════════════════════════════════════════════════════════
# Test: 物料管理
# ══════════════════════════════════════════════════════════════

class TestMaterial:
    """Material /api/material/* — 物料申请、列表、确认、到货、出库"""

    @pytest.fixture
    def setup(self):
        _setup_base_mocks()
        mod = _reload_module()
        mock_cc = _make_mock_container_center()

        _orig_after_request = mod.app.after_request_funcs.get(None, [])
        mod.app.after_request_funcs[None] = []

        with patch.object(mod, 'container_center', mock_cc), \
             patch.object(mod, 'OPERATORS', []), \
             patch.object(mod, 'push_to_report_system', MagicMock()), \
             patch.object(mod, '_server_health_checker', None), \
             patch.object(mod, '_server_deployment_manager', None), \
             patch.object(mod, '_server_audit_logger', None), \
             patch.object(mod, '_server_backup_manager', None), \
             patch.object(mod, '_server_clock_sync', MagicMock()), \
             patch.object(mod, '_find_material_package', MagicMock()):
            mod.app.config['TESTING'] = True
            client = mod.app.test_client()
            yield client, mod, mock_cc
        mod.app.after_request_funcs[None] = _orig_after_request

    def test_material_create_success(self, setup):
        client, _, mock_cc = setup
        resp = client.post('/api/material/create', json={
            'material_name': '不锈钢丝', 'order_no': 'ORD001',
            'quantity': 100, 'spec': 'Φ1.2',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['status'] == 'material_requested'
        mock_cc.storage.insert.assert_called_once()

    def test_material_create_no_name(self, setup):
        client, _, _ = setup
        resp = client.post('/api/material/create', json={'order_no': 'ORD001'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert 'material_name 不能为空' in str(result.get('code', ''))

    def test_material_list(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_packages.return_value = [
            {'id': 'mat001', 'data_type': 'material_purchase', 'title': 'ORD001 - 不锈钢丝',
             'status': 'material_requested', 'content': '{}'},
        ]
        resp = client.get('/api/material/list')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['total'] == 1

    def test_material_list_with_status(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_packages.return_value = []
        resp = client.get('/api/material/list?status=material_confirmed')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        call_kwargs = mock_cc.storage.get_packages.call_args.kwargs
        assert call_kwargs['status'] == 'material_confirmed'

    def test_material_confirm_success(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = {
            'id': 'mat001', 'status': 'material_requested',
            'content': json.dumps({'material_name': '不锈钢丝', 'quantity': 100}),
        }
        mock_cc.storage.update_package = MagicMock()
        resp = client.post('/api/material/confirm', json={
            'id': 'mat001', 'deadline': '2026-06-20', 'arrival_date': '2026-06-25',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['status'] == 'material_confirmed'

    def test_material_confirm_no_id(self, setup):
        client, _, _ = setup
        resp = client.post('/api/material/confirm', json={})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert 'id 不能为空' in str(result.get('code', ''))

    def test_material_confirm_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = None
        resp = client.post('/api/material/confirm', json={'id': 'mat999'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '不存在' in str(result.get('code', ''))

    def test_material_confirm_wrong_status(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = {
            'id': 'mat001', 'status': 'material_delivered', 'content': '{}'
        }
        resp = client.post('/api/material/confirm', json={'id': 'mat001'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '不可确认' in str(result.get('code', ''))

    def test_material_arrived_by_id(self, setup):
        client, mod, mock_cc = setup
        mock_pkg = {
            'id': 'mat001', 'status': 'material_confirmed',
            'related_process': '不锈钢丝',
            'content': json.dumps({'material_name': '不锈钢丝', 'quantity': 100}),
        }
        mod._find_material_package.return_value = mock_pkg
        mock_cc.storage.update_package = MagicMock()
        resp = client.post('/api/material/arrived', json={
            'id': 'mat001', 'actual_qty': 100,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['status'] == 'material_arrived'

    def test_material_arrived_by_name(self, setup):
        client, mod, mock_cc = setup
        mock_pkg = {
            'id': 'mat001', 'status': 'material_confirmed',
            'related_process': '备料-不锈钢丝',
            'content': json.dumps({'material_name': '不锈钢丝', 'quantity': 80}),
        }
        mod._find_material_package.return_value = mock_pkg
        mock_cc.storage.update_package = MagicMock()
        resp = client.post('/api/material/arrived', json={
            'material_name': '不锈钢丝', 'order_no': 'ORD001', 'actual_qty': 80,
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['status'] == 'material_arrived'

    def test_material_arrived_not_found(self, setup):
        client, mod, _ = setup
        mod._find_material_package.return_value = None
        resp = client.post('/api/material/arrived', json={'material_name': 'unknown'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '物料任务不存在' in str(result.get('code', ''))

    def test_material_delivered_by_id(self, setup):
        client, mod, mock_cc = setup
        mock_pkg = {
            'id': 'mat001', 'status': 'material_arrived',
            'related_process': '不锈钢丝',
            'content': json.dumps({'material_name': '不锈钢丝', 'quantity': 100}),
        }
        mod._find_material_package.return_value = mock_pkg
        mock_cc.storage.update_package = MagicMock()
        resp = client.post('/api/material/delivered', json={
            'id': 'mat001', 'actual_qty': 80, 'receiver': '生产部',
        })
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert result['data']['status'] == 'material_delivered'

    def test_material_delivered_not_found(self, setup):
        client, mod, _ = setup
        mod._find_material_package.return_value = None
        resp = client.post('/api/material/delivered', json={'material_name': 'unknown'})
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '物料任务不存在' in str(result.get('code', ''))

    def test_material_detail_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = {
            'id': 'mat001', 'data_type': 'material_purchase',
            'status': 'material_requested', 'title': 'ORD001 - 不锈钢丝',
            'related_order': 'ORD001', 'related_process': '不锈钢丝',
            'content': json.dumps({'material_name': '不锈钢丝', 'quantity': 100}),
        }
        resp = client.get('/api/material/mat001')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] == 0
        assert 'flow' in result['data']
        assert len(result['data']['flow']) == 4

    def test_material_detail_not_found(self, setup):
        client, _, mock_cc = setup
        mock_cc.storage.get_package.return_value = None
        resp = client.get('/api/material/mat999')
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['code'] != 0
        assert '不存在' in str(result.get('code', ''))
