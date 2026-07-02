# -*- coding: utf-8 -*-
"""
RE-001 TASK-05: schedule 模块事务化测试

覆盖:
- /api/schedule_record/update (排产修正) - 事务包裹 + 失败回滚
- /api/schedule_record/withdraw (排产撤回) - 事务包裹 + 失败回滚

测试矩阵 (DESIGN §7.1):
- T-001: schedule 修正 - 正常路径 (UPDATE + INSERT history + COMMIT)
- T-002: schedule 修正 - 失败回滚 (history INSERT 失败 → ROLLBACK + 500)
- T-003: schedule 撤回 - 正常路径 (UPDATE status='withdrawn' + INSERT + COMMIT)
- T-004: schedule 撤回 - 失败回滚 (UPDATE 失败 → ROLLBACK + 500)

实现策略: 与 material/outsource/quality 一致 - 从 app.py 提取源码 exec 到最小 Flask app
"""
import json
import sys
import textwrap
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 从 app.py 提取 schedule 路由源码
# ---------------------------------------------------------------------------
def _extract_schedule_routes():
    """从 app.py 中提取 schedule_record_update 和 schedule_record_admin_withdraw 的源码。"""
    import os
    app_py = os.path.join(os.path.dirname(__file__), '..', '..', 'app.py')
    with open(app_py, 'r', encoding='utf-8') as f:
        source = f.read()

    routes = {}
    for func_name in ['schedule_record_update', 'schedule_record_admin_withdraw']:
        start_idx = source.find(f'def {func_name}(')
        assert start_idx > 0, f"未找到 {func_name}"
        decorator_start = source.rfind('@app.route', 0, start_idx)
        assert decorator_start > 0, f"未找到 {func_name} 的装饰器"
        line_start = source.rfind('\n', 0, decorator_start) + 1
        next_route = source.find('@app.route', start_idx)
        end_idx = next_route if next_route > 0 else len(source)
        routes[func_name] = source[line_start:end_idx].rstrip()
    return routes


@pytest.fixture
def schedule_app():
    """构建一个最小 Flask app，包含 schedule_record_update 和 schedule_record_admin_withdraw。"""
    import types
    from flask import Flask, jsonify, request

    fake_notify = MagicMock()
    fake_bridge_pkg = MagicMock()
    fake_sync = MagicMock()
    fake_sync.send = MagicMock()
    sys.modules['notify'] = fake_notify
    if 'bridge' not in sys.modules:
        sys.modules['bridge'] = fake_bridge_pkg
    sys.modules['bridge.sync_client'] = fake_sync

    fake_core_cfg = types.ModuleType('core.config')
    fake_core_cfg.CONTAINER_MYSQL_CFG = {
        'host': '127.0.0.1', 'port': 3306,
        'user': 'root', 'password': '',
        'database': 'container_center', 'charset': 'utf8mb4',
    }
    fake_core_cfg.DB_CONNECT_TIMEOUT = 5
    sys.modules['core.config'] = fake_core_cfg

    fake_pymysql = MagicMock()
    sys.modules['pymysql'] = fake_pymysql

    app = Flask(__name__)
    app.config['TESTING'] = True

    routes_source = _extract_schedule_routes()
    exec_globals = {
        '__builtins__': __builtins__,
        'app': app,
        'request': request,
        'jsonify': jsonify,
        'json': json,
        'logging': __import__('logging'),
        'pymysql': fake_pymysql,
        'logger': __import__('logging').getLogger('schedule_test'),
    }

    for func_name, source in routes_source.items():
        source = textwrap.dedent(source)
        compiled = compile(source, f'<test>{func_name}', 'exec')
        exec(compiled, exec_globals)

    yield app


# ---------------------------------------------------------------------------
# Fake 连接 + Cursor
# ---------------------------------------------------------------------------
class _FakeCursor:
    def __init__(self):
        self.execute = MagicMock(return_value=1)
        self.fetchone = MagicMock(return_value=None)
        self.description = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeConnection:
    def __init__(self):
        self._cursor = _FakeCursor()
        self.cursor = MagicMock(return_value=self._cursor)
        self.commit = MagicMock()
        self.rollback = MagicMock()
        self.close = MagicMock()


def _setup_existing_schedule(cursor, status='active', target_operator='王五',
                              related_order='WO2026002', related_process='排产调度'):
    """模拟 SELECT FOR UPDATE 查到的现有排产记录。"""
    cursor.fetchone.return_value = (
        100,                            # id
        related_order,                  # related_order
        related_process,                # related_process
        'schedule-record-1',            # title
        'content-1',                    # content
        'high',                         # priority
        target_operator,                # target_operator
        status,                         # status
    )
    cursor.description = [
        ('id',), ('related_order',), ('related_process',),
        ('title',), ('content',), ('priority',),
        ('target_operator',), ('status',),
    ]


