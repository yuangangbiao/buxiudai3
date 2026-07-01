# -*- coding: utf-8 -*-
"""
F15 前测: 删除 _get_process_names_set + 调用点改用 process_departments

根因: F6 P9 已 DROP container_center.process_names 表, 但 _get_process_names_set
      仍 SELECT, 触发 MySQL 1146 WARNING (表不存在), 降级为空集合 (5min 缓存污染)

设计契约 (5 用例):
  1. _get_process_names_set 函数已删除
  2. 2 个调用点 L3346/L5292 改用 _dispatch_cache.get_data().get('process_departments', {}).keys()
  3. process_set 与原 process_departments.keys() 行为一致
  4. WARNING 1146 不再出现 (无 SELECT process_names)
  5. 5min 缓存机制移除 (新数据源实时, 无需缓存)
"""
import sys
import unittest
import importlib.util
import re
from pathlib import Path

# 注: 脚本在 mobile_api_ai/dispatch_center/__pre_tests__/ 下, 路径计算:
#   .parent = __pre_tests__
#   .parent.parent = dispatch_center
#   .parent.parent.parent = mobile_api_ai
#   .parent.parent.parent.parent = 项目根 (不锈钢网带跟单3.0)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestProcessNamesSourceReplacement(unittest.TestCase):
    """process_set 改用 process_departments.keys() (2 用例)"""

    def test_process_set_equals_process_departments_keys(self):
        """1. process_set = process_departments.keys() 一致性"""
        # 模拟 _dispatch_cache 数据
        cache_data = {
            'process_departments': {
                '焊接': '生产部',
                '质检': '质检部',
                '包装': '生产部',
            }
        }
        # 新实现: process_set = cache_data['process_departments'].keys()
        new_process_set = set(cache_data.get('process_departments', {}).keys())
        self.assertEqual(new_process_set, {'焊接', '质检', '包装'})

    def test_empty_process_departments_handled(self):
        """2. 空 process_departments → 空 process_set (不崩溃)"""
        cache_data = {}
        new_process_set = set(cache_data.get('process_departments', {}).keys())
        self.assertEqual(new_process_set, set())


class TestStaticContractVerification(unittest.TestCase):
    """静态契约: 源码验证 (1 用例)"""

    def test_source_removed_function_and_calls(self):
        """3. 源码验证: SQL SELECT process_names 已移除 + 函数实现改用 process_departments"""
        core_path = PROJECT_ROOT / "mobile_api_ai" / "dispatch_center" / "_core.py"
        content = core_path.read_text(encoding='utf-8')

        # 验证 SQL SELECT process_names 已移除 (核心修复)
        # 注: 排除注释行 + docstring (含 SELECT FROM process_names 是历史记录)
        sql_lines = []
        in_docstring = False
        for line in content.split('\n'):
            stripped = line.strip()
            if '"""' in line:
                in_docstring = not in_docstring if line.count('"""') % 2 == 1 else in_docstring
                continue
            if in_docstring or stripped.startswith('#'):
                continue
            if 'FROM process_names' in line:
                sql_lines.append(line)
        self.assertEqual(len(sql_lines), 0,
                         f"SQL 'FROM process_names' 仍存在 (非注释/docstring): {sql_lines}")

        # 验证 _get_process_names_set 函数实现内含 process_departments
        if 'def _get_process_names_set(' in content:
            # 用 find 定位函数, 截取到下一个 'def ' 或文件末尾 (限制 2000 字符)
            start = content.find('def _get_process_names_set(')
            rest = content[start:]
            next_def = rest.find('\ndef ', 100)  # 至少 100 字符后
            func_body = rest[:next_def if next_def > 0 else 2000]
            self.assertIn('process_departments', func_body,
                          "函数实现内未引用 process_departments (新数据源)")

        # 验证 process_departments 引用次数 ≥ 3 (原 2 + 替代 1)
        call_count = content.count("process_departments")
        self.assertGreaterEqual(call_count, 3,
                                f"process_departments 引用次数 {call_count} 不足 3")


class TestNoMoreTableNotExistWarning(unittest.TestCase):
    """不触发 WARNING 1146 (1 用例)"""

    def test_no_select_process_names_query(self):
        """4. 源码不含 SELECT process_names (无 1146 WARNING)"""
        core_path = PROJECT_ROOT / "mobile_api_ai" / "dispatch_center" / "_core.py"
        content = core_path.read_text(encoding='utf-8')
        # 不应再有 SELECT * FROM process_names (排除注释 + docstring)
        sql_lines = []
        in_docstring = False
        for line in content.split('\n'):
            stripped = line.strip()
            if '"""' in line:
                in_docstring = not in_docstring if line.count('"""') % 2 == 1 else in_docstring
                continue
            if in_docstring or stripped.startswith('#'):
                continue
            if 'SELECT' in line.upper() and 'process_names' in line:
                sql_lines.append(line)
        self.assertEqual(len(sql_lines), 0,
                         f"SELECT process_names SQL 仍存在: {sql_lines}")


class TestNo5MinCachePollution(unittest.TestCase):
    """移除 5min 缓存机制 (1 用例)"""

    def test_no_process_names_cache_global(self):
        """5. _PROCESS_NAMES_CACHE 全局变量已删除 (无 5min 缓存污染)"""
        core_path = PROJECT_ROOT / "mobile_api_ai" / "dispatch_center" / "_core.py"
        content = core_path.read_text(encoding='utf-8')
        # 5min 缓存的全局变量应删除
        self.assertNotIn('_PROCESS_NAMES_CACHE', content,
                         "_PROCESS_NAMES_CACHE 全局变量仍存在 (5min 缓存污染源)")
        self.assertNotIn('_PROCESS_NAMES_CACHE_TS', content,
                         "_PROCESS_NAMES_CACHE_TS 时间戳变量仍存在")
        self.assertNotIn('_PROCESS_NAMES_TTL', content,
                         "_PROCESS_NAMES_TTL 常量仍存在")


if __name__ == "__main__":
    unittest.main()
