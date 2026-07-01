# -*- coding: utf-8 -*-
"""
任务容器池模块 (Task Pool)
负责存储和管理所有待执行的任务

架构说明：
- 容器池位于桌面端，作为数据中心
- 移动端不直接访问数据库，只从容器池获取任务
- 任务包含完整上下文，移动端只需执行并返回结果
- 支持 SQLite 持久化，服务重启后数据不丢失

持久化说明：
- 使用 storage_layer.py 的存储抽象层
- 每次状态变更立即持久化
- 服务启动时自动从存储加载任务
- 存储失败时自动降级到内存存储
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from storage_layer import create_storage, BaseStorage
    STORAGE_LAYER_AVAILABLE = True
except ImportError:
    STORAGE_LAYER_AVAILABLE = False
    BaseStorage = None


class SimpleMemoryStorage:
    """TaskPool专用简化内存存储（降级用）"""
    def __init__(self):
        self._packages: Dict[str, Dict] = {}

    def save_package(self, package: Dict) -> bool:
        self._packages[package.get('id')] = package
        return True

    def get_package(self, package_id: str):
        return self._packages.get(package_id)

    def get_packages(self, status: str = None, data_type: str = None,
                    operator: str = None, limit: int = 100):
        results = list(self._packages.values())
        if status:
            results = [p for p in results if p.get('status') == status]
        if data_type:
            results = [p for p in results if p.get('data_type') == data_type]
        if operator:
            results = [p for p in results if p.get('target_operator') == operator]
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def delete_package(self, package_id: str) -> bool:
        if package_id in self._packages:
            del self._packages[package_id]
            return True
        return False


class TaskStatus(Enum):
    PENDING = 'pending'       # 待分配
    ASSIGNED = 'assigned'      # 已分配
    IN_PROGRESS = 'in_progress'  # 执行中
    COMPLETED = 'completed'    # 已完成
    CANCELLED = 'cancelled'    # 已取消
    FAILED = 'failed'          # 执行失败

class TaskType(Enum):
    REPORT = 'report'          # 报工任务
    QUALITY = 'quality'        # 质检任务
    MATERIAL = 'material'       # 物料需求
    APPROVAL = 'approval'      # 审批任务
    OTHER = 'other'            # 其他任务

class Task:
    """任务对象"""

    def __init__(self, task_type: str, title: str, content: Dict,
                 operator_id: str = None, priority: str = 'normal',
                 deadline: datetime = None, related_order: str = None,
                 related_process: str = None, tags: List[str] = None,
                 flow_type: str = ''):  # 修补 T6 (F6.1)
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
        self.flow_type = flow_type  # 修补 T6 (F6.1) - 与 T1 DDL DEFAULT '' 对齐

        self.status = TaskStatus.PENDING.value
        self.created_at = datetime.now()
        self.assigned_at = None
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.version = 1

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'task_type': self.task_type,
            'title': self.title,
            'content': self.content,
            'operator_id': self.operator_id,
            'priority': self.priority,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'related_order': self.related_order,
            'related_process': self.related_process,
            'tags': self.tags,
            'flow_type': self.flow_type,  # 修补 T6 (F6.1)
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'version': self.version
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        task = cls(
            task_type=data['task_type'],
            title=data['title'],
            content=data['content'],
            operator_id=data.get('operator_id'),
            priority=data.get('priority', 'normal'),
            deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
            related_order=data.get('related_order'),
            related_process=data.get('related_process'),
            tags=data.get('tags', []),
            flow_type=data.get('flow_type', '')  # 修补 T6 (F6.1) forward compat
        )
        task.id = data.get('id', task.id)
        task.status = data.get('status', TaskStatus.PENDING.value)
        task.version = data.get('version', 1)
        if data.get('created_at'):
            task.created_at = datetime.fromisoformat(data['created_at'])
        return task


class TaskPool:
    """
    任务容器池
    统一管理所有任务类型
    支持 SQLite 持久化
    """

    @staticmethod
    def _init_indices() -> tuple:
        """修补 T7 (F7.2): 工厂函数统一管理 task_index + _flow_type_index
        消除 T3 教训 #7 的 dict literal 重复 key 反模式 (L182-184/L189-191)"""
        task_index = {tt: [] for tt in ['report', 'quality', 'material', 'approval', 'other']}
        flow_type_index = {ft: [] for ft in [
            'production', 'quality', 'material_purchase', 'outsource', 'repair'
        ]}  # 5 种 flow_type (与 T5 D3.1 对齐)
        return task_index, flow_type_index

    def __init__(self, storage_config: Dict = None):
        if storage_config is None:
            storage_config = {'type': 'sqlite', 'db_path': 'task_pool.db'}

        self.storage: Optional[BaseStorage] = None
        self.tasks: Dict[str, Task] = {}
        self.task_index, self._flow_type_index = self._init_indices()  # 修补 T7 (F7.2)

        if STORAGE_LAYER_AVAILABLE:
            try:
                self.storage = create_storage(storage_config)
                loaded = self.load_from_storage()
                logger.info(f"[TaskPool] 存储初始化成功，加载了 {loaded} 个任务")
            except Exception as e:
                logger.warning(f"[TaskPool] 存储初始化失败，降级到内存存储: {e}")
                self.storage = SimpleMemoryStorage()
                self.tasks = {}
                self.task_index, self._flow_type_index = self._init_indices()  # 修补 T7 (F7.2)
        else:
            logger.warning("[TaskPool] 存储层不可用，使用内存存储")
            self.storage = SimpleMemoryStorage()
            self.tasks = {}
            self.task_index, self._flow_type_index = self._init_indices()  # 修补 T7 (F7.2)

    def _task_to_package(self, task: Task) -> Dict:
        """将 Task 对象转换为 storage_layer 的 package 格式"""
        return {
            'id': task.id,
            'data_type': task.task_type,
            'title': task.title,
            'content': task.content,
            'source': 'task_pool',
            'priority': task.priority,
            'status': task.status,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'distributed_at': task.assigned_at.isoformat() if task.assigned_at else None,
            'acknowledged_at': None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'last_reminded_at': None,
            'target_operator': task.operator_id,
            'target_device': None,
            'tags': task.tags,
            'related_order': task.related_order,
            'related_process': task.related_process
        }

    def _package_to_task(self, pkg: Dict) -> Task:
        """将 storage_layer 的 package 格式转换为 Task 对象"""
        task = Task(
            task_type=pkg['data_type'],
            title=pkg.get('title', ''),
            content=pkg.get('content', {}),
            operator_id=pkg.get('target_operator'),
            priority=pkg.get('priority', 'normal'),
            deadline=None,
            related_order=pkg.get('related_order'),
            related_process=pkg.get('related_process'),
            tags=pkg.get('tags', [])
        )
        task.id = pkg['id']
        task.status = pkg['status']

        if pkg.get('created_at'):
            task.created_at = datetime.fromisoformat(pkg['created_at'])
        if pkg.get('distributed_at'):
            task.assigned_at = datetime.fromisoformat(pkg['distributed_at'])
        if pkg.get('started_at'):
            task.started_at = datetime.fromisoformat(pkg['started_at'])
        if pkg.get('completed_at'):
            task.completed_at = datetime.fromisoformat(pkg['completed_at'])

        task.version = pkg.get('version', 1)
        return task

    def _save_task(self, task: Task) -> bool:
        """保存任务到存储"""
        if not hasattr(self.storage, 'save_package'):
            return False
        try:
            pkg = self._task_to_package(task)
            return self.storage.save_package(pkg)
        except Exception as e:
            logger.error(f"[TaskPool] 保存任务失败: {e}")
            return False

    def _load_task(self, package_id: str) -> Optional[Task]:
        """从存储加载单个任务"""
        if not self.storage:
            return None
        try:
            pkg = self.storage.get_package(package_id)
            if pkg:
                return self._package_to_task(pkg)
            return None
        except Exception as e:
            logger.error(f"[TaskPool] 加载任务失败: {e}")
            return None

    def load_from_storage(self) -> int:
        """从存储加载所有任务，返回加载数量"""
        if not self.storage:
            return 0
        try:
            packages = self.storage.get_packages(limit=10000)
            count = 0
            for pkg in packages:
                if pkg.get('status') == TaskStatus.COMPLETED.value:
                    continue
                task = self._package_to_task(pkg)
                self.tasks[task.id] = task
                if task.task_type in self.task_index:
                    self.task_index[task.task_type].append(task.id)
                # 修补 T7 (F7.6): 重建 _flow_type_index (从存储加载的 task 也含 flow_type)
                if task.flow_type and task.flow_type in self._flow_type_index:
                    self._flow_type_index[task.flow_type].append(task.id)
                count += 1
            return count
        except Exception as e:
            logger.error(f"[TaskPool] 从存储加载失败: {e}")
            return 0

    def add_task(self, task: Task) -> str:
        """添加任务到容器池"""
        self.tasks[task.id] = task
        if task.task_type in self.task_index:
            self.task_index[task.task_type].append(task.id)
        # 修补 T7 (F7.3): 同时维护 _flow_type_index
        if task.flow_type and task.flow_type in self._flow_type_index:
            self._flow_type_index[task.flow_type].append(task.id)
        self._save_task(task)
        return task.id

    def get_task(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        return self.tasks.get(task_id)

    def get_tasks_by_type(self, task_type: str,
                          status: str = None,
                          operator_id: str = None) -> List[Task]:
        """根据类型获取任务列表"""
        task_ids = self.task_index.get(task_type, [])
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

    def get_tasks_by_flow_type(self, flow_type: str,
                                status: str = None,
                                operator_id: str = None) -> List[Task]:
        """修补 T7 (F7.4): 根据 flow_type 获取任务列表

        Args:
            flow_type: flow_type 字符串 (5 种之一: production/quality/material_purchase/outsource/repair)
            status: 任务状态过滤 (可选)
            operator_id: 操作员ID过滤 (可选)

        Returns:
            匹配条件的 Task 列表
        """
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

    def get_pending_tasks(self, operator_id: str = None,
                          task_types: List[str] = None) -> List[Task]:
        """获取待处理任务"""
        task_types = task_types or ['report', 'quality', 'material', 'approval']
        result = []

        for t_type in task_types:
            tasks = self.get_tasks_by_type(t_type, status=TaskStatus.PENDING.value)
            for task in tasks:
                if operator_id is None or task.operator_id is None or task.operator_id == operator_id:
                    result.append(task)

        result.sort(key=lambda x: (x.priority == 'low', x.created_at))
        return result

    def assign_task(self, task_id: str, operator_id: str) -> bool:
        """分配任务给员工"""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING.value:
            return False

        task.operator_id = operator_id
        task.status = TaskStatus.ASSIGNED.value
        task.assigned_at = datetime.now()
        self._save_task(task)
        return True

    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.ASSIGNED.value:
            return False

        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.now()
        task.version += 1
        self._save_task(task)
        return True

    def complete_task(self, task_id: str, result: Dict) -> bool:
        """完成任务"""
        task = self.tasks.get(task_id)
        if not task or task.status not in [TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value]:
            return False

        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now()
        task.result = result
        task.version += 1
        self._save_task(task)
        return True

    def cancel_task(self, task_id: str, reason: str = None) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task or task.status in [TaskStatus.COMPLETED.value]:
            return False

        task.status = TaskStatus.CANCELLED.value
        task.result = {'cancel_reason': reason}
        self._save_task(task)
        return True

    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if self.task_index[task.task_type] and task_id in self.task_index[task.task_type]:
            self.task_index[task.task_type].remove(task_id)
        # 修补 T7 (F7.5): 同步清理 _flow_type_index
        if task.flow_type and task.flow_type in self._flow_type_index:
            if task_id in self._flow_type_index[task.flow_type]:
                self._flow_type_index[task.flow_type].remove(task_id)
        del self.tasks[task_id]

        if self.storage:
            try:
                self.storage.delete_package(task_id)
            except Exception as e:
                logger.error(f"[TaskPool] 删除存储任务失败: {e}")

        return True

    def get_pool_status(self) -> Dict:
        """获取容器池状态"""
        status = {k: [] for k in self.task_index.keys()}
        for task_type, task_ids in self.task_index.items():
            status[task_type] = [self.tasks[tid].status for tid in task_ids if tid in self.tasks]

        summary = {}
        for task_type, statuses in status.items():
            summary[task_type] = {
                'total': len(statuses),
                'pending': statuses.count(TaskStatus.PENDING.value),
                'assigned': statuses.count(TaskStatus.ASSIGNED.value),
                'in_progress': statuses.count(TaskStatus.IN_PROGRESS.value),
                'completed': statuses.count(TaskStatus.COMPLETED.value)
            }

        return {
            'total_tasks': len(self.tasks),
            'by_type': summary
        }


def _create_task_pool_with_storage(storage_config: Dict = None) -> TaskPool:
    """创建带持久化的任务池（便捷函数）"""
    return TaskPool(storage_config)


task_pool = TaskPool()
