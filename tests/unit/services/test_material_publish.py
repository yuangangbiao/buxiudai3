# -*- coding: utf-8 -*-
"""
material_publish_service.py 单元测试
"""

import pytest


class TestMaterialPublishService:

    def test_service_init(self):
        """验证服务初始化"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        assert service is not None
        assert hasattr(service, 'is_enabled')
        assert hasattr(service, 'get_prepared_materials')
        assert hasattr(service, 'publish_requirements')

    def test_is_enabled(self):
        """验证功能开启检查"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        enabled = service.is_enabled()
        assert isinstance(enabled, bool)

    def test_is_available(self):
        """验证服务可用性检查"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        available = service.is_available()
        assert isinstance(available, bool)

    def test_get_prepared_materials(self):
        """验证获取备料列表（无数据时）"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        materials = service.get_prepared_materials(order_id=0, process_id=0)
        assert isinstance(materials, list)

    def test_get_selected_materials(self):
        """验证获取已勾选物料"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        selected = service.get_selected_materials(order_id=0, process_id=0)
        assert isinstance(selected, list)

    def test_register_event_handler(self):
        """验证事件处理器注册"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        result = service.register_event_handler()
        assert isinstance(result, bool)


class TestMaterialPublishServiceMocked:

    def test_handle_material_prepared_with_disabled(self):
        """验证功能关闭时处理"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()
        service._enabled = False

        event_data = {
            'order_id': 1,
            'process_id': 1
        }

        service.handle_material_prepared('material:prepared', event_data)

    def test_handle_material_prepared_with_missing_data(self):
        """验证数据不完整时处理"""
        from material_publish_service import MaterialPublishService

        service = MaterialPublishService()

        incomplete_data = {}

        service.handle_material_prepared('material:prepared', incomplete_data)
