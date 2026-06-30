# -*- coding: utf-8 -*-
"""
manual_publish_service.py 单元测试
"""

import pytest


class TestManualPublishService:

    def test_service_init(self):
        """验证服务初始化"""
        from manual_publish_service import ManualPublishService

        svc = ManualPublishService()
        assert svc is not None
        assert hasattr(svc, 'publish_single')
        assert hasattr(svc, 'publish_batch')
        assert hasattr(svc, 'get_publishable_processes')

    def test_is_available(self):
        """验证服务可用性检查"""
        from manual_publish_service import ManualPublishService

        svc = ManualPublishService()
        available = svc.is_available()
        assert isinstance(available, bool)

    def test_publish_single_when_disabled(self):
        """验证功能禁用时发布"""
        from manual_publish_service import ManualPublishService

        svc = ManualPublishService()
        svc._enabled = False

        result = svc.publish_single(
            order_no='TEST001',
            process_name='编织'
        )
        assert not result

    def test_publish_single_when_auto_mode(self):
        """验证自动模式下拒绝发布"""
        from manual_publish_service import ManualPublishService
        from publish_mode_manager import get_publish_mode_manager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = get_publish_mode_manager()
        mgr.set_mode('auto')

        svc = ManualPublishService()
        svc._enabled = True

        result = svc.publish_single(
            order_no='TEST002',
            process_name='编织'
        )
        assert not result

    def test_publish_single_no_integration(self):
        """验证集成不可用时发布失败"""
        from manual_publish_service import ManualPublishService
        from publish_mode_manager import get_publish_mode_manager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = get_publish_mode_manager()
        mgr.set_mode('manual')

        svc = ManualPublishService()
        svc._enabled = True
        svc._integration_available = False

        result = svc.publish_single(
            order_no='TEST003',
            process_name='编织'
        )
        assert not result

    def test_publish_batch_empty_list(self):
        """验证空列表批量发布"""
        from manual_publish_service import ManualPublishService

        svc = ManualPublishService()
        svc._enabled = True
        svc._integration_available = True

        result = svc.publish_batch(
            order_no='TEST004',
            process_list=[]
        )
        assert result == []

    def test_get_publishable_processes(self):
        """验证获取可发布工序"""
        from manual_publish_service import ManualPublishService

        svc = ManualPublishService()
        processes = svc.get_publishable_processes()
        assert isinstance(processes, list)


class TestManualPublishServiceSingleton:

    def test_get_manual_publish_service(self):
        """验证获取全局实例"""
        from manual_publish_service import get_manual_publish_service, reset_manual_publish_service

        reset_manual_publish_service()
        svc1 = get_manual_publish_service()
        svc2 = get_manual_publish_service()
        assert svc1 is svc2

    def test_reset_manual_publish_service(self):
        """验证重置功能"""
        from manual_publish_service import get_manual_publish_service, reset_manual_publish_service

        svc1 = get_manual_publish_service()
        reset_manual_publish_service()
        svc2 = get_manual_publish_service()
        assert svc1 is not svc2