def _strip_sqls(cursor):
    return [str(c.args[0]) for c in cursor.execute.call_args_list if c.args]


# ---------------------------------------------------------------------------
# /api/schedule_record/update  — 排产修正
# ---------------------------------------------------------------------------
class TestScheduleCorrectRollback:
    """排产修正接口 - 事务化测试"""

    def test_schedule_update_rollback(self, schedule_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE → INSERT history → COMMIT
        场景 B (失败): history INSERT 抛异常 → ROLLBACK + 500
        """
        client = schedule_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_schedule(fake_conn._cursor)

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/schedule_record/update', json={
                'record_id': 100,
                'title': 'updated-schedule-title',
                'admin_user': 'admin',
                'reason': 'admin_force',
            })

        assert resp.status_code == 200, f"期望 200, 实际 {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data['code'] == 0, f"期望 code=0, 实际: {data}"
        assert '已修改' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any('UPDATE container_center.process_sub_steps SET' in s and 'WHERE id=%s' in s for s in sqls), \
            f"缺少 UPDATE 主表, 实际: {sqls}"
        assert any('INSERT INTO container_center.data_regression_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        # 验证 data_type='schedule' 在参数元组中
        history_args_found = False
        for call in fake_conn._cursor.execute.call_args_list:
            if call.args and 'INSERT INTO container_center.data_regression_history' in str(call.args[0]):
                # 参数顺序: data_type, record_id, order_no, step_name, field_before, field_after, ...
                if len(call.args) > 1 and call.args[1][0] == 'schedule':
                    history_args_found = True
                    break
        assert history_args_found, "data_type='schedule' 未出现在 history INSERT 参数中"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_schedule(fake_conn._cursor)

        def fail_on_insert(*args, **kwargs):
            sql = str(args[0]) if args else ''
            if 'INSERT INTO container_center.data_regression_history' in sql:
                raise Exception('UNIQUE constraint violation: history duplicate')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_insert

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/schedule_record/update', json={
                'record_id': 100,
                'title': 'updated-schedule-title',
                'admin_user': 'admin',
            })

        assert resp.status_code == 500
        data = resp.get_json()
        assert data['code'] == 500
        assert '事务失败' in data['message']
        assert '已回滚' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert not any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"失败路径不应执行 COMMIT, 实际: {sqls}"
        fake_conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# /api/schedule_record/withdraw  — 排产撤回
# ---------------------------------------------------------------------------
class TestScheduleWithdrawRollback:
    """排产撤回接口 - 事务化测试"""

    def test_schedule_withdraw_rollback(self, schedule_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE status='withdrawn' → INSERT history → COMMIT
        场景 B (失败): UPDATE 抛异常 → ROLLBACK + 500
        """
        client = schedule_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_schedule(fake_conn._cursor, status='active', target_operator='王五')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/schedule_record/withdraw', json={
                'record_id': 100,
                'admin_user': 'admin',
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 0
        assert '已撤回' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any("UPDATE container_center.process_sub_steps SET status='withdrawn'" in s for s in sqls), \
            f"缺少 UPDATE 软删除, 实际: {sqls}"
        assert any('INSERT INTO container_center.data_regression_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        # 验证 data_type='schedule' 在参数元组中
        history_args_found = False
        for call in fake_conn._cursor.execute.call_args_list:
            if call.args and 'INSERT INTO container_center.data_regression_history' in str(call.args[0]):
                if len(call.args) > 1 and call.args[1][0] == 'schedule':
                    history_args_found = True
                    break
        assert history_args_found, "data_type='schedule' 未出现在 history INSERT 参数中"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_schedule(fake_conn._cursor, status='active', target_operator='王五')

        def fail_on_update(*args, **kwargs):
            sql = str(args[0]) if args else ''
            if "SET status='withdrawn'" in sql:
                raise Exception('lock wait timeout exceeded')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_update

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/schedule_record/withdraw', json={
                'record_id': 100,
                'admin_user': 'admin',
            })

        assert resp.status_code == 500
        data = resp.get_json()
        assert data['code'] == 500
        assert '事务失败' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert not any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"失败路径不应执行 COMMIT, 实际: {sqls}"
        fake_conn.rollback.assert_called_once()
