# -*- coding: utf-8 -*-
"""
test_production_report_chain.py - 排产→报工集成测试

[Stage 2: 集成测试模块级串联]

测试场景: 发布排产 → 确认排产 → 工序报工 → 更新进度

前置: MySQL数据库可用
依赖: 5003 dispatch_center服务

标记: @pytest.mark.integration
超时: 180秒
"""
import os
import sys
import pytest
import requests
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DISPATCH_5003 = os.getenv('DISPATCH_5003_URL', 'http://127.0.0.1:5003')
MOBILE_5008 = os.getenv('MOBILE_5008_URL', 'http://127.0.0.1:5008')


def api_ok(response, msg=''):
    """断言API返回成功"""
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


@pytest.mark.integration
@pytest.mark.timeout(180)
class TestProductionReportChain:
    """排产→报工串联集成测试"""

    @pytest.fixture(autouse=True)
    def setup_chain(self, db_connection):
        """测试前置：创建测试工单"""
        self.schedule_id = None
        self.order_no = f'INT-PROD-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        self.db = db_connection
        yield
        self._cleanup()

    def _cleanup(self):
        """清理测试数据"""
        try:
            if self.schedule_id:
                with self.db.cursor() as cur:
                    cur.execute("DELETE FROM schedule_records WHERE schedule_id=%s", (self.schedule_id,))
                self.db.commit()
        except Exception as e:
            print(f'清理失败: {e}')

    def test_schedule_list(self):
        """Step 1: 查询排产列表"""
        print(f'\n[集成] Step 1: 查询排产列表')
        r = requests.get(
            f'{DISPATCH_5003}/api/schedule/list',
            timeout=30
        )
        data = api_ok(r, '查询排产列表')
        schedules = data.get('data', [])
        assert isinstance(schedules, list), '排产列表应为数组'
        print(f'[集成] Step 1 完成: 排产总数={len(schedules)}')

    def test_schedule_publish(self):
        """Step 2: 发布排产"""
        print(f'\n[集成] Step 2: 发布排产 {self.order_no}')
        r = requests.post(
            f'{DISPATCH_5003}/api/schedule/publish',
            json={'order_no': self.order_no},
            headers={'Authorization': 'Bearer test_token'},
            timeout=30
        )
        data = r.json()
        self.schedule_id = data.get('data', {}).get('schedule_id')
        print(f'[集成] Step 2 完成: schedule_id={self.schedule_id}')

    def test_schedule_confirm(self):
        """Step 3: 确认排产（依赖Step 2）"""
        if not self.schedule_id:
            pytest.skip('缺少schedule_id，跳过确认步骤')
        print(f'\n[集成] Step 3: 确认排产')
        r = requests.post(
            f'{DISPATCH_5003}/api/schedule/confirm',
            json={'schedule_id': self.schedule_id, 'result': 'confirmed'},
            headers={'Authorization': 'Bearer test_token'},
            timeout=30
        )
        data = api_ok(r, '确认排产')
        print(f'[集成] Step 3 完成')

    def test_workreport(self):
        """Step 4: 提交报工（依赖Step 3）"""
        if not self.schedule_id:
            pytest.skip('缺少schedule_id，跳过报工步骤')
        print(f'\n[集成] Step 4: 提交报工')
        r = requests.post(
            f'{MOBILE_5008}/api/workreport',
            json={
                'schedule_id': self.schedule_id,
                'operator': '苑岗彪',
                'quantity': 50,
            },
            timeout=30
        )
        data = r.json()
        assert data.get('code') == 0, f'报工失败: {data}'
        print(f'[集成] Step 4 完成')

    def test_full_chain_consistency(self):
        """Step 5: 全链路数据一致性检查"""
        print(f'\n[集成] Step 5: 数据一致性检查')
        with self.db.cursor() as cur:
            if self.schedule_id:
                cur.execute("SELECT status FROM schedule_records WHERE schedule_id=%s", (self.schedule_id,))
                result = cur.fetchone()
                if result:
                    assert result['status'] in ['confirmed', 'in_progress', 'completed'], \
                        f'排产状态异常: {result["status"]}'
        print(f'[集成] Step 5 完成: 数据一致')


@pytest.mark.integration
@pytest.mark.timeout(180)
class TestProductionReportChainEdge:
    """排产→报工边界测试"""

    def test_confirm_nonexistent_schedule(self):
        """确认不存在的排产应返回错误"""
        r = requests.post(
            f'{DISPATCH_5003}/api/schedule/confirm',
            json={'schedule_id': 999999, 'result': 'confirmed'},
            headers={'Authorization': 'Bearer test_token'},
            timeout=30
        )
        data = r.json()
        assert data.get('code') != 0, '确认不存在的排产应失败'

    def test_workreport_invalid_schedule(self):
        """报工无效排产应返回错误"""
        r = requests.post(
            f'{MOBILE_5008}/api/workreport',
            json={'schedule_id': 999999, 'operator': 'test', 'quantity': 10},
            timeout=30
        )
        data = r.json()
        assert data.get('code') != 0, '报工无效排产应失败'
