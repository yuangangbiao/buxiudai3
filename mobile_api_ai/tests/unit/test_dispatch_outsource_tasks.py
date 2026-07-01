# -*- coding: utf-8 -*-
"""
P2 bug 修复验证: 调度中心订单模块加载外协任务

Bug: dispatch_center/_core.py 中 list_processes / workorder 详情接口
     的加载逻辑只识别 report/material/quality/repair 4 种 data_type,
     缺少 outsource,导致 data_type='outsource' 的任务被静默丢弃。

修复后:
- list_processes: p['outsource_tasks'] 应包含所有相关 outsource 包
- workorder 详情: outsource_tasks 应包含,不再落入 other_tasks
"""
import pytest
from unittest.mock import MagicMock, patch


def _make_pkg(data_type, related_order, **kwargs):
    """构造 data_package 字典"""
    pkg = {
        'id': f'pkg-{data_type}-{related_order}',
        'data_type': data_type,
        'related_order': related_order,
        'related_process': kwargs.get('related_process', f'{data_type}流程'),
        'status': kwargs.get('status', 'pending'),
        'content': kwargs.get('content', {}),
        'created_at': kwargs.get('created_at', '2026-06-10T08:00:00'),
        'updated_at': kwargs.get('updated_at', '2026-06-10T08:00:00'),
    }
    pkg.update(kwargs)
    return pkg


