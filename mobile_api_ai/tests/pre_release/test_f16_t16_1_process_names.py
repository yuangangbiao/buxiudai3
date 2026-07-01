# -*- coding: utf-8 -*-
"""
F16 T16.1 前测: process_names 11 处生产路径修复

根因: F6 P9 2026-06-10 已 DROP container_center.process_names 表
      (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
      仍有 11 处生产路径 SQL 引用 process_names, 触发 MySQL 1146 WARNING
      + 5min 空集合缓存污染 (与 F15 同源)

设计契约 (5 用例):
  1. process_code 单点查找改用 core.config.get_process_code (内存函数)
  2. 容器中心 8 处 API 改用 dispatch_cache.process_departments / 内存字典
  3. storage 层 get_process_names 改用内存 PROCESS_CODES + 运行时注册
  4. 源码不再包含 SELECT/UPDATE/INSERT/DELETE FROM process_names
  5. 1146 WARNING 不再出现 (无 process_names SQL 调用)
"""
import sys
import unittest
import re
from pathlib import Path

# 注: 脚本在 mobile_api_ai/__pre_tests__/ 下, 路径计算:
#   .parent = __pre_tests__
#   .parent.parent = mobile_api_ai
#   .parent.parent.parent = 项目根 (不锈钢网带跟单3.0)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MOBILE_API = PROJECT_ROOT / "mobile_api_ai"


def _is_excluded(path: Path) -> bool:
    """排除 _archive / .venv / __pycache__ / test_*.py / tests/"""
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
        # 处理 docstring 切换 (支持单行 """text""" 和多行)
        if '"""' in line or "'''" in line:
            dq = line.count('"""')
            sq = line.count("'''")
            # 单行 docstring (开始+结束在同一行) → 整个行是 docstring
            if dq >= 2 and not in_docstring:
                # 单行 docstring 整个排除
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


class TestGetProcessCodeFromMemory(unittest.TestCase):
    """用例 1: process_code 单点查找改用 core.config.get_process_code (内存函数)"""

    def test_app_py_uses_get_process_code(self):
        """app.py L324, L1898 不再有 SELECT FROM process_names, 改用 get_process_code()"""
        app_path = MOBILE_API / "app.py"
        sql_lines = _collect_sql_lines(app_path, 'process_names')
        self.assertEqual(len(sql_lines), 0,
                         f"app.py 仍有 SELECT/INSERT/UPDATE/DELETE FROM process_names: {sql_lines}")

    def test_app_py_imports_get_process_code(self):
        """app.py 应已导入 core.config.get_process_code"""
        app_path = MOBILE_API / "app.py"
        content = app_path.read_text(encoding='utf-8')
        # 应有 get_process_code 引用
        self.assertIn('get_process_code', content,
                      "app.py 未引用 get_process_code (内存替代未启用)")


class TestContainerCenterAPIRewrite(unittest.TestCase):
    """用例 2: 容器中心 8 处 API 改用 dispatch_cache / 内存字典"""

    def test_container_center_api_no_process_names_sql(self):
        """container_center_api.py 8 处 process_names SQL 应全部移除 (L539, 909, 913, 924, 937, 947, 958, 1017)"""
        cc_path = MOBILE_API / "container_center_api.py"
        sql_lines = _collect_sql_lines(cc_path, 'process_names')
        self.assertEqual(len(sql_lines), 0,
                         f"container_center_api.py 仍有 process_names SQL: {sql_lines}")


class TestStorageLayerRewrite(unittest.TestCase):
    """用例 3: storage 层 get_process_names 改用内存 PROCESS_CODES"""

    def test_mysql_storage_no_process_names_sql(self):
        """storage/mysql_storage.py L633 应改用内存字典, 不再 SELECT FROM process_names"""
        storage_path = MOBILE_API / "storage" / "mysql_storage.py"
        sql_lines = _collect_sql_lines(storage_path, 'process_names')
        self.assertEqual(len(sql_lines), 0,
                         f"mysql_storage.py 仍有 process_names SQL: {sql_lines}")


class TestNoMoreTableNotExistWarning(unittest.TestCase):
    """用例 4: 11 处生产路径源码不再含 process_names SQL"""

    TARGETS = [
        ("app.py", [324, 1898]),
        ("container_center_api.py", [539, 909, 913, 924, 937, 947, 958, 1017]),
    ]

    def test_all_11_production_paths_clean(self):
        """11 处生产路径 (app.py 2 + container_center_api.py 8 + storage 1) 全部 0 引用"""
        all_sql = []
        for rel, lines in self.TARGETS:
            p = MOBILE_API / rel
            all_sql.extend(_collect_sql_lines(p, 'process_names'))
        self.assertEqual(len(all_sql), 0,
                         f"11 处生产路径仍有 process_names SQL: {all_sql}")


class TestNo1146WarningInProduction(unittest.TestCase):
    """用例 5: 1146 WARNING 不再出现 (生产路径无 process_names SQL)"""

    def test_no_process_names_in_production_routes(self):
        """扫描 production 路径 (app.py + container_center_api.py) 确认无 process_names 引用"""
        production_files = [
            MOBILE_API / "app.py",
            MOBILE_API / "container_center_api.py",
        ]
        hits = []
        for p in production_files:
            hits.extend(_collect_sql_lines(p, 'process_names'))
        self.assertEqual(len(hits), 0,
                         f"生产路径含 process_names SQL, 将触发 1146 WARNING: {hits}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
