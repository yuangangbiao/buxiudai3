# -*- coding: utf-8 -*-
"""
RE-001 TASK-01: sub-steps 模块事务化测试

覆盖:
- /api/process_sub_step/withdraw (子步骤撤回) - 窄边界事务包裹 + 失败回滚
- /api/report_record/update (子步骤修正) - 宽边界事务包裹 (3 表) + 失败回滚
- /api/report_record/withdraw (子步骤调度员撤回) - 窄边界事务包裹 + 失败回滚

测试矩阵 (DESIGN §7.1):
- T-001: sub-steps 撤回 - 正常路径 (UPDATE + INSERT history + COMMIT)
- T-002: sub-steps 撤回 - 失败回滚 (history INSERT 失败 → ROLLBACK + 500)
- T-003: sub-steps 修正 (3表宽边界) - 正常路径 (UPDATE + INSERT history + UPDATE process_records + COMMIT)
- T-004: sub-steps 修正 (3表宽边界) - 失败回滚 (history INSERT 失败 → ROLLBACK + 500)
- T-005: sub-steps 撤回(2) - 正常路径 (UPDATE + INSERT history + COMMIT)
- T-006: sub-steps 撤回(2) - 失败回滚 (history INSERT 失败 → ROLLBACK + 500)

实现策略:
- 从 app.py 提取 _sync_completed_qty_to_package + 3 个路由函数源码
- 在最小 Flask app 中 exec 注册
- 这样测试的是**实际生产代码逻辑**，而不是复制版本
- 路由函数体内使用模块级 logger (与 app.py L43 一致)，需在 exec_globals 中注入
"""
import json
import os
import sys
import textwrap
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 从 app.py 提取 sub-steps 路由源码并 exec 到最小 Flask app
# ---------------------------------------------------------------------------
def _extract_substeps_routes():
    """从 app.py 中提取 sub-steps 相关的 1 个辅助函数 + 3 个路由函数。

    顺序很重要: 辅助函数 _sync_completed_qty_to_package 必须先 exec，
    这样后续 3 个路由函数才能正确引用它。
    """
    app_py = os.path.join(os.path.dirname(__file__), '..', '..', 'app.py')
    with open(app_py, 'r', encoding='utf-8') as f:
        source = f.read()

    routes = {}
    for func_name in [
        '_sync_completed_qty_to_package',  # 辅助函数 (无装饰器)
        'withdraw_sub_step',
        'report_record_update',
        'report_record_admin_withdraw',
    ]:
        # 找到 def 行
        start_idx = source.find(f'def {func_name}(')
        assert start_idx > 0, f"未找到 {func_name}"
        # 向上找 @app.route 装饰器 (辅助函数无装饰器)
        decorator_start = source.rfind('@app.route', 0, start_idx)
        if decorator_start > 0:
            # 回溯到 @app.route 所在行的行首 (否则首行无缩进会导致 IndentationError)
            line_start = source.rfind('\n', 0, decorator_start) + 1
        else:
            # 辅助函数没有装饰器: 从 def 所在行的行首开始
            line_start = source.rfind('\n', 0, start_idx) + 1
        # 向下找函数体结束: 找到下一个 @app.route
        next_route = source.find('@app.route', start_idx)
        if next_route > 0:
            end_idx = next_route
        else:
            end_idx = len(source)
        routes[func_name] = source[line_start:end_idx].rstrip()
    return routes


@pytest.fixture
def substeps_app():
    """构建一个最小 Flask app，包含 sub-steps 3 个路由 + 1 个辅助函数。"""
    import types
    from flask import Flask, jsonify, request

    # 桩模块 (sub-steps 路由内会本地 import notify / bridge.sync_client)
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
    routes_source = _extract_substeps_routes()

    # 准备 exec 上下文
    # 路由函数体内使用模块级 logger (与 app.py L43 logger = logging.getLogger(__name__) 一致)
    import logging as _logging
    exec_globals = {
        '__builtins__': __builtins__,
        'app': app,
        'request': request,
        'jsonify': jsonify,
        'json': json,
        'logging': _logging,
        'logger': _logging.getLogger('substeps_re001_test'),
        'pymysql': fake_pymysql,
    }

    for func_name, source in routes_source.items():
        # 去除公共前导空白 (因为提取的代码有 4 空格缩进)
        source = textwrap.dedent(source)
        compiled = compile(source, f'<test>{func_name}', 'exec')
        exec(compiled, exec_globals)

    yield app


