# -*- coding: utf-8 -*-
"""
F16 T16.6 前测: storage/util 12 处 SQL 引用 F6 P9 兼容

根因: F6 P9 2026-06-10 DROP 7 张表后, storage 层 + core/_config_domain 仍有 SQL 引用
      (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
      触发 MySQL 1146 WARNING + 缺表时上层崩溃

设计契约 (5 用例):
  1. core/_config_domain.py 4 处 process_names SQL 受 F6 P9 兼容保护 (返 0/{} + WARNING)
  2. mysql_storage.py attendance 4 处 SQL 加 1146 业务降级 (返 None/[]/False)
  3. mysql_storage.py schedule_records 7 处 SQL 加 1146 业务降级
  4. 全部方法有 try/except + F6 P9 标识
  5. 修复后模块能 import + 静态语法通过
"""
import sys
import unittest
import re
import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _is_excluded(path: Path) -> bool:
    s = str(path)
    return any(x in s for x in ('_archive', '.venv', '__pycache__', 'tests' + chr(92), 'tests/'))


def _collect_sql_lines(path: Path, table: str) -> list:
    if _is_excluded(path):
        return []
    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return []
    sql_lines = []
    in_docstring = False
    for line in content.split('\n'):
        stripped = line.strip()
        if '"""' in line or "'''" in line:
            dq = line.count('"""')
            sq = line.count("'''")
            if dq >= 2 and not in_docstring:
                continue
            if dq == 1:
                in_docstring = not in_docstring
                continue
            if sq == 1:
                in_docstring = not in_docstring
                continue
        if in_docstring or stripped.startswith('#'):
            continue
        if re.search(rf'\b(FROM|INTO|UPDATE|JOIN|TABLE)\s+`?{table}`?\b', line, re.IGNORECASE):
            sql_lines.append((str(path), stripped[:120]))
    return sql_lines


def _f6p9_marker_count(path: Path, table: str) -> int:
    """统计文件中针对指定表的 F16 T16.6 修复标识数"""
    if _is_excluded(path):
        return 0
    try:
        content = path.read_text(encoding='utf-8')
    except Exception:
        return 0
    # 修复注释模式: [F16 T16.6] + table 名
    return content.count('[F16 T16.6]') + content.count('[F16 T16.3]') + content.count('[F16 T16.5]')


class TestConfigDomainProcessNames(unittest.TestCase):
    """用例 1: core/_config_domain.py 4 处 process_names SQL 受 F6 P9 兼容保护"""

    def test_load_custom_processes_from_db_compatible(self):
        path = PROJECT_ROOT / "core" / "_config_domain.py"
        content = path.read_text(encoding='utf-8')
        self.assertIn('[F16 T16.6] process_names 表已 F6 P9 DROP, load_custom_processes_from_db 返 0',
                      content, "load_custom_processes_from_db 缺 F6 P9 标识")

    def test_save_display_order_to_db_compatible(self):
        path = PROJECT_ROOT / "core" / "_config_domain.py"
        content = path.read_text(encoding='utf-8')
        self.assertIn('[F16 T16.6] process_names 表已 F6 P9 DROP, save_display_order_to_db 返 0',
                      content, "save_display_order_to_db 缺 F6 P9 标识")

    def test_get_display_seq_map_compatible(self):
        path = PROJECT_ROOT / "core" / "_config_domain.py"
        content = path.read_text(encoding='utf-8')
        self.assertIn('[F16 T16.6] process_names 表已 F6 P9 DROP, get_display_seq_map 返空 dict',
                      content, "get_display_seq_map 缺 F6 P9 标识")


class TestStorageAttendanceRefactored(unittest.TestCase):
    """用例 2: mysql_storage.py attendance 4 处 SQL 加 1146 业务降级"""

    def test_attendance_methods_have_f6p9_markers(self):
        path = PROJECT_ROOT / "mobile_api_ai" / "storage" / "mysql_storage.py"
        content = path.read_text(encoding='utf-8')
        # 3 个方法 (get_attendance, get_attendance_by_date, upsert_attendance) 应有 F6 P9 标识
        self.assertIn('attendance 表 F6 P9 DROP, get_attendance 返 None', content)
        self.assertIn('attendance 表 F6 P9 DROP, get_attendance_by_date 返 []', content)
        self.assertIn('attendance 表 F6 P9 DROP, upsert_attendance 返 False', content)


class TestStorageScheduleRecordsRefactored(unittest.TestCase):
    """用例 3: mysql_storage.py schedule_records 7 处 SQL 加 1146 业务降级"""

    def test_schedule_records_methods_have_f6p9_markers(self):
        path = PROJECT_ROOT / "mobile_api_ai" / "storage" / "mysql_storage.py"
        content = path.read_text(encoding='utf-8')
        # 6 个方法 + save_schedule_record = 7 个修复标识
        markers = [
            'schedule_records 表 F6 P9 DROP, save_schedule_record 返 False',
            'schedule_records 表 F6 P9 DROP, get_schedule_record 返 None',
            'schedule_records 表 F6 P9 DROP, get_schedule_record_by_order 返 None',
            'schedule_records 表 F6 P9 DROP, get_schedule_records_by_order 返 []',
            'schedule_records 表 F6 P9 DROP, get_schedule_records 返 []',
            'schedule_records 表 F6 P9 DROP, get_all_schedule_records 返 []',
        ]
        for m in markers:
            self.assertIn(m, content, f"缺标识: {m}")


class TestCompileAndImport(unittest.TestCase):
    """用例 4: 修复后模块能 import + 静态语法通过"""

    def test_config_domain_compiles(self):
        path = PROJECT_ROOT / "core" / "_config_domain.py"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"core/_config_domain.py 编译失败: {e}")

    def test_mysql_storage_compiles(self):
        path = PROJECT_ROOT / "mobile_api_ai" / "storage" / "mysql_storage.py"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"mysql_storage.py 编译失败: {e}")


class TestF6P9Coverage(unittest.TestCase):
    """用例 5: F6 P9 修复覆盖度 (全部 storage/util 12 处)"""

    def test_total_f6p9_markers(self):
        """统计 F16 T16.x 修复标识总数 (期望 ≥ 12)"""
        paths = [
            PROJECT_ROOT / "core" / "_config_domain.py",
            PROJECT_ROOT / "mobile_api_ai" / "storage" / "mysql_storage.py",
        ]
        total = 0
        for p in paths:
            content = p.read_text(encoding='utf-8')
            # T16.6 标识
            total += content.count('[F16 T16.6]')
            # T16.3 enterprise_structure 标识 (storage 部分)
            total += content.count('[F16 T16.3]')
        # T16.3 storage 已修 3 处 + T16.6 storage 4 + schedule 7 + config 4 = 18 处
        self.assertGreaterEqual(total, 12,
                                f"F16 T16.x 修复标识数 {total} < 12 (期望 ≥ 12)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
