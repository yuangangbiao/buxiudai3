# -*- coding: utf-8 -*-
"""
Pytest配置：共享 fixtures — 父项目路径注入（测试环境下 core.config 等需从父项目加载）
"""
import os, sys
_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
import sys
from unittest.mock import MagicMock, patch
import pytest


# [v3.8.2] Stub fixtures (补充) — 让 tests/e2e/conftest.py 的 from tests.conftest import 工作
# 背景: tests/e2e/conftest.py 从 tests.conftest import 8 个 fixture,
#       但 sys.path[0] = mobile_api_ai, Python 解析 tests.conftest 时优先找到 mobile_api_ai/tests/conftest.py
# 修复: 在这里也提供同样的 stub fixtures (与 tests/conftest.py 保持一致)
SERVICES = {
    'web_5001': 'http://127.0.0.1:5001',
    'dispatch_5003': 'http://127.0.0.1:5003',
    'mobile_5008': 'http://127.0.0.1:5008',
    'sync_8008': 'http://127.0.0.1:8008',
}


@pytest.fixture(scope='session')
def setup_test_environment():
    """[v3.8.2 Stub] 同 tests/conftest.py"""
    os.environ.setdefault('TESTING', '1')
    os.environ.setdefault('DISPATCH_CENTER_USE_DB', '0')
    yield
    os.environ.pop('TESTING', None)


@pytest.fixture
def db_session():
    """[v3.8.2 Stub] 同 tests/conftest.py"""
    pytest.skip('[v3.8.2 Stub] db_session 需真实 MySQL')


@pytest.fixture
def db_fixture():
    """[v3.8.2 Stub]"""
    pytest.skip('[v3.8.2 Stub] db_fixture 待实现')


@pytest.fixture
def isolated_data():
    """[v3.8.2 Stub]"""
    pytest.skip('[v3.8.2 Stub] isolated_data 待实现')


@pytest.fixture
def login_as():
    """[v3.8.2 Stub]"""
    pytest.skip('[v3.8.2 Stub] login_as 需 Playwright')


@pytest.fixture
def admin_page():
    """[v3.8.2 Stub]"""
    pytest.skip('[v3.8.2 Stub] admin_page 需 Playwright')


@pytest.fixture
def operator_page():
    """[v3.8.2 Stub]"""
    pytest.skip('[v3.8.2 Stub] operator_page 需 Playwright')


@pytest.fixture
def screenshot_on_failure():
    """[v3.8.2 Stub]"""
    pytest.skip('[v3.8.2 Stub] screenshot_on_failure 需 Playwright')


def _fix_syspath():
    """Ensure root dir is at sys.path[0] so models/* and constants resolve correctly."""
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (_root, _test_dir):
        while p in sys.path:
            sys.path.remove(p)
    sys.path.insert(0, _root)
    sys.path.insert(1, _test_dir)
    # If wrong constants was cached, purge so it's reloaded from root
    if 'constants' in sys.modules:
        if not hasattr(sys.modules['constants'], 'OrderStatus'):
            del sys.modules['constants']


# Session-level fix (may be overwritten by collection)
def pytest_sessionstart(session):
    _fix_syspath()


# Per-test fix: runs right before each test, AFTER all collection path injection
def pytest_runtest_setup(item):
    _fix_syspath()
    # Warm-import models.database with correct sys.path so the transitive
    # import chain (models.__init__ -> models.order -> constants.OrderStatus)
    # completes with root at sys.path[0].  This avoids ImportError when
    # mock_db fixture later does patch('models.database.get_connection')
    # which short-circuits via sys.modules on subsequent lookups.
    if 'models.database' not in sys.modules:
        try:
            import models.database  # noqa: F811
        except ImportError:
            pass


@pytest.fixture
def mock_db():
    """
    Mock database connection fixture.
    Patches both models.database.get_connection and models.base_dao.get_connection.
    """
    with patch('models.database.get_connection') as mock_db_fn, \
         patch('models.base_dao.get_connection') as mock_base_fn:
        mock_conn = MagicMock(name='mock_connection')
        mock_cursor = MagicMock(name='mock_cursor')
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.__exit__.return_value = None
        mock_conn.commit.return_value = None
        mock_conn.close.return_value = None
        mock_db_fn.return_value = mock_conn
        mock_base_fn.return_value = mock_conn

        yield {
            'conn': mock_conn,
            'cursor': mock_cursor,
        }


