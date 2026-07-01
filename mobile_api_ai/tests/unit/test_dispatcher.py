# -*- coding: utf-8 -*-
"""
dispatcher 单元测试

覆盖：
- DispatchResult 类
- Dispatcher 初始化
- register_handler
- dispatch / dispatch_task
- receive_result
- get_task_detail
- cancel_task
- 默认处理器（report/quality/material/approval）
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestDispatchResult:
    """DispatchResult 类测试"""

    def test_init(self):
        from container.dispatcher import DispatchResult
        r = DispatchResult(True, 'ok', {'x': 1})
        assert r.success is True
        assert r.message == 'ok'
        assert r.data == {'x': 1}
        assert isinstance(r.timestamp, datetime)

    def test_to_dict(self):
        from container.dispatcher import DispatchResult
        r = DispatchResult(True, 'ok', {'x': 1})
        d = r.to_dict()
        assert d['success'] is True
        assert d['message'] == 'ok'
        assert d['data'] == {'x': 1}
        assert 'timestamp' in d

    def test_default_data_none(self):
        from container.dispatcher import DispatchResult
        r = DispatchResult(False, 'fail')
        assert r.data is None


class TestDispatcherInit:
    """Dispatcher 初始化测试"""

    def test_init(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        d = Dispatcher(pool)
        assert d.pool is pool
        assert 'report' in d.handlers
        assert 'quality' in d.handlers
        assert 'material' in d.handlers
        assert 'approval' in d.handlers

    def test_register_default_handlers(self):
        from container.dispatcher import Dispatcher
        d = Dispatcher(MagicMock())
        assert callable(d.handlers['report'])
        assert callable(d.handlers['quality'])
        assert callable(d.handlers['material'])
        assert callable(d.handlers['approval'])

    def test_register_handler(self):
        from container.dispatcher import Dispatcher
        d = Dispatcher(MagicMock())
        handler = MagicMock()
        d.register_handler('custom', handler)
        assert d.handlers['custom'] is handler


class TestDispatch:
    """dispatch 测试"""

    def test_dispatch_success(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task1 = MagicMock()
        task1.id = 'T1'
        task1.to_dict.return_value = {'id': 'T1'}
        task2 = MagicMock()
        task2.id = 'T2'
        task2.to_dict.return_value = {'id': 'T2'}
        pool.get_pending_tasks.return_value = [task1, task2]
        pool.assign_task.return_value = True

        d = Dispatcher(pool)
        result = d.dispatch('OP001', max_count=5)
        assert result.success is True
        assert result.data['total'] == 2

    def test_dispatch_with_filter(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.get_pending_tasks.return_value = []
        d = Dispatcher(pool)
        d.dispatch('OP001', task_types=['report'])
        args = pool.get_pending_tasks.call_args.args
        assert args[1] == ['report']

    def test_dispatch_respects_max_count(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        tasks = []
        for i in range(10):
            t = MagicMock()
            t.id = f'T{i}'
            t.to_dict.return_value = {'id': f'T{i}'}
            tasks.append(t)
        pool.get_pending_tasks.return_value = tasks
        pool.assign_task.return_value = True

        d = Dispatcher(pool)
        result = d.dispatch('OP001', max_count=3)
        assert result.data['total'] == 3

    def test_dispatch_assign_failure_skipped(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        t1 = MagicMock(); t1.id = 'T1'; t1.to_dict.return_value = {'id': 'T1'}
        t2 = MagicMock(); t2.id = 'T2'; t2.to_dict.return_value = {'id': 'T2'}
        pool.get_pending_tasks.return_value = [t1, t2]
        pool.assign_task.side_effect = [True, False]
        d = Dispatcher(pool)
        result = d.dispatch('OP001', max_count=5)
        assert result.data['total'] == 1

    def test_dispatch_default_task_types(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.get_pending_tasks.return_value = []
        d = Dispatcher(pool)
        d.dispatch('OP001')
        args = pool.get_pending_tasks.call_args.args
        assert 'report' in args[1]


class TestDispatchTask:
    """dispatch_task 测试"""

    def test_task_not_found(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.get_task.return_value = None
        d = Dispatcher(pool)
        result = d.dispatch_task('T999', 'OP001')
        assert result.success is False

    def test_task_wrong_status(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'completed'
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        result = d.dispatch_task('T1', 'OP001')
        assert result.success is False
        assert '状态' in result.message

    def test_dispatch_task_success(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'pending'
        task.to_dict.return_value = {'id': 'T1'}
        pool.get_task.return_value = task
        pool.assign_task.return_value = True
        d = Dispatcher(pool)
        result = d.dispatch_task('T1', 'OP001')
        assert result.success is True

    def test_dispatch_task_assign_fail(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'pending'
        pool.get_task.return_value = task
        pool.assign_task.return_value = False
        d = Dispatcher(pool)
        result = d.dispatch_task('T1', 'OP001')
        assert result.success is False


class TestReceiveResult:
    """receive_result 测试"""

    def test_task_not_found(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.get_task.return_value = None
        d = Dispatcher(pool)
        result = d.receive_result('T999', {})
        assert result.success is False

    def test_already_completed(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'completed'
        task.id = 'T1'
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        result = d.receive_result('T1', {})
        assert result.success is False
        assert '已完成' in result.message

    def test_with_handler(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'pending'
        task.task_type = 'report'
        task.id = 'T1'
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        d.register_handler('report', lambda t, r: {'custom': 'result'})
        result = d.receive_result('T1', {'data': 'x'})
        assert result.success is True
        assert result.data == {'custom': 'result'}
        assert pool.complete_task.called

    def test_without_handler(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'pending'
        task.task_type = 'unknown_type'
        task.id = 'T1'
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        result = d.receive_result('T1', {'data': 'x'})
        assert result.success is True

    def test_handler_exception(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.status = 'pending'
        task.task_type = 'custom'
        task.id = 'T1'
        pool.get_task.return_value = task
        d = Dispatcher(pool)

        def bad_handler(t, r):
            raise Exception('handler error')

        d.register_handler('custom', bad_handler)
        result = d.receive_result('T1', {})
        assert result.success is False
        assert '处理结果失败' in result.message


class TestGetTaskDetail:
    """get_task_detail 测试"""

    def test_not_found(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.get_task.return_value = None
        d = Dispatcher(pool)
        result = d.get_task_detail('T999')
        assert result.success is False

    def test_no_operator_filter(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.to_dict.return_value = {'id': 'T1'}
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        result = d.get_task_detail('T1')
        assert result.success is True

    def test_with_operator_match(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.operator_id = 'OP001'
        task.to_dict.return_value = {'id': 'T1'}
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        result = d.get_task_detail('T1', 'OP001')
        assert result.success is True

    def test_with_operator_mismatch(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        task = MagicMock()
        task.operator_id = 'OP002'
        pool.get_task.return_value = task
        d = Dispatcher(pool)
        result = d.get_task_detail('T1', 'OP001')
        assert result.success is False
        assert '无权访问' in result.message


class TestCancelTask:
    """cancel_task 测试"""

    def test_cancel_success(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.cancel_task.return_value = True
        d = Dispatcher(pool)
        result = d.cancel_task('T1', 'reason')
        assert result.success is True
        assert pool.cancel_task.called

    def test_cancel_failure(self):
        from container.dispatcher import Dispatcher
        pool = MagicMock()
        pool.cancel_task.return_value = False
        d = Dispatcher(pool)
        result = d.cancel_task('T1')
        assert result.success is False


class TestDefaultHandlers:
    """默认处理器测试"""

    def test_handle_report(self):
        from container.dispatcher import Dispatcher
        d = Dispatcher(MagicMock())
        task = MagicMock()
        task.id = 'T1'
        task.related_order = 'ORD001'
        task.related_process = '焊接'
        task.operator_id = 'OP001'
        task.content = {'record_id': 'R1'}
        result = d._handle_report_result(task, {'completed_qty': 100, 'status': 'done'})
        assert result['action'] == 'report_completed'
        assert result['order_no'] == 'ORD001'
        assert result['quantity'] == 100

    def test_handle_quality(self):
        from container.dispatcher import Dispatcher
        d = Dispatcher(MagicMock())
        task = MagicMock()
        task.id = 'T1'
        task.related_order = 'ORD001'
        task.operator_id = 'OP001'
        task.content = {'order_id': 'O1'}
        result = d._handle_quality_result(task, {'result': 'pass'})
        assert result['action'] == 'quality_completed'
        assert result['result'] == 'pass'

    def test_handle_material(self):
        from container.dispatcher import Dispatcher
        d = Dispatcher(MagicMock())
        task = MagicMock()
        task.id = 'T1'
        task.related_order = 'ORD001'
        task.operator_id = 'OP001'
        task.content = {}
        result = d._handle_material_result(task, {'material': '钢板', 'qty': 50})
        assert result['action'] == 'material_delivered'

    def test_handle_approval(self):
        from container.dispatcher import Dispatcher
        d = Dispatcher(MagicMock())
        task = MagicMock()
        task.id = 'T1'
        task.related_order = 'ORD001'
        task.operator_id = 'OP001'
        task.content = {}
        result = d._handle_approval_result(task, {'approved': True})
        assert result['action'] == 'approval_completed'
