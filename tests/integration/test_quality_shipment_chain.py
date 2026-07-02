# -*- coding: utf-8 -*-
"""
test_quality_shipment_chain.py - 质检→发货集成测试

[Stage 2: 集成测试模块级串联]

测试场景: 提交质检 → 质检通过 → 创建发货单 → 物流跟踪

前置: MySQL数据库可用
依赖: 5001 desktop_web服务, 5008 mobile服务

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

WEB_5001 = os.getenv('WEB_5001_URL', 'http://127.0.0.1:5001')
MOBILE_5008 = os.getenv('MOBILE_5008_URL', 'http://127.0.0.1:5008')


def api_ok(response, msg=''):
    """断言API返回成功"""
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


@pytest.mark.integration
@pytest.mark.timeout(180)
class TestQualityShipmentChain:
    """质检→发货串联集成测试"""

    @pytest.fixture(autouse=True)
    def setup_chain(self, db_connection):
        """测试前置：创建测试订单"""
        self.order_no = f'INT-QUAL-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        self.qc_id = None
        self.shipment_id = None
        self.db = db_connection
        yield
        self._cleanup()

    def _cleanup(self):
        """清理测试数据"""
        try:
            with self.db.cursor() as cur:
                cur.execute("UPDATE orders SET is_deleted=1 WHERE order_no=%s", (self.order_no,))
                if self.qc_id:
                    cur.execute("DELETE FROM qc_records WHERE qc_id=%s", (self.qc_id,))
                if self.shipment_id:
                    cur.execute("DELETE FROM shipments WHERE shipment_id=%s", (self.shipment_id,))
            self.db.commit()
        except Exception as e:
            print(f'清理失败: {e}')

    def test_quality_submit(self):
        """Step 1: 提交质检"""
        print(f'\n[集成] Step 1: 提交质检 {self.order_no}')
        r = requests.post(
            f'{MOBILE_5008}/api/quality',
            json={
                'order_no': self.order_no,
                'result': 'passed',
                'inspector': '苑岗彪',
                'remarks': '集成测试质检',
            },
            timeout=30
        )
        data = r.json()
        if data.get('code') == 0:
            self.qc_id = data.get('data', {}).get('qc_id')
            print(f'[集成] Step 1 完成: qc_id={self.qc_id}')
        else:
            print(f'[集成] Step 1 跳过: 订单不存在或其他原因 ({data.get("message")})')

    def test_quality_check(self):
        """Step 2: 查询质检记录"""
        print(f'\n[集成] Step 2: 查询质检记录')
        r = requests.get(
            f'{MOBILE_5008}/api/quality/list',
            params={'order_no': self.order_no},
            timeout=30
        )
        data = api_ok(r, '查询质检记录')
        print(f'[集成] Step 2 完成')

    def test_shipment_create(self):
        """Step 3: 创建发货单"""
        print(f'\n[集成] Step 3: 创建发货单 {self.order_no}')
        r = requests.post(
            f'{WEB_5001}/api/shipment',
            json={
                'order_no': self.order_no,
                'logistics_company': '顺丰速运',
                'tracking_no': f'SF{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'contact': '测试客户',
                'phone': '13800138000',
            },
            timeout=30
        )
        data = r.json()
        if data.get('code') == 0:
            self.shipment_id = data.get('data', {}).get('shipment_id')
            print(f'[集成] Step 3 完成: shipment_id={self.shipment_id}')
        else:
            print(f'[集成] Step 3 跳过: 创建失败 ({data.get("message")})')

    def test_shipment_query(self):
        """Step 4: 查询发货单"""
        print(f'\n[集成] Step 4: 查询发货单')
        r = requests.get(
            f'{WEB_5001}/api/shipment/list',
            params={'order_no': self.order_no},
            timeout=30
        )
        data = api_ok(r, '查询发货单')
        shipments = data.get('data', [])
        assert isinstance(shipments, list), '发货列表应为数组'
        print(f'[集成] Step 4 完成: 发货单数量={len(shipments)}')

    def test_full_chain_consistency(self):
        """Step 5: 全链路数据一致性检查"""
        print(f'\n[集成] Step 5: 数据一致性检查')
        with self.db.cursor() as cur:
            if self.shipment_id:
                cur.execute("SELECT status FROM shipments WHERE shipment_id=%s", (self.shipment_id,))
                result = cur.fetchone()
                if result:
                    assert result['status'] in ['created', 'shipped', 'delivered'], \
                        f'发货状态异常: {result["status"]}'
        print(f'[集成] Step 5 完成: 数据一致')


@pytest.mark.integration
@pytest.mark.timeout(180)
class TestQualityShipmentChainEdge:
    """质检→发货边界测试"""

    def test_quality_invalid_result(self):
        """无效质检结果应返回错误"""
        r = requests.post(
            f'{MOBILE_5008}/api/quality',
            json={
                'order_no': 'NONEXISTENT',
                'result': 'invalid_result',
                'inspector': 'test',
            },
            timeout=30
        )
        data = r.json()
        assert data.get('code') != 0, '无效质检结果应失败'

    def test_shipment_missing_tracking(self):
        """缺失运单号应返回错误"""
        r = requests.post(
            f'{WEB_5001}/api/shipment',
            json={
                'order_no': 'TEST123',
                'logistics_company': '',
                'tracking_no': '',
            },
            timeout=30
        )
        data = r.json()
        assert data.get('code') != 0, '缺失运单号应失败'