@pytest.fixture
def mock_api_client():
    """
    Mock ContainerCenterClient API fixture.
    Patches container_center.client.ContainerCenterClient and
    sets up common method return values with sample data.
    """
    from tests.fixtures.mock_api_data import (
        SAMPLE_WORK_ORDER,
        SAMPLE_WORK_ORDERS,
        SAMPLE_OPERATORS,
        SAMPLE_MESSAGE_RESPONSE,
        SAMPLE_DISTRIBUTE_RESPONSE,
        SAMPLE_QUERY_RESPONSE,
        SAMPLE_EMPTY_RESPONSE,
    )

    mock_client = MagicMock(name='ContainerCenterClient')

    mock_client.query_documents.return_value = SAMPLE_QUERY_RESPONSE
    mock_client.get_document.return_value = SAMPLE_WORK_ORDER
    mock_client.create_document.return_value = SAMPLE_WORK_ORDER
    mock_client.update_document.return_value = SAMPLE_WORK_ORDER
    mock_client.delete_document.return_value = True
    mock_client.send_message.return_value = SAMPLE_MESSAGE_RESPONSE
    mock_client.distribute.return_value = SAMPLE_DISTRIBUTE_RESPONSE
    mock_client.get_operators.return_value = SAMPLE_OPERATORS
    mock_client._request.return_value = {'code': 0, 'message': 'success'}

    with patch('container_center.client.ContainerCenterClient', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_storage():
    """
    Mock storage layer fixture.
    Creates a MagicMock implementing BaseStorage interface methods
    and patches StorageFactory to return it.
    """
    from tests.fixtures.mock_storage_data import (
        SAMPLE_PACKAGE,
        SAMPLE_DISPATCH_COMMAND,
        SAMPLE_PROCESS_RECORD,
        SAMPLE_SUB_STEP,
        SAMPLE_COLLECTION_RECORD,
        SAMPLE_SCHEDULE_RECORD,
        SAMPLE_COST,
    )

    storage = MagicMock(name='BaseStorage')

    storage.connect.return_value = True
    storage.disconnect.return_value = None
    storage.health_check.return_value = {'status': 'healthy'}

    storage.save_package.return_value = True
    storage.get_package.return_value = SAMPLE_PACKAGE
    storage.get_packages.return_value = [SAMPLE_PACKAGE]
    storage.update_package_status.return_value = True
    storage.delete_package.return_value = True
    storage.save_return_record.return_value = True

    # dispatch_commands 相关 mock（表已删除）

    storage.save_process_record.return_value = True
    storage.get_process_record.return_value = SAMPLE_PROCESS_RECORD
    storage.save_sub_step.return_value = True
    storage.get_sub_steps_by_process.return_value = [SAMPLE_SUB_STEP]
    storage.get_recent_sub_step.return_value = None
    storage.get_sub_step_summary.return_value = {
        'total_quantity': 10, 'batch_count': 1,
    }
    storage.dedup_process_sub_steps.return_value = 0

    storage.save_collection_record.return_value = True
    storage.get_collection_record.return_value = SAMPLE_COLLECTION_RECORD
    storage.get_collection_records.return_value = [SAMPLE_COLLECTION_RECORD]
    storage.update_collection_record_status.return_value = True
    storage.get_all_collection_records.return_value = [SAMPLE_COLLECTION_RECORD]

    storage.save_schedule_record.return_value = True
    storage.get_schedule_record.return_value = SAMPLE_SCHEDULE_RECORD
    storage.get_schedule_record_by_order.return_value = SAMPLE_SCHEDULE_RECORD
    storage.get_schedule_records.return_value = [SAMPLE_SCHEDULE_RECORD]
    storage.get_all_schedule_records.return_value = [SAMPLE_SCHEDULE_RECORD]

    storage.log_schedule_flow.return_value = True
    storage.get_schedule_flow_logs.return_value = []

    storage.save_data_flow_log.return_value = True
    storage.get_data_flow_logs.return_value = []
    storage.get_all_data_flow_logs.return_value = []

    storage.log_sync.return_value = None

    storage.save_order_cost.return_value = True
    storage.get_order_cost.return_value = SAMPLE_COST

    storage.get_material_unit_price.return_value = 15.0
    storage.save_material_unit_price.return_value = True
    storage.get_all_material_prices.return_value = []
    storage.get_labor_unit_price.return_value = 25.0
    storage.save_labor_unit_price.return_value = True
    storage.get_all_labor_prices.return_value = []

    with patch('storage_layer.StorageFactory.get_instance', return_value=storage), \
         patch('storage_layer.StorageFactory.create', return_value=storage):
        yield storage
