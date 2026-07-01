# -*- coding: utf-8 -*-
"""
RE-001 TASK-04: outsource 模块事务化测试

覆盖:
- /api/outsource_record/update (外协修正) - 事务包裹 + 失败回滚
- /api/outsource_record/withdraw (外协撤回) - 事务包裹 + 失败回滚

测试矩阵 (DESIGN §7.1):
- T-001: outsource 修正 - 正常路径 (动态 SQL UPDATE + INSERT history + COMMIT)
- T-002: outsource 修正 - 失败回滚 (history INSERT 失败 → ROLLBACK + 500)
- T-003: outsource 撤回 - 正常路径 (UPDATE status='withdrawn' + INSERT + COMMIT)
- T-004: outsource 撤回 - 失败回滚 (UPDATE 失败 → ROLLBACK + 500)

实现策略:
- 从 app.py 提取 outsource_record_update / outsource_record_admin_withdraw 的源码
- 在最小 Flask app 中 exec 注册
- 这样测试的是**实际生产代码逻辑**，而不是复制版本
"""
import json
import sys
import textwrap
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 从 app.py 提取 outsource 路由源码并 exec 到最小 Flask app
# ---------------------------------------------------------------------------
def _extract_outsource_routes():
    """从 app.py 中提取 outsource_record_update 和 outsource_record_admin_withdraw 的源码。"""
    import os
    app_py = os.path.join(os.path.dirname(__file__), '..', '..', 'app.py')
    with open(app_py, 'r', encoding='utf-8') as f:
        source = f.read()

    routes = {}
    for func_name, end_marker in [
        ('outsource_record_update', '# === RE-001: 事务包裹 START (outsource 撤回) ==='),
        ('outsource_record_admin_withdraw', '# === RE-001: 事务包裹 END ==='),
    ]:
        # 找到 def 行
        start_idx = source.find(f'def {func_name}(')
        assert start_idx > 0, f"未找到 {func_name}"
        # 找到函数体对应的 @app.route 装饰器起点
        decorator_start = source.rfind('@app.route', 0, start_idx)
        assert decorator_start > 0, f"未找到 {func_name} 的装饰器"
        # 回溯到 @app.route 所在行的行首 (否则首行无缩进会导致 IndentationError)
        line_start = source.rfind('\n', 0, decorator_start) + 1
        # 向下找函数体结束: 找到下一个 @app.route
        next_route = source.find('@app.route', start_idx)
        if next_route > 0:
            end_idx = next_route
        else:
            end_idx = len(source)
        routes[func_name] = source[line_start:end_idx].rstrip()
    return routes


@pytest.fixture
def outsource_app():
    """构建一个最小 Flask app，包含 outsource_record_update 和 outsource_record_admin_withdraw。"""
    import types
    from flask import Flask, jsonify, request

    # 桩模块 (外协接口不直接调用 notify/bridge，但保持与 quality 测试一致的桩)
    fake_notify = MagicMock()
    fake_bridge_pkg = MagicMock()
    fake_sync = MagicMock()
    fake_sync.send = MagicMock()
    sys.modules['notify'] = fake_notify
    if 'bridge' not in sys.modules:
        sys.modules['bridge'] = fake_bridge_pkg
    sys.modules['bridge.sync_client'] = fake_sync

    # core.config 桩 (函数内有 from core.config import ... 本地导入)
    fake_core_cfg = types.ModuleType('core.config')
    fake_core_cfg.CONTAINER_MYSQL_CFG = {
        'host': '127.0.0.1', 'port': 3306,
        'user': 'root', 'password': '',
        'database': 'container_center', 'charset': 'utf8mb4',
    }
    fake_core_cfg.DB_CONNECT_TIMEOUT = 5
    sys.modules['core.config'] = fake_core_cfg

    # 桩 pymysql
    fake_pymysql = MagicMock()
    sys.modules['pymysql'] = fake_pymysql

    app = Flask(__name__)
    app.config['TESTING'] = True

    # 提取并 exec 路由源码
    routes_source = _extract_outsource_routes()

    # 准备 exec 上下文
    import logging as _logging
    exec_globals = {
        '__builtins__': __builtins__,
        'app': app,
        'request': request,
        'jsonify': jsonify,
        'json': json,
        'logging': _logging,
        # 路由函数体内使用模块级 logger (与 app.py L43 logger = logging.getLogger(__name__) 一致)
        'logger': _logging.getLogger('outsource_re001_test'),
        'pymysql': fake_pymysql,
    }

    for func_name, source in routes_source.items():
        # 去除公共前导空白 (因为提取的代码有 4 空格缩进)
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


