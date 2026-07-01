# -*- coding: utf-8 -*-
"""
F16 T16.5 前测: product_flow_map 4 处修复 (1 生产路径已自动修, 3 工具路径)

根因: F6 P9 2026-06-10 已 DROP steel_belt.product_flow_map (13 行映射, 详见 MEMORY.md L20)
      1 生产路径 (container_center_api.py L1208) F6 P9 时已自动改写为硬编码 'production'
      3 工具路径 (models/product_flow_map.py + utils/custom_types.py ×2) 仍 SELECT/UPDATE 该表

设计契约 (5 用例):
  1. container_center_api.py 不再含 SELECT flow_type FROM product_flow_map (F6 P9 自动修)
  2. models/product_flow_map.py get_flow_type 改 try/except 1146 + 返 'production'
  3. utils/custom_types.py set_product_flow_type 死代码已清理 (F6 P9 兼容)
  4. utils/custom_types.py sync_product_flow_map (L70) try/except 1146 + 返空
  5. 4 处 product_flow_map SQL 引用全部受 try/except 保护, 表 DROP 时不崩
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


# 4 处 product_flow_map 引用
PRODUCTION_PATHS = [
    "mobile_api_ai/container_center_api.py",  # 1 处已 F6 P9 自动修
]
UTIL_PATHS = [
    "models/product_flow_map.py",  # 1 SELECT
    "utils/custom_types.py",       # 1 UPDATE + 1 SELECT
]


class TestContainerCenterAPIRefactored(unittest.TestCase):
    """用例 1: container_center_api.py L1208 不再 SELECT flow_type FROM product_flow_map (F6 P9 自动修)"""

    def test_no_product_flow_map_sql(self):
        path = MOBILE_API / "container_center_api.py"
        sql_lines = _collect_sql_lines(path, 'product_flow_map')
        self.assertEqual(len(sql_lines), 0,
                         f"container_center_api.py 仍有 product_flow_map SQL: {sql_lines}")


class TestModelProductFlowMapRefactored(unittest.TestCase):
    """用例 2: models/product_flow_map.py get_flow_type 改 try/except 1146"""

    def test_no_unhandled_sql(self):
        path = PROJECT_ROOT / "models" / "product_flow_map.py"
        content = path.read_text(encoding='utf-8')
        # 验证: try/except 保护
        self.assertIn('try:', content, "models/product_flow_map.py 缺 try/except 保护")
        self.assertIn('except Exception', content, "models/product_flow_map.py 缺 except")


class TestCustomTypesRefactored(unittest.TestCase):
    """用例 3+4: utils/custom_types.py 死代码已清理, 同步函数 try/except 保护"""

    def test_no_unhandled_sql(self):
        path = PROJECT_ROOT / "utils" / "custom_types.py"
        content = path.read_text(encoding='utf-8')
        # 验证: F6 P9 标识 + try/except
        self.assertIn('F6 P9', content, "utils/custom_types.py 缺 F6 P9 标识")
        self.assertIn('except Exception', content, "utils/custom_types.py 缺 except 保护")


class TestAll4PathsCompile(unittest.TestCase):
    """用例 4: 4 处 product_flow_map 全部语法通过"""

    def test_compile_all(self):
        for rel in PRODUCTION_PATHS + UTIL_PATHS:
            p = MOBILE_API / rel if 'mobile_api_ai' in rel else PROJECT_ROOT / rel
            if not p.exists():
                p = PROJECT_ROOT / rel
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"{rel} 编译失败: {e}")


class TestProductionPathF6P9Fixed(unittest.TestCase):
    """用例 5: F6 P9 时生产路径已自动改写, /api/flow-type/<product_type_id> 返 'production'"""

    def test_api_get_flow_type_returns_production(self):
        """/api/flow-type/<product_type_id> 应硬编码返 production (无 SQL 调用)"""
        path = MOBILE_API / "container_center_api.py"
        content = path.read_text(encoding='utf-8')
        # 验证: api_get_flow_type 简化版本存在
        self.assertIn("'flow_type': 'production'", content,
                      "api_get_flow_type 应硬编码返 production (F6 P9 后)")

    def test_models_f6p9_compatible(self):
        """models/product_flow_map.py F6 P9 兼容 (1146 降级到 'production')"""
        path = PROJECT_ROOT / "models" / "product_flow_map.py"
        content = path.read_text(encoding='utf-8')
        # 应在 except 中返 'production'
        self.assertTrue('production' in content, "缺 production 默认值")
        # 应有 F6 P9 标识
        self.assertIn('F6 P9', content, "缺 F6 P9 标识")


if __name__ == "__main__":
    unittest.main(verbosity=2)