# ---------------------------------------------------------------------------
# Fake 连接 + Cursor (同时兼容老 cur=conn.cursor() 和新 with conn.cursor() as c 两种模式)
# ---------------------------------------------------------------------------
class _FakeCursor:
    """同时兼容 `cur = conn.cursor()` 老模式 和 `with conn.cursor() as c` 新模式。"""
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
        # 老模式 `cur = conn.cursor()` 直接返回 self._cursor
        self.cursor = MagicMock(return_value=self._cursor)
        self.commit = MagicMock()
        self.rollback = MagicMock()
        self.close = MagicMock()


def _setup_existing_substep(cursor, quantity=10.0, operator='张三', order_no='WO2026001',
                            step_name='焊接', batch_no='B001', created_at=None):
    """模拟 SELECT FOR UPDATE 查到的现有 sub-step 记录。

    参数:
        quantity: 报工数量 (用于测试 "无变化" 检查)
        operator: 操作员 (用于 history 写入)
        created_at: 创建时间,默认为当前时间 (避免触发 24h 修正期限检查)
    """
    if created_at is None:
        created_at = datetime.now()  # 默认当前时间 (避免 24h 限制)
    cursor.fetchone.return_value = (
        1,                              # id
        order_no,                       # order_no
        step_name,                      # step_name
        batch_no,                       # batch_no
        quantity,                       # quantity
        operator,                       # operator
        created_at,                     # created_at (datetime 对象)
    )
    cursor.description = [
        ('id',), ('order_no',), ('step_name',),
        ('batch_no',), ('quantity',), ('operator',), ('created_at',),
    ]


def _strip_sqls(cursor):
    """从 cursor.execute.call_args_list 提取所有 SQL 字符串。"""
    return [str(c.args[0]) for c in cursor.execute.call_args_list if c.args]


# ---------------------------------------------------------------------------
# /api/process_sub_step/withdraw  — sub-steps 撤回（窄边界）
# ---------------------------------------------------------------------------
class TestSubStepsWithdrawRollback:
    """sub-steps 撤回接口 - 事务化测试"""

    def test_substeps_withdraw_rollback(self, substeps_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE process_sub_steps SET quantity=0
                       → INSERT process_sub_steps_history → COMMIT
        场景 B (失败): history INSERT 抛异常 → ROLLBACK + 500
        """
        client = substeps_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_substep(fake_conn._cursor, quantity=10.0, operator='张三')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/process_sub_step/withdraw', json={
                'sub_step_id': 1,
                'operator': '张三',
            })

        assert resp.status_code == 200, f"期望 200, 实际 {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data['code'] == 0, f"期望 code=0, 实际: {data}"
        assert '已撤回' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any('UPDATE process_sub_steps SET quantity=0' in s for s in sqls), \
            f"缺少 UPDATE 软删除, 实际: {sqls}"
        assert any('INSERT INTO process_sub_steps_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_substep(fake_conn._cursor, quantity=10.0, operator='张三')

        def fail_on_insert(*args, **kwargs):
            """模拟 history INSERT 失败,触发 ROLLBACK。"""
            sql = str(args[0]) if args else ''
            if 'INSERT INTO process_sub_steps_history' in sql:
                raise Exception('UNIQUE constraint violation: history duplicate')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_insert

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/process_sub_step/withdraw', json={
                'sub_step_id': 1,
                'operator': '张三',
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
# /api/report_record/update  — sub-steps 修正（宽边界 3 表）
# ---------------------------------------------------------------------------
class TestSubStepsCorrectWideRollback:
    """sub-steps 修正接口 - 宽边界事务化测试 (3 表同时提交)"""

    def test_substeps_correct_wide_rollback(self, substeps_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE process_sub_steps (主表)
                       → INSERT process_sub_steps_history
                       → UPDATE process_records (宽边界第 3 表)
                       → COMMIT
        场景 B (失败): history INSERT 抛异常 → ROLLBACK + 500
        """
        client = substeps_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        # new_quantity=5.0 < old_qty=10.0,避免触发订单上限校验 (order_req 检查)
        _setup_existing_substep(fake_conn._cursor, quantity=10.0, operator='张三')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/report_record/update', json={
                'sub_step_id': 1,
                'new_quantity': 5.0,
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
        # 验证 3 表都在事务内
        assert any('UPDATE process_sub_steps SET quantity=' in s for s in sqls), \
            f"缺少 UPDATE process_sub_steps 主表, 实际: {sqls}"
        assert any('INSERT INTO process_sub_steps_history' in s for s in sqls), \
            f"缺少 INSERT process_sub_steps_history, 实际: {sqls}"
        assert any('UPDATE process_records SET last_reverted_at' in s for s in sqls), \
            f"缺少 UPDATE process_records (宽边界 3 表), 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_substep(fake_conn._cursor, quantity=10.0, operator='张三')

        def fail_on_insert(*args, **kwargs):
            """模拟 history INSERT 失败,触发 ROLLBACK (3 表全部回滚)。"""
            sql = str(args[0]) if args else ''
            if 'INSERT INTO process_sub_steps_history' in sql:
                raise Exception('UNIQUE constraint violation: history duplicate')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_insert

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/report_record/update', json={
                'sub_step_id': 1,
                'new_quantity': 5.0,
                'admin_user': 'admin',
            })

        assert resp.status_code == 500
        data = resp.get_json()
        assert data['code'] == 500
        assert '事务失败' in data['message']
        assert '已回滚' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        # 失败路径: 3 表都未 COMMIT
        assert not any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"失败路径不应执行 COMMIT, 实际: {sqls}"
        # 验证 3 表的写入都没提交 (应有 START TRANSACTION, 但无 COMMIT)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"应有 START TRANSACTION, 实际: {sqls}"
        fake_conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# /api/report_record/withdraw  — sub-steps 调度员撤回（窄边界）
