# -*- coding: utf-8 -*-
"""
task_recall_service.py 单元测试
"""

import pytest


class TestTaskRecallService:

    def test_service_init(self):
        """验证服务初始化"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        assert svc is not None
        assert hasattr(svc, 'recall_task')
        assert hasattr(svc, 'can_recall')
        assert hasattr(svc, 'get_recallable_statuses')

    def test_is_available(self):
        """验证服务可用性检查"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        available = svc.is_available()
        assert isinstance(available, bool)

    def test_get_recallable_statuses(self):
        """验证获取可撤回状态列表"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        statuses = svc.get_recallable_statuses()
        assert isinstance(statuses, list)
        assert 'pending' in statuses
        assert 'distributed' in statuses

    def test_can_recall_when_disabled(self):
        """验证功能禁用时不可撤回"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        svc._enabled = False

        result = svc.can_recall('task_123')
        assert not result

    def test_can_recall_nonexistent_task(self):
        """验证不存在任务不可撤回"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        svc._enabled = True
        svc._integration_available = False

        result = svc.can_recall('nonexistent_task')
        assert not result

    def test_recall_task_when_disabled(self):
        """验证功能禁用时撤回失败"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        svc._enabled = False

        result = svc.recall_task('task_123')
        assert not result

    def test_recall_task_no_integration(self):
        """验证集成不可用时撤回失败"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        svc._enabled = True
        svc._integration_available = False

        result = svc.recall_task('task_123')
        assert not result

    def test_get_tasks_by_order(self):
        """验证获取订单任务"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        svc._integration_available = False

        tasks = svc.get_tasks_by_order('ORD123')
        assert isinstance(tasks, list)

    def test_get_recallable_tasks(self):
        """验证获取可撤回任务"""
        from task_recall_service import TaskRecallService

        svc = TaskRecallService()
        svc._integration_available = False

        tasks = svc.get_recallable_tasks()
        assert isinstance(tasks, list)


class TestTaskRecallServiceSingleton:

    def test_get_task_recall_service(self):
        """验证获取全局实例"""
        from task_recall_service import get_task_recall_service, reset_task_recall_service

        reset_task_recall_service()
        svc1 = get_task_recall_service()
        svc2 = get_task_recall_service()
        assert svc1 is svc2

    def test_reset_task_recall_service(self):
        """验证重置功能"""
        from task_recall_service import get_task_recall_service, reset_task_recall_service

        svc1 = get_task_recall_service()
        reset_task_recall_service()
        svc2 = get_task_recall_service()
        assert svc1 is not svc2
