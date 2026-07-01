# -*- coding: utf-8 -*-
"""
T1 前测：验证 0610_data_packages_flow_type.py 的 SQL 语法与执行路径
无需真实 DB 连接，用 mock cursor 验证:
  1. 文件能成功 exec（无 Python 语法错误）
  2. upgrade() 路径对 data_packages 执行了 ADD COLUMN flow_type
  3. upgrade() 路径对 data_packages 执行了 2 个索引 idx_pkg_flow + idx_pkg_flow_order
  4. upgrade() 顺手对 process_records 也加了 flow_type 列
  5. downgrade() 路径执行了 DROP COLUMN + DROP INDEX（按反序）

执行方式:
    cd mobile_api_ai/migrations
    py -m unittest __pre_tests__.test_0610_data_packages_flow_type -v
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
    """收集器: 记录所有执行的 SQL 语句（按顺序）"""
    def __init__(self):
        self.statements = []

    def __call__(self, sql: str) -> None:
        self.statements.append(sql.strip())


class Test0610Migration(unittest.TestCase):
    """T1 前测用例"""

    def setUp(self):
        self.collected = CollectedSQL()
        self.mock_conn = MagicMock()
        # mock conn.cursor() 返回的对象作为 context manager
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.execute = self.collected
        self.mock_conn.cursor.return_value = mock_cm

    def _exec_migration(self, rollback: bool = False) -> list:
        """exec 0610 迁移文件, 收集所有 SQL"""
        migration_file = MIGRATIONS_DIR / '0610_data_packages_flow_type.py'
        self.assertTrue(migration_file.exists(), f'迁移文件不存在: {migration_file}')

        namespace = {
            'conn': self.mock_conn,
            'cursor': None,  # run.py 初始为 None
            'ROLLBACK': rollback,
        }
        # exec 本文件, 让文件末尾的入口判断走 upgrade() 或 downgrade()
        with open(migration_file, 'r', encoding='utf-8') as f:
            code = f.read()
        exec(compile(code, str(migration_file), 'exec'), namespace)
        return self.collected.statements

    # ── 1 ──
    def test_file_exists_and_executable(self):
        """迁移文件存在且可 exec（无 Python 语法错误）"""
        try:
            self._exec_migration(rollback=False)
        except SyntaxError as e:
            self.fail(f'迁移文件 Python 语法错误: {e}')

    # ── 2 ──
    def test_upgrade_adds_flow_type_to_data_packages(self):
        """upgrade() 对 data_packages 执行 ADD COLUMN flow_type"""
        stmts = self._exec_migration(rollback=False)
        # 找 ALTER TABLE data_packages ADD COLUMN flow_type
        matched = [s for s in stmts
                   if 'ALTER TABLE' in s.upper()
                   and 'data_packages' in s
                   and 'ADD COLUMN' in s.upper()
                   and 'flow_type' in s]
        self.assertEqual(len(matched), 1,
                         f'期望 data_packages ADD COLUMN flow_type 1 次, 实际 {len(matched)} 次. SQL: {stmts}')
        # 字段类型: VARCHAR(64)
        self.assertIn('VARCHAR(64)', matched[0],
                      f'flow_type 应为 VARCHAR(64), 实际 SQL: {matched[0]}')
        # DEFAULT ''
        self.assertIn("DEFAULT ''", matched[0],
                      f'flow_type 应有 DEFAULT \'\', 实际 SQL: {matched[0]}')

    # ── 3 ──
    def test_upgrade_adds_two_indexes(self):
        """upgrade() 对 data_packages 添加 2 索引"""
        stmts = self._exec_migration(rollback=False)
        # 找 data_packages 的 ADD INDEX
        idx_stmts = [s for s in stmts
                     if 'ALTER TABLE' in s.upper()
                     and 'data_packages' in s
                     and 'ADD INDEX' in s.upper()]
        self.assertEqual(len(idx_stmts), 2,
                         f'期望 data_packages 2 个索引, 实际 {len(idx_stmts)} 个. SQL: {idx_stmts}')
        # 索引名
        idx_names = []
        for s in idx_stmts:
            # ADD INDEX idx_xxx (...) 提取 idx_xxx
            import re
            m = re.search(r'ADD INDEX\s+(\w+)', s, re.IGNORECASE)
            if m:
                idx_names.append(m.group(1))
        self.assertIn('idx_pkg_flow', idx_names,
                      f'期望索引 idx_pkg_flow, 实际: {idx_names}')
        self.assertIn('idx_pkg_flow_order', idx_names,
                      f'期望索引 idx_pkg_flow_order, 实际: {idx_names}')

    # ── 4 ──
    def test_upgrade_patches_process_records(self):
        """upgrade() 顺手对 process_records 加 flow_type 列（补 fix_missing_tables.sql 的缺）"""
        stmts = self._exec_migration(rollback=False)
        # 找 ALTER TABLE process_records ADD COLUMN flow_type
        matched = [s for s in stmts
                   if 'ALTER TABLE' in s.upper()
                   and 'process_records' in s
                   and 'ADD COLUMN' in s.upper()
                   and 'flow_type' in s]
        self.assertGreaterEqual(len(matched), 1,
                               f'期望 process_records ADD COLUMN flow_type 至少 1 次, 实际 {len(matched)} 次. SQL: {stmts}')

    # ── 5 ──
    def test_downgrade_drops_column_and_indexes(self):
        """downgrade() 路径 DROP COLUMN + DROP INDEX（按反序）"""
        stmts = self._exec_migration(rollback=True)
        # data_packages 应有 DROP COLUMN + DROP INDEX
        drop_col_data = [s for s in stmts
                         if 'ALTER TABLE' in s.upper()
                         and 'data_packages' in s
                         and 'DROP COLUMN' in s.upper()]
        drop_idx_data = [s for s in stmts
                         if 'ALTER TABLE' in s.upper()
                         and 'data_packages' in s
                         and 'DROP INDEX' in s.upper()]
        self.assertEqual(len(drop_col_data), 1, f'data_packages DROP COLUMN 应 1 次, 实际 {len(drop_col_data)}')
        self.assertEqual(len(drop_idx_data), 2, f'data_packages DROP INDEX 应 2 次, 实际 {len(drop_idx_data)}')
        # 反序: DROP INDEX 在 DROP COLUMN 之前执行（先删索引再删列）
        # 找到两个操作的位置
        first_drop_idx = next(i for i, s in enumerate(stmts) if s in drop_idx_data)
        first_drop_col = next(i for i, s in enumerate(stmts) if s in drop_col_data)
        self.assertLess(first_drop_idx, first_drop_col,
                        f'DROP INDEX 必须在 DROP COLUMN 之前执行（索引依赖列）')

    # ── 6 ──
    def test_python_u_execution_environment_check(self):
        """T1 DDL 脚本必须用 python -u (unbuffered) + 检测执行环境（进化项 #10+）"""
        # 读取迁移文件源码, 验证包含环境检测代码
        migration_file = MIGRATIONS_DIR / '0610_data_packages_flow_type.py'
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # 必须有 sys.platform 检测 或 等价的环境检查
        has_platform_check = 'sys.platform' in content or 'platform.system' in content
        self.assertTrue(has_platform_check,
                        'T1 迁移必须检测执行环境 (sys.platform / platform.system)，避免跨平台 SQL 错误')


if __name__ == "__main__":
    unittest.main()
