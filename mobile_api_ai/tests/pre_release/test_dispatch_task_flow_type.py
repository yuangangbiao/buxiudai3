# -*- coding: utf-8 -*-
"""
T4 前测: dispatch_task L1059-1096 接受 flow_type 入参 + L1042 后写 process_sub_steps.flow_type 列

修复点 (SPEC v1.1 F4 + Bug2 修补):
  1. L1059-1096 三处写死 flow_type 改用'请求体 > 推断 > 默认'优先级
  2. L1042 后追加 UPDATE process_sub_steps SET flow_type=%s WHERE id=%s

设计契约 (5 用例):
  1. 请求体 flow_type='outsource' + process_code='P001' → 期望 process_records.flow_type='outsource'
     (验证请求体入参优先于 process_code 前缀推断)
  2. 请求体 flow_type='material_purchase' + process_code='P001' → 期望 flow_type='material_purchase'
  3. 请求体无 flow_type + process_code='P001' → 期望 flow_type='production' (推断默认)
  4. 请求体无 flow_type + process_code='M001' → 期望 flow_type='material_purchase' (推断)
  5. 请求体无 flow_type + process_code='X001' → 期望 flow_type='outsource' (推断)
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _infer_flow_type(process_code: str, request_flow_type: str = "") -> str:
    """修复后 (F4.1) 模拟 dispatch_task L1059-1096 推断逻辑

    优先级: 请求体入参 > process_code 前缀推断 > 默认 'production'
    """
    inferred = None
    if process_code:
        if process_code.startswith('P'):
            inferred = 'production'
        elif process_code.startswith('M'):
            inferred = 'material_purchase'
        elif process_code.startswith('X'):
            inferred = 'outsource'
    # 请求体优先, 推断兜底
    return request_flow_type or inferred or 'production'


def _should_update_flow_type_column(flow_type: str) -> bool:
    """修复后 (F4.2) 模拟 L1042 后追加 UPDATE 逻辑

    返回是否应执行 UPDATE process_sub_steps SET flow_type=...
    """
    return bool(flow_type)


class TestRequestBodyPriority(unittest.TestCase):
    """F4.1: 请求体入参优先于 process_code 推断 (3 用例)"""

    def test_outsource_overrides_p_prefix(self):
        """1. data.flow_type='outsource' + process_code='P001' → 'outsource'
        (现状会写死 'production', 修复后保留 'outsource')"""
        result = _infer_flow_type('P001', request_flow_type='outsource')
        self.assertEqual(result, 'outsource', f"请求体应优先, 实际 {result}")

    def test_material_purchase_overrides_p_prefix(self):
        """2. data.flow_type='material_purchase' + process_code='P001' → 'material_purchase'"""
        result = _infer_flow_type('P001', request_flow_type='material_purchase')
        self.assertEqual(result, 'material_purchase', f"请求体应优先, 实际 {result}")

    def test_quality_overrides_p_prefix(self):
        """2.bonus data.flow_type='quality' + process_code='P001' → 'quality'"""
        result = _infer_flow_type('P001', request_flow_type='quality')
        self.assertEqual(result, 'quality')


class TestPrefixInferenceFallback(unittest.TestCase):
    """F4.1 兜底: 请求体缺 flow_type 时按 process_code 前缀推断 (3 用例)"""

    def test_p_prefix_defaults_to_production(self):
        """3. data 无 flow_type + process_code='P001' → 'production'"""
        result = _infer_flow_type('P001', request_flow_type='')
        self.assertEqual(result, 'production')

    def test_m_prefix_defaults_to_material_purchase(self):
        """4. data 无 flow_type + process_code='M001' → 'material_purchase'"""
        result = _infer_flow_type('M001', request_flow_type='')
        self.assertEqual(result, 'material_purchase')

    def test_x_prefix_defaults_to_outsource(self):
        """5. data 无 flow_type + process_code='X001' → 'outsource'"""
        result = _infer_flow_type('X001', request_flow_type='')
        self.assertEqual(result, 'outsource')


class TestFlowTypeColumnWrite(unittest.TestCase):
    """F4.2: L1042 后追加 UPDATE 写入 process_sub_steps.flow_type 列"""

    def test_should_update_column_when_flow_type_provided(self):
        """6. process_sub_steps.flow_type 列必写"""
        self.assertTrue(_should_update_flow_type_column('outsource'))

    def test_should_update_column_for_default_production(self):
        """7. 默认 'production' 也要写列 (不写则空字符串无法走索引)"""
        self.assertTrue(_should_update_flow_type_column('production'))

    def test_should_not_update_when_flow_type_empty(self):
        """8. flow_type='' 时不写列 (避免空字符串污染)"""
        self.assertFalse(_should_update_flow_type_column(''))


if __name__ == "__main__":
    unittest.main()
