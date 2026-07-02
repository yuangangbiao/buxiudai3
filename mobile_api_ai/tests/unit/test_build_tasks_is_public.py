# -*- coding: utf-8 -*-
"""
任务列表 is_public 字段补充 - 单元测试

覆盖范围 (边界矩阵):
- T-01: 全员任务 (is_public=1, target_operator='') → 输出 is_public=1
- T-02: 指派任务 (is_public=0, target_operator='张三') → 输出 is_public=0
- T-03: 兜底场景 (is_public 字段缺失) → 输出 is_public=0
- T-04: is_public 为字符串 '1'/'0' → 正确转换
- T-05: is_public 为 True/False → 正确转换
- T-06: is_public 为非法字符串 'abc' → 输出 is_public=0 (兜底)
- T-07: is_public 为 None → 输出 is_public=0 (兜底)
- T-08: 排序不变 - process_code 升序仍生效

实现策略:
- 直接从 legacy_routes.py 提取 _build_tasks_from_packages 源码
- 在隔离命名空间中 exec 出来（避免 api.legacy_routes 的重型 import 链拖垮测试）
- mock cc.storage.get_packages 返回受控的 packages 列表
- 用 sys.modules 注入 is_production_code 避免 process_code_classifier import
"""
import os
import re
import sys
from unittest.mock import MagicMock

import pytest


