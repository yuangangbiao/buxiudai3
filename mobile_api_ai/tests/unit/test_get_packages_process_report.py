# -*- coding: utf-8 -*-
"""
[bug fix] MySQLStorage.get_packages 不处理 process_report 等 data_type

P0 修复测试:
- 验证 data_type='process_report' 能查询 process_sub_steps 表
- 验证 data_type='process_task' / 'report' 同样能查询 process_sub_steps 表
- 验证 _TASK_TYPE_TABLE_MAP 中所有映射到 process_sub_steps 的 key 都被 get_packages 支持
- 验证 status / related_order 过滤参数与 process_report 兼容
- 验证 limit / offset 正确传递
- 验证未知 data_type 仍返回 [] (向后兼容)
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


# ────── 测试基础设施 ──────

class _FakeCursor:
    def __init__(self):
        self.execute = MagicMock(return_value=1)
        self.rowcount = 1
        self.lastrowid = 0
        self.fetchone = MagicMock(return_value=None)
        self.fetchall = MagicMock(return_value=[])
        self.close = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None


class _FakeConnection:
    def __init__(self):
        self.cursor_mock = _FakeCursor()
        self.open = True

    def cursor(self, *a, **kw):
        return self.cursor_mock

    def ping(self, reconnect=False):
        pass

    def close(self):
        pass

    def begin(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


class _FakePool:
    def __init__(self):
        self._conn = _FakeConnection()

    def connection(self):
        return self._FakeConnCtx(self._conn)

    class _FakeConnCtx:
        def __init__(self, conn):
            self._conn = conn

        def __enter__(self):
            return self._conn

        def __exit__(self, *a):
            return None

    def close(self):
        pass


def _capture_sql(storage_obj):
    """获取 get_packages 调用 fetch_all 的 SQL"""
    call = storage_obj.fetch_all.call_args
    return call[0][0] if call else ''


def _capture_params(storage_obj):
    """获取 get_packages 调用 fetch_all 的 params"""
    call = storage_obj.fetch_all.call_args
    return call[0][1] if call and len(call[0]) > 1 else ()


@pytest.fixture(autouse=True)
def _setup_modules():
    """注入 core.exceptions / core.config / utils.auto_schema 等依赖"""
    # 防止 dotenv 加载真实 .env
    if 'dotenv' not in sys.modules:
        import dotenv as _dv
        sys.modules['dotenv'] = _dv

    # mock core.exceptions (本仓库中尚未存在, 但被 mysql_storage 直接 import)
    if 'core.exceptions' not in sys.modules:
        mock_exc = MagicMock()
        mock_exc.safe_cursor_execute = MagicMock(return_value=1)
        mock_exc.safe_cursor_insert = MagicMock(return_value=0)
        sys.modules['core.exceptions'] = mock_exc

    with patch('storage.mysql_storage.load_dotenv'):
        if 'core.config' not in sys.modules:
            mock_cfg = MagicMock()
            mock_cfg.CONTAINER_MYSQL_CFG = {
                'host': '127.0.0.1', 'port': 3306,
                'user': 'root', 'password': '',
                'database': 'container_center', 'charset': 'utf8mb4',
            }
            mock_cfg.DB_CONNECT_TIMEOUT = 5
            sys.modules['core.config'] = mock_cfg
        if 'utils.auto_schema' not in sys.modules:
            mock_mod = MagicMock()
            mock_mod.auto_ensure_schema = MagicMock()
            sys.modules['utils.auto_schema'] = mock_mod

    yield

    for m in ['utils.auto_schema', 'core.config', 'core.exceptions',
              'storage.mysql_storage']:
        sys.modules.pop(m, None)


@pytest.fixture
def fake_pool():
    return _FakePool()


@pytest.fixture
def storage(fake_pool):
    """已连接 MySQLStorage, fetch_all 被 mock"""
    with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
        import storage.mysql_storage as sms
        s = sms.MySQLStorage()
        s.connect()
        # mock fetch_all 以便断言 SQL/参数
        s.fetch_all = MagicMock(return_value=[{'id': 1, 'order_no': 'ORD-X', 'status': 'pending'}])
        yield s


# ────── P0 核心修复验证 ──────

class TestGetPackagesProcessReport:
    """P0 修复: get_packages 支持 process_report / process_task / report"""

    def test_process_report_targets_process_sub_steps(self, storage):
        """[P0 核心] data_type='process_report' 必须查询 process_sub_steps"""
        result = storage.get_packages(data_type='process_report', related_order='WO-X', limit=10)
        assert result == [{'id': 1, 'order_no': 'ORD-X', 'status': 'pending'}]
        sql = _capture_sql(storage)
        assert 'process_sub_steps' in sql, f"Expected process_sub_steps in SQL, got: {sql}"
        assert 'FROM process_sub_steps' in sql.replace('\n', ' ').replace('  ', ' ')

    def test_process_task_targets_process_sub_steps(self, storage):
        """data_type='process_task' 必须查询 process_sub_steps (与 _TASK_TYPE_TABLE_MAP 对齐)"""
        storage.get_packages(data_type='process_task', limit=20)
        sql = _capture_sql(storage)
        assert 'process_sub_steps' in sql

    def test_report_targets_process_sub_steps(self, storage):
        """data_type='report' 必须查询 process_sub_steps (与 _TASK_TYPE_TABLE_MAP 对齐)"""
        storage.get_packages(data_type='report', limit=20)
        sql = _capture_sql(storage)
        assert 'process_sub_steps' in sql

    def test_process_existing_still_works(self, storage):
        """data_type='process' (原有) 不被破坏"""
        storage.get_packages(data_type='process', limit=20)
        sql = _capture_sql(storage)
        assert 'process_sub_steps' in sql

    def test_production_existing_still_works(self, storage):
        """data_type='production' (原有) 不被破坏"""
        storage.get_packages(data_type='production', limit=20)
        sql = _capture_sql(storage)
        assert 'process_sub_steps' in sql

    def test_process_report_with_status_filter(self, storage):
        """[关键] process_report + status 过滤参数必须正确传递"""
        storage.get_packages(data_type='process_report', status='pending', limit=5)
        params = _capture_params(storage)
        # 期望 params = ('pending', 5, 0)
        assert 'pending' in params
        assert 5 in params
        assert 0 in params

    def test_process_report_with_related_order_filter(self, storage):
        """[关键] process_report + related_order 过滤参数必须正确传递"""
        storage.get_packages(data_type='process_report', related_order='WO-2026-001', limit=10)
        params = _capture_params(storage)
        assert 'WO-2026-001' in params
        assert 10 in params

    def test_process_report_with_offset(self, storage):
        """[关键] process_report + offset 必须正确传递"""
        storage.get_packages(data_type='process_report', limit=20, offset=100)
        params = _capture_params(storage)
        assert 20 in params
        assert 100 in params

    def test_process_report_returns_empty_when_no_data(self, storage):
        """[边界] process_report 无数据时返回 [] 而不是 None"""
        storage.fetch_all = MagicMock(return_value=[])
        result = storage.get_packages(data_type='process_report')
        assert result == []

    def test_process_report_returns_empty_when_fetch_all_returns_none(self, storage):
        """[边界] fetch_all 返回 None 时降级为 [] (与现有 quality 分支一致)"""
        storage.fetch_all = MagicMock(return_value=None)
        result = storage.get_packages(data_type='process_report')
        assert result == []


# ────── 已有分支回归保护 ──────

class TestGetPackagesExistingBranches:
    """回归保护: 已有 quality / material_request 分支不被破坏"""

    def test_quality_branch_unchanged(self, storage):
        storage.get_packages(data_type='quality', status='pending', limit=10)
        sql = _capture_sql(storage)
        assert 'quality_records' in sql
        assert 'process_sub_steps' not in sql

    def test_material_request_branch_unchanged(self, storage):
        storage.get_packages(data_type='material_request', related_order='WO-M', limit=10)
        sql = _capture_sql(storage)
        assert 'material_records' in sql
        assert 'process_sub_steps' not in sql

    def test_material_purchase_branch_unchanged(self, storage):
        storage.get_packages(data_type='material_purchase', limit=10)
        sql = _capture_sql(storage)
        assert 'material_records' in sql

    def test_unknown_data_type_returns_empty(self, storage):
        """[边界] 未知 data_type 返回 [] (向后兼容)"""
        result = storage.get_packages(data_type='never_existed_type')
        assert result == []

    def test_no_data_type_returns_empty(self, storage):
        """[边界] 无 data_type 返回 [] (向后兼容)"""
        result = storage.get_packages()
        assert result == []


# ────── 与 _TASK_TYPE_TABLE_MAP 一致性审查 ──────

class TestTaskTypeMapConsistency:
    """验证 get_packages 的 process 分支覆盖 _TASK_TYPE_TABLE_MAP 中所有 process_sub_steps 映射"""

    # _TASK_TYPE_TABLE_MAP 中映射到 process_sub_steps 的所有 key
    PROCESS_KEYS = ('process', 'production', 'report', 'process_report', 'process_task')

    def test_all_process_sub_steps_keys_supported(self, storage):
        """[审查] _TASK_TYPE_TABLE_MAP 中所有映射到 process_sub_steps 的 key,
        get_packages 都能正确查询 process_sub_steps 表"""
        missing = []
        for key in self.PROCESS_KEYS:
            storage.fetch_all.reset_mock()
            storage.get_packages(data_type=key, limit=10)
            sql = _capture_sql(storage)
            if 'process_sub_steps' not in sql:
                missing.append(key)
        assert missing == [], f"以下 data_type 未被 get_packages 支持: {missing}"

    def test_process_sub_steps_map_includes_process_report(self):
        """[一致性] 静态断言 _TASK_TYPE_TABLE_MAP['process_report'] == 'process_sub_steps'"""
        from storage.mysql_storage import MySQLStorage
        assert MySQLStorage._TASK_TYPE_TABLE_MAP.get('process_report') == 'process_sub_steps'
        assert MySQLStorage._TASK_TYPE_TABLE_MAP.get('process_task') == 'process_sub_steps'
        assert MySQLStorage._TASK_TYPE_TABLE_MAP.get('report') == 'process_sub_steps'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
