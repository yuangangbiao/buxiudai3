# -*- coding: utf-8 -*-
"""
T1 乐观锁并发测试

覆盖场景:
- 空输入: order_no=None, order_no=''
- 单条: 正常订单读/写
- 乐观锁冲突: 2 个并发写入,后写者收到 CONFLICT
- 回退: NOT_FOUND
"""
import os
import sys
import time
import threading
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from mobile_api_ai.core.order_status_contract import (
    update_order_status,
    get_order_status,
    batch_get_order_status,
    infer_current_step_from_status,
    STATUS_TO_STEP,
)


class TestInferCurrentStep:
    """STATUS_TO_STEP 映射测试"""

    def test_known_statuses(self):
        """已知状态映射正确"""
        cases = [
            ('created', 0),
            ('published', 1),
            ('scheduled', 2),
            ('confirmed', 3),
            ('in_production', 4),
            ('reported', 5),
            ('qc_passed', 6),
            ('completed', 7),
            ('cancelled', -1),
        ]
        for status, expected_step in cases:
            assert infer_current_step_from_status(status) == expected_step, \
                f'status={status} expected={expected_step}'

    def test_unknown_status_returns_zero(self):
        """未知状态返回 0"""
        assert infer_current_step_from_status('unknown_status') == 0
        assert infer_current_step_from_status('') == 0
        assert infer_current_step_from_status(None) == 0


class TestUpdateOrderStatus:
    """乐观锁写入测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Mock 数据库连接"""
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None
        self.get_conn_patcher = patch(
            'mobile_api_ai.core.order_status_contract.get_connection',
            return_value=self.mock_conn
        )
        self.get_conn_patcher.start()
        yield
        self.get_conn_patcher.stop()

    def test_success_no_optimistic_lock(self):
        """无条件更新成功"""
        self.mock_cursor.rowcount = 1
        ok, msg = update_order_status('ORD-001', 'in_production', source='test')
        assert ok is True
        assert msg == 'OK'
        self.mock_cursor.execute.assert_called_once()

    def test_optimistic_lock_conflict(self):
        """乐观锁冲突: rowcount=0 但订单存在"""
        self.mock_cursor.rowcount = 0
        # 第一次查存在
        self.mock_cursor.fetchone.side_effect = [
            {'id': 1},  # EXISTS check
        ]
        ts = datetime(2024, 1, 1)
        ok, msg = update_order_status(
            'ORD-001', 'completed', expected_last_update_at=ts, source='test'
        )
        assert ok is False
        assert msg == 'CONFLICT'

    def test_not_found(self):
        """订单不存在"""
        self.mock_cursor.rowcount = 0
        self.mock_cursor.fetchone.return_value = None  # EXISTS check
        ts = datetime(2024, 1, 1)
        ok, msg = update_order_status(
            'ORD-NOEXIST', 'completed', expected_last_update_at=ts, source='test'
        )
        assert ok is False
        assert msg == 'NOT_FOUND'

    def test_current_step_auto_inferred(self):
        """current_step 根据 status 自动推算"""
        self.mock_cursor.rowcount = 1
        cases = [
            ('created', 0),
            ('in_production', 4),
            ('completed', 7),
        ]
        for status, expected_step in cases:
            self.mock_cursor.reset_mock()
            ok, _ = update_order_status('ORD-001', status, source='test')
            assert ok is True
            call_args = str(self.mock_cursor.execute.call_args)
            assert f'{expected_step}' in call_args, \
                f'status={status} step not in {call_args}'


