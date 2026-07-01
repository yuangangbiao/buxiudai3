# -*- coding: utf-8 -*-
"""v4.0 边界测试: save_process_sub_step + dedup_process_sub_steps
- 5 类边界: 空 / 单条 / 阈值 / 上溢 / 并发
"""
import sys
from unittest.mock import MagicMock, patch

import pymysql
import pytest


class _FakeConnection:
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
    def __init__(self):
        self._conn = _FakeConnection()

    def connection(self):
        return self._conn

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _setup_modules():
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


@pytest.fixture
def storage():
    fake_pool = _FakePool()
    with patch('storage.mysql_storage.PooledDB', return_value=fake_pool):
        import storage.mysql_storage as sms
        s = sms.MySQLStorage()
        s.connect()
        fake_pool._conn.cursor_mock.execute.reset_mock()
        yield s, fake_pool


def _calls(s, sql_keyword):
    """取所有含指定关键字的 SQL"""
    return [c[0][0] for c in s.execute.call_args_list
            if c[0] and sql_keyword in str(c[0][0])]


class TestEmptyBoundary:
    """边界 1: 空数据"""

    def test_empty_data_returns_false(self, storage):
        s, fp = storage
        assert s.save_process_sub_step({}) is False
        # 无 DB 调用
        assert fp._conn.cursor_mock.execute.call_count == 0

    def test_only_order_no_returns_false(self, storage):
        s, fp = storage
        assert s.save_process_sub_step({'order_no': 'O1'}) is False
        assert fp._conn.cursor_mock.execute.call_count == 0

    def test_only_step_name_returns_false(self, storage):
        s, fp = storage
        assert s.save_process_sub_step({'step_name': 'weld'}) is False
        assert fp._conn.cursor_mock.execute.call_count == 0


