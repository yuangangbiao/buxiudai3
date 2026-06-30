# -*- coding: utf-8 -*-
"""
[v3.8.0] desktop_container_integration.py SQLite 移除测试

覆盖:
- 默认初始化走 MySQL ContainerCenter (无 SQLite)
- CONTAINER_CENTER_API_URL 设置时走 HTTP 客户端
- 老 db_path 参数被忽略 + WARNING 日志
- publish_report_task / publish_material_task / publish_quality_task 向后兼容
- get_all_tasks / get_task_by_id / get_task_count API 完整

策略:
- sys.modules 注入 fake container_center_client / container_center_v5 模块
- 每个测试重置 fake 类的 return_value, 避免跨测试污染
"""
import os
import sys
import types
import importlib.util
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _fresh_fakes():
    """每个测试都创建新的 MagicMock 类注入 sys.modules, 避免跨测试污染"""
    if 'desktop_container_integration_v380' in sys.modules:
        del sys.modules['desktop_container_integration_v380']

    fake_cc_client = types.ModuleType('fake_container_center_client')
    fake_cc_client.ContainerCenterClient = MagicMock()
    sys.modules['container_center_client'] = fake_cc_client

    fake_cc_v5 = types.ModuleType('fake_container_center_v5')
    fake_cc_v5.ContainerCenter = MagicMock()
    sys.modules['container_center_v5'] = fake_cc_v5

    yield {
        'ContainerCenterClient': fake_cc_client.ContainerCenterClient,
        'ContainerCenter': fake_cc_v5.ContainerCenter,
    }

    # teardown
    sys.modules.pop('container_center_client', None)
    sys.modules.pop('container_center_v5', None)
    sys.modules.pop('desktop_container_integration_v380', None)