# ---------------------------------------------------------------------------
class TestSubStepsWithdraw2Rollback:
    """sub-steps 调度员撤回接口 - 事务化测试"""

    def test_substeps_withdraw2_rollback(self, substeps_app):
        """
        场景 A (正常): START TRANSACTION → UPDATE process_sub_steps SET quantity=0
                       → INSERT process_sub_steps_history → COMMIT
        场景 B (失败): history INSERT 抛异常 → ROLLBACK + 500
        """
        client = substeps_app.test_client()

        # ---------- 场景 A: 正常路径 ----------
        fake_conn = _FakeConnection()
        _setup_existing_substep(fake_conn._cursor, quantity=10.0, operator='张三')

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/report_record/withdraw', json={
                'sub_step_id': 1,
                'admin_user': 'admin',
            })

        assert resp.status_code == 200, f"期望 200, 实际 {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data['code'] == 0, f"期望 code=0, 实际: {data}"
        assert '已撤回' in data['message']

        sqls = _strip_sqls(fake_conn._cursor)
        assert any('START TRANSACTION' in s for s in sqls), \
            f"缺少 START TRANSACTION, 实际: {sqls}"
        assert any('UPDATE process_sub_steps SET quantity=0' in s for s in sqls), \
            f"缺少 UPDATE 软删除, 实际: {sqls}"
        assert any('INSERT INTO process_sub_steps_history' in s for s in sqls), \
            f"缺少 INSERT history, 实际: {sqls}"
        assert any(s.strip().upper() == 'COMMIT' for s in sqls), \
            f"缺少 COMMIT, 实际: {sqls}"
        fake_conn.close.assert_called_once()
        fake_conn.rollback.assert_not_called()

        # ---------- 场景 B: 失败回滚 ----------
        fake_conn = _FakeConnection()
        _setup_existing_substep(fake_conn._cursor, quantity=10.0, operator='张三')

        def fail_on_insert(*args, **kwargs):
            """模拟 history INSERT 失败,触发 ROLLBACK。"""
            sql = str(args[0]) if args else ''
            if 'INSERT INTO process_sub_steps_history' in sql:
                raise Exception('UNIQUE constraint violation: history duplicate')
            return 1
        fake_conn._cursor.execute.side_effect = fail_on_insert

        with patch('pymysql.connect', return_value=fake_conn):
            resp = client.post('/api/report_record/withdraw', json={
                'sub_step_id': 1,
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
