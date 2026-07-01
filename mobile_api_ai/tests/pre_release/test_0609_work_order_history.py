# -*- coding: utf-8 -*-
"""
T1 前测：验证 0609_work_order_history.py 的 SQL 语法与执行路径
无需真实 DB 连接，用 mock cursor 验证：
  1. 文件能成功 exec（无 Python 语法错误）
  2. upgrade() 路径执行了 CREATE TABLE
  3. downgrade() 路径执行了 DROP TABLE
  4. SQL 关键字与字段名拼写正确

执行方式:
    cd mobile_api_ai/migrations
    python -m unittest __pre_tests__.test_0609_work_order_history -v
"""
import os
import sys
import unittest
from unittest.mock import MagicMock
from pathlib import Path

# 把 migrations 目录加入 path
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MIGRATIONS_DIR))


class CollectedSQL:
    """收集器：记录所有执行的 SQL 语句（按顺序）"""
    def __init__(self):
        self.statements = []

    def __call__(self, sql: str) -> None:
        self.statements.append(sql.strip())


class Test0609Migration(unittest.TestCase):
    """T1 前测用例"""

    def setUp(self):
        # 每次测试清空收集器
        self.collected = CollectedSQL()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value.execute = self.collected

    def _exec_migration(self, rollback: bool = False) -> list:
        """exec 0609 迁移文件，收集所有 SQL"""
        migration_file = MIGRATIONS_DIR / '0609_work_order_history.py'
        self.assertTrue(migration_file.exists(), f'迁移文件不存在: {migration_file}')

        namespace = {
            'conn': self.mock_conn,
            'cursor': None,  # run.py 初始为 None
            'ROLLBACK': rollback,
        }
        exec(migration_file.read_text(encoding='utf-8'), namespace)
        return self.collected.statements

    def test_upgrade_creates_table(self):
        """↑ upgrade 必须执行 CREATE TABLE IF NOT EXISTS"""
        stmts = self._exec_migration(rollback=False)
        self.assertEqual(len(stmts), 1, f'upgrade 应该执行 1 条 SQL，实际 {len(stmts)}')
        sql = stmts[0]
        self.assertIn('CREATE TABLE', sql.upper())
        self.assertIn('IF NOT EXISTS', sql.upper())
        self.assertIn('container_center.work_order_history', sql)

    def test_upgrade_includes_all_required_columns(self):
        """↑ upgrade 必须包含全部 9 个字段"""
        stmts = self._exec_migration(rollback=False)
        sql = stmts[0]
        required_columns = [
            'id', 'order_no', 'field_name',
            'old_value', 'new_value', 'changed_by',
            'change_reason', 'change_source', 'changed_at',
        ]
        for col in required_columns:
            self.assertIn(col, sql, f'缺少字段: {col}')

    def test_upgrade_includes_all_required_indexes(self):
        """↑ upgrade 必须包含 4 个索引（order_no, field_name, changed_at, order_no+field_name）"""
        stmts = self._exec_migration(rollback=False)
        sql = stmts[0]
        required_indexes = [
            'idx_woh_order_no',
            'idx_woh_field_name',
            'idx_woh_changed_at',
            'idx_woh_order_field',
        ]
        for idx in required_indexes:
            self.assertIn(idx, sql, f'缺少索引: {idx}')

    def test_upgrade_uses_innodb_utf8mb4(self):
        """↑ upgrade 必须使用 InnoDB + utf8mb4（与 0608 风格一致）"""
        stmts = self._exec_migration(rollback=False)
        sql = stmts[0].upper()
        self.assertIn('ENGINE=INNODB', sql)
        self.assertIn('CHARSET=UTF8MB4', sql)

    def test_downgrade_drops_table(self):
        """↓ downgrade 必须执行 DROP TABLE IF EXISTS"""
        stmts = self._exec_migration(rollback=True)
        self.assertEqual(len(stmts), 1, f'downgrade 应该执行 1 条 SQL，实际 {len(stmts)}')
        sql = stmts[0]
        self.assertIn('DROP TABLE', sql.upper())
        self.assertIn('IF EXISTS', sql.upper())
        self.assertIn('container_center.work_order_history', sql)

    def test_no_python_syntax_error(self):
        """文件本身必须能 exec 通过（无语法错误）"""
        try:
            self._exec_migration(rollback=False)
        except SyntaxError as e:
            self.fail(f'0609 迁移文件有 Python 语法错误: {e}')

    def test_isolated_from_0607_0608(self):
        """T1 不应修改 0607/0608 文件（独立性）"""
        for old_file in ['0607_data_regression.sql', '0608_data_regression_history.sql']:
            path = MIGRATIONS_DIR / old_file
            # 仅检查文件未被本任务改动（mtime 不能晚于今天）
            import time
            if path.exists():
                mtime = path.stat().st_mtime
                # 本任务起始时间：2026-06-09 00:00:00
                # 0 时区时间戳
                task_start_ts = time.mktime((2026, 6, 9, 0, 0, 0, 0, 0, 0))
                self.assertLess(
                    mtime, task_start_ts,
                    f'{old_file} 被本次任务修改（mtime 晚于 2026-06-09），破坏独立性'
                )


if __name__ == '__main__':
    unittest.main(verbosity=2)
