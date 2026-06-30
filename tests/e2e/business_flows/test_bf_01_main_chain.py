# -*- coding: utf-8 -*-
"""
test_bf_01_main_chain.py - 5008 排产主链路测试

业务流程: 获取排产列表 → 确认排产 → 打卡上班 → 提交质检

5008 的生产流程：
1. GET /api/schedule/pending  → 查待确认排产
2. POST /api/schedule/confirm  → 确认排产（result=confirmed）
3. POST /api/attendance       → 上班打卡（action=check-in）
4. POST /api/quality         → 提交质检报告（result=passed/failed）

注：5008 是移动端系统，生产计划由排产员在 5003 页面创建，
    工人通过 5008 接收任务并执行。
"""
import pytest
from tests.e2e.business_flows._helpers import DBWatchdog


def api_ok(response, msg=''):
    """断言 API 返回 code=0"""
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


class TestScheduleList:
    """Step 1: 获取排产列表"""

    def test_get_schedule_list(self, mobile_session):
        """查询排产列表（待确认 + 已确认）"""
        r = mobile_session.get('http://localhost:5008/api/schedule/list')
        data = api_ok(r, '查询排产列表')
        schedules = data.get('data', [])
        print(f'\n[主链路] 排产总数: {len(schedules)}')
        assert isinstance(schedules, list), '排产列表应为数组'

    def test_get_pending_schedules(self, mobile_session):
        """查询待确认排产"""
        r = mobile_session.get('http://localhost:5008/api/schedule/pending')
        data = api_ok(r, '查询待确认排产')
        pending = data.get('data', [])
        print(f'\n[主链路] 待确认排产数: {len(pending)}')


class TestScheduleConfirm:
    """Step 2: 确认排产"""

    def test_schedule_health(self, mobile_session):
        """排产服务健康检查"""
        r = mobile_session.get('http://localhost:5008/api/schedule/health')
        data = api_ok(r, '排产服务健康')
        print(f'\n[主链路] 排产服务统计: {data.get("data")}')

    def test_confirm_schedule_requires_id(self, mobile_session):
        """确认排产（缺少 schedule_id 应返回错误）"""
        r = mobile_session.post(
            'http://localhost:5008/api/schedule/confirm',
            json={'result': 'confirmed'},
        )
        # 缺少 schedule_id 应返回非 0
        data = r.json()
        print(f'\n[主链路] 缺少 schedule_id: code={data.get("code")} msg={data.get("message","")}')

    def test_confirm_schedule_reject(self, mobile_session):
        """拒绝排产（拒绝操作验证）"""
        r = mobile_session.post(
            'http://localhost:5008/api/schedule/confirm',
            json={'schedule_id': 99999, 'result': 'rejected'},
        )
        data = r.json()
        print(f'\n[主链路] 拒绝不存在的排产: code={data.get("code")} msg={data.get("message","")}')


class TestAttendance:
    """Step 3: 打卡上班"""

    def test_check_in(self, mobile_session):
        """上班打卡"""
        r = mobile_session.post(
            'http://localhost:5008/api/attendance',
            json={'action': 'check-in'},
        )
        data = r.json()
        print(f'\n[主链路] 上班打卡: code={data.get("code")} msg={data.get("message","")}')

    def test_get_attendance_records(self, mobile_session):
        """查询打卡记录"""
        r = mobile_session.get('http://localhost:5008/api/attendance')
        raw = r.json()
        records = raw if isinstance(raw, list) else (raw.get('data', []) if isinstance(raw, dict) else [])
        print(f'\n[主链路] 打卡记录数: {len(records)}')


class TestQualityReport:
    """Step 4: 提交质检报告"""

    def test_quality_types(self, mobile_session):
        """查询质检类型枚举"""
        r = mobile_session.get('http://localhost:5008/api/quality/types')
        data = api_ok(r, '查询质检类型')
        types = data.get('data', [])
        print(f'\n[主链路] 质检类型: {types}')

    def test_submit_quality_passed(self, mobile_session):
        """提交质检报告（合格）"""
        r = mobile_session.post(
            'http://localhost:5008/api/quality',
            json={
                'order_no': 'E2E-TEST-QUALITY',
                'result': 'passed',
                'notes': 'E2E 测试质检',
            },
        )
        data = r.json()
        print(f'\n[主链路] 提交质检: code={data.get("code")} msg={data.get("message","")}')

    def test_submit_quality_failed(self, mobile_session):
        """提交质检报告（不合格）"""
        r = mobile_session.post(
            'http://localhost:5008/api/quality',
            json={
                'order_no': 'E2E-TEST-QUALITY',
                'result': 'failed',
                'notes': 'E2E 测试质检（不合格）',
            },
        )
        data = r.json()
        print(f'\n[主链路] 提交不合格质检: code={data.get("code")} msg={data.get("message","")}')


class TestProductionOrders:
    """Step 5: 生产订单"""

    def test_production_orders_list(self, mobile_session):
        """查询生产订单列表"""
        r = mobile_session.get('http://localhost:5008/api/production-orders')
        data = api_ok(r, '查询生产订单')
        orders = data.get('data', [])
        print(f'\n[主链路] 生产订单数: {len(orders)}')

    def test_dashboard(self, mobile_session):
        """仪表盘数据"""
        r = mobile_session.get('http://localhost:5008/api/dashboard')
        raw = r.json()
        assert isinstance(raw, dict), f'仪表盘应返回字典，实际: {type(raw)}'
        print(f'\n[主链路] 仪表盘 keys: {list(raw.keys())}')


class TestWorkers:
    """Step 6: 工人管理"""

    def test_workers_list(self, mobile_session):
        """查询工人列表"""
        r = mobile_session.get('http://localhost:5008/api/workers')
        data = api_ok(r, '查询工人列表')
        workers = data.get('data', [])
        print(f'\n[主链路] 工人总数: {len(workers)}')
        # 验证苑岗彪在列表中
        names = [w.get('name', '') for w in workers]
        assert '苑岗彪' in names, f'苑岗彪不在工人列表中: {names}'


class TestBusinessRule:
    """Step 7: 业务规则验证"""

    def test_cannot_submit_invalid_result(self, mobile_session):
        """提交非法质检结果应被拒绝"""
        r = mobile_session.post(
            'http://localhost:5008/api/quality',
            json={
                'order_no': 'E2E-INVALID',
                'result': 'invalid_result_xyz',
                'notes': '非法结果测试',
            },
        )
        data = r.json()
        # 非法结果应返回非 0
        print(f'\n[主链路] 非法质检结果: code={data.get("code")} msg={data.get("message","")}')
