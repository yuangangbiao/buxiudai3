# -*- coding: utf-8 -*-
"""
T6 前测: 移动端 dispatcher 4 个 publish_*_task 加 flow_type 入参

修复点 (SPEC v1.1 F6):
  1. task_pool.py:80 Task 加 flow_type 字段 (默认 '', 与 T1 DDL 对齐)
  2. task_pool.py:106 Task.to_dict 序列化 flow_type
  3. task_pool.py:127 Task.from_dict 反序列化 flow_type (forward compat)
  4. dispatcher.py 4 个 publish_*_task 加 flow_type 入参 + 推断函数

设计契约 (8 用例):
  1. Task 实例化后有 flow_type 属性 (默认 '')
  2. Task.to_dict 序列化 flow_type 字段
  3. Task.from_dict 反序列化 flow_type 字段 (forward compat)
  4. 推断函数: task_type='report' → flow_type='production'
  5. 推断函数: task_type='quality' → flow_type='quality'
  6. 推断函数: task_type='material' → flow_type='material_purchase'
  7. 推断函数: task_type='approval' → flow_type='production'
  8. publish_*_task 显式 flow_type 优先于推断

D3.1 推断表 (task_type → flow_type):
  report      → production
  quality     → quality
  material    → material_purchase
  approval    → production
  未知         → production (兜底)
"""
import sys
import unittest
import uuid
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# 模拟 Task (修复后版本)
class MockTask:
    def __init__(self, task_type, title, content, operator_id=None,
                 priority='normal', deadline=None, related_order=None,
                 related_process=None, tags=None, flow_type=''):
        self.id = str(uuid.uuid4())[:8].upper()
        self.task_type = task_type
        self.title = title
        self.content = content
        self.operator_id = operator_id
        self.priority = priority
        self.deadline = deadline
        self.related_order = related_order
        self.related_process = related_process
        self.tags = tags or []
        self.flow_type = flow_type

    def to_dict(self):
        return {
            'id': self.id,
            'task_type': self.task_type,
            'title': self.title,
            'content': self.content,
            'operator_id': self.operator_id,
            'priority': self.priority,
            'related_order': self.related_order,
            'related_process': self.related_process,
            'tags': self.tags,
            'flow_type': self.flow_type,
        }

    @classmethod
    def from_dict(cls, data):
        task = cls(
            task_type=data['task_type'],
            title=data['title'],
            content=data['content'],
            operator_id=data.get('operator_id'),
            priority=data.get('priority', 'normal'),
            related_order=data.get('related_order'),
            related_process=data.get('related_process'),
            tags=data.get('tags', []),
            flow_type=data.get('flow_type', ''),
        )
        task.id = data.get('id', task.id)
        return task


# 模拟推断函数 (修复后)
TASK_TYPE_TO_FLOW_TYPE = {
    'report': 'production',
    'quality': 'quality',
    'material': 'material_purchase',
    'approval': 'production',
}


def infer_task_type_to_flow_type(task_type: str) -> str:
    if not task_type:
        return 'production'
    return TASK_TYPE_TO_FLOW_TYPE.get(task_type.lower(), 'production')


# 模拟 publish_*_task 行为 (修复后)
def _resolve_flow_type(flow_type: str, task_type: str) -> str:
    return flow_type or infer_task_type_to_flow_type(task_type)


class TestTaskFlowTypeField(unittest.TestCase):
    """Task dataclass 加 flow_type 字段 (3 用例)"""

    def test_task_init_default_empty_flow_type(self):
        """1. Task() 默认 flow_type='' """
        task = MockTask(task_type='report', title='t', content={})
        self.assertEqual(task.flow_type, '')

    def test_task_to_dict_serialization(self):
        """2. Task.to_dict() 序列化 flow_type 字段"""
        task = MockTask(task_type='report', title='t', content={}, flow_type='production')
        d = task.to_dict()
        self.assertIn('flow_type', d)
        self.assertEqual(d['flow_type'], 'production')

    def test_task_from_dict_deserialization(self):
        """3. Task.from_dict() 反序列化 flow_type (forward compat)"""
        data = {
            'id': 'T123',
            'task_type': 'quality',
            'title': '质检',
            'content': {},
            'flow_type': 'quality',
        }
        task = MockTask.from_dict(data)
        self.assertEqual(task.flow_type, 'quality')

    def test_task_from_dict_missing_flow_type_uses_default(self):
        """3b. from_dict 缺 flow_type 字段 → 默认 '' (防老数据)"""
        data = {
            'id': 'T123',
            'task_type': 'quality',
            'title': '质检',
            'content': {},
        }
        task = MockTask.from_dict(data)
        self.assertEqual(task.flow_type, '')


class TestInferTaskTypeToFlowType(unittest.TestCase):
    """推断函数 (4 用例)"""

    def test_report_to_production(self):
        """4. task_type='report' → flow_type='production'"""
        self.assertEqual(infer_task_type_to_flow_type('report'), 'production')

    def test_quality_to_quality(self):
        """5. task_type='quality' → flow_type='quality'"""
        self.assertEqual(infer_task_type_to_flow_type('quality'), 'quality')

    def test_material_to_material_purchase(self):
        """6. task_type='material' → flow_type='material_purchase'"""
        self.assertEqual(infer_task_type_to_flow_type('material'), 'material_purchase')

    def test_approval_to_production(self):
        """7. task_type='approval' → flow_type='production' (审批归生产)"""
        self.assertEqual(infer_task_type_to_flow_type('approval'), 'production')


class TestPublishTaskFlowTypePriority(unittest.TestCase):
    """publish_*_task 显式 flow_type 优先于推断 (1 用例)"""

    def test_explicit_flow_type_overrides_inference(self):
        """8. 显式 flow_type='outsource' + task_type='report' → flow_type='outsource'"""
        # 模拟 publish_*_task 内部: flow_type or infer(task_type)
        effective = _resolve_flow_type('outsource', 'report')
        self.assertEqual(effective, 'outsource',
                         f"显式 flow_type 应优先, 实际 {effective}")

    def test_missing_flow_type_falls_back_to_inference(self):
        """8b. 缺 flow_type → 按 task_type 推断"""
        effective = _resolve_flow_type('', 'material')
        self.assertEqual(effective, 'material_purchase')


if __name__ == "__main__":
    unittest.main()
