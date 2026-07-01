# -*- coding: utf-8 -*-
"""
[P1 bug fix 2026-06-23] MySQLStorage.get_packages 6 个 data_type 静默丢数据

P1 修复测试 (小贺):
- 修复前: get_packages 走 if/elif, 14 个 _TASK_TYPE_TABLE_MAP key 已漏 6 个:
    quality_inspection / quality_task → quality_records
    material / material_pickup       → material_records
    repair                            → repair_records
    outsource                         → outsource_records
  表现: 6 个 data_type 全部静默返 []
  真实业务影响: legacy_routes.py:599 data_type='quality_task' 静默丢数据
- 修复后: get_packages 用 _TASK_TYPE_TABLE_MAP.get() 自动派发, 14 个 key 全覆盖

测试覆盖:
1. 6 个新分支 P1 验证 (quality_inspection/quality_task/material/material_pickup/repair/outsource)
2. _TASK_TYPE_TABLE_MAP 14 个 key 全覆盖 (含已修 8 个 + 新修 6 个)
3. status / related_order 过滤参数与 6 个新分支兼容
4. limit / offset 正确传递
5. 回归保护: 原 4 个分支 (quality/material_request/material_purchase/process系) 不被破坏
6. 边界: 未知 data_type / 无 data_type 仍返 []
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


# ────── 测试基础设施 (复用 test_get_packages_process_report.py 的 fake_pool) ──────

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
    if 'dotenv' not in sys.modules:
        import dotenv as _dv
        sys.modules['dotenv'] = _dv

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
        s.fetch_all = MagicMock(return_value=[{'id': 1, 'order_no': 'ORD-X', 'status': 'pending'}])
        yield s


# ────── P1 核心: 6 个新 data_type 静默丢数据修复验证 ──────

class TestGetPackagesP1SilentDrop:
    """P1 修复: 6 个之前静默丢数据的 data_type 全部能查到正确表"""

    # ── quality 3 个分支 (含 2 个新增) ──

    def test_quality_inspection_targets_quality_records(self, storage):
        """[P1 核心] data_type='quality_inspection' 必须查询 quality_records
        修复前: 走 else 分支 → 返 []
        修复后: 查 _TASK_TYPE_TABLE_MAP → quality_records
        """
        storage.get_packages(data_type='quality_inspection', related_order='WO-Q1', limit=10)
        sql = _capture_sql(storage)
        assert 'quality_records' in sql, f"Expected quality_records, got: {sql}"
        assert 'process_sub_steps' not in sql

    def test_quality_task_targets_quality_records(self, storage):
        """[P1 核心] data_type='quality_task' 必须查询 quality_records
        真实业务调用: legacy_routes.py:599 cc.storage.get_packages(data_type='quality_task', limit=200)
        修复前: 静默返 [] → 质检任务在 UI 上完全消失
        修复后: 正常返回数据
        """
        storage.get_packages(data_type='quality_task', limit=200)
        sql = _capture_sql(storage)
        assert 'quality_records' in sql, f"Expected quality_records, got: {sql}"
        assert 'process_sub_steps' not in sql

    # ── material 4 个分支 (含 2 个新增) ──

    def test_material_targets_material_records(self, storage):
        """[P1 核心] data_type='material' 必须查询 material_records
        修复前: 走 else 分支 → 返 []
        """
        storage.get_packages(data_type='material', related_order='WO-M1', limit=10)
        sql = _capture_sql(storage)
        assert 'material_records' in sql, f"Expected material_records, got: {sql}"
        assert 'process_sub_steps' not in sql

    def test_material_pickup_targets_material_records(self, storage):
        """[P1 核心] data_type='material_pickup' 必须查询 material_records
        业务场景: 仓库领料任务 (区别于 material_request 申请)
        """
        storage.get_packages(data_type='material_pickup', limit=20)
        sql = _capture_sql(storage)
        assert 'material_records' in sql, f"Expected material_records, got: {sql}"
        assert 'process_sub_steps' not in sql

    # ── repair ──

    def test_repair_targets_repair_records(self, storage):
        """[P1 核心] data_type='repair' 必须查询 repair_records
        修复前: 走 else 分支 → 返 []
        业务影响: 报修任务列表空
        """
        storage.get_packages(data_type='repair', related_order='WO-R1', limit=10)
        sql = _capture_sql(storage)
        assert 'repair_records' in sql, f"Expected repair_records, got: {sql}"
        assert 'process_sub_steps' not in sql
        assert 'material_records' not in sql

    # ── outsource ──

    def test_outsource_targets_outsource_records(self, storage):
        """[P1 核心] data_type='outsource' 必须查询 outsource_records
        修复前: 走 else 分支 → 返 []
        业务影响: 外协任务列表空
        """
        storage.get_packages(data_type='outsource', related_order='WO-O1', limit=10)
        sql = _capture_sql(storage)
        assert 'outsource_records' in sql, f"Expected outsource_records, got: {sql}"
        assert 'process_sub_steps' not in sql
        assert 'material_records' not in sql


# ────── 过滤参数与新分支兼容 ──────

class TestGetPackagesP1Filters:
    """验证 status / related_order / limit / offset 在 6 个新分支上正确传递"""

    def test_repair_with_status_filter(self, storage):
        storage.get_packages(data_type='repair', status='pending', limit=5)
        params = _capture_params(storage)
        assert 'pending' in params
        assert 5 in params
        assert 0 in params

    def test_outsource_with_related_order_filter(self, storage):
        storage.get_packages(data_type='outsource', related_order='WO-2026-001', limit=10)
        params = _capture_params(storage)
        assert 'WO-2026-001' in params
        assert 10 in params

    def test_quality_inspection_with_offset(self, storage):
        storage.get_packages(data_type='quality_inspection', limit=20, offset=100)
        params = _capture_params(storage)
        assert 20 in params
        assert 100 in params

    def test_material_pickup_with_both_filters(self, storage):
        storage.get_packages(data_type='material_pickup', status='completed',
                              related_order='WO-MP-1', limit=50, offset=200)
        params = _capture_params(storage)
        assert 'completed' in params
        assert 'WO-MP-1' in params
        assert 50 in params
        assert 200 in params


# ────── _TASK_TYPE_TABLE_MAP 14 个 key 全覆盖审查 ──────

class TestAllTableMapKeysSupported:
    """验证 get_packages 覆盖 _TASK_TYPE_TABLE_MAP 全部 14 个 key"""

    EXPECTED_MAP = {
        'quality': 'quality_records',
        'quality_inspection': 'quality_records',
        'quality_task': 'quality_records',
        'material_request': 'material_records',
        'material_purchase': 'material_records',
        'material': 'material_records',
        'material_pickup': 'material_records',
        'repair': 'repair_records',
        'outsource': 'outsource_records',
        'process': 'process_sub_steps',
        'production': 'process_sub_steps',
        'report': 'process_sub_steps',
        'process_report': 'process_sub_steps',
        'process_task': 'process_sub_steps',
    }

    def test_all_14_keys_supported(self, storage):
        """[审查] _TASK_TYPE_TABLE_MAP 中所有 14 个 key, get_packages 都能派发到正确表"""
        missing = []
        wrong_table = []
        for key, expected_table in self.EXPECTED_MAP.items():
            storage.fetch_all.reset_mock()
            storage.get_packages(data_type=key, limit=10)
            sql = _capture_sql(storage)
            if expected_table not in sql:
                missing.append((key, expected_table, sql))

        assert missing == [], f"以下 data_type 未正确派发: {missing}"

    def test_static_assert_table_map_contents(self):
        """[静态] _TASK_TYPE_TABLE_MAP 内容锁定, 防意外增删"""
        from storage.mysql_storage import MySQLStorage
        assert MySQLStorage._TASK_TYPE_TABLE_MAP == self.EXPECTED_MAP, \
            f"_TASK_TYPE_TABLE_MAP 内容变更, 请同步更新 EXPECTED_MAP 防止遗漏"

    def test_no_silent_drop_after_fix(self, storage):
        """[核心] 6 个 P1 修复点全部不再返 [] (前提: fetch_all 返回数据)"""
        storage.fetch_all = MagicMock(return_value=[{'id': 1}])
        previously_broken = [
            'quality_inspection', 'quality_task',
            'material', 'material_pickup',
            'repair', 'outsource',
        ]
        for dt in previously_broken:
            result = storage.get_packages(data_type=dt)
            assert result == [{'id': 1}], \
                f"data_type={dt} 修复后仍返 {result}, 应为 [{{'id': 1}}]"


# ────── 回归保护: 原 4 个分支 ──────

class TestGetPackagesRegression:
    """回归保护: 已修 8 个分支 (quality/material_request/material_purchase/process系) 不被破坏"""

    def test_quality_branch(self, storage):
        storage.get_packages(data_type='quality', status='pending', limit=10)
        sql = _capture_sql(storage)
        assert 'quality_records' in sql

    def test_material_request_branch(self, storage):
        storage.get_packages(data_type='material_request', related_order='WO-M', limit=10)
        sql = _capture_sql(storage)
        assert 'material_records' in sql

    def test_material_purchase_branch(self, storage):
        storage.get_packages(data_type='material_purchase', limit=10)
        sql = _capture_sql(storage)
        assert 'material_records' in sql

    def test_process_sub_steps_branch(self, storage):
        for dt in ('process', 'production', 'process_report', 'process_task', 'report'):
            storage.fetch_all.reset_mock()
            storage.get_packages(data_type=dt, limit=10)
            sql = _capture_sql(storage)
            assert 'process_sub_steps' in sql, \
                f"data_type={dt} 应查 process_sub_steps, 实查: {sql}"


# ────── 边界: 未知 data_type / 无 data_type ──────

class TestGetPackagesEdgeCases:
    """边界: 未知 data_type 仍返 [], 不抛异常"""

    def test_unknown_data_type_returns_empty(self, storage):
        result = storage.get_packages(data_type='never_existed_type')
        assert result == []

    def test_no_data_type_returns_empty(self, storage):
        result = storage.get_packages()
        assert result == []

    def test_empty_string_data_type_returns_empty(self, storage):
        result = storage.get_packages(data_type='')
        assert result == []

    def test_none_data_type_returns_empty(self, storage):
        result = storage.get_packages(data_type=None)
        assert result == []

    def test_fetch_all_returns_none_fallback_to_empty_list(self, storage):
        """[边界] fetch_all 返 None 时降级为 [] (与现有 quality 分支一致)"""
        storage.fetch_all = MagicMock(return_value=None)
        for dt in ('quality_inspection', 'repair', 'outsource'):
            result = storage.get_packages(data_type=dt)
            assert result == [], f"data_type={dt} 应降级为 [], 实返 {result}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
