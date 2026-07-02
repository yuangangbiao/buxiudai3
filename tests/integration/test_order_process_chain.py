# -*- coding: utf-8 -*-
"""
test_order_process_chain.py - 订单→工艺集成测试

[Stage 2: 集成测试模块级串联]

测试场景: 创建订单 → 匹配工艺路线 → 计算工序

前置: MySQL数据库可用
依赖: 5001 desktop_web服务

标记: @pytest.mark.integration
超时: 180秒

服务不可用时自动跳过
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


def _service_alive(url, timeout=2):
    """检查服务是否可达"""
    try:
        r = requests.get(url, timeout=timeout)
        return True
    except Exception:
        return False


def _require_service():
    """检查服务是否在线，不在线则跳过"""
    if not _service_alive(f'{WEB_5001}/'):
        pytest.skip(f'5001 desktop_web服务不可用，跳过集成测试')


def api_ok(response, msg=''):
    """断言API返回成功"""
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


@pytest.mark.integration
@pytest.mark.timeout(180)
class TestOrderProcessChain:
    """订单→工艺串联集成测试"""

    @pytest.fixture(autouse=True)
    def setup_chain(self, db_connection):
        """测试前置：检查服务 + 创建测试订单"""
        _require_service()
        self.order_no = f'INT-CHAIN-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        self.db = db_connection
        self.process_id = None
        yield
        self._cleanup()

    def _cleanup(self):
        """清理测试数据"""
        try:
            with self.db.cursor() as cur:
                cur.execute("UPDATE orders SET is_deleted=1 WHERE order_no=%s", (self.order_no,))
                cur.execute("DELETE FROM process_steps WHERE order_no=%s", (self.order_no,))
            self.db.commit()
        except Exception as e:
            print(f'清理失败: {e}')

    def test_order_creation(self):
        """Step 1: 创建订单"""
        print(f'\n[集成] Step 1: 创建订单 {self.order_no}')
        r = requests.post(
            f'{WEB_5001}/api/orders/create',
            json={
                'order_no': self.order_no,
                'customer': '集成测试客户',
                'product_type': '标准网带',
                'quantity': 100,
                'delivery_date': (datetime.now().replace(hour=23, minute=59, second=59)).strftime('%Y-%m-%d'),
            },
            timeout=30
        )
        data = api_ok(r, '创建订单')
        assert data['data']['order_no'] == self.order_no

        with self.db.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE order_no=%s", (self.order_no,))
            result = cur.fetchone()
            assert result is not None, '订单未创建成功'
            assert result['status'] in ['created', 'pending'], f'订单状态异常: {result["status"]}'
        print(f'[集成] Step 1 完成: 订单已创建')

    def test_process_matching(self):
        """Step 2: 工艺匹配（依赖Step 1）"""
        print(f'\n[集成] Step 2: 工艺匹配')
        r = requests.get(
            f'{WEB_5001}/api/process/match',
            params={'order_no': self.order_no},
            timeout=30
        )
        data = api_ok(r, '工艺匹配')
        self.process_id = data['data'].get('process_id')
        assert self.process_id is not None, '工艺ID为空'
        print(f'[集成] Step 2 完成: process_id={self.process_id}')

    def test_process_calculation(self):
        """Step 3: 工序计算（依赖Step 2）"""
        print(f'\n[集成] Step 3: 工序计算')
        r = requests.post(
            f'{WEB_5001}/api/process/calculate',
            json={'order_no': self.order_no, 'process_id': self.process_id},
            timeout=30
        )
        data = api_ok(r, '工序计算')
        steps = data['data'].get('steps', [])
        assert len(steps) > 0, '工序列表为空'

        with self.db.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM process_steps WHERE order_no=%s", (self.order_no,))
            result = cur.fetchone()
            assert result['cnt'] > 0, '工序未生成'
        print(f'[集成] Step 3 完成: 生成{len(steps)}个工序')

    def test_full_chain_consistency(self):
        """Step 4: 全链路数据一致性检查"""
        print(f'\n[集成] Step 4: 数据一致性检查')
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    o.order_no,
                    o.status as order_status,
                    COUNT(ps.id) as step_count
                FROM orders o
                LEFT JOIN process_steps ps ON o.order_no = ps.order_no
                WHERE o.order_no = %s
                GROUP BY o.order_no, o.status
            """, (self.order_no,))
            result = cur.fetchone()
            assert result is not None, '订单数据不一致'
            assert result['step_count'] > 0, '工序数量为0'
        print(f'[集成] Step 4 完成: 数据一致')


@pytest.mark.integration
@pytest.mark.timeout(180)
class TestOrderProcessChainEdge:
    """订单→工艺边界测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """检查服务是否可用"""
        _require_service()

    def test_empty_order_no(self):
        """空订单号应返回错误"""
        r = requests.post(
            f'{WEB_5001}/api/orders/create',
            json={'order_no': '', 'customer': 'test'},
            timeout=30
        )
        data = r.json()
        assert data.get('code') != 0, '空订单号应失败'

    def test_invalid_process_id(self):
        """无效工艺ID应返回错误"""
        r = requests.post(
            f'{WEB_5001}/api/process/calculate',
            json={'order_no': 'NONEXISTENT', 'process_id': 999999},
            timeout=30
        )
        data = r.json()
        assert data.get('code') != 0, '无效工艺ID应失败'
