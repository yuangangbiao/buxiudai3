# -*- coding: utf-8 -*-
"""
[v3.7.5] dispatch_center.publisher 单元测试

[注意] 使用 importlib 直接加载 publisher，绕过 dispatch_center.__init__.py
原因：__init__.py 有 pre-existing import 问题
"""
import sys
import os
import importlib.util
import pytest


def _load_publisher_directly():
    """直接加载 publisher.py，绕过 __init__.py"""
    publisher_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'mobile_api_ai', 'dispatch_center', 'publisher.py'
    )
    spec = importlib.util.spec_from_file_location("_publisher_module", publisher_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def publisher_module():
    """加载 publisher 模块"""
    return _load_publisher_directly()


class TestPublisherModule:
    """publisher 模块测试"""

    def test_get_publisher_report(self, publisher_module):
        """获取 report publisher"""
        p = publisher_module.get_publisher('report')
        assert p is not None
        assert p.name == 'report'

    def test_get_publisher_material(self, publisher_module):
        """获取 material publisher"""
        p = publisher_module.get_publisher('material')
        assert p is not None
        assert p.name == 'material'

    def test_get_publisher_task_recall(self, publisher_module):
        """获取 task_recall publisher"""
        p = publisher_module.get_publisher('task_recall')
        assert p is not None
        assert p.name == 'task_recall'

    def test_get_publisher_invalid_type(self, publisher_module):
        """无效 publisher_type 应抛 ValueError"""
        with pytest.raises(ValueError, match="未知"):
            publisher_module.get_publisher('invalid_type')

    def test_singleton_pattern(self, publisher_module):
        """单例模式"""
        p1 = publisher_module.get_publisher('report')
        p2 = publisher_module.get_publisher('report')
        assert p1 is p2

    def test_publish_default(self, publisher_module):
        """publish 默认返回 True"""
        p = publisher_module.get_publisher('report')
        assert p.publish({'key': 'value'}) is True

    def test_recall_default(self, publisher_module):
        """recall 默认返回 True"""
        p = publisher_module.get_publisher('report')
        assert p.recall('T001') is True


class TestBackwardCompatibility:
    """向后兼容测试"""

    def test_get_integration_emits_warning(self, publisher_module):
        """get_integration() 发出 DeprecationWarning"""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            publisher_module.get_integration()

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert 'get_integration' in str(w[0].message)

    def test_get_integration_returns_publisher(self, publisher_module):
        """get_integration() 返回 report publisher"""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            integration = publisher_module.get_integration()
            expected = publisher_module.get_publisher('report')

        assert integration is expected

    def test_module_exports(self, publisher_module):
        """模块正确导出"""
        expected = {
            'BasePublisher', 'ReportPublisher', 'MaterialPublisher',
            'TaskRecallPublisher', 'get_publisher', 'get_integration',
        }
        for name in expected:
            assert hasattr(publisher_module, name), f"缺少导出: {name}"