SAMPLE_PACKAGES = [
    _make_pkg('report', 'ORD-TEST-001', status='in_progress',
              content={'completed_qty': 5, 'quantity': 10, 'status': '生产中',
                       'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
    _make_pkg('material', 'ORD-TEST-001', status='pending',
              content={'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
    _make_pkg('material_purchase', 'ORD-TEST-001', status='pending',
              content={'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
    _make_pkg('purchase', 'ORD-TEST-001', status='pending',
              content={'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
    _make_pkg('quality', 'ORD-TEST-001', status='pending',
              content={'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
    _make_pkg('repair', 'ORD-TEST-001', status='pending',
              content={'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
    _make_pkg('outsource', 'ORD-TEST-001', status='pending',
              content={'order_no': 'ORD-TEST-001', 'related_order': 'ORD-TEST-001'}),
]

SAMPLE_PROCESSES = [{
    'id': 'p1', 'order_no': 'ORD-TEST-001',
    'flow_type': 'production', 'current_step': 1,
    'product_name': '不锈钢网带', 'quantity': 10, 'unit': '米',
    'customer_name': '客户A', 'delivery_date': '2026-07-01',
    'status': 'in_production', 'steps': [], 'created_at': '', 'updated_at': '',
}]


@pytest.fixture
def flask_app():
    """提供 Flask app context,让 request/Blueprint 可工作"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    with app.test_request_context('/'):
        yield app


@pytest.fixture
def mock_dispatch_deps(flask_app):
    """mock 依赖项:_core 顶层 import 时的 DispatchContext + 缓存"""
    from mobile_api_ai.dispatch_center import _core as dc_core

    mock_cc = MagicMock()
    mock_cc.storage.get_all_process_records.return_value = []
    mock_cc.storage.get_packages.return_value = SAMPLE_PACKAGES
    mock_cc.get_sub_step_summary.return_value = {'completed_qty': 0, 'order_qty': 0, 'shipped_qty': 0}

    mock_ctx = MagicMock()
    mock_ctx.get_container_center.return_value = mock_cc
    mock_ctx.get_cached_work_orders.return_value = {
        'items': SAMPLE_PACKAGES, 'data': SAMPLE_PACKAGES, 'total': len(SAMPLE_PACKAGES)
    }
    mock_ctx.invalidate_work_order_cache.return_value = None

    mock_cache = MagicMock()
    mock_cache.get_data.return_value = {
        'processes': SAMPLE_PROCESSES,
        'flow_matching_rules': [],
    }

    patches = [
        patch.object(dc_core, 'DispatchContext', return_value=mock_ctx),
        patch.object(dc_core, '_dispatch_cache', mock_cache),
        patch.object(dc_core, '_get_container_center', return_value=mock_cc),
        patch.object(dc_core, '_get_cached_work_orders',
                     return_value={'items': SAMPLE_PACKAGES, 'data': SAMPLE_PACKAGES}),
        patch.object(dc_core, '_extract_items',
                     side_effect=lambda r: r.get('items', r.get('data', [])) if isinstance(r, dict) else r),
    ]
    for p in patches:
        p.start()
    yield {'ctx': mock_ctx, 'cc': mock_cc, 'cache': mock_cache}
    for p in patches:
        p.stop()


# ───────────────────────── 测试: list_processes 应加载 outsource ─────────────────────────


class TestListProcessesOutsourceTasks:
    """验证 /api/dispatch-center/processes 列表接口能加载 outsource 任务"""

    def test_outsource_tasks_field_initialized(self, mock_dispatch_deps):
        """修复后: p['outsource_tasks'] 字段必须存在"""
        from mobile_api_ai.dispatch_center._core import list_processes
        response = list_processes()
        data = response.get_json()
        assert data['code'] == 0
        assert len(data['data']) == 1
        process = data['data'][0]
        assert 'outsource_tasks' in process, \
            f"必须存在 outsource_tasks 字段,实际字段: {list(process.keys())}"

    def test_outsource_packages_classified_correctly(self, mock_dispatch_deps):
        """修复后: 7 个包分别归入对应列表(物料包含 material/material_purchase/purchase 三种)"""
        from mobile_api_ai.dispatch_center._core import list_processes
        response = list_processes()
        data = response.get_json()
        process = data['data'][0]
        assert len(process['process_tasks']) == 1, f"工序任务数: {len(process['process_tasks'])}"
        assert len(process['material_tasks']) == 3, \
            f"物料任务数(应包含 material/material_purchase/purchase): {len(process['material_tasks'])}"
        assert len(process['quality_tasks']) == 1, f"质检任务数: {len(process['quality_tasks'])}"
        assert len(process['repair_tasks']) == 1, f"维修任务数: {len(process['repair_tasks'])}"
        assert len(process['outsource_tasks']) == 1, \
            f"应有 1 个外协任务(修复后),实际: {len(process.get('outsource_tasks', []))}"

    def test_outsource_task_data_complete(self, mock_dispatch_deps):
        """修复后: outsource 任务的完整数据被保留"""
        from mobile_api_ai.dispatch_center._core import list_processes
        response = list_processes()
        data = response.get_json()
        process = data['data'][0]
        outsource = process['outsource_tasks']
        assert len(outsource) == 1
        assert outsource[0]['data_type'] == 'outsource'
        assert outsource[0]['related_order'] == 'ORD-TEST-001'


# ───────────────────────── 测试: workorder 详情应加载 outsource ─────────────────────────


class TestWorkorderDetailOutsourceTasks:
    """验证 /api/dispatch-center/workorder/<order_no> 详情接口能加载 outsource 任务"""

    def _get_detail_func(self):
        """定位 workorder 详情接口函数"""
        from mobile_api_ai.dispatch_center import _core as dc_core
        for name in dir(dc_core):
            obj = getattr(dc_core, name)
            if callable(obj) and getattr(obj, '__name__', '') == 'workorder_detail':
                return obj
        raise RuntimeError('未找到 workorder_detail 函数')

    def test_outsource_not_in_other_tasks(self, mock_dispatch_deps):
        """修复后: outsource 包不应被归入 other_tasks"""
        detail_func = self._get_detail_func()
        response = detail_func('ORD-TEST-001')
        data = response.get_json()
        assert data['code'] == 0
        result = data['data']
        assert len(result['outsource_tasks']) == 1, \
            f"应有 1 个外协任务,实际: {len(result['outsource_tasks'])}"
        assert len(result['other_tasks']) == 0, \
            f"修复后 other_tasks 应为空(outsource 已被独立分类),实际: {len(result['other_tasks'])}"

    def test_outsource_task_in_correct_list(self, mock_dispatch_deps):
        """修复后: 7 种类型各自归入对应列表(物料包含 material/material_purchase/purchase)"""
        detail_func = self._get_detail_func()
        response = detail_func('ORD-TEST-001')
        data = response.get_json()
        result = data['data']
        assert len(result['material_tasks']) == 3, \
            f"物料任务数(应包含 material/material_purchase/purchase): {len(result['material_tasks'])}"
        assert len(result['process_tasks']) == 1
        assert len(result['quality_tasks']) == 1
        assert len(result['repair_tasks']) == 1
        assert len(result['outsource_tasks']) == 1
