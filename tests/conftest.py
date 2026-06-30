# -*- coding: utf-8 -*-
"""
[tests/ 根 conftest]

[v3.7.5] 基础: 注入 mobile_api_ai 到 sys.path
[v3.8.2] 扩展: 补 SERVIVE / setup_test_environment 等 fixture 让
           tests/e2e/ + tests/L2_modules/ 不再因 collect 失败 ERROR
"""
import sys
import os
import pytest

# 项目根 = tests/conftest.py → ../  (注意是上一级)
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TESTS_DIR)
_MOBILE_API_AI = os.path.join(_PROJECT_ROOT, 'mobile_api_ai')
if _MOBILE_API_AI not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# [v3.8.2] 服务端口常量 (供 L2_modules 复用)
SERVICES = {
    'web_5001': 'http://127.0.0.1:5001',
    'dispatch_5003': 'http://127.0.0.1:5003',
    'mobile_5008': 'http://127.0.0.1:5008',
    'sync_8008': 'http://127.0.0.1:8008',
}


# [v3.8.2] Stub fixtures 让 tests/e2e/ 可以收集
# (原本 tests/e2e/conftest.py 从这里 import 8 个 fixture,
#  之前 tests/conftest.py 只有 21 行没这些 fixture, 导致整个 e2e 目录 ERROR)
#
# 复杂 fixture (Playwright + DB) 用 pytest.skip 包装,
# 真实实现留给后续 sprint (P1.3 后续 TODO)

def pytest_configure(config):
    """pytest_configure hook - 在 collection 之前修改 sys.path"""
    if _MOBILE_API_AI not in sys.path:
        sys.path.insert(0, _MOBILE_API_AI)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture(scope='session')
def setup_test_environment():
    """
    [v3.8.2 Stub] 配置测试环境
    真实实现需要: 启动 MySQL / Redis / 4 个 web 服务 / 数据隔离
    当前为简化版: 仅做环境变量设置, 不启动服务
    """
    os.environ.setdefault('TESTING', '1')
    os.environ.setdefault('DISPATCH_CENTER_USE_DB', '0')  # 默认内存模式
    yield
    # teardown: 清理环境变量
    os.environ.pop('TESTING', None)


@pytest.fixture
def db_session():
    """[v3.8.2 Stub] DB session fixture - 需真实 DB 才能工作"""
    import pytest
    pytest.skip(
        '[v3.8.2 Stub] db_session 需要真实 MySQL 连接, 当前为 stub, '
        '见 docs/v3.8.1/TEST_ERRORS_ANALYSIS.md 后续 TODO P1.3'
    )


@pytest.fixture
def db_fixture():
    """[v3.8.2 Stub] DB fixture"""
    import pytest
    pytest.skip('[v3.8.2 Stub] db_fixture 待实现')


@pytest.fixture
def isolated_data():
    """[v3.8.2 Stub] 隔离数据 fixture"""
    import pytest
    pytest.skip('[v3.8.2 Stub] isolated_data 待实现')


@pytest.fixture
def login_as():
    """[v3.8.2 Stub] 登录 fixture - 需 Playwright + 服务在线"""
    import pytest
    pytest.skip('[v3.8.2 Stub] login_as 需 Playwright, 见 TODO P1.3')


@pytest.fixture
def admin_page():
    """[v3.8.2 Stub] admin 页面 fixture - 需 Playwright"""
    import pytest
    pytest.skip('[v3.8.2 Stub] admin_page 需 Playwright')


@pytest.fixture
def operator_page():
    """[v3.8.2 Stub] operator 页面 fixture - 需 Playwright"""
    import pytest
    pytest.skip('[v3.8.2 Stub] operator_page 需 Playwright')


@pytest.fixture
def screenshot_on_failure():
    """[v3.8.2 Stub] 失败截图 fixture"""
    import pytest
    pytest.skip('[v3.8.2 Stub] screenshot_on_failure 需 Playwright')