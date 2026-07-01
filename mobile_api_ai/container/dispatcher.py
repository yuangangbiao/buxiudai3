# -*- coding: utf-8 -*-
"""
分配器模块 (Dispatcher)
负责将容器池中的任务分配给移动端，并处理结果回写
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from .task_pool import TaskPool, Task, TaskStatus, TaskType


# 修补 T6 (D3.1 推断): task_type → flow_type 映射表
# 与 SPEC v1.1 F6 一致: report/approval → production, quality → quality,
#                              material → material_purchase
TASK_TYPE_TO_FLOW_TYPE = {
    'report': 'production',
    'quality': 'quality',
    'material': 'material_purchase',
    'approval': 'production',
}


def infer_task_type_to_flow_type(task_type: str) -> str:
    """T6 推断函数 (模块级, 纯函数)

    Args:
        task_type: task_type 字符串 (如 'report'/'quality'/'material'/'approval')

    Returns:
        flow_type 字符串 (5 种之一: production/quality/material_purchase/repair/outsource)
        未知或空 → 兜底 'production'
    """
    if not task_type:
        return 'production'
    return TASK_TYPE_TO_FLOW_TYPE.get(task_type.lower(), 'production')

class DispatchResult:
    """分配结果"""

    def __init__(self, success: bool, message: str, data: Any = None):
        self.success = success
        self.message = message
        self.data = data
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


class Dispatcher:
    """
    任务分配器
    核心职责：
    1. 将任务分配给指定员工
    2. 接收移动端执行结果
    3. 回写到桌面端系统
    """

    def __init__(self, task_pool: TaskPool):
        self.pool = task_pool
        self.handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认结果处理器"""
        self.register_handler('report', self._handle_report_result)
        self.register_handler('quality', self._handle_quality_result)
        self.register_handler('material', self._handle_material_result)
        self.register_handler('approval', self._handle_approval_result)

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务结果处理器"""
        self.handlers[task_type] = handler

    def dispatch(self, operator_id: str,
                 task_types: List[str] = None,
                 flow_types: List[str] = None,  # 修补 T10 (F10.1)
                 max_count: int = 10) -> DispatchResult:
        """
        分配任务给员工

        Args:
            operator_id: 员工ID
            task_types: 要分配的任务类型列表 (D3.1 老路径)
            flow_types: 要分配的 flow_type 列表 (T10 新增, 优先于 task_types)
            max_count: 最大分配数量

        Returns:
            分配结果，包含任务列表

        路由策略 (D-T10.1):
          - flow_types 显式 (非 None) → 走 flow_type 路由, 调用 get_tasks_by_flow_type
          - flow_types=None → 走原 task_types 路径 (向后兼容)
        """
        if flow_types is not None:
            # 修补 T10 (F10.1): flow_types 显式优先
            # 空列表等价于"不过滤 flow_type", 兜底 5 种全集
            target_fts = flow_types if flow_types else [
                'production', 'quality', 'material_purchase', 'outsource', 'repair'
            ]
            tasks = []
            for ft in target_fts:
                tasks.extend(self.pool.get_tasks_by_flow_type(
                    ft, status='pending', operator_id=operator_id
                ))
            # 排序策略与 get_pending_tasks 一致 (D-T10.5)
            tasks.sort(key=lambda x: (x.priority == 'low', x.created_at))
        else:
            task_types = task_types or ['report', 'quality', 'material', 'approval']
            tasks = self.pool.get_pending_tasks(operator_id, task_types)

        assigned = []
        for task in tasks[:max_count]:
            if self.pool.assign_task(task.id, operator_id):
                assigned.append(task.to_dict())

        return DispatchResult(
            success=True,
            message=f'已分配 {len(assigned)} 个任务',
            data={'tasks': assigned, 'total': len(assigned)}
        )

    def dispatch_task(self, task_id: str, operator_id: str) -> DispatchResult:
        """分配指定任务给员工"""
        task = self.pool.get_task(task_id)
        if not task:
            return DispatchResult(False, f'任务 {task_id} 不存在')

        if task.status != TaskStatus.PENDING.value:
            return DispatchResult(False, f'任务状态不是待分配，当前状态: {task.status}')

        if self.pool.assign_task(task_id, operator_id):
            return DispatchResult(True, f'已将任务分配给 {operator_id}', task.to_dict())

        return DispatchResult(False, '分配失败')

    def receive_result(self, task_id: str, result_data: Dict) -> DispatchResult:
        """
        接收移动端执行结果

        Args:
            task_id: 任务ID
            result_data: 执行结果数据

        Returns:
            处理结果
        """
        task = self.pool.get_task(task_id)
        if not task:
            return DispatchResult(False, f'任务 {task_id} 不存在')

        if task.status == TaskStatus.COMPLETED.value:
            return DispatchResult(False, '任务已完成，不能重复提交')

        handler = self.handlers.get(task.task_type)
        if handler:
            try:
                handler_result = handler(task, result_data)
                if handler_result:
                    self.pool.complete_task(task_id, result_data)
                    return DispatchResult(True, '提交成功', handler_result)
            except Exception as e:
                return DispatchResult(False, f'处理结果失败: {str(e)}')

        self.pool.complete_task(task_id, result_data)
        return DispatchResult(True, '提交成功')

    def get_task_detail(self, task_id: str, operator_id: str = None) -> DispatchResult:
        """获取任务详情"""
        task = self.pool.get_task(task_id)
        if not task:
            return DispatchResult(False, f'任务 {task_id} 不存在')

        if operator_id and task.operator_id and task.operator_id != operator_id:
            return DispatchResult(False, '无权访问此任务')

        return DispatchResult(True, '获取成功', task.to_dict())

    def cancel_task(self, task_id: str, reason: str = None) -> DispatchResult:
        """取消任务"""
        if self.pool.cancel_task(task_id, reason):
            return DispatchResult(True, '任务已取消')
        return DispatchResult(False, '取消失败，任务可能已完成')

    def _handle_report_result(self, task: Task, result_data: Dict) -> Dict:
        """
        处理报工结果
        回写到桌面端生产记录表
        """
        return {
            'action': 'report_completed',
            'task_id': task.id,
            'order_no': task.related_order,
            'process': task.related_process,
            'quantity': result_data.get('completed_qty'),
            'status': result_data.get('status'),
            'operator': task.operator_id,
            'completed_at': datetime.now().isoformat(),
            'db_write_needed': True,
            'db_table': 'production_process_records',
            'db_where': {'id': task.content.get('record_id')}
        }

    def _handle_quality_result(self, task: Task, result_data: Dict) -> Dict:
        """
        处理质检结果
        回写到桌面端质检记录表
        """
        return {
            'action': 'quality_completed',
            'task_id': task.id,
            'order_no': task.related_order,
            'result': result_data.get('result'),
            'inspector': task.operator_id,
            'completed_at': datetime.now().isoformat(),
            'db_write_needed': True,
            'db_table': 'quality_records',
            'db_where': {'order_id': task.content.get('order_id')}
        }

    def _handle_material_result(self, task: Task, result_data: Dict) -> Dict:
        """
        处理物料结果
        回写到桌面端物料记录表
        """
        return {
            'action': 'material_delivered',
            'task_id': task.id,
            'material_name': task.content.get('material_name'),
            'quantity': result_data.get('quantity'),
            'operator': task.operator_id,
            'completed_at': datetime.now().isoformat(),
            'db_write_needed': True,
            'db_table': 'material_records',
            'db_where': {'id': task.content.get('record_id')}
        }

    def _handle_approval_result(self, task: Task, result_data: Dict) -> Dict:
        """
        处理审批结果
        回写到桌面端审批记录表
        """
        return {
            'action': 'approval_completed',
            'task_id': task.id,
            'order_no': task.related_order,
            'decision': result_data.get('decision'),
            'reason': result_data.get('reason'),
            'approver': task.operator_id,
            'completed_at': datetime.now().isoformat(),
            'db_write_needed': True,
            'db_table': 'approval_records',
            'db_where': {'id': task.content.get('approval_id')}
        }


class TaskPublisher:
    """
    任务发布器
    桌面端使用此模块发布任务到容器池
    """

    def __init__(self, task_pool: TaskPool):
        self.pool = task_pool

    def publish_report_task(self, order_no: str, process_name: str,
                            record_id: int, operator_id: str,
                            planned_qty: int, priority: str = 'normal',
                            flow_type: str = '') -> str:  # 修补 T6 (F6.2)
        """发布报工任务"""
        # 修补 T6 (F6.6): 显式 flow_type 优先, 推断兜底
        effective_flow_type = flow_type or infer_task_type_to_flow_type('report')
        task = Task(
            task_type='report',
            title=f'报工：{process_name}',
            content={
                'record_id': record_id,
                'planned_qty': planned_qty,
                'order_no': order_no
            },
            operator_id=operator_id,
            priority=priority,
            related_order=order_no,
            related_process=process_name,
            tags=['报工', process_name],
            flow_type=effective_flow_type  # 修补 T6 (F6.2)
        )
        return self.pool.add_task(task)

    def publish_quality_task(self, order_no: str, order_id: int,
                             inspector_id: str, inspection_type: str,
                             priority: str = 'normal',
                             flow_type: str = '') -> str:  # 修补 T6 (F6.3)
        """发布质检任务"""
        # 修补 T6 (F6.6): 显式 flow_type 优先, 推断兜底
        effective_flow_type = flow_type or infer_task_type_to_flow_type('quality')
        task = Task(
            task_type='quality',
            title=f'质检：{inspection_type}',
            content={
                'order_id': order_id,
                'inspection_type': inspection_type
            },
            operator_id=inspector_id,
            priority=priority,
            related_order=order_no,
            tags=['质检', inspection_type],
            flow_type=effective_flow_type  # 修补 T6 (F6.3)
        )
        return self.pool.add_task(task)

    def publish_material_task(self, order_no: str, material_name: str,
                              quantity: int, operator_id: str,
                              priority: str = 'normal',
                              flow_type: str = '') -> str:  # 修补 T6 (F6.4)
        """发布物料需求任务"""
        # 修补 T6 (F6.6): 显式 flow_type 优先, 推断兜底
        effective_flow_type = flow_type or infer_task_type_to_flow_type('material')
        task = Task(
            task_type='material',
            title=f'领料：{material_name}',
            content={
                'material_name': material_name,
                'quantity': quantity
            },
            operator_id=operator_id,
            priority=priority,
            related_order=order_no,
            tags=['领料', material_name],
            flow_type=effective_flow_type  # 修补 T6 (F6.4)
        )
        return self.pool.add_task(task)

    def publish_approval_task(self, order_no: str, approval_id: int,
                              approver_id: str, reason: str,
                              priority: str = 'high',
                              flow_type: str = '') -> str:  # 修补 T6 (F6.5)
        """发布审批任务"""
        # 修补 T6 (F6.6): 显式 flow_type 优先, 推断兜底
        effective_flow_type = flow_type or infer_task_type_to_flow_type('approval')
        task = Task(
            task_type='approval',
            title=f'审批：{reason[:20]}',
            content={
                'approval_id': approval_id,
                'reason': reason
            },
            operator_id=approver_id,
            priority=priority,
            related_order=order_no,
            tags=['审批'],
            flow_type=effective_flow_type  # 修补 T6 (F6.5)
        )
        return self.pool.add_task(task)
