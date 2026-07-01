# -*- coding: utf-8 -*-
"""
RE-001 TASK-02: quality 模块事务化测试

覆盖:
- /api/quality_record/update (质量修正) - 事务包裹 + 失败回滚
- /api/quality_record/withdraw (质量撤回) - 事务包裹 + 失败回滚

测试矩阵 (DESIGN §7.1):
- T-001: quality 修正 - 正常路径 (UPDATE + INSERT history + COMMIT)
- T-002: quality 修正 - 失败回滚 (history INSERT 失败 → ROLLBACK + 500)
- T-003: quality 撤回 - 正常路径 (UPDATE status='withdrawn' + INSERT + COMMIT)
- T-004: quality 撤回 - 失败回滚 (UPDATE 失败 → ROLLBACK + 500)

实现策略:
- 从 app.py 提取 quality_record_update / quality_record_admin_withdraw 的源码
- 在最小 Flask app 中 exec 注册
- 这样测试的是**实际生产代码逻辑**，而不是复制版本
"""
import json
import sys
import textwrap
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 从 app.py 提取 quality 路由源码并 exec 到最小 Flask app
# ---------------------------------------------------------------------------
def _extract_quality_routes():
    """从 app.py 中提取 quality_record_update 和 quality_record_admin_withdraw 的源码。"""
    import os
    app_py = os.path.join(os.path.dirname(__file__), '..', '..', 'app.py')
    with open(app_py, 'r', encoding='utf-8') as f:
        source = f.read()

    # 用字符串定位提取两个函数体 (从 def 行到下一个同级 def 或 # === RE-001 包裹结束)
    routes = {}
    for func_name, end_marker in [
        ('quality_record_update', '# === RE-001: 事务包裹 START (quality 修正) ==='),
        ('quality_record_admin_withdraw', '# === RE-001: 事务包裹 START (quality 撤回) ==='),
    ]:
        # 找到 def 行
        start_idx = source.find(f'def {func_name}(')
        assert start_idx > 0, f"未找到 {func_name}"
        # 找到函数体结束 (下一个 @app.route 或 文件结束)
        # 从 def 行向前看，找到对应的 @app.route 装饰器
        # 向上找 @app.route
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
def quality_app():
    """构建一个最小 Flask app，包含 quality_record_update 和 quality_record_admin_withdraw。"""
    import types
    from flask import Flask, jsonify, request

    # 桩模块
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
    routes_source = _extract_quality_routes()

    # 准备 exec 上下文
    exec_globals = {
        '__builtins__': __builtins__,
        'app': app,
        'request': request,
        'jsonify': jsonify,
        'json': json,
        'logging': __import__('logging'),
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
        self.cursor = MagicMock()
        self.cursor.return_value.__enter__ = MagicMock(return_value=self._cursor)
        self.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self.commit = MagicMock()
        self.rollback = MagicMock()
        self.close = MagicMock()


def _setup_existing_record(cursor, result='合格', status='active'):
    cursor.fetchone.return_value = (
        1, 'WO2026001', '焊接', result, '张三', status
    )
    cursor.description = [
        ('id',), ('order_no',), ('process_name',),
        ('result',), ('inspector',), ('status',),
    ]


def _strip_sqls(cursor):
    return [str(c.args[0]) for c in cursor.execute.call_args_list if c.args]


def patch_pymysql(fake_conn):
    """patch sys.modules['pymysql'] 以返回 fake_conn。"""
    fake_pymysql = MagicMock()
    fake_pymysql.connect.return_value = fake_conn
    return patch('sys.modules', {'pymysql': fake_pymysql})


# ---------------------------------------------------------------------------
# /api/quality_record/update  — 质量修正
# ---------------------------------------------------------------------------
class TestQualityCorrectRollback:
    """质量修正接口 - 事务化测试"""

    def test_quality_correct_rollback(self, quality_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE → INSERT history → COMMIT
        场景 B (失败): history INSERT 抛异常 → ROLLBACK + 500
        """
        client = quality_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_record(fake_conn._cursor, result='合格')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/quality_record/update', json={
                'record_id': 1,
                'new_result': '不合格',
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
        assert any('UPDATE container_center.quality_records SET result' in s for s in sqls), \
            f"缺少 UPDATE 主表, 实际: {sqls}"
        assert any('INSERT INTO container_center.data_regression_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_record(fake_conn._cursor, result='合格')

        def fail_on_insert(*args, **kwargs):
            sql = str(args[0]) if args else ''
            if 'INSERT INTO container_center.data_regression_history' in sql:
                raise Exception('UNIQUE constraint violation: history duplicate')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_insert

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/quality_record/update', json={
                'record_id': 1,
                'new_result': '不合格',
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
# /api/quality_record/withdraw  — 质量撤回
# ---------------------------------------------------------------------------
class TestQualityWithdrawRollback:
    """质量撤回接口 - 事务化测试"""

    def test_quality_withdraw_rollback(self, quality_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE status='withdrawn' → INSERT history → COMMIT
        场景 B (失败): UPDATE 抛异常 → ROLLBACK + 500
        """
        client = quality_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_record(fake_conn._cursor, result='合格', status='active')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/quality_record/withdraw', json={
                'record_id': 1,
                'admin_user': 'admin',
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 0
        assert '已撤回' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any("UPDATE container_center.quality_records SET status='withdrawn'" in s for s in sqls), \
            f"缺少 UPDATE 软删除, 实际: {sqls}"
        assert any('INSERT INTO container_center.data_regression_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_record(fake_conn._cursor, result='合格', status='active')

        def fail_on_update(*args, **kwargs):
            sql = str(args[0]) if args else ''
            if "SET status='withdrawn'" in sql:
                raise Exception('lock wait timeout exceeded')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_update

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/quality_record/withdraw', json={
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
