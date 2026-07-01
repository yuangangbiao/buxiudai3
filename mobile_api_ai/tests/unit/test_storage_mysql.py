# -*- coding: utf-8 -*-
"""单元测试: MySQLStorage — mock dbutils.PooledDB + pymysql"""
import sys
from unittest.mock import MagicMock, patch

import pymysql
import pytest


class _FakeConnection:
    """模拟 pymysql Connection，支持 with conn: 和 conn.cursor()。"""
    def __init__(self):
        self.cursor_mock = MagicMock()
        self.cursor_mock.execute.return_value = 1
        self.cursor_mock.rowcount = 1
        self.cursor_mock.lastrowid = 0
        self.open = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def cursor(self):
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=self.cursor_mock)
        ctx.__exit__ = MagicMock(return_value=None)
        return ctx

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
    """模拟 PooledDB 实例。"""
    def __init__(self):
        self._conn = _FakeConnection()

    def connection(self):
        return self._conn

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _setup_modules():
    """注入依赖模块。"""
    # 阻止 dotenv 加载真实 .env
    if 'dotenv' not in sys.modules:
        import dotenv as _dv
        sys.modules['dotenv'] = _dv
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
    for m in ['utils.auto_schema', 'core.config', 'storage.mysql_storage']:
        sys.modules.pop(m, None)


@pytest.fixture
def fake_pool():
    return _FakePool()


@pytest.fixture
def storage(fake_pool):
    """已连接 MySQLStorage。"""
    with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
        import storage.mysql_storage as sms
        s = sms.MySQLStorage()
        s.connect()
        fake_pool._conn.cursor_mock.execute.reset_mock()
        yield s, fake_pool


class TestConnection:
    def test_connect_success(self, fake_pool):
        with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
            import storage.mysql_storage as sms
            s = sms.MySQLStorage()
            assert s._pool is None
            ok = s.connect()
            assert ok is True
            assert s._pool is not None

    def test_connect_failure(self):
        with patch('storage.mysql_storage.PooledDB',
                   side_effect=pymysql.Error('refused')):
            import storage.mysql_storage as sms
            s = sms.MySQLStorage()
            ok = s.connect()
            assert ok is False
            assert s._pool is None

    def test_disconnect(self, storage):
        s, _ = storage
        s.disconnect()
        assert s._pool is None

    def test_context_manager(self, fake_pool):
        with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
            import storage.mysql_storage as sms
            with sms.MySQLStorage() as s:
                assert s._pool is not None
            assert s._pool is None


class TestHealthCheck:
    def test_ok(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {'ok': 1}
        r = s.health_check()
        assert r['status'] == 'ok'

    def test_error(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.execute.side_effect = pymysql.Error('down')
        r = s.health_check()
        assert r['status'] == 'error'


class TestCRUD:
    def test_fetch_one(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {'id': 1}
        r = s.fetch_one('SELECT 1')
        assert r == {'id': 1}

    def test_fetch_one_none(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = None
        r = s.fetch_one('SELECT 1')
        assert r is None

    def test_fetch_all(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchall.return_value = [{'a': 1}, {'a': 2}]
        r = s.fetch_all('SELECT 1')
        assert len(r) == 2

    def test_execute(self, storage):
        s, fp = storage
        r = s.execute("INSERT INTO t VALUES (1)")
        assert r == 1

    def test_insert(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.lastrowid = 42
        r = s.insert('test', {'name': 'x'})
        assert r == 42

    def test_update(self, storage):
        s, fp = storage
        r = s.update('test', {'v': 2}, 'id=%s', (1,))
        assert r == 1


class TestSaveProcessRecord:
    """check-then-insert-or-update"""

    def test_insert_new(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.side_effect = [None, None]  # 不存在
        fp._conn.cursor_mock.lastrowid = 100
        assert s.save_process_record({'id': 'r1', 'order_no': 'O1', 'product_name': 'X'}) is True
        # 验证执行了 INSERT
        sqls = [c[0][0] for c in fp._conn.cursor_mock.execute.call_args_list if c[0]]
        assert any('INSERT' in str(s) for s in sqls), f"Expected INSERT, got: {sqls}"

    def test_update_existing(self, storage):
        s, fp = storage
        # fetchone 返回非空 = 存在
        fp._conn.cursor_mock.fetchone.side_effect = [{'1': 1}, None]
        assert s.save_process_record({'id': 'r1', 'order_no': 'O1', 'product_name': 'Y'}) is True
        sqls = [c[0][0] for c in fp._conn.cursor_mock.execute.call_args_list if c[0]]
        assert any('UPDATE' in str(s) for s in sqls), f"Expected UPDATE, got: {sqls}"


class TestSaveSubStep:
    def test_insert_new(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.side_effect = [None, None]
        fp._conn.cursor_mock.lastrowid = 200
        assert s.save_sub_step({'id': 'ss1', 'order_no': 'X', 'step_name': 'cut'}) is True

    def test_update_existing(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.side_effect = [{'1': 1}, None]
        assert s.save_sub_step({'id': 'ss1', 'order_no': 'X', 'step_name': 'cut'}) is True
        sqls = [c[0][0] for c in fp._conn.cursor_mock.execute.call_args_list if c[0]]
        assert any('UPDATE' in str(s) for s in sqls)


class TestSaveProcessSubStep:
    def test_skip_existing(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {'id': 'existing'}
        assert s.save_process_sub_step({
            'order_no': 'O1', 'step_name': 'weld', 'process_code': 'W01'
        }) is True
        # 不应有 INSERT
        inserts = [c for c in fp._conn.cursor_mock.execute.call_args_list
                   if c[0] and 'INSERT' in str(c[0][0])]
        assert len(inserts) == 0


class TestSaveScheduleRecord:
    def test_insert_new(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.side_effect = [None, None]
        fp._conn.cursor_mock.lastrowid = 300
        assert s.save_schedule_record({'id': 'sch1', 'order_no': 'O1'}) is True

    def test_update_existing(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.side_effect = [{'1': 1}, None]
        assert s.save_schedule_record({'id': 'sch1', 'order_no': 'O1'}) is True
        sqls = [c[0][0] for c in fp._conn.cursor_mock.execute.call_args_list if c[0]]
        assert any('UPDATE' in str(s) for s in sqls)


class TestEnterpriseStructure:
    def test_get(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {
            'departments': '[{"id":1}]', 'users': '[{"userid":"u1"}]',
            'updated_at': '2026-01-01',
        }
        r = s.get_enterprise_structure()
        assert r['departments'] == [{'id': 1}]
        assert r['users'] == [{'userid': 'u1'}]

    def test_get_empty(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = None
        assert s.get_enterprise_structure() is None

    def test_save(self, storage):
        s, _ = storage
        r = s.save_enterprise_structure({
            'departments': [], 'users': []
        })
        # insert returns lastrowid or None; update returns affected rows
        assert r is not None

    def test_load_alias(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = None
        assert s.load_enterprise_structure() is None


class TestCreateStorage:
    def test_entry(self, fake_pool):
        with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
            import storage.mysql_storage as sms
            s = sms.create_mysql_storage()
            assert s._pool is not None
            s.disconnect()


class TestDDLSkip:
    """_ensure_all_tables 在表已存在时跳过"""

    def test_skip_when_tables_exist(self, fake_pool):
        with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
            import storage.mysql_storage as sms
            s = sms.MySQLStorage()
            s.connect()
            # _tables_ensured 应为 True（information_schema 查询返回了数据）
            assert s._tables_ensured is True