def _extract_function_source():
    """从 legacy_routes.py 中提取 _build_tasks_from_packages 函数源码"""
    api_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', 'api', 'legacy_routes.py'
    )
    api_path = os.path.abspath(api_path)
    with open(api_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # 定位 def _build_tasks_from_packages
    start_marker = 'def _build_tasks_from_packages('
    start_idx = source.find(start_marker)
    assert start_idx > 0, f"未找到 _build_tasks_from_packages 函数定义"

    # 找到下一个顶级 def (即函数体结束)
    next_def = source.find('\ndef ', start_idx + len(start_marker))
    end_idx = next_def if next_def > 0 else len(source)

    func_source = source[start_idx:end_idx].rstrip()
    return func_source


def _build_isolated_namespace():
    """构建最小隔离命名空间，注入依赖 stub"""
    import types

    ns = {
        '__builtins__': __builtins__,
        'json': __import__('json'),
    }

    # 注入 is_production_code stub (让所有 process_code 都通过)
    ns['is_production_code'] = lambda code: True
    return ns


@pytest.fixture(scope='module')
def build_fn():
    """加载 _build_tasks_from_packages 函数（一次性）"""
    func_source = _extract_function_source()
    ns = _build_isolated_namespace()
    # 去掉函数内的 mobile_api_ai. 前缀（隔离命名空间中没有 mobile_api_ai 包）
    func_source = func_source.replace(
        'from mobile_api_ai.core.process_code_classifier import is_production_code',
        '# is_production_code stubbed',
    )
    exec(func_source, ns)
    return ns['_build_tasks_from_packages']


def _build_cc(packages):
    """构造 cc mock，cc.storage.get_packages 返回 packages"""
    cc = MagicMock()
    cc.storage.get_packages.return_value = packages
    return cc


def _make_pkg(pid, target_operator, is_public, process_code='P1', content=None):
    """构造 process_sub_steps 字典"""
    return {
        'id': pid,
        'target_operator': target_operator,
        'is_public': is_public,
        'related_process': f'工序{pid}',
        'title': f'任务{pid}',
        'process_code': process_code,
        'completed_qty': 0,
        'status': 'pending',
        'created_at': '2026-06-16 10:00:00',
        'content': content or {},
    }


class TestBuildTasksIsPublic:
    """_build_tasks_from_packages 中 is_public 字段处理测试"""

    # ==================== T-01 ~ T-02 正常路径 ====================
    def test_t01_all_staff_task(self, build_fn):
        """全员任务 (is_public=1, operator='') → is_public=1"""
        cc = _build_cc([_make_pkg(1, target_operator='', is_public=1)])
        tasks = build_fn(cc, 'WO001', 100)
        assert len(tasks) == 1
        assert tasks[0]['is_public'] == 1
        assert tasks[0]['operator'] == '全员'

    def test_t02_assigned_task(self, build_fn):
        """指派任务 (is_public=0, operator='张三') → is_public=0"""
        cc = _build_cc([_make_pkg(2, target_operator='张三', is_public=0)])
        tasks = build_fn(cc, 'WO001', 100)
        assert len(tasks) == 1
        assert tasks[0]['is_public'] == 0
        assert tasks[0]['operator'] == '张三'

    # ==================== T-03 ~ T-07 边界场景 ====================
    def test_t03_field_missing_defaults_to_zero(self, build_fn):
        """is_public 字段缺失 → is_public=0 (按指派任务处理)"""
        pkg = _make_pkg(3, target_operator='李四', is_public=0)
        pkg.pop('is_public')
        cc = _build_cc([pkg])
        tasks = build_fn(cc, 'WO001', 100)
        assert tasks[0]['is_public'] == 0

    def test_t04_string_one_zero(self, build_fn):
        """is_public 为字符串 '1'/'0' → 正确转 int"""
        cc = _build_cc([
            _make_pkg(4, target_operator='', is_public='1'),
            _make_pkg(5, target_operator='王五', is_public='0'),
        ])
        tasks = build_fn(cc, 'WO001', 100)
        ops = {t['operator']: t['is_public'] for t in tasks}
        assert ops['全员'] == 1
        assert ops['王五'] == 0

    def test_t05_boolean_values(self, build_fn):
        """is_public 为 True/False → 正确转 1/0"""
        cc = _build_cc([
            _make_pkg(6, target_operator='', is_public=True),
            _make_pkg(7, target_operator='赵六', is_public=False),
        ])
        tasks = build_fn(cc, 'WO001', 100)
        ops = {t['operator']: t['is_public'] for t in tasks}
        assert ops['全员'] == 1
        assert ops['赵六'] == 0

    def test_t06_invalid_string_defaults_to_zero(self, build_fn):
        """is_public 为非法字符串 'abc' → 兜底 0"""
        cc = _build_cc([_make_pkg(8, target_operator='钱七', is_public='abc')])
        tasks = build_fn(cc, 'WO001', 100)
        assert tasks[0]['is_public'] == 0
        assert tasks[0]['operator'] == '钱七'

    def test_t07_none_defaults_to_zero(self, build_fn):
        """is_public 为 None → 兜底 0"""
        cc = _build_cc([_make_pkg(9, target_operator='孙八', is_public=None)])
        tasks = build_fn(cc, 'WO001', 100)
        assert tasks[0]['is_public'] == 0

    # ==================== T-08 排序保持 ====================
    def test_t08_sort_preserved(self, build_fn):
        """process_code 升序排序仍生效 (P1 < P2 < P10)"""
        cc = _build_cc([
            _make_pkg(10, target_operator='', is_public=1, process_code='P10'),
            _make_pkg(11, target_operator='周九', is_public=0, process_code='P2'),
            _make_pkg(12, target_operator='吴十', is_public=0, process_code='P1'),
        ])
        tasks = build_fn(cc, 'WO001', 100)
        codes = [t['process_code'] for t in tasks]
        assert codes == ['P1', 'P2', 'P10']

    # ==================== 混合场景 ====================
    def test_mixed_tasks_all_have_is_public(self, build_fn):
        """混合 (全员 + 指派) 任务列表，所有 task 都带 is_public 字段"""
        cc = _build_cc([
            _make_pkg(20, target_operator='', is_public=1),
            _make_pkg(21, target_operator='冯十一', is_public=0),
        ])
        tasks = build_fn(cc, 'WO001', 100)
        assert len(tasks) == 2
        for t in tasks:
            assert 'is_public' in t
            assert isinstance(t['is_public'], int)
            assert t['is_public'] in (0, 1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])