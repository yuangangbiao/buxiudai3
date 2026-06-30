# -*- coding: utf-8 -*-
"""
[v3.7.0] L1 冒烟测试 conftest
[v3.8.1] 统一清理模式 (conftest_helpers)

L1 冒烟测试是离线测试，不依赖真实服务和浏览器。
重写全局 conftest.py 的重型 fixture，避免健康检查和浏览器启动卡死测试。
"""
import pytest
import os
import sys
from unittest.mock import MagicMock

# [v3.8.1] 统一从 conftest_helpers 导入清理逻辑
try:
    from conftest_helpers import ensure_sys_path, clean_polluting_modules
    _HAS_HELPERS = True
except ImportError:
    try:
        from tests.conftest_helpers import ensure_sys_path, clean_polluting_modules
        _HAS_HELPERS = True
    except ImportError:
        _HAS_HELPERS = False

# [v3.8.1] 统一 sys.modules 清理 hook
if _HAS_HELPERS:
    try:
        from conftest_helpers import pytest_pycollect_makemodule, pytest_collection_modifyitems
    except ImportError:
        from tests.conftest_helpers import pytest_pycollect_makemodule, pytest_collection_modifyitems


# ==================== 屏蔽全局重型 fixture ====================
# 阻止 tests/conftest.py 的以下 fixture 影响 L1 测试：
# - setup_test_environment: 健康检查 + DB 连接
# - playwright_instance / browser / context: 浏览器启动
# - admin_page / operator_page: 登录

@pytest.fixture
def setup_test_environment(request):
    """L1 版本：跳过健康检查和 DB 准备（mock 即可）"""
    yield


@pytest.fixture
def playwright_instance():
    """L1 不需要浏览器"""
    yield MagicMock()


@pytest.fixture
def browser(playwright_instance):
    yield MagicMock()


@pytest.fixture
def context(browser):
    yield MagicMock()


@pytest.fixture
def page(context):
    p = MagicMock()
    p.set_default_timeout = MagicMock()
    p.set_default_navigation_timeout = MagicMock()
    yield p


@pytest.fixture
def page_with_trace(context):
    yield MagicMock()


@pytest.fixture
def page_with_video(context):
    yield MagicMock()


@pytest.fixture
def admin_page(page, login_as):
    """L1 mock 版本"""
    return page


@pytest.fixture
def operator_page(page, login_as):
    return page


@pytest.fixture
def login_as(page):
    """L1 mock 版本"""
    def _login(role='admin'):
        from tests.fixtures.users import get_user
        return get_user(role)
    return _login


@pytest.fixture
def retry_helper():
    def _retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    return _retry


@pytest.fixture
def db_session():
    return MagicMock()


@pytest.fixture
def db_fixture():
    return MagicMock()


@pytest.fixture
def isolated_data():
    class Ctx:
        def make_test_order(self, **kwargs):
            from tests.fixtures.orders import make_test_order
            return make_test_order(**kwargs)
        def cleanup(self):
            pass
    return Ctx()


@pytest.fixture
def screenshot_on_failure(request):
    yield


# ==================== L1 特有 fixture ====================

@pytest.fixture(autouse=True)
def l1_isolate_environment():
    """L1 测试环境隔离 - 不连接真实服务"""
    # 确保 L1 测试不连接 MySQL
    os.environ.setdefault('L1_TEST_MODE', 'true')
    yield
