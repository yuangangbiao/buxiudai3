# -*- coding: utf-8 -*-
"""
e2e conftest 协调 - 修复 A3/A6

与 tests/conftest.py 协调，避免 fixture 冲突。
- 不重复定义全局 fixture
- 复用 tests.conftest 的 db/page/login_as 等
- 仅定义 e2e 特有的辅助 fixture
"""
import pytest


# 重新导出全局 fixture，让 e2e 测试直接使用
from tests.conftest import (
    setup_test_environment,
    db_session,
    db_fixture,
    isolated_data,
    login_as,
    admin_page,
    operator_page,
    screenshot_on_failure,
)


# e2e 特有 fixture
@pytest.fixture
def e2e_client():
    """e2e API 客户端"""
    from tests.core.api_client import APIClient
    return APIClient('desktop_web')


@pytest.fixture
def admin_session():
    """5008 admin 会话（X-User-Id）"""
    import requests
    sess = requests.Session()
    sess.headers.update({'Content-Type': 'application/json', 'X-User-Id': '1'})
    return sess


@pytest.fixture
def worker_session():
    """5008 worker 会话（X-User-Id）"""
    import requests
    sess = requests.Session()
    sess.headers.update({'Content-Type': 'application/json', 'X-User-Id': 'YuanGangBiao'})
    return sess


@pytest.fixture
def viewer_session():
    """5008 viewer 会话（X-User-Id）"""
    import requests
    sess = requests.Session()
    sess.headers.update({'Content-Type': 'application/json', 'X-User-Id': 'ZhaoXiaoMing'})
    return sess


@pytest.fixture
def unique_order_no():
    """生成唯一工单号"""
    import time
    return f'E2E-ORDER-{int(time.time() * 1000)}'


@pytest.fixture
def e2e_dispatcher_client():
    """5003 调度 API 客户端"""
    from tests.core.api_client import APIClient
    return APIClient('dispatch')


@pytest.fixture
def e2e_mobile_client():
    """5008 移动 API 客户端"""
    from tests.core.api_client import APIClient
    return APIClient('mobile')


__all__ = [
    'setup_test_environment',
    'db_session', 'db_fixture', 'isolated_data',
    'login_as', 'admin_page', 'operator_page',
    'screenshot_on_failure',
    'e2e_client', 'e2e_dispatcher_client', 'e2e_mobile_client',
]
