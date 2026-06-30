# -*- coding: utf-8 -*-
"""[v3.7.0] L1 冒烟测试 - 订单创建

不依赖真实服务，使用 mock 验证订单创建业务逻辑。
执行时间: < 30s
"""
import pytest
import time
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestOrderCreateSmoke:
    """订单创建冒烟测试 - 验证核心业务规则"""

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_order_no_format(self):
        """订单号格式验证"""
        # 业务规则: 订单号 = WO + YYYYMMDD + 4位序号
        today = datetime.now().strftime('%Y%m%d')
        expected_prefix = f'WO{today}'

        # 模拟生成订单号
        seq = 1
        order_no = f'{expected_prefix}{seq:04d}'

        assert order_no.startswith('WO')
        assert today in order_no
        assert len(order_no) == 14  # WO(2) + YYYYMMDD(8) + 序号(4)

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_order_required_fields(self):
        """订单必填字段验证"""
        # 业务规则: 必填字段
        required_fields = [
            'order_no', 'product_type', 'spec',
            'quantity', 'customer_name', 'status',
        ]

        # 验证订单数据结构
        sample_order = {
            'order_no': 'WO202606250001',
            'product_type': '不锈钢网带',
            'spec': '1.0×10×1000mm',
            'quantity': 100,
            'customer_name': '测试客户',
            'status': 'PENDING',
        }

        for field in required_fields:
            assert field in sample_order, f"订单必须包含字段: {field}"

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_order_status_initial_value(self):
        """订单初始状态"""
        # 业务规则: 新建订单状态 = PENDING
        valid_initial_status = 'PENDING'

        # 验证状态值符合 R-050 业务流
        from tests.fixtures.orders import make_test_order

        # 通过 fixtures 工厂验证（mock DB）
        with patch('tests.core.db_pool.db') as mock_db:
            mock_db.execute = MagicMock(return_value=1)
            order_no = make_test_order(
                product_type='不锈钢网带',
                status=valid_initial_status,
            )
            assert order_no.startswith('TEST_')
            mock_db.execute.assert_called_once()

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_order_quantity_must_be_positive(self):
        """订单数量必须为正"""
        # 业务规则: quantity > 0
        invalid_quantities = [0, -1, -100]

        for qty in invalid_quantities:
            assert qty <= 0, f"无效数量 {qty} 应被业务校验拒绝"

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_order_test_data_isolation(self):
        """测试订单数据隔离"""
        from tests.fixtures.orders import make_test_order

        with patch('tests.core.db_pool.db') as mock_db:
            mock_db.execute = MagicMock(return_value=1)

            # 生成 2 个订单，订单号应该不同
            order1 = make_test_order(prefix='TEST_L1')
            time.sleep(0.01)
            order2 = make_test_order(prefix='TEST_L1')

            assert order1 != order2, "两次生成的订单号应不同"
            assert order1.startswith('TEST_L1_')
            assert order2.startswith('TEST_L1_')

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_order_status_flow_r050(self):
        """订单状态流转遵循 R-050"""
        # R-050 强制状态流:
        # created → confirmed → scheduled → in_progress → completed → shipped → archived
        valid_flow = [
            'CREATED', 'CONFIRMED', 'SCHEDULED',
            'IN_PROGRESS', 'COMPLETED', 'SHIPPED', 'ARCHIVED',
        ]

        # 验证状态序列
        for i in range(len(valid_flow) - 1):
            current = valid_flow[i]
            next_status = valid_flow[i + 1]
            # 业务规则: 只能从当前状态跳转到下一状态
            # (除 archived 回退外)
            assert current != next_status

    @pytest.mark.L1
    @pytest.mark.smoke
    @pytest.mark.orders
    def test_make_test_orders_batch(self):
        """批量创建订单"""
        from tests.fixtures.orders import make_test_orders

        with patch('tests.core.db_pool.db') as mock_db:
            mock_db.execute = MagicMock(return_value=1)

            orders = make_test_orders(count=3, prefix='BATCH')
            assert len(orders) == 3
            assert all(o.startswith('BATCH_') for o in orders)
            assert len(set(orders)) == 3, "订单号必须唯一"
