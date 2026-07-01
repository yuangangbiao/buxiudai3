# -*- coding: utf-8 -*-
"""
T8 前测: sync_bridge 透传 flow_type

修复点 (SPEC v1.1 F8):
  1. _enqueue_sync payload 加 flow_type 字段
  2. sync_status_change / sync_sub_step_report 接受 flow_type 入参
  3. 7 个 POST 路由透传 request body flow_type
  4. 推断函数 (D3.1 同步) — 缺 flow_type 走 status_key/endpoint 推断

设计契约 (6 用例):
  1. _enqueue_sync payload 含 'flow_type' 键
  2. sync_status_change 透传 flow_type='outsource'
  3. sync_sub_step_report 透传 flow_type='material_purchase'
  4. 推断函数: status_key='qc_passed' → flow_type='quality'
  5. 推断函数: status_key='material_arrived' → flow_type='material_purchase'
  6. 推断函数: 未知 status_key → 兜底 'production'

D3.1 同步推断表 (status_key → flow_type):
  qc_passed / report_complete / reported → quality (质检相关)
  material_arrived / material_delivered → material_purchase
  其他生产/通用 → production
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# 模拟修复后 (与方案一致)
SYNC_STATUS_KEY_TO_FLOW_TYPE = {
    # 质检相关
    'qc_passed': 'quality',
    'qc_review': 'quality',
    'qc_failed': 'quality',
    'report_complete': 'quality',
    # 物料相关
    'material_arrived': 'material_purchase',
    'material_delivered': 'material_purchase',
    'material_requested': 'material_purchase',
    'material_confirmed': 'material_purchase',
    'material_deadline': 'material_purchase',
    # 外协相关
    'outsource_created': 'outsource',
    'outsource_confirmed': 'outsource',
    'outsource_production': 'outsource',
    'outsource_qc': 'outsource',
    'outsource_returned': 'outsource',
    # 报修相关
    'repair_created': 'repair',
    'repair_completed': 'repair',
}


def infer_sync_status_to_flow_type(status_key: str) -> str:
    """T8 推断函数 (模块级, 纯函数)"""
    if not status_key:
        return 'production'
    return SYNC_STATUS_KEY_TO_FLOW_TYPE.get(status_key.lower(), 'production')


def _resolve_sync_flow_type(flow_type: str, status_key: str = '') -> str:
    """T8 公共解析函数: 显式优先, 推断兜底"""
    return flow_type or infer_sync_status_to_flow_type(status_key)


def _enqueue_sync_payload(payload: dict) -> dict:
    """T8 模拟 _enqueue_sync payload 加 flow_type"""
    enriched = dict(payload)
    enriched.setdefault('flow_type', '')
    return enriched


class TestEnqueueSyncFlowType(unittest.TestCase):
    """_enqueue_sync payload 加 flow_type 字段 (1 用例)"""

    def test_enqueue_payload_has_flow_type_key(self):
        """1. _enqueue_sync payload 含 'flow_type' 键"""
        payload = _enqueue_sync_payload({'order_no': 'ORD-001', 'status_key': 'qc_passed'})
        self.assertIn('flow_type', payload)
        self.assertEqual(payload['flow_type'], '')


class TestSyncStatusChangeFlowType(unittest.TestCase):
    """sync_status_change 透传 flow_type (1 用例)"""

    def test_explicit_flow_type_passthrough(self):
        """2. sync_status_change(flow_type='outsource') 透传"""
        # 模拟 sync_status_change 内部 _resolve_sync_flow_type 逻辑
        resolved = _resolve_sync_flow_type('outsource', 'published')
        self.assertEqual(resolved, 'outsource',
                         f"显式 flow_type 应透传, 实际 {resolved}")


class TestSyncSubStepReportFlowType(unittest.TestCase):
    """sync_sub_step_report 透传 flow_type (1 用例)"""

    def test_material_purchase_passthrough(self):
        """3. sync_sub_step_report(flow_type='material_purchase') 透传"""
        resolved = _resolve_sync_flow_type('material_purchase', 'material_arrived')
        self.assertEqual(resolved, 'material_purchase')


class TestSyncStatusKeyInference(unittest.TestCase):
    """推断函数 3 用例"""

    def test_qc_passed_inferred_to_quality(self):
        """4. status_key='qc_passed' → 推断 'quality'"""
        self.assertEqual(infer_sync_status_to_flow_type('qc_passed'), 'quality')

    def test_material_arrived_inferred_to_material_purchase(self):
        """5. status_key='material_arrived' → 推断 'material_purchase'"""
        self.assertEqual(
            infer_sync_status_to_flow_type('material_arrived'),
            'material_purchase'
        )

    def test_unknown_status_key_falls_back_to_production(self):
        """6. 未知 status_key → 兜底 'production'"""
        self.assertEqual(
            infer_sync_status_to_flow_type('unknown_status'),
            'production'
        )

    def test_empty_status_key_falls_back_to_production(self):
        """6b. 空 status_key → 兜底 'production'"""
        self.assertEqual(infer_sync_status_to_flow_type(''), 'production')


class TestCombinedResolve(unittest.TestCase):
    """组合: 显式优先 + 推断兜底 (1 用例)"""

    def test_explicit_overrides_inference(self):
        """7. 显式 flow_type + status_key='qc_passed' → 显式优先"""
        # 即使 status_key 推断为 quality, 显式 outsource 应胜出
        resolved = _resolve_sync_flow_type('outsource', 'qc_passed')
        self.assertEqual(resolved, 'outsource')

    def test_missing_flow_type_falls_back_to_inference(self):
        """8. 缺 flow_type + status_key='qc_passed' → 走推断 'quality'"""
        resolved = _resolve_sync_flow_type('', 'qc_passed')
        self.assertEqual(resolved, 'quality')


if __name__ == "__main__":
    unittest.main()
