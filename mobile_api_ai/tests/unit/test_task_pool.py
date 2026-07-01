# -*- coding: utf-8 -*-
"""
task_pool 单元测试

覆盖：
- TaskStatus/TaskType 枚举
- PREFIX_TO_PAGE / PAGE_TO_TYPES 映射
- Task 类
- SimpleMemoryStorage
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestEnums:
    """枚举测试"""

    def test_task_status_values(self):
        from container.task_pool import TaskStatus
        assert TaskStatus.PENDING.value == 'pending'
        assert TaskStatus.ASSIGNED.value == 'assigned'
        assert TaskStatus.IN_PROGRESS.value == 'in_progress'
        assert TaskStatus.COMPLETED.value == 'completed'
        assert TaskStatus.CANCELLED.value == 'cancelled'
        assert TaskStatus.FAILED.value == 'failed'

    def test_task_type_values(self):
        from container.task_pool import TaskType
        assert TaskType.REPORT.value == 'report'
        assert TaskType.QUALITY.value == 'quality'
        assert TaskType.MATERIAL.value == 'material'
        assert TaskType.APPROVAL.value == 'approval'
        assert TaskType.OTHER.value == 'other'


class TestPrefixMapping:
    """映射测试"""

    def test_prefix_to_page(self):
        from container.task_pool import PREFIX_TO_PAGE
        assert PREFIX_TO_PAGE['report'] == 'scan_report'
        assert PREFIX_TO_PAGE['quality'] == 'quality'
        assert PREFIX_TO_PAGE['material'] == 'material'

    def test_page_to_types(self):
        from container.task_pool import PAGE_TO_TYPES
        assert 'report' in PAGE_TO_TYPES['scan_report']
        assert PAGE_TO_TYPES['quality'] == ['quality']


class TestTask:
    """Task 类测试"""

    def test_init_basic(self):
        from container.task_pool import Task
        task = Task('report', '测试任务', {'x': 1})
        assert task.id is not None
        assert task.task_type == 'report'
        assert task.title == '测试任务'
        assert task.content == {'x': 1}
        assert task.status == 'pending'
        assert task.version == 1

    def test_init_with_optional(self):
        from container.task_pool import Task
        deadline = datetime(2026, 12, 31)
        task = Task(
            task_type='quality',
            title='质检',
            content={},
            operator_id='OP001',
            priority='high',
            deadline=deadline,
            related_order='ORD001',
            related_process='焊接',
            tags=['urgent']
        )
        assert task.operator_id == 'OP001'
        assert task.priority == 'high'
        assert task.deadline == deadline
        assert task.related_order == 'ORD001'
        assert task.tags == ['urgent']

    def test_to_dict(self):
        from container.task_pool import Task
        task = Task('report', 'test', {'x': 1})
        d = task.to_dict()
        assert d['task_type'] == 'report'
        assert d['title'] == 'test'
        assert d['status'] == 'pending'
        assert d['page_route'] == 'scan_report'

    def test_to_dict_with_deadline(self):
        from container.task_pool import Task
        task = Task('report', 'test', {}, deadline=datetime(2026, 12, 31))
        d = task.to_dict()
        assert d['deadline'] is not None
        assert '2026-12-31' in d['deadline']

    def test_to_dict_no_deadline(self):
        from container.task_pool import Task
        task = Task('report', 'test', {})
        d = task.to_dict()
        assert d['deadline'] is None

    def test_to_dict_with_times(self):
        from container.task_pool import Task
        task = Task('report', 'test', {})
        task.assigned_at = datetime.now()
        task.started_at = datetime.now()
        task.completed_at = datetime.now()
        d = task.to_dict()
        assert d['assigned_at'] is not None
        assert d['started_at'] is not None
        assert d['completed_at'] is not None

    def test_from_dict_minimal(self):
        from container.task_pool import Task
        data = {
            'task_type': 'report',
            'title': 'test',
            'content': {'x': 1}
        }
        task = Task.from_dict(data)
        assert task.task_type == 'report'
        assert task.status == 'pending'

    def test_from_dict_full(self):
        from container.task_pool import Task
        deadline = datetime(2026, 12, 31)
        data = {
            'id': 'T001',
            'task_type': 'quality',
            'title': 'test',
            'content': {'x': 1},
            'operator_id': 'OP001',
            'priority': 'high',
            'deadline': deadline.isoformat(),
            'related_order': 'ORD001',
            'tags': ['urgent'],
            'status': 'assigned',
            'version': 3,
            'created_at': datetime(2026, 1, 1).isoformat()
        }
        task = Task.from_dict(data)
        assert task.id == 'T001'
        assert task.operator_id == 'OP001'
        assert task.status == 'assigned'
        assert task.version == 3
        assert task.deadline == deadline

    def test_from_dict_no_deadline(self):
        from container.task_pool import Task
        data = {'task_type': 'report', 'title': 'test', 'content': {}}
        task = Task.from_dict(data)
        assert task.deadline is None


class TestSimpleMemoryStorage:
    """SimpleMemoryStorage 测试"""

    def setup_method(self):
        from container.task_pool import SimpleMemoryStorage
        self.storage = SimpleMemoryStorage()

    def test_save_and_get(self):
        self.storage.save_package({'id': 'P1', 'name': 'test'})
        result = self.storage.get_package('P1')
        assert result['name'] == 'test'

    def test_get_nonexistent(self):
        assert self.storage.get_package('P999') is None

    def test_get_packages(self):
        self.storage.save_package({'id': 'P1', 'status': 'pending', 'data_type': 'a'})
        self.storage.save_package({'id': 'P2', 'status': 'done', 'data_type': 'b'})
        results = self.storage.get_packages()
        assert len(results) == 2

    def test_get_packages_filter_status(self):
        self.storage.save_package({'id': 'P1', 'status': 'pending'})
        self.storage.save_package({'id': 'P2', 'status': 'done'})
        results = self.storage.get_packages(status='pending')
        assert len(results) == 1
        assert results[0]['id'] == 'P1'

    def test_get_packages_filter_data_type(self):
        self.storage.save_package({'id': 'P1', 'data_type': 'a'})
        self.storage.save_package({'id': 'P2', 'data_type': 'b'})
        results = self.storage.get_packages(data_type='a')
        assert len(results) == 1

    def test_get_packages_filter_operator(self):
        self.storage.save_package({'id': 'P1', 'target_operator': 'OP001'})
        self.storage.save_package({'id': 'P2', 'target_operator': 'OP002'})
        results = self.storage.get_packages(operator='OP001')
        assert len(results) == 1

    def test_get_packages_limit(self):
        for i in range(10):
            self.storage.save_package({'id': f'P{i}', 'created_at': f'2026-01-{i:02d}'})
        results = self.storage.get_packages(limit=3)
        assert len(results) == 3

    def test_delete_existing(self):
        self.storage.save_package({'id': 'P1'})
        assert self.storage.delete_package('P1') is True

    def test_delete_nonexistent(self):
        assert self.storage.delete_package('P999') is False


class TestTaskPool:
    """TaskPool 测试（内存模式）"""

    def test_init_memory_only(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            assert pool.storage is None
            assert pool.tasks == {}

    def test_init_with_storage(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', True):
            with patch('container.task_pool.create_storage') as mock_create:
                mock_storage = MagicMock()
                mock_storage.load_packages.return_value = []
                mock_create.return_value = mock_storage
                pool = TaskPool(storage_config={'type': 'mysql'})
                assert pool.storage is mock_storage

    def test_add_task(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            assert task.id in pool.tasks
            assert 'report' in pool.task_index
            assert task.id in pool.task_index['report']

    def test_add_task_with_optional(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task(
                'quality', 'test', {},
                operator_id='OP001',
                priority='high',
                related_order='ORD001'
            )
            assert task.operator_id == 'OP001'
            assert task.priority == 'high'

    def test_add_task_uses_default_route(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('unknown_type', 'test', {})
            assert task is not None

    def test_get_task(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            assert pool.get_task(task.id) is task

    def test_get_task_nonexistent(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            assert pool.get_task('nonexistent') is None

    def test_assign_task(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            result = pool.assign_task(task.id, 'OP001')
            assert result is True
            assert task.operator_id == 'OP001'
            assert task.status == 'assigned'

    def test_assign_already_assigned(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            pool.assign_task(task.id, 'OP001')
            result = pool.assign_task(task.id, 'OP002')
            assert result is False
            assert task.operator_id == 'OP001'

    def test_assign_nonexistent(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            assert pool.assign_task('nonexistent', 'OP001') is False

    def test_complete_task(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            pool.assign_task(task.id, 'OP001')
            result = pool.complete_task(task.id, {'data': 'x'})
            assert result is True
            assert task.status == 'completed'
            assert task.result == {'data': 'x'}
            assert task.completed_at is not None

    def test_complete_task_not_assigned(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            result = pool.complete_task(task.id, {})
            assert result is False

    def test_cancel_task(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            result = pool.cancel_task(task.id, 'reason')
            assert result is True
            assert task.status == 'cancelled'

    def test_cancel_completed_task(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            task = pool.add_task('report', 'test', {})
            pool.assign_task(task.id, 'OP001')
            pool.complete_task(task.id, {})
            result = pool.cancel_task(task.id)
            assert result is False

    def test_cancel_nonexistent(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            assert pool.cancel_task('nonexistent') is False

    def test_get_pending_tasks(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            pool.add_task('report', 't1', {})
            pool.add_task('quality', 't2', {})
            pool.add_task('material', 't3', {})
            pending = pool.get_pending_tasks(task_types=['report', 'quality'])
            assert len(pending) == 2

    def test_get_pending_tasks_all(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            pool.add_task('report', 't1', {})
            pool.add_task('quality', 't2', {})
            pending = pool.get_pending_tasks()
            assert len(pending) == 2

    def test_get_pending_tasks_limit(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            for i in range(20):
                pool.add_task('report', f't{i}', {})
            pending = pool.get_pending_tasks(limit=5)
            assert len(pending) == 5

    def test_count_tasks(self):
        from container.task_pool import TaskPool
        with patch('container.task_pool.STORAGE_LAYER_AVAILABLE', False):
            pool = TaskPool(storage_config={'type': 'memory'})
            pool.add_task('report', 't1', {})
            pool.add_task('report', 't2', {})
            assert pool.count_tasks() == 2
            assert pool.count_tasks(task_type='report') == 2
            assert pool.count_tasks(task_type='quality') == 0
