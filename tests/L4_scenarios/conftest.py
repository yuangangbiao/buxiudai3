# -*- coding: utf-8 -*-
"""
[v3.7.1] L4 业务场景测试 conftest
[v3.8.1] 统一清理模式 (conftest_helpers)

L4 业务场景测试通常是离线测试。
重写全局 conftest 的重型 fixture。
"""
import pytest
import os
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


@pytest.fixture
def setup_test_environment(request):
    yield


@pytest.fixture
def playwright_instance():
    yield MagicMock()


@pytest.fixture
def browser(playwright_instance):
    yield MagicMock()


@pytest.fixture
def context(browser):
    yield MagicMock()


@pytest.fixture
def page(context):
    yield MagicMock()


@pytest.fixture
def page_with_trace(context):
    yield MagicMock()


@pytest.fixture
def page_with_video(context):
    yield MagicMock()


@pytest.fixture
def admin_page(page, login_as):
    return page


@pytest.fixture
def operator_page(page, login_as):
    return page


@pytest.fixture
def login_as(page):
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


@pytest.fixture(autouse=True)
def l4_isolate_environment():
    os.environ.setdefault('L4_TEST_MODE', 'true')
    yield
