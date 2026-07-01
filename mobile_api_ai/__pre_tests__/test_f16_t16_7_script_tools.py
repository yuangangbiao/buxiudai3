# -*- coding: utf-8 -*-
"""
F16 T16.7 前测: 脚本工具 3 处 process_names 修复

根因: F6 P9 2026-06-10 DROP 7 张表后, scripts/ 目录 3 个工具脚本仍有 SELECT FROM process_names
      (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
      check_all_dbs.py 实际查 sub_steps (不在 DROP 列表), 已通过
      schedule_records scripts 已 T16.2 修 (clean_dispatch_cache.py) + T16.6 修 (storage 层)

设计契约 (5 用例):
  1. scripts/q_describe_tables.py 不再 SELECT FROM process_names (F6 P9 改用 dispatch_cache)
  2. scripts/fix_4orders_anomaly.py 不再 SELECT FROM process_names
  3. scripts/migrations/migrate_data_type_to_v1.py 不再 SELECT FROM process_names
  4. 3 个 scripts 改用 PROCESS_CODES + _custom_process_codes 内存数据
  5. 3 个 scripts 编译通过 + 修复标识存在
"""
import sys
import unittest
import re
import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


SCRIPTS = [
    "scripts/q_describe_tables.py",
    "scripts/fix_4orders_anomaly.py",
    "scripts/migrations/migrate_data_type_to_v1.py",
]


def _has_process_names_sql(content: str) -> bool:
    """检测文中是否含 SELECT/INSERT/UPDATE/DELETE FROM process_names (排除注释)"""
    in_docstring = False
    for line in content.split('\n'):
        stripped = line.strip()
        if '"""' in line or "'''" in line:
            dq = line.count('"""')
            sq = line.count("'''")
            if dq >= 2 and not in_docstring:
                continue  # 单行 docstring
            if dq == 1:
                in_docstring = not in_docstring
                continue
            if sq == 1:
                in_docstring = not in_docstring
                continue
        if in_docstring or stripped.startswith('#'):
            continue
        if re.search(r'\b(FROM|INTO|UPDATE|JOIN|TABLE)\s+`?process_names`?\b', line, re.IGNORECASE):
            return True
    return False


class TestQDescribeTablesRefactored(unittest.TestCase):
    """用例 1: q_describe_tables.py 不再 SELECT FROM process_names"""

    def test_no_process_names_sql(self):
        path = PROJECT_ROOT / "scripts" / "q_describe_tables.py"
        if not path.exists():
            self.skipTest("文件不存在")
        content = path.read_text(encoding='utf-8')
        self.assertFalse(_has_process_names_sql(content),
                         f"q_describe_tables.py 仍含 process_names SQL")


class TestFix4OrdersAnomalyRefactored(unittest.TestCase):
    """用例 2: fix_4orders_anomaly.py 不再 SELECT FROM process_names"""

    def test_no_process_names_sql(self):
        path = PROJECT_ROOT / "scripts" / "fix_4orders_anomaly.py"
        if not path.exists():
            self.skipTest("文件不存在")
        content = path.read_text(encoding='utf-8')
        self.assertFalse(_has_process_names_sql(content),
                         f"fix_4orders_anomaly.py 仍含 process_names SQL")


class TestMigrateDataTypeRefactored(unittest.TestCase):
    """用例 3: migrate_data_type_to_v1.py 不再 SELECT FROM process_names"""

    def test_no_process_names_sql(self):
        path = PROJECT_ROOT / "scripts" / "migrations" / "migrate_data_type_to_v1.py"
        if not path.exists():
            self.skipTest("文件不存在")
        content = path.read_text(encoding='utf-8')
        self.assertFalse(_has_process_names_sql(content),
                         f"migrate_data_type_to_v1.py 仍含 process_names SQL")


class TestScriptsUseMemoryDataSource(unittest.TestCase):
    """用例 4: 3 个 scripts 改用 PROCESS_CODES 内存数据"""

    def test_q_describe_uses_process_codes(self):
        path = PROJECT_ROOT / "scripts" / "q_describe_tables.py"
        if not path.exists():
            self.skipTest("文件不存在")
        content = path.read_text(encoding='utf-8')
        self.assertIn('PROCESS_CODES', content,
                      "q_describe_tables.py 未引用 PROCESS_CODES (未改用内存)")

    def test_fix_4orders_uses_process_codes(self):
        path = PROJECT_ROOT / "scripts" / "fix_4orders_anomaly.py"
        if not path.exists():
            self.skipTest("文件不存在")
        content = path.read_text(encoding='utf-8')
        self.assertIn('PROCESS_CODES', content,
                      "fix_4orders_anomaly.py 未引用 PROCESS_CODES (未改用内存)")

    def test_migrate_uses_process_codes(self):
        path = PROJECT_ROOT / "scripts" / "migrations" / "migrate_data_type_to_v1.py"
        if not path.exists():
            self.skipTest("文件不存在")
        content = path.read_text(encoding='utf-8')
        self.assertIn('PROCESS_CODES', content,
                      "migrate_data_type_to_v1.py 未引用 PROCESS_CODES (未改用内存)")


class TestScriptsCompileAndF6P9Marker(unittest.TestCase):
    """用例 5: 3 个 scripts 编译通过 + 修复标识存在"""

    def test_all_compile(self):
        for rel in SCRIPTS:
            p = PROJECT_ROOT / rel
            if not p.exists():
                continue
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"{rel} 编译失败: {e}")

    def test_all_have_f6p9_marker(self):
        for rel in SCRIPTS:
            p = PROJECT_ROOT / rel
            if not p.exists():
                continue
            content = p.read_text(encoding='utf-8')
            self.assertIn('F16 T16.7', content,
                          f"{rel} 缺 F16 T16.7 修复标识")


if __name__ == "__main__":
    unittest.main(verbosity=2)
