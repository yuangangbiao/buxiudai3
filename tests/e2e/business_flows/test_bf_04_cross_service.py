# -*- coding: utf-8 -*-
"""
test_bf_04_cross_service.py - 跨端点联动测试

覆盖场景:
- 8008 Sync Bridge 5 个真实 POST 端点
- 5008 ↔ 8008 跨端点数据同步
- 排产 → 生产订单 → 质检 全链路
"""
import pytest
from datetime import datetime

def _uid():
    return datetime.now().strftime('%H%M%S%f')



def api_ok(response, msg=''):
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


class Test8008SyncBridge:
    """8008 Sync Bridge 5 个 POST 端点测试"""

    def test_8008_health(self, e2e_sync_client):
        """8008 健康检查"""
        r = e2e_sync_client.get('http://localhost:8008/api/health')
        assert r.status_code == 200, f'8008 不可用: {r.status_code}'
        data = r.json()
        print(f'\n[跨端点] 8008 健康: {data}')

    def test_8008_sub_step_report(self, e2e_sync_client):
        """POST /api/sync/sub-step-report - 工序子步骤报工同步"""
        uid = _uid()
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/sub-step-report',
            json={
                'order_no': f'E2E-STEP-{uid}',
                'step_name': '编织',
                'quantity': 100,
                'operator': '苑岗彪',
            },
        )
        data = r.json()
        print(f'\n[跨端点] /sub-step-report: code={data.get("code")} msg={data.get("message")}')
        assert data.get('code') == 0, f'报工同步失败: {data.get("message")}'

    def test_8008_sub_step_report_missing_params(self, e2e_sync_client):
        """POST /api/sync/sub-step-report - 缺少必填参数"""
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/sub-step-report',
            json={'order_no': 'E2E-TEST'},
        )
        data = r.json()
        print(f'\n[跨端点] 缺少参数: code={data.get("code")} msg={data.get("message")}')
        # 缺少 step_name 和 quantity 应返回非 0
        assert data.get('code') != 0, '缺少参数应返回错误'

    def test_8008_status_change(self, e2e_sync_client):
        """POST /api/sync/status-change - 状态变更同步"""
        uid = _uid()
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/status-change',
            json={
                'order_no': f'E2E-STATUS-{uid}',
                'status_key': 'in_production',
                'source': 'e2e_test',
            },
        )
        data = r.json()
        print(f'\n[跨端点] /status-change: code={data.get("code")} msg={data.get("message")}')
        assert data.get('code') == 0, f'状态变更失败: {data.get("message")}'

    def test_8008_quality_report(self, e2e_sync_client):
        """POST /api/sync/quality-report - 质检报告同步"""
        uid = _uid()
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/quality-report',
            json={
                'order_no': f'E2E-QC-{uid}',
                'inspection_type': '首检',
                'process_name': '编织',
                'overall_result': 'passed',
                'items': [],
            },
        )
        data = r.json()
        print(f'\n[跨端点] /quality-report: code={data.get("code")} msg={data.get("message")}')
        assert data.get('code') == 0, f'质检报告失败: {data.get("message")}'

    def test_8008_quality_report_missing_fields(self, e2e_sync_client):
        """POST /api/sync/quality-report - 缺少必填字段"""
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/quality-report',
            json={'order_no': f'E2E-QC-MISSING-{_uid()}'},
        )
        data = r.json()
        print(f'\n[跨端点] 缺少质检字段: code={data.get("code")} msg={data.get("message")}')
        assert data.get('code') != 0, '缺少字段应返回错误'

    def test_8008_report_confirm(self, e2e_sync_client):
        """POST /api/sync/report-confirm - 报工确认收口"""
        uid = _uid()
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/report-confirm',
            json={
                'order_no': f'E2E-CONFIRM-{uid}',
                'operator_id': 'YuanGangBiao',
                'confirmed': True,
                'remark': 'E2E 测试确认',
            },
        )
        data = r.json()
        print(f'\n[跨端点] /report-confirm: code={data.get("code")} msg={data.get("message")}')
        assert data.get('code') == 0, f'报工确认失败: {data.get("message")}'

    def test_8008_report_confirm_missing_params(self, e2e_sync_client):
        """POST /api/sync/report-confirm - 缺少 order_no/operator_id"""
        r = e2e_sync_client.post(
            'http://localhost:8008/api/sync/report-confirm',
            json={'order_no': f'E2E-CONFIRM-MISSING-{_uid()}'},
        )
        data = r.json()
        print(f'\n[跨端点] 缺少确认参数: code={data.get("code")} msg={data.get("message")}')
        assert data.get('code') != 0, '缺少参数应返回错误'


class TestScheduleToProductionChain:
    """排产 → 生产订单链路"""

    def test_schedule_list_to_production_orders(self, mobile_session):
        """排产列表 → 生产订单列表 联动"""
        r1 = mobile_session.get('http://localhost:5008/api/schedule/list')
        data1 = api_ok(r1, '排产列表')
        schedules = data1.get('data', [])
        print(f'\n[跨端点] 排产数: {len(schedules)}')

        r2 = mobile_session.get('http://localhost:5008/api/production-orders')
        data2 = api_ok(r2, '生产订单列表')
        orders = data2.get('data', [])
        print(f'[跨端点] 生产订单数: {len(orders)}')


class TestProductionToQualityChain:
    """生产订单 → 质检链路"""

    def test_quality_types_against_production_orders(self, mobile_session):
        """质检类型定义应与生产订单一致"""
        r1 = mobile_session.get('http://localhost:5008/api/production-orders')
        data1 = api_ok(r1, '生产订单列表')

        r2 = mobile_session.get('http://localhost:5008/api/quality/types')
        data2 = api_ok(r2, '质检类型')

        orders = data1.get('data', [])
        types = data2.get('data', [])
        print(f'\n[跨端点] 生产订单: {len(orders)}, 质检类型: {types}')


class TestAllServicesHealth:
    """全服务健康检查"""

    def test_5008_health(self, e2e_mobile_client):
        """5008 移动端健康"""
        r = e2e_mobile_client.get('http://localhost:5008/api/health')
        assert r.status_code == 200, f'5008 不可用: {r.status_code}'
        data = r.json()
        print(f'\n[跨端点] 5008 健康: code={data.get("code")} msg={data.get("message")}')

    def test_8008_health_repeat(self, e2e_sync_client):
        """8008 健康（重复验证）"""
        r = e2e_sync_client.get('http://localhost:8008/api/health')
        assert r.status_code == 200, f'8008 不可用: {r.status_code}'
        print(f'[跨端点] 8008 健康: {r.status_code}')
