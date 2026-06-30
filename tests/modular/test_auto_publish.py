# -*- coding: utf-8 -*-
"""
auto_publish_service.py 单元测试
"""

import pytest


class TestAutoPublishService:

    def test_service_init(self):
        """验证服务初始化"""
        from auto_publish_service import AutoPublishService

        service = AutoPublishService()
        assert service is not None
        assert hasattr(service, 'is_auto_publish_enabled')
        assert hasattr(service, 'should_auto_publish')
        assert hasattr(service, 'publish_task')

    def test_is_auto_publish_enabled(self):
        """验证开关状态检查"""
        from auto_publish_service import AutoPublishService

        service = AutoPublishService()
        enabled = service.is_auto_publish_enabled()
        assert isinstance(enabled, bool)

    def test_should_auto_publish(self):
        """验证自动发布判断"""
        from auto_publish_service import AutoPublishService
        from core.events import EventType

        service = AutoPublishService()
        should = service.should_auto_publish(EventType.PRODUCTION_CONFIRMED)
        assert isinstance(should, bool)

        should_not = service.should_auto_publish('invalid:event')
        assert not should_not

    def test_is_available(self):
        """验证服务可用性检查"""
        from auto_publish_service import AutoPublishService

        service = AutoPublishService()
        available = service.is_available()
        assert isinstance(available, bool)

    def test_get_retry_config(self):
        """验证重试配置获取"""
        from auto_publish_service import AutoPublishService

        service = AutoPublishService()
        retry_config = service._get_retry_config()
        assert isinstance(retry_config, dict)
        assert 'retry_count' in retry_config
        assert 'retry_interval' in retry_config

    def test_register_event_handler(self):
        """验证事件处理器注册"""
        from auto_publish_service import AutoPublishService

        service = AutoPublishService()
        result = service.register_event_handler()
        assert isinstance(result, bool)


class TestAutoPublishServiceMocked:

    def test_handle_production_confirmed_with_disabled(self):
        """验证开关关闭时处理排产确认"""
        from auto_publish_service import AutoPublishService
        from modular_config import ModularConfig

        ModularConfig.set_auto_publish_enabled(False)

        service = AutoPublishService()
        service._auto_publish_enabled = False

        event_data = {
            'order_id': 1,
            'production_id': 1,
            'process_id': 1
        }

        service.handle_production_confirmed('production:confirmed', event_data)

    def test_handle_production_confirmed_with_missing_data(self):
        """验证数据不完整时处理"""
        from auto_publish_service import AutoPublishService

        service = AutoPublishService()

        incomplete_data = {
            'order_id': 1
        }

        service.handle_production_confirmed('production:confirmed', incomplete_data)
