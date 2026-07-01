# -*- coding: utf-8 -*-
"""
F16 T16.3 前测: enterprise_structure 6 处 (3 生产路径 + 3 storage 工具) 修复

根因: F6 P9 2026-06-10 已 DROP container_center.enterprise_structure (MySQL)
      + steel_belt.enterprise_structure (MySQL)
      (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
      仍有 6 处 SQL 引用 enterprise_structure, 触发 MySQL 1146 WARNING

设计契约 (5 用例):
  1. container_center_api.py L2688 不再 SELECT FROM enterprise_structure
  2. container_center_v5.py L1401 不再 SELECT FROM enterprise_structure
  3. scripts/tools/check_db.py 不再 SELECT FROM enterprise_structure
  4. storage/mysql_storage.py L369+L536+L553 不再 SELECT FROM enterprise_structure
  5. 替代数据源 data/enterprise_structure.json 存在且格式正确
"""
import sys
import unittest
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MOBILE_API = PROJECT_ROOT / "mobile_api_ai"


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


# 6 处 enterprise_structure 引用
PRODUCTION_PATHS = [
    "mobile_api_ai/container_center_api.py",
    "mobile_api_ai/container_center_v5.py",
    "mobile_api_ai/scripts/tools/check_db.py",
]
STORAGE_PATHS = [
    "mobile_api_ai/storage/mysql_storage.py",
]


class TestContainerCenterAPIRefactored(unittest.TestCase):
    """用例 1: container_center_api.py L2688 不再 SELECT FROM enterprise_structure"""

    def test_no_enterprise_structure_sql(self):
        path = MOBILE_API / "container_center_api.py"
        sql_lines = _collect_sql_lines(path, 'enterprise_structure')
        self.assertEqual(len(sql_lines), 0,
                         f"container_center_api.py 仍有 enterprise_structure SQL: {sql_lines}")


class TestContainerCenterV5Refactored(unittest.TestCase):
    """用例 2: container_center_v5.py L1401 不再 SELECT FROM enterprise_structure"""

    def test_no_enterprise_structure_sql(self):
        path = MOBILE_API / "container_center_v5.py"
        sql_lines = _collect_sql_lines(path, 'enterprise_structure')
        self.assertEqual(len(sql_lines), 0,
                         f"container_center_v5.py 仍有 enterprise_structure SQL: {sql_lines}")


class TestCheckDBRefactored(unittest.TestCase):
    """用例 3: scripts/tools/check_db.py 不再 SELECT FROM enterprise_structure"""

    def test_no_enterprise_structure_sql(self):
        path = MOBILE_API / "scripts" / "tools" / "check_db.py"
        sql_lines = _collect_sql_lines(path, 'enterprise_structure')
        self.assertEqual(len(sql_lines), 0,
                         f"check_db.py 仍有 enterprise_structure SQL: {sql_lines}")


class TestStorageLayerRefactored(unittest.TestCase):
    """用例 4: storage/mysql_storage.py L369+L536+L553 不再 SELECT FROM enterprise_structure"""

    def test_no_enterprise_structure_sql(self):
        path = MOBILE_API / "storage" / "mysql_storage.py"
        sql_lines = _collect_sql_lines(path, 'enterprise_structure')
        self.assertEqual(len(sql_lines), 0,
                         f"mysql_storage.py 仍有 enterprise_structure SQL: {sql_lines}")


class TestAlternativeDataSource(unittest.TestCase):
    """用例 5: 替代数据源 data/enterprise_structure.json 存在且格式正确"""

    def test_json_file_exists(self):
        path = PROJECT_ROOT / "data" / "enterprise_structure.json"
        self.assertTrue(path.exists(),
                        f"替代数据源 {path} 不存在")

    def test_json_format_valid(self):
        path = PROJECT_ROOT / "data" / "enterprise_structure.json"
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            self.fail(f"JSON 格式错误: {e}")
        # 必需字段
        self.assertIn('departments', data, "缺 departments 字段")
        self.assertIn('users', data, "缺 users 字段")
        self.assertIsInstance(data['departments'], list, "departments 应为 list")
        self.assertIsInstance(data['users'], list, "users 应为 list")


if __name__ == "__main__":
    unittest.main(verbosity=2)
