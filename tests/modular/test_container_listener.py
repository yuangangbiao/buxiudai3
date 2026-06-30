# -*- coding: utf-8 -*-
"""
container_event_listener.py 单元测试
"""

import pytest


class TestContainerEventListener:

    def test_listener_init(self):
        """验证监听器初始化"""
        from container_event_listener import ContainerEventListener

        listener = ContainerEventListener()
        assert listener is not None

    def test_is_ready_property(self):
        """验证监听器就绪状态"""
        from container_event_listener import ContainerEventListener

        listener = ContainerEventListener()
        assert listener.is_ready is not None
