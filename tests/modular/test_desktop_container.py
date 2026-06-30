# -*- coding: utf-8 -*-
"""
[v3.7.5 迁移] dispatch_center.publisher 单元测试

[Q-B6 2026-06-25] 原文件测试 desktop_container_integration.DesktopContainerIntegration
已迁移到 dispatch_center.publisher（新 API）
"""
import pytest


class TestPublisherIntegration:
    """publisher 集成测试（v3.7.5 替代原 DesktopContainerIntegration 测试）"""

    def test_report_publisher_init(self):
        """report publisher 初始化"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher
        p = get_publisher('report')
        assert p is not None
        assert p.name == 'report'

    def test_material_publisher_init(self):
        """material publisher 初始化"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher
        p = get_publisher('material')
        assert p is not None
        assert p.name == 'material'

    def test_task_recall_publisher_init(self):
        """task_recall publisher 初始化"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher
        p = get_publisher('task_recall')
        assert p is not None
        assert p.name == 'task_recall'

    def test_publish_method(self):
        """publish 方法"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher
        p = get_publisher('report')
        result = p.publish({'order_no': 'WO202606250001', 'qty': 100})
        assert result is True

    def test_recall_method(self):
        """recall 方法"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher
        p = get_publisher('task_recall')
        result = p.recall('T202606250001')
        assert result is True

    def test_singleton_per_type(self):
        """同类型 publisher 单例"""
        from mobile_api_ai.dispatch_center.publisher import get_publisher
        p1 = get_publisher('report')
        p2 = get_publisher('report')
        assert p1 is p2
