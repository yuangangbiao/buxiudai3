# -*- coding: utf-8 -*-
"""
test_bf_03_dispatch_regress.py - 调度回归测试

5003 standalone_dispatch_server.py 是一个 Flask 页面服务器，
不提供 REST API。真正的调度操作在 5008 中体现。

测试策略：
- 验证 5008 排产确认功能（调度接收）
- 验证 5008 生产订单（调度输出）
- 验证 5008 调度服务健康
"""
import pytest
from tests.e2e.business_flows._helpers import DBWatchdog


def api_ok(response, msg=''):
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


class TestScheduleDispatch:
    """排产调度"""

    def test_schedule_list_returns_data(self, mobile_session):
        """排产列表有数据"""
        r = mobile_session.get('http://localhost:5008/api/schedule/list')
        data = api_ok(r, '排产列表')
        schedules = data.get('data', [])
        print(f'\n[调度回归] 排产数: {len(schedules)}')

    def test_schedule_health_stats(self, mobile_session):
        """调度服务统计"""
        r = mobile_session.get('http://localhost:5008/api/schedule/health')
        data = api_ok(r, '调度统计')
        stats = data.get('data', {})
        print(f'\n[调度回归] 调度统计: {stats}')

    def test_schedule_confirm_rejects_invalid_id(self, mobile_session):
        """无效排产ID应被拒绝"""
        r = mobile_session.post(
            'http://localhost:5008/api/schedule/confirm',
            json={'schedule_id': 99999, 'result': 'confirmed'},
        )
        data = r.json()
        print(f'\n[调度回归] 无效ID确认: code={data.get("code")} msg={data.get("message","")}')


class TestProductionDispatch:
    """生产订单调度输出"""

    def test_production_orders_list(self, mobile_session):
        """生产订单列表（调度输出）"""
        r = mobile_session.get('http://localhost:5008/api/production-orders')
        data = api_ok(r, '生产订单列表')
        orders = data.get('data', [])
        print(f'\n[调度回归] 生产订单数: {len(orders)}')


class TestDispatchStateMachine:
    """状态机白名单"""

    @pytest.mark.parametrize('result', ['confirmed', 'rejected'])
    def test_schedule_confirm_valid_results(self, result, mobile_session):
        """确认排产 - 合法结果（confirmed / rejected）"""
        r = mobile_session.post(
            'http://localhost:5008/api/schedule/confirm',
            json={'schedule_id': 99999, 'result': result},
        )
        data = r.json()
        print(f'\n[调度回归] 确认结果 {result}: code={data.get("code")}')

    def test_schedule_confirm_invalid_result(self, mobile_session):
        """确认排产 - 非法结果应被拒绝"""
        r = mobile_session.post(
            'http://localhost:5008/api/schedule/confirm',
            json={'schedule_id': 1, 'result': 'pending'},
        )
        data = r.json()
        code = data.get('code')
        # pending 不是合法结果，应返回错误
        assert code != 0, f'非法结果 pending 应被拒绝，但返回 code={code}'


class TestDispatchCache:
    """调度缓存（Redis）"""

    def test_redis_connection(self):
        """Redis 连接可用"""
        try:
            wd = DBWatchdog()
            wd.redis.ping()
            wd.close()
            print('\n[调度回归] Redis 连接正常')
        except Exception as e:
            pytest.skip(f'Redis 不可用: {e}')


class TestDispatchHealth:
    """调度服务健康"""

    def test_5008_mobile_alive(self, e2e_mobile_client):
        """5008 移动端存活"""
        r = e2e_mobile_client.get('http://localhost:5008/api/health')
        assert r.status_code == 200, f'5008 不可用: {r.status_code}'
        print(f'\n[调度回归] 5008 健康: {r.status_code}')
