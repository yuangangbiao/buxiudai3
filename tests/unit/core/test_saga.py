# -*- coding: utf-8 -*-
"""core/saga.py 补充测试"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


class TestSagaOrchestrator:
    """Saga 编排器测试"""

    def test_run_success(self):
        from core.saga import SagaOrchestrator, SagaStep
        step1_executed = []
        step2_executed = []

        saga = SagaOrchestrator("test", [
            SagaStep("s1", lambda: step1_executed.append(1) or True, lambda: None),
            SagaStep("s2", lambda: step2_executed.append(1) or True, lambda: None),
        ])
        result = saga.run()
        assert result['success'] is True
        assert len(result['log']) == 2
        assert len(step1_executed) == 1
        assert len(step2_executed) == 1

    def test_run_with_compensation(self):
        from core.saga import SagaOrchestrator, SagaStep
        compensated = []
        saga = SagaOrchestrator("test_compensate", [
            SagaStep("s1", lambda: True, lambda: compensated.append("comp_s1")),
            SagaStep("s2", lambda: False, lambda: compensated.append("comp_s2")),
        ])
        result = saga.run()
        assert result['success'] is False
        assert "comp_s1" in compensated
        assert len(compensated) >= 1

    def test_saga_step_dataclass(self):
        from core.saga import SagaStep
        step = SagaStep("test", lambda: True, lambda: None)
        assert step.name == "test"
        assert callable(step.execute)
        assert callable(step.compensate)

    def test_create_order_fulfillment_saga(self):
        from core.saga import create_order_fulfillment_saga
        saga = create_order_fulfillment_saga("ORD-001")
        assert saga.name == "order_fulfillment_ORD-001"
        assert len(saga.steps) == 4

    def test_create_order_fulfillment_saga_run(self):
        from core.saga import create_order_fulfillment_saga
        saga = create_order_fulfillment_saga("ORD-002")
        result = saga.run()
        assert result['success'] is True
        assert len(result['log']) == 4


class TestSagaSaveDeadLetter:
    """_save_dead_letter 方法测试 —— 覆盖 L47-66"""

    def test_dead_letter_write_success(self):
        """补偿失败 → _save_dead_letter 正常写入数据库"""
        from core.saga import SagaOrchestrator, SagaStep
        with patch('core.saga.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            saga = SagaOrchestrator("test_dead", [
                SagaStep("s1", lambda: True, lambda: (_ for _ in ()).throw(RuntimeError("补偿爆炸"))),
                SagaStep("s2", lambda: False, lambda: None),
            ])
            result = saga.run()

        assert result['success'] is False
        # 补偿 s1 时异常，死信应写入
        assert mock_cursor.execute.call_count >= 2
        # 检查 INSERT 死信语句
        insert_calls = [c for c in mock_cursor.execute.call_args_list if 'INSERT INTO saga_dead_letter' in str(c)]
        assert len(insert_calls) >= 1
        assert 'test_dead' in str(insert_calls[0])
        assert '补偿爆炸' in str(insert_calls[0])
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_dead_letter_write_fail_logged(self):
        """_save_dead_letter 写入数据库失败 → 记录日志不抛异常"""
        from core.saga import SagaOrchestrator, SagaStep
        with patch('core.saga.get_connection') as mock_get_conn, \
             patch('core.saga.logger') as mock_logger:
            mock_get_conn.side_effect = RuntimeError("数据库挂了")

            saga = SagaOrchestrator("test_dead_fail", [
                SagaStep("s1", lambda: True, lambda: (_ for _ in ()).throw(RuntimeError("补偿爆炸"))),
                SagaStep("s2", lambda: False, lambda: None),
            ])
            # run 本身不应抛异常
            result = saga.run()

        assert result['success'] is False
        mock_logger.error.assert_any_call('[Saga] dead_letter写入失败: 数据库挂了')

    def test_dead_letter_create_table_syntax(self):
        """死信表 DDL 语法验证"""
        from core.saga import SagaOrchestrator, SagaStep
        from datetime import datetime
        with patch('core.saga.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            saga = SagaOrchestrator("syntax_test", [
                SagaStep("s1", lambda: True, lambda: (_ for _ in ()).throw(RuntimeError("x"))),
                SagaStep("s2", lambda: False, lambda: None),
            ])
            saga.run()

        # DDL call
        ddl_call = mock_cursor.execute.call_args_list[0]
        assert 'CREATE TABLE IF NOT EXISTS saga_dead_letter' in str(ddl_call)
        assert 'saga_name VARCHAR(100)' in str(ddl_call)
        assert 'created_at DATETIME' in str(ddl_call)