class _FakeConnection:
    def __init__(self):
        self._cursor = _FakeCursor()
        # outsource 函数用 `cur = conn.cursor()` 旧模式，需让 cursor() 直接返回 _FakeCursor
        self.cursor = MagicMock(return_value=self._cursor)
        self.commit = MagicMock()
        self.rollback = MagicMock()
        self.close = MagicMock()


def _setup_existing_outsource_record(cursor, status='active', priority='normal',
                                     target_operator='张三'):
    """设置 SELECT * FROM data_packages 返回的模拟行。

    列顺序必须与 description 一致,确保 dict(zip(col, row)) 中各 .get(key) 能取到值。
    """
    cursor.fetchone.return_value = (
        1,                       # id
        'outsource',             # data_type
        'WO2026001',             # related_order
        '焊接',                  # related_process (step_name)
        '委托加工单1',            # title
        '详情内容',              # content
        priority,                # priority
        target_operator,         # target_operator
        status,                  # status
        '2026-06-08 10:00:00',   # created_at
    )
    cursor.description = [
        ('id',), ('data_type',), ('related_order',), ('related_process',),
        ('title',), ('content',), ('priority',), ('target_operator',),
        ('status',), ('created_at',),
    ]


def _strip_sqls(cursor):
    return [str(c.args[0]) for c in cursor.execute.call_args_list if c.args]


# ---------------------------------------------------------------------------
# /api/outsource_record/update  — 外协修正
# ---------------------------------------------------------------------------
class TestOutsourceCorrectRollback:
    """外协修正接口 - 事务化测试"""

    def test_outsource_update_rollback(self, outsource_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE (动态 set_clause) → INSERT history → COMMIT
        场景 B (失败): history INSERT 抛异常 → ROLLBACK + 500
        """
        client = outsource_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_outsource_record(fake_conn._cursor, status='active', priority='normal')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/outsource_record/update', json={
                'record_id': 1,
                'priority': 'high',
                'admin_user': 'admin',
                'reason': 'admin_force',
            })

        assert resp.status_code == 200, f"期望 200, 实际 {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data['code'] == 0, f"期望 code=0, 实际: {data}"
        assert '外协记录已修改' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any('UPDATE container_center.data_packages SET priority' in s for s in sqls), \
            f"缺少 UPDATE 主表 (动态 set_clause), 实际: {sqls}"
        assert any('INSERT INTO container_center.data_regression_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_outsource_record(fake_conn._cursor, status='active', priority='normal')

        def fail_on_insert(*args, **kwargs):
            sql = str(args[0]) if args else ''
            if 'INSERT INTO container_center.data_regression_history' in sql:
                raise Exception('UNIQUE constraint violation: history duplicate')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_insert

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/outsource_record/update', json={
                'record_id': 1,
                'priority': 'high',
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
# /api/outsource_record/withdraw  — 外协撤回
# ---------------------------------------------------------------------------
class TestOutsourceWithdrawRollback:
    """外协撤回接口 - 事务化测试"""

    def test_outsource_withdraw_rollback(self, outsource_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE status='withdrawn' → INSERT history → COMMIT
        场景 B (失败): UPDATE 抛异常 → ROLLBACK + 500
        """
        client = outsource_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_outsource_record(fake_conn._cursor, status='active', priority='normal')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/outsource_record/withdraw', json={
                'record_id': 1,
                'admin_user': 'admin',
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 0
        assert '已撤回外协记录' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any("UPDATE container_center.data_packages SET status='withdrawn'" in s for s in sqls), \
            f"缺少 UPDATE 软删除, 实际: {sqls}"
        assert any('INSERT INTO container_center.data_regression_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_outsource_record(fake_conn._cursor, status='active', priority='normal')

        def fail_on_update(*args, **kwargs):
            sql = str(args[0]) if args else ''
            if "SET status='withdrawn'" in sql:
                raise Exception('lock wait timeout exceeded')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_update

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/outsource_record/withdraw', json={
                'record_id': 1,
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