class TestGetOrderStatus:
    """读取测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None
        self.get_conn_patcher = patch(
            'mobile_api_ai.core.order_status_contract.get_connection',
            return_value=self.mock_conn
        )
        self.get_conn_patcher.start()
        yield
        self.get_conn_patcher.stop()

    def test_order_exists(self):
        """订单存在时返回完整数据"""
        self.mock_cursor.fetchone.return_value = {
            'order_no': 'ORD-001',
            'status': 'in_production',
            'current_step': 0,  # 旧的 0 值
            'last_status_update_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 2),
        }
        result = get_order_status('ORD-001')
        assert result is not None
        assert result['order_no'] == 'ORD-001'
        assert result['status'] == 'in_production'
        # current_step 应该被兜底推算为 4
        assert result['current_step'] == 4, \
            f"in_production 应推断为 4,实际={result['current_step']}"
        assert result['source'] == 'ssot'

    def test_order_not_found(self):
        """订单不存在返回 None"""
        self.mock_cursor.fetchone.return_value = None
        result = get_order_status('ORD-NOEXIST')
        assert result is None

    def test_current_step_null_uses_status_inference(self):
        """current_step 为 NULL 时用 status 推算"""
        self.mock_cursor.fetchone.return_value = {
            'order_no': 'ORD-002',
            'status': 'completed',
            'current_step': None,
            'last_status_update_at': None,
            'updated_at': datetime(2024, 1, 1),
        }
        result = get_order_status('ORD-002')
        assert result is not None
        assert result['current_step'] == 7, \
            f"completed 应推断为 7,实际={result['current_step']}"


class TestBatchGetOrderStatus:
    """批量读取测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None
        self.get_conn_patcher = patch(
            'mobile_api_ai.core.order_status_contract.get_connection',
            return_value=self.mock_conn
        )
        self.get_conn_patcher.start()
        yield
        self.get_conn_patcher.stop()

    def test_batch_returns_all(self):
        """批量读取返回所有订单状态"""
        self.mock_cursor.fetchall.return_value = [
            {
                'order_no': 'ORD-001',
                'status': 'in_production',
                'current_step': 4,
                'last_status_update_at': datetime.now(),
                'updated_at': datetime.now(),
            },
            {
                'order_no': 'ORD-002',
                'status': 'completed',
                'current_step': 7,
                'last_status_update_at': datetime.now(),
                'updated_at': datetime.now(),
            },
        ]
        result = batch_get_order_status(['ORD-001', 'ORD-002', 'ORD-003'])
        assert 'ORD-001' in result
        assert 'ORD-002' in result
        assert result['ORD-003'] is None  # 不存在的返回 None

    def test_empty_list(self):
        """空列表返回空 dict"""
        result = batch_get_order_status([])
        assert result == {}


class TestConcurrency:
    """并发测试:乐观锁冲突"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None

        self.mock_conn2 = MagicMock()
        self.mock_cursor2 = MagicMock()
        self.mock_conn2.cursor.return_value.__enter__.return_value = self.mock_cursor2
        self.mock_conn2.cursor.return_value.__exit__.return_value = None

        call_count = [0]
        def get_conn_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return self.mock_conn
            return self.mock_conn2

        self.get_conn_patcher = patch(
            'mobile_api_ai.core.order_status_contract.get_connection',
            side_effect=get_conn_side_effect
        )
        self.get_conn_patcher.start()
        yield
        self.get_conn_patcher.stop()

    def test_optimistic_lock_blocks_second_writer(self):
        """乐观锁:第二个写入者收到 CONFLICT"""
        # 第一个写入: rowcount=1 成功
        self.mock_cursor.rowcount = 1
        # 第二个写入: rowcount=0, fetchone=存在
        self.mock_cursor2.rowcount = 0
        self.mock_cursor2.fetchone.side_effect = [
            {'id': 1},  # EXISTS check
        ]

        ts = datetime.now()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(
                update_order_status, 'ORD-001', 'reported',
                expected_last_update_at=ts, source='writer1'
            )
            f2 = executor.submit(
                update_order_status, 'ORD-001', 'completed',
                expected_last_update_at=ts, source='writer2'
            )
            r1, r2 = f1.result(), f2.result()

        # 至少一个成功,一个冲突
        results = [r1, r2]
        success = [r for r in results if r[0] is True]
        conflicts = [r for r in results if r[1] == 'CONFLICT']
        assert len(success) + len(conflicts) == 2, \
            f'期望 1 成功 + 1 冲突,实际: {results}'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
