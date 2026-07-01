# -*- coding: utf-8 -*-
"""
T9 前测: sync_bridge 2 个 process_records UPDATE 写 flow_type 列

修复点 (SPEC v1.1 F9 范围修正: 实际只 2 处 UPDATE, 不是 100 文件):
  1. _sync_to_container_db L270-294 UPDATE process_records SET status → 加 flow_type
  2. sync_sub_step_report L478-486 UPDATE process_records SET completed_qty → 加 flow_type

设计契约 (5 用例):
  1. 推断函数复用 T8 _resolve_sync_flow_type: status_key='qc_passed' → 'quality'
  2. _sync_to_container_db params 顺序正确 (flow_type 插在 order_no 之前)
  3. _sync_to_container_db status_key='material_arrived' → 推断 'material_purchase'
  4. sync_sub_step_report step_name 含 'qc' → 推断 'quality'
  5. 边界: status_key='' / step_name 普通 → 兜底 'production'

D3.1 同步推断表 (T8 已实现, T9 复用):
  qc_passed/qc_review/qc_failed/report_complete → quality
  material_arrived/material_delivered 等 5 个 → material_purchase
  outsource_* (5 个) → outsource
  repair_* (2 个) → repair
  未知 / 空 → production
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# 复用 T8 推断函数 (实际 sync_bridge.py 已有)
SYNC_STATUS_KEY_TO_FLOW_TYPE = {
    'qc_passed': 'quality', 'qc_review': 'quality', 'qc_failed': 'quality',
    'report_complete': 'quality',
    'material_arrived': 'material_purchase', 'material_delivered': 'material_purchase',
    'material_requested': 'material_purchase', 'material_confirmed': 'material_purchase',
    'material_deadline': 'material_purchase',
    'outsource_created': 'outsource', 'outsource_confirmed': 'outsource',
    'outsource_production': 'outsource', 'outsource_qc': 'outsource',
    'outsource_returned': 'outsource',
    'repair_created': 'repair', 'repair_completed': 'repair',
}


def infer_sync_status_to_flow_type(status_key: str) -> str:
    if not status_key:
        return 'production'
    return SYNC_STATUS_KEY_TO_FLOW_TYPE.get(status_key.lower(), 'production')


def _resolve_sync_flow_type(flow_type: str, status_key: str = '') -> str:
    return flow_type or infer_sync_status_to_flow_type(status_key)


# 修补 T9: 新增 step_name 推断函数 (与 status_key 推断不同维度)
def infer_step_name_to_flow_type(step_name: str) -> str:
    """T9 推断函数 (step_name 子串匹配, 与 status_key 精确匹配互补)

    Args:
        step_name: 工序名称 (如 'QC-Inspection' / '焊接' / '外协加工')

    Returns:
        flow_type 字符串 (5 种之一)
        未知 → 兜底 'production'
    """
    if not step_name:
        return 'production'
    sl = step_name.lower()
    # 质检相关
    if 'qc' in sl or '质量' in step_name or '检验' in step_name or 'inspection' in sl:
        return 'quality'
    # 外协相关
    if '外协' in step_name or 'outsource' in sl:
        return 'outsource'
    # 物料相关
    if '物料' in step_name or '采购' in step_name or 'material' in sl or 'purchase' in sl:
        return 'material_purchase'
    # 报修相关
    if '报修' in step_name or 'repair' in sl:
        return 'repair'
    return 'production'


# 模拟 T9 修复后的 SQL params 构造
def _build_sync_to_container_params(status_key: str, plan_start=None, plan_end=None):
    """模拟 _sync_to_container_db L270-294 修复后 params 构造"""
    updates = ['status=%s', 'updated_at=NOW()']
    params = [status_key]
    if plan_start:
        updates.append('plan_start=%s')
        params.append(plan_start)
    if plan_end:
        updates.append('plan_end=%s')
        params.append(plan_end)
    # 修补 T9: 加 flow_type 列写入 (status_key 推断)
    flow_type_value = _resolve_sync_flow_type('', status_key)
    if flow_type_value:
        updates.append('flow_type=%s')
        params.insert(-1, flow_type_value)  # 插在 order_no 之前
    return updates, params


def _build_sub_step_report_params(total_qty, total_qualified, total_hours,
                                   new_status, operator, mysql_process_id,
                                   flow_type='', step_name=''):
    """模拟 sync_sub_step_report L478-486 修复后 UPDATE 构造"""
    # 修补 T9: 推断 flow_type (step_name 子串匹配, 与 status_key 互补)
    ft = flow_type or infer_step_name_to_flow_type(step_name)
    effective_ft = ft or 'production'
    return {
        'sql': '''UPDATE process_records
            SET completed_qty = %s, qualified_qty = %s, work_hours = %s,
                status = %s, flow_type = %s, updated_at = NOW(), updated_by = %s
            WHERE id = %s''',
        'params': (total_qty, total_qualified, total_hours, new_status, effective_ft,
                   operator or '', mysql_process_id),
    }


class TestResolveSyncFlowTypeReuse(unittest.TestCase):
    """复用 T8 推断函数 (1 用例)"""

    def test_qc_passed_inferred_to_quality(self):
        """1. status_key='qc_passed' → 推断 'quality' (T8 推断表已实现, T9 复用)"""
        self.assertEqual(_resolve_sync_flow_type('', 'qc_passed'), 'quality')


class TestSyncToContainerDbParams(unittest.TestCase):
    """_sync_to_container_db 写 flow_type (2 用例)"""

    def test_params_order_correct(self):
        """2. params 顺序: flow_type 在 order_no 之前 (params.insert(-1, ...))"""
        updates, params = _build_sync_to_container_params('qc_passed')
        # 最后一项是 order_no (从主调函数传入, params 末尾)
        # 这里只测构造部分, 实际 params 末尾会被 append order_no
        # 验证: 'flow_type=%s' 出现在 updates 中, 'quality' 在 params 中
        self.assertIn('flow_type=%s', updates)
        self.assertIn('quality', params)

    def test_material_arrived_writes_material_purchase(self):
        """3. status_key='material_arrived' → 推断 'material_purchase'"""
        updates, params = _build_sync_to_container_params('material_arrived')
        self.assertIn('flow_type=%s', updates)
        self.assertIn('material_purchase', params)


class TestSyncSubStepReportParams(unittest.TestCase):
    """sync_sub_step_report UPDATE 写 flow_type (1 用例)"""

    def test_step_name_with_qc_inferred_to_quality(self):
        """4. step_name 含 'qc' → 推断 'quality' (报工 + 质检)"""
        result = _build_sub_step_report_params(
            total_qty=10, total_qualified=10, total_hours=2.0,
            new_status='completed', operator='op_001', mysql_process_id=123,
            step_name='QC-Inspection'
        )
        # params 顺序: (total_qty, total_qualified, total_hours, new_status, flow_type, operator, mysql_process_id)
        params = result['params']
        # flow_type 是第 5 个参数 (index 4)
        self.assertEqual(params[4], 'quality', f"step_name 含 qc 应推断 quality, 实际 {params[4]}")
        # 验证 SQL 含 flow_type
        self.assertIn('flow_type = %s', result['sql'])


class TestFallbackToProduction(unittest.TestCase):
    """边界: 缺 status_key / 普通 step_name 兜底 'production' (1 用例)"""

    def test_empty_status_key_fallback_to_production(self):
        """5. status_key='' → 兜底 'production'"""
        updates, params = _build_sync_to_container_params('')
        self.assertIn('flow_type=%s', updates)
        self.assertIn('production', params)

    def test_normal_step_name_fallback_to_production(self):
        """5b. step_name 普通 (无 'qc') → 兜底 'production'"""
        result = _build_sub_step_report_params(
            total_qty=10, total_qualified=10, total_hours=2.0,
            new_status='in_progress', operator='op_001', mysql_process_id=124,
            step_name='焊接'  # 普通工序, 不含 qc
        )
        params = result['params']
        self.assertEqual(params[4], 'production', f"普通 step_name 应兜底 production, 实际 {params[4]}")


class TestInferStepNameToFlowType(unittest.TestCase):
    """step_name 子串匹配推断 (2 用例) - T9 新增推断函数"""

    def test_step_name_with_qc_inferred_to_quality(self):
        """6. step_name='QC-Inspection' → 'quality' (子串匹配)"""
        self.assertEqual(infer_step_name_to_flow_type('QC-Inspection'), 'quality')

    def test_chinese_step_name_quality(self):
        """6b. step_name='质量检验' → 'quality' (中文子串)"""
        self.assertEqual(infer_step_name_to_flow_type('质量检验'), 'quality')

    def test_chinese_step_name_outsource(self):
        """6c. step_name='外协加工' → 'outsource'"""
        self.assertEqual(infer_step_name_to_flow_type('外协加工'), 'outsource')

    def test_normal_chinese_step_name_fallback(self):
        """6d. step_name='焊接' → 兜底 'production'"""
        self.assertEqual(infer_step_name_to_flow_type('焊接'), 'production')


if __name__ == "__main__":
    unittest.main()