def _load_module():
    """直接加载 desktop_container_integration.py 模块"""
    tests_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(tests_dir, 'desktop_container_integration.py')
    spec = importlib.util.spec_from_file_location(
        "desktop_container_integration_v380", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dci(_fresh_fakes):
    """加载 desktop_container_integration 模块"""
    return _load_module()


# ============ v3.8.0 关键改造点 ============

class TestV380SqliteRemoval:
    """[v3.8.0] SQLite 代码路径已移除"""

    def test_no_type_sqlite_runtime_in_source(self, dci):
        """源码运行时代码无 'sqlite' 硬编码（注释/docstring 除外）"""
        path = dci.__file__
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        import re
        runtime_lines = []
        for ln in source.split('\n'):
            stripped = ln.strip()
            if (stripped.startswith('#') or stripped.startswith('"""')
                    or stripped.startswith("'''")):
                continue
            if re.search(r"['\"]sqlite['\"]", stripped):
                runtime_lines.append(stripped)
        assert runtime_lines == [], (
            f"v3.8.0 SQLite 代码路径未清除: {runtime_lines}"
        )

    def test_default_init_uses_mysql(self, dci, _fresh_fakes):
        """默认初始化走 MySQL ContainerCenter（不传 sqlite type）"""
        cc_mock = _fresh_fakes['ContainerCenter']
        cc_instance = MagicMock(name='ContainerCenterInstance')
        cc_mock.return_value = cc_instance

        # 清空环境变量, 确保走 MySQL 路径
        env_backup = os.environ.pop('CONTAINER_CENTER_API_URL', None)
        env_backup2 = os.environ.pop('CONTAINER_URL', None)
        try:
            integration = dci.DesktopContainerIntegration()
        finally:
            if env_backup is not None:
                os.environ['CONTAINER_CENTER_API_URL'] = env_backup
            if env_backup2 is not None:
                os.environ['CONTAINER_URL'] = env_backup2

        assert integration._initialized is True
        assert integration._container_center is cc_instance
        # 验证 ContainerCenter() 调用时未传 type='sqlite'
        call_args = cc_mock.call_args
        assert call_args == () or 'type' not in (call_args.kwargs or {}), \
            f"v3.8.0 默认应不传 type 参数, 实际: {call_args}"

    def test_http_url_uses_client(self, dci, _fresh_fakes):
        """CONTAINER_CENTER_API_URL 设置时走 HTTP 客户端"""
        client_mock_cls = _fresh_fakes['ContainerCenterClient']
        client_instance = MagicMock(name='ClientInstance')
        client_mock_cls.return_value = client_instance

        os.environ['CONTAINER_CENTER_API_URL'] = 'http://localhost:5003'
        try:
            integration = dci.DesktopContainerIntegration()
        finally:
            os.environ.pop('CONTAINER_CENTER_API_URL', None)

        assert integration._initialized is True
        assert integration._center_client is client_instance
        assert integration._container_center is None
        client_mock_cls.assert_called_once_with(base_url='http://localhost:5003')


# ============ 向后兼容 ============

class TestBackwardCompat:
    """publish_*/get_* 公开 API 向后兼容（SQLite 移除后）"""

    def test_publish_report_task_signature(self, dci):
        assert callable(dci.DesktopContainerIntegration.publish_report_task)

    def test_publish_material_task_signature(self, dci):
        assert callable(dci.DesktopContainerIntegration.publish_material_task)

    def test_publish_quality_task_signature(self, dci):
        assert callable(dci.DesktopContainerIntegration.publish_quality_task)

    def test_get_all_tasks_signature(self, dci):
        assert callable(dci.DesktopContainerIntegration.get_all_tasks)

    def test_get_task_by_id_signature(self, dci):
        assert callable(dci.DesktopContainerIntegration.get_task_by_id)

    def test_get_task_count_signature(self, dci):
        assert callable(dci.DesktopContainerIntegration.get_task_count)

    def test_get_integration_function_exists(self, dci):
        assert callable(dci.get_integration)

    def test_reset_integration_function_exists(self, dci):
        assert callable(dci.reset_integration)


# ============ 业务行为 ============

class TestBusinessBehavior:
    """核心业务方法走 HTTP API 或 MySQL 路径"""

    def test_publish_report_via_http_client(self, dci, _fresh_fakes):
        """HTTP 客户端模式下, publish_report_task 调 _center_client.publish_task"""
        client_mock_cls = _fresh_fakes['ContainerCenterClient']
        client_instance = MagicMock(name='ClientInstance')
        client_instance.publish_task.return_value = {'task_id': 'T-NEW-001'}
        client_mock_cls.return_value = client_instance

        os.environ['CONTAINER_CENTER_API_URL'] = 'http://localhost:5003'
        try:
            integration = dci.DesktopContainerIntegration()
            result = integration.publish_report_task(
                order_no='WO-V380-001',
                process_name='拉丝',
                operator_id='OP001'
            )
        finally:
            os.environ.pop('CONTAINER_CENTER_API_URL', None)

        assert result == 'T-NEW-001'
        client_instance.publish_task.assert_called_once()
        call_kwargs = client_instance.publish_task.call_args.kwargs
        assert call_kwargs['task_type'] == 'report'
        assert call_kwargs['content']['order_no'] == 'WO-V380-001'

    def test_get_all_tasks_via_http_client(self, dci, _fresh_fakes):
        """HTTP 客户端模式下, get_all_tasks 调 _center_client.get_all_tasks"""
        client_mock_cls = _fresh_fakes['ContainerCenterClient']
        client_instance = MagicMock(name='ClientInstance')
        client_instance.get_all_tasks.return_value = [
            {'id': 'T-1', 'title': '报工A'},
            {'id': 'T-2', 'title': '报工B'},
        ]
        client_mock_cls.return_value = client_instance

        os.environ['CONTAINER_CENTER_API_URL'] = 'http://localhost:5003'
        try:
            integration = dci.DesktopContainerIntegration()
            tasks = integration.get_all_tasks(limit=50)
        finally:
            os.environ.pop('CONTAINER_CENTER_API_URL', None)

        assert len(tasks) == 2
        client_instance.get_all_tasks.assert_called_once_with(limit=50)

    def test_db_path_kwarg_warns_and_falls_back(self, dci, _fresh_fakes, caplog):
        """老 db_path 参数被忽略 + WARNING 日志"""
        import logging
        caplog.set_level(logging.WARNING)

        cc_mock = _fresh_fakes['ContainerCenter']
        cc_instance = MagicMock(name='ContainerCenterInstance')
        cc_mock.return_value = cc_instance

        env_backup = os.environ.pop('CONTAINER_CENTER_API_URL', None)
        env_backup2 = os.environ.pop('CONTAINER_URL', None)
        try:
            dci.DesktopContainerIntegration(db_path='/tmp/should_be_ignored.db')
        finally:
            if env_backup is not None:
                os.environ['CONTAINER_CENTER_API_URL'] = env_backup
            if env_backup2 is not None:
                os.environ['CONTAINER_URL'] = env_backup2

        warning_msgs = [r.message for r in caplog.records if r.levelname == 'WARNING']
        assert any('已移除 SQLite 支持' in m for m in warning_msgs), \
            f"未发现 SQLite 移除警告: {warning_msgs}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
