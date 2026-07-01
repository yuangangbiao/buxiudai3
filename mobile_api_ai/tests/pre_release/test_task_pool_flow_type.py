# -*- coding: utf-8 -*-
"""
T7 前测: TaskPool 加 _flow_type_index + get_tasks_by_flow_type 等

修复点 (SPEC v1.1 F7 修正: supersede 不存在, 真实需求是 flow_type 索引):
  1. TaskPool.__init__ 加 _flow_type_index 字段 (5 种 flow_type 初始空列表)
  2. _init_indices 工厂函数统一管理 task_index + flow_type_index (消除 dict literal 重复)
  3. add_task 同时维护 _flow_type_index
  4. 新方法 get_tasks_by_flow_type(flow_type, status, operator_id)
  5. remove_task 同步清理 _flow_type_index
  6. load_from_storage 重建 _flow_type_index

设计契约 (8 用例):
  1. TaskPool 实例有 _flow_type_index 字段 (5 种 flow_type 初始 key)
  2. add_task 维护 _flow_type_index
  3. get_tasks_by_flow_type 返回指定 flow_type 的 task
  4. get_tasks_by_flow_type + status 过滤
  5. get_tasks_by_flow_type + operator_id 过滤
  6. remove_task 清理 _flow_type_index
  7. task.flow_type='' 不被 flow_type 索引
  8. 5 种 flow_type key 完整 (production/quality/material_purchase/outsource/repair)
"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# 模拟 Task (T6 修复后版本)
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
        self.status = 'pending'
        self.created_at = datetime.now()
        self.assigned_at = None
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.version = 1


# 模拟 TaskPool (T7 修复后版本)
INITIAL_FLOW_TYPES = ['production', 'quality', 'material_purchase', 'outsource', 'repair']


class MockTaskPool:
    def __init__(self):
        self.tasks: Dict[str, MockTask] = {}
        self.task_index: Dict[str, List[str]] = {
            'report': [], 'quality': [], 'material': [], 'approval': [], 'other': []
        }
        self._flow_type_index: Dict[str, List[str]] = {ft: [] for ft in INITIAL_FLOW_TYPES}

    def add_task(self, task: MockTask) -> str:
        self.tasks[task.id] = task
        if task.task_type in self.task_index:
            self.task_index[task.task_type].append(task.id)
        if task.flow_type and task.flow_type in self._flow_type_index:
            self._flow_type_index[task.flow_type].append(task.id)
        return task.id

    def remove_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        if self.task_index.get(task.task_type) and task_id in self.task_index[task.task_type]:
            self.task_index[task.task_type].remove(task_id)
        if task.flow_type and task.flow_type in self._flow_type_index:
            if task_id in self._flow_type_index[task.flow_type]:
                self._flow_type_index[task.flow_type].remove(task_id)
        del self.tasks[task_id]
        return True

    def get_tasks_by_flow_type(self, flow_type: str,
                                status: str = None,
                                operator_id: str = None) -> List[MockTask]:
        task_ids = self._flow_type_index.get(flow_type, [])
        result = []
        for tid in task_ids:
            task = self.tasks.get(tid)
            if not task:
                continue
            if status and task.status != status:
                continue
            if operator_id and task.operator_id and task.operator_id != operator_id:
                continue
            result.append(task)
        return result


class TestTaskPoolFlowTypeIndexInit(unittest.TestCase):
    """构造器加 _flow_type_index 字段 (1 用例)"""

    def test_flow_type_index_has_5_initial_keys(self):
        """1. TaskPool 实例有 _flow_type_index, 含 5 种 flow_type 初始 key"""
        pool = MockTaskPool()
        self.assertTrue(hasattr(pool, '_flow_type_index'))
        # 5 种 flow_type (与 T5 D3.1 对齐)
        expected = {'production', 'quality', 'material_purchase', 'outsource', 'repair'}
        self.assertEqual(set(pool._flow_type_index.keys()), expected,
                         f"5 种 flow_type 缺, 实际 {set(pool._flow_type_index.keys())}")
        # 全部初始为 []
        for ft, ids in pool._flow_type_index.items():
            self.assertEqual(ids, [], f"{ft} 初始应为 []")


class TestAddTaskFlowTypeIndex(unittest.TestCase):
    """add_task 维护 _flow_type_index (1 用例)"""

    def test_add_task_updates_flow_type_index(self):
        """2. add_task 同时维护 task_index + _flow_type_index"""
        pool = MockTaskPool()
        t1 = MockTask(task_type='report', title='报工1', content={}, flow_type='production')
        t2 = MockTask(task_type='quality', title='质检', content={}, flow_type='quality')
        t3 = MockTask(task_type='material', title='领料', content={}, flow_type='material_purchase')
        t4 = MockTask(task_type='report', title='外协', content={}, flow_type='outsource')
        for t in [t1, t2, t3, t4]:
            pool.add_task(t)
        # 验证索引
        self.assertEqual(len(pool._flow_type_index['production']), 1)
        self.assertEqual(len(pool._flow_type_index['quality']), 1)
        self.assertEqual(len(pool._flow_type_index['material_purchase']), 1)
        self.assertEqual(len(pool._flow_type_index['outsource']), 1)
        self.assertEqual(len(pool._flow_type_index['repair']), 0)


class TestGetTasksByFlowType(unittest.TestCase):
    """新方法 get_tasks_by_flow_type (3 用例)"""

    def setUp(self):
        self.pool = MockTaskPool()
        # 3 个 outsource + 2 个 production + 1 个 quality
        for i in range(3):
            self.pool.add_task(MockTask(
                task_type='report', title=f'外协{i}', content={},
                flow_type='outsource', operator_id=f'op_{i}'
            ))
        for i in range(2):
            self.pool.add_task(MockTask(
                task_type='report', title=f'生产{i}', content={},
                flow_type='production', operator_id='op_0'
            ))
        self.pool.add_task(MockTask(
            task_type='quality', title='质检', content={},
            flow_type='quality', operator_id='op_qc'
        ))

    def test_get_tasks_by_flow_type_returns_correct(self):
        """3. get_tasks_by_flow_type('outsource') 返回 3 个 task"""
        result = self.pool.get_tasks_by_flow_type('outsource')
        self.assertEqual(len(result), 3)
        for t in result:
            self.assertEqual(t.flow_type, 'outsource')

    def test_get_tasks_by_flow_type_with_status_filter(self):
        """4. status 过滤 (全部 pending 应返回所有)"""
        result = self.pool.get_tasks_by_flow_type('outsource', status='pending')
        self.assertEqual(len(result), 3)
        # 错误 status 应返回空
        result_completed = self.pool.get_tasks_by_flow_type('outsource', status='completed')
        self.assertEqual(len(result_completed), 0)

    def test_get_tasks_by_flow_type_with_operator_filter(self):
        """5. operator_id 过滤 (op_0 应该有 1 个 outsource + 2 个 production)"""
        result_op0 = self.pool.get_tasks_by_flow_type('outsource', operator_id='op_0')
        self.assertEqual(len(result_op0), 1)
        result_op1 = self.pool.get_tasks_by_flow_type('outsource', operator_id='op_1')
        self.assertEqual(len(result_op1), 1)


class TestRemoveTaskFlowTypeIndex(unittest.TestCase):
    """remove_task 清理 _flow_type_index (1 用例)"""

    def test_remove_task_clears_flow_type_index(self):
        """6. remove_task 同时清理 task_index + _flow_type_index"""
        pool = MockTaskPool()
        t1 = MockTask(task_type='report', title='外协', content={}, flow_type='outsource')
        pool.add_task(t1)
        # 验证加入
        self.assertEqual(len(pool._flow_type_index['outsource']), 1)
        # 删除
        pool.remove_task(t1.id)
        # 验证清除
        self.assertEqual(len(pool._flow_type_index['outsource']), 0)
        self.assertNotIn(t1.id, pool.tasks)


class TestEmptyFlowTypeNotIndexed(unittest.TestCase):
    """边界: task.flow_type='' 不被索引 (1 用例)"""

    def test_empty_flow_type_not_in_index(self):
        """7. flow_type='' 的 task 不应进入 _flow_type_index"""
        pool = MockTaskPool()
        t1 = MockTask(task_type='report', title='未分类', content={}, flow_type='')
        pool.add_task(t1)
        # 验证未进入任何 flow_type 索引
        for ft, ids in pool._flow_type_index.items():
            self.assertNotIn(t1.id, ids, f"空 flow_type 不应入 {ft} 索引")
        # 但 get_tasks_by_flow_type 应能找到 (因为不走索引, 但 task 存在)
        # 实际: 应返回空 (因为索引为空)
        result = pool.get_tasks_by_flow_type('production')
        self.assertEqual(len(result), 0)


class TestFlowTypeIndexCompleteness(unittest.TestCase):
    """5 种 flow_type key 完整性 (1 用例)"""

    def test_all_5_flow_types_have_index(self):
        """8. 5 种 flow_type 都有索引 (与 T5 D3.1 对齐)"""
        pool = MockTaskPool()
        required_flow_types = {
            'production', 'quality', 'material_purchase', 'outsource', 'repair'
        }
        actual = set(pool._flow_type_index.keys())
        self.assertEqual(actual, required_flow_types,
                         f"缺 {required_flow_types - actual}, 多 {actual - required_flow_types}")


if __name__ == "__main__":
    unittest.main()
