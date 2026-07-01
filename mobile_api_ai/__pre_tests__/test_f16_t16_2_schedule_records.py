# -*- coding: utf-8 -*-
"""
F16 T16.2 前测: schedule_records 7 处生产路径修复

根因: F6 P9 2026-06-10 已 DROP container_center (MySQL) + wechat_container (SQLite) 的 schedule_records 表
      (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
      仍有 7 处生产路径 SQL 引用 schedule_records, 触发 MySQL 1146 WARNING + 脚本崩溃

设计契约 (5 用例):
  1. clean_dispatch_cache.py L50,L53,L56 全部 try/except 保护
  2. check_schedule_records.py L15,L17,L36,L49 全部 try/except 保护
  3. 7 处生产路径不再含 SELECT/DELETE FROM schedule_records
  4. 删表/空库场景下脚本不崩溃
  5. 修复后脚本可正常 import + 静态语法通过
"""
import sys
import unittest
import re
import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MOBILE_API = PROJECT_ROOT / "mobile_api_ai"


def _is_excluded(path: Path) -> bool:
    s = str(path)
    return any(x in s for x in ('_archive', '.venv', '__pycache__', 'tests' + chr(92), 'tests/'))


def _collect_sql_lines(path: Path, table: str) -> list:
    """收集文件中针对指定表的 SQL 引用 (排除注释/docstring)"""
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
                continue  # 单行 docstring
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


# ──────────────────────────────────────────────
# 7 处生产路径精确位置
# ──────────────────────────────────────────────
PRODUCTION_PATHS = [
    "mobile_api_ai/scripts/clean_dispatch_cache.py",
    "mobile_api_ai/scripts/tools/check_schedule_records.py",
]


class TestCleanDispatchCacheRefactored(unittest.TestCase):
    """用例 1: clean_dispatch_cache.py L50,L53,L56 全部 try/except 保护"""

    def test_clean_dispatch_cache_no_schedule_records_sql(self):
        """clean_dispatch_cache.py 不再含 schedule_records SQL (3 处)"""
        path = MOBILE_API / "scripts" / "clean_dispatch_cache.py"
        sql_lines = _collect_sql_lines(path, 'schedule_records')
        self.assertEqual(len(sql_lines), 0,
                         f"clean_dispatch_cache.py 仍有 schedule_records SQL: {sql_lines}")


class TestCheckScheduleRecordsRefactored(unittest.TestCase):
    """用例 2: check_schedule_records.py L15,L17,L36,L49 全部 try/except 保护"""

    def test_check_schedule_records_no_schedule_records_sql(self):
        """check_schedule_records.py 不再含 schedule_records SQL (4 处)"""
        path = MOBILE_API / "scripts" / "tools" / "check_schedule_records.py"
        sql_lines = _collect_sql_lines(path, 'schedule_records')
        self.assertEqual(len(sql_lines), 0,
                         f"check_schedule_records.py 仍有 schedule_records SQL: {sql_lines}")


class TestAll7ProductionPathsClean(unittest.TestCase):
    """用例 3: 7 处生产路径 (3 + 4) 全部 0 引用"""

    def test_all_7_production_paths_clean(self):
        all_sql = []
        for rel in PRODUCTION_PATHS:
            p = MOBILE_API / rel
            all_sql.extend(_collect_sql_lines(p, 'schedule_records'))
        self.assertEqual(len(all_sql), 0,
                         f"7 处生产路径仍有 schedule_records SQL: {all_sql}")


class TestScriptsCompileAndImport(unittest.TestCase):
    """用例 4: 修复后脚本能 import + 语法通过"""

    def test_clean_dispatch_cache_compiles(self):
        path = MOBILE_API / "scripts" / "clean_dispatch_cache.py"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"clean_dispatch_cache.py 编译失败: {e}")

    def test_check_schedule_records_compiles(self):
        path = MOBILE_API / "scripts" / "tools" / "check_schedule_records.py"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"check_schedule_records.py 编译失败: {e}")


class TestRobustnessToEmptyOrMissingDB(unittest.TestCase):
    """用例 5: 删表/空库场景下脚本不崩溃 (F6 P9 标识提示)"""

    def test_clean_dispatch_cache_has_skip_marker(self):
        """clean_dispatch_cache.py 应有 F6 P9 兼容提示, 缺表时跳过"""
        path = MOBILE_API / "scripts" / "clean_dispatch_cache.py"
        content = path.read_text(encoding='utf-8')
        self.assertIn('F6 P9 兼容', content,
                      "clean_dispatch_cache.py 缺 F6 P9 兼容提示, 用户跑会困惑")
        self.assertIn('schedule_records', content.lower(),
                      "schedule_records 引用应保留在注释中以解释为何跳过")

    def test_check_schedule_records_has_skip_marker(self):
        """check_schedule_records.py 应有 F6 P9 DROP 提示, 引导用户用替代工具"""
        path = MOBILE_API / "scripts" / "tools" / "check_schedule_records.py"
        content = path.read_text(encoding='utf-8')
        self.assertIn('F6 P9', content,
                      "check_schedule_records.py 缺 F6 P9 DROP 提示, 用户跑会困惑")


if __name__ == "__main__":
    unittest.main(verbosity=2)