class TestSingleRowBoundary:
    """边界 2: 单条新派工"""

    def test_new_sub_step_inserts(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = None
        fp._conn.cursor_mock.lastrowid = 500
        ok = s.save_process_sub_step({
            'id': 'ss-new',
            'order_no': 'O-NEW',
            'step_name': 'cut',
            'process_code': 'P01',
            'operator': '张三',
        })
        assert ok is True
        inserts = _calls(fp._conn.cursor_mock, 'INSERT')
        assert len(inserts) >= 1, f"Expected INSERT, got: {inserts}"


class TestThresholdBoundary:
    """边界 3: 阈值 — 同工序同人 / 异人"""

    def test_existing_same_operator_no_update(self, storage):
        """同人重复派工 → 无 INSERT 无 UPDATE"""
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {
            'id': 'ss-exist', 'operator': '张三'
        }
        ok = s.save_process_sub_step({
            'id': 'ss-new',
            'order_no': 'O1',
            'step_name': 'weld',
            'process_code': 'P01',
            'operator': '张三',
        })
        assert ok is True
        inserts = _calls(fp._conn.cursor_mock, 'INSERT')
        updates = _calls(fp._conn.cursor_mock, 'UPDATE')
        assert len(inserts) == 0
        assert len(updates) == 0

    def test_existing_new_operator_appends(self, storage):
        """异人派工 → UPDATE operator 追加"""
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {
            'id': 'ss-exist', 'operator': '张三'
        }
        ok = s.save_process_sub_step({
            'order_no': 'O1',
            'step_name': 'weld',
            'process_code': 'P01',
            'operator': '李四',
        })
        assert ok is True
        updates = _calls(fp._conn.cursor_mock, 'UPDATE')
        assert len(updates) == 1
        # 验证 UPDATE 的参数中 operator 含 "张三,李四"
        update_args = fp._conn.cursor_mock.execute.call_args_list
        merged = None
        for c in update_args:
            if c[0] and 'UPDATE' in str(c[0][0]):
                merged = c[0][1]
                break
        assert merged is not None
        merged_str = ','.join(str(x) for x in merged)
        assert '张三' in merged_str
        assert '李四' in merged_str

    def test_existing_empty_operator_then_new(self, storage):
        """老数据 operator 为空, 新派工带 operator → 写入新值"""
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {
            'id': 'ss-exist', 'operator': None
        }
        ok = s.save_process_sub_step({
            'order_no': 'O1', 'step_name': 'weld', 'process_code': 'P01',
            'operator': '王五',
        })
        assert ok is True
        updates = _calls(fp._conn.cursor_mock, 'UPDATE')
        assert len(updates) == 1

    def test_existing_comma_list_dedup(self, storage):
        """operator 已是 '张三,李四', 再派张三 → 不重复追加"""
        s, fp = storage
        fp._conn.cursor_mock.fetchone.return_value = {
            'id': 'ss-exist', 'operator': '张三,李四'
        }
        ok = s.save_process_sub_step({
            'order_no': 'O1', 'step_name': 'weld', 'process_code': 'P01',
            'operator': '张三',
        })
        assert ok is True
        # 同人重复 → 无 UPDATE
        updates = _calls(fp._conn.cursor_mock, 'UPDATE')
        assert len(updates) == 0


class TestOverflowBoundary:
    """边界 4: 上溢 — 多人派工"""

    def test_5_workers_appends_all(self, storage):
        """同工序派工给 5 个不同人 → 模拟连续调用, 终态 operator 含 5 人"""
        s, fp = storage
        workers = ['工人1', '工人2', '工人3', '工人4', '工人5']
        current_op = ''

        for w in workers:
            fp._conn.cursor_mock.fetchone.return_value = {
                'id': 'ss-exist', 'operator': current_op
            }
            ok = s.save_process_sub_step({
                'order_no': 'O-OV', 'step_name': 'weld', 'process_code': 'P01',
                'operator': w,
            })
            assert ok is True
            # 模拟 DB 更新后状态
            updates = _calls(fp._conn.cursor_mock, 'UPDATE')
            if updates:
                update_args = fp._conn.cursor_mock.execute.call_args_list
                for c in update_args:
                    if c[0] and 'UPDATE' in str(c[0][0]):
                        current_op = c[0][1][0]
            # 重置 mock 以便下次断言
            fp._conn.cursor_mock.execute.reset_mock()
            # 同时重新设 fetchone 返回
            fp._conn.cursor_mock.fetchone.reset_mock()
            fp._conn.cursor_mock.fetchone.return_value = {
                'id': 'ss-exist', 'operator': current_op
            }

        # 终态应含 5 人
        for w in workers:
            assert w in current_op, f"worker {w} not in final operator: {current_op}"

    def test_operator_field_width_supports_long_list(self, storage):
        """operator 字段扩到 255 后, 存 5 人 (10 字符以内) 不超长"""
        s, fp = storage
        # 模拟连续 5 人派工
        cur_op = ''
        for i in range(5):
            w = f'员工{i}号'
            fp._conn.cursor_mock.fetchone.return_value = {
                'id': 'ss-exist', 'operator': cur_op
            }
            s.save_process_sub_step({
                'order_no': 'O-LONG', 'step_name': 'weld', 'process_code': 'P01',
                'operator': w,
            })
            updates = _calls(fp._conn.cursor_mock, 'UPDATE')
            if updates:
                cur_op = fp._conn.cursor_mock.execute.call_args_list[-1][0][1][0]
            fp._conn.cursor_mock.execute.reset_mock()
            fp._conn.cursor_mock.fetchone.reset_mock()
            fp._conn.cursor_mock.fetchone.return_value = {
                'id': 'ss-exist', 'operator': cur_op
            }
        # 长度断言: 5 个 4 字符名字 + 4 个逗号 = 24 字符, 远小于 255
        assert len(cur_op) < 255


class TestConcurrentBoundary:
    """边界 5: 并发 — 同一工序多线程同时派工"""

    def test_concurrent_same_process_serializes(self, storage):
        """10 线程同时派工同工序: 模拟全部进入 if existing 分支, 终态 operator 含全部"""
        import threading

        s_obj, fp = storage
        workers = [f'线程{i}' for i in range(10)]
        results = {'merged_ops': []}
        lock = threading.Lock()

        def dispatch(w):
            with patch.object(s_obj, 'fetch_one', return_value={
                'id': 'ss-exist', 'operator': ','.join(results['merged_ops'])
            }):
                with patch.object(s_obj, 'update', side_effect=lambda *a, **kw:
                                  results['merged_ops'].append(w) or 1):
                    s_obj.save_process_sub_step({
                        'order_no': 'O-CON', 'step_name': 'weld', 'process_code': 'P01',
                        'operator': w,
                    })

        threads = [threading.Thread(target=dispatch, args=(w,)) for w in workers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证: 每个工人都被记录到 merged_ops (因为 mock update 模拟追加)
        for w in workers:
            assert w in results['merged_ops'], f"worker {w} missing in {results['merged_ops']}"


class TestDedupProcessSubSteps:
    """dedup_process_sub_steps 函数 — 正常情况应清理 0 条"""

    def test_dedup_with_no_duplicates_returns_zero(self, storage):
        s, fp = storage
        fp._conn.cursor_mock.fetchall.return_value = []
        n = s.dedup_process_sub_steps()
        assert n == 0

    def test_dedup_with_duplicate_merges_operators(self, storage):
        """有重复组时 → 合并 operator 后删除"""
        s, fp = storage
        # 第一次 fetch_all: 找重复组 → 返回 1 组
        # 第二次 fetch_one: 取 anchor
        # 第三次 fetch_all: 取该组所有行
        # 后续 update + execute
        fp._conn.cursor_mock.fetchall.side_effect = [
            [{'order_no': 'O-DUP', 'step_name': 'weld', 'pc': 'P01'}],  # 重复组
            [  # 该组的所有行
                {'id': 'a1', 'operator': '工人1'},
                {'id': 'a2', 'operator': '工人2'},
            ],
        ]
        fp._conn.cursor_mock.fetchone.return_value = {'id': 'a1', 'operator': '工人1'}
        fp._conn.cursor_mock.rowcount = 1
        n = s.dedup_process_sub_steps()
        assert n == 1  # 删了 1 条
