# -*- coding: utf-8 -*-
"""
任务撤回服务 - Task Recall Service

撤回已发布的任务

使用方式：
    from task_recall_service import TaskRecallService, get_task_recall_service

    # 获取服务
    svc = get_task_recall_service()

    # 撤回任务
    success = svc.recall_task('task_id_123')

    # 检查任务是否可撤回
    can_recall = svc.can_recall('task_id_123')

    # 获取可撤回状态列表
    statuses = svc.get_recallable_statuses()
"""

import sys
import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

MOBILE_API_AI_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'mobile_api_ai')
if MOBILE_API_AI_PATH not in sys.path:
    sys.path.insert(0, MOBILE_API_AI_PATH)


class TaskRecallService:
    """
    任务撤回服务

    职责：
        - 撤回已发布的任务
        - 检查任务是否可撤回
        - 获取任务详情
    """

    RECALLABLE_STATUSES = ['pending', 'distributed']
    NON_RECALLABLE_STATUSES = ['acknowledged', 'completed', 'recalled']

    def __init__(self):
        """
        初始化任务撤回服务
        """
        self._load_config()
        self._init_integration()

    def _load_config(self) -> None:
        """
        加载配置
        """
        try:
            from modular_config import ModularConfig
            config = ModularConfig()
            recall_config = config.get_config('task_recall', {})
            self._enabled = recall_config.get('enabled', True)
            self._max_recall_attempts = recall_config.get('max_recall_attempts', 3)
        except Exception:
            self._enabled = True
            self._max_recall_attempts = 3

    def _init_integration(self) -> None:
        """
        初始化容器集成
        """
        try:
            # [Q-B6 v3.7.5 修复 2026-06-25] 改用 dispatch_center.publisher
            from mobile_api_ai.dispatch_center.publisher import get_publisher
            self._integration = get_publisher('task_recall')
            self._integration_available = True
        except Exception as e:
            logger.warning(f'[任务撤回] 容器集成不可用: {e}')
            self._integration = None
            self._integration_available = False

    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            是否可用
        """
        return self._enabled and self._integration_available

    def _notify_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        发送事件通知

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        try:
            from event_bus import EventBus
            EventBus.publish(event_type, data)
        except ImportError:
            logger.warning('[任务撤回] EventBus不可用')
        except Exception as e:
            logger.warning(f'[任务撤回] 事件通知失败: {e}')

    def get_recallable_statuses(self) -> List[str]:
        """
        获取可撤回的状态列表

        Returns:
            可撤回状态列表
        """
        return self.RECALLABLE_STATUSES.copy()

    def can_recall(self, task_id: str) -> bool:
        """
        检查任务是否可撤回

        Args:
            task_id: 任务ID

        Returns:
            是否可撤回
        """
        if not self._enabled:
            logger.warning('[任务撤回] 功能未启用')
            return False

        task_info = self.get_task_info(task_id)
        if not task_info:
            logger.warning(f'[任务撤回] 任务不存在: {task_id}')
            return False

        status = task_info.get('status', '')
        if status in self.RECALLABLE_STATUSES:
            return True

        logger.info(f'[任务撤回] 任务不可撤回: status={status}')
        return False

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典
        """
        if not self._integration_available:
            logger.error('[任务撤回] 容器集成不可用')
            return None

        try:
            return self._integration.get_task_by_id(task_id)
        except Exception as e:
            logger.error(f'[任务撤回] 获取任务详情失败: {e}')
            return None

    def recall_task(self, task_id: str) -> bool:
        """
        撤回任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功撤回
        """
        if not self._enabled:
            logger.warning('[任务撤回] 功能未启用')
            return False

        if not self._integration_available:
            logger.error('[任务撤回] 容器集成不可用')
            return False

        task_info = self.get_task_info(task_id)
        if not task_info:
            logger.error(f'[任务撤回] 任务不存在: {task_id}')
            self._notify_event('TASK_RECALL_FAILED', {
                'task_id': task_id,
                'reason': 'task_not_found'
            })
            return False

        status = task_info.get('status', '')
        if status not in self.RECALLABLE_STATUSES:
            logger.warning(f'[任务撤回] 任务不可撤回: status={status}')
            self._notify_event('TASK_RECALL_FAILED', {
                'task_id': task_id,
                'reason': f'invalid_status_{status}'
            })
            return False

        try:
            logger.info(f'[任务撤回] 开始撤回任务: {task_id}')

            success = self._do_recall(task_id, task_info)

            if success:
                self._notify_event('TASK_RECALLED', {
                    'task_id': task_id,
                    'order_no': task_info.get('order_no', ''),
                    'process_name': task_info.get('process_name', ''),
                    'original_status': status
                })
                logger.info(f'[任务撤回] 任务撤回成功: {task_id}')
            else:
                self._notify_event('TASK_RECALL_FAILED', {
                    'task_id': task_id,
                    'reason': 'recall_operation_failed'
                })

            return success

        except Exception as e:
            logger.error(f'[任务撤回] 撤回任务异常: {e}')
            self._notify_event('TASK_RECALL_FAILED', {
                'task_id': task_id,
                'reason': str(e)
            })
            return False

    def _do_recall(self, task_id: str, task_info: Dict[str, Any]) -> bool:
        """
        执行撤回操作

        Args:
            task_id: 任务ID
            task_info: 任务信息

        Returns:
            是否成功
        """
        try:
            storage = self._integration._container_center.storage
            original_data = storage.get_package(task_id)

            if not original_data:
                logger.error(f'[任务撤回] 无法获取原始数据: {task_id}')
                return False

            recalled_data = original_data.copy()
            recalled_data['status'] = 'recalled'
            recalled_data['recalled_at'] = self._get_current_timestamp()
            recalled_data['previous_status'] = task_info.get('status', '')

            storage.save_package(recalled_data)

            logger.info(f'[任务撤回] 任务状态已更新: {task_id} -> recalled')
            return True

        except Exception as e:
            logger.error(f'[任务撤回] 执行撤回失败: {e}')
            return False

    def _get_current_timestamp(self) -> str:
        """
        获取当前时间戳

        Returns:
            ISO格式时间戳
        """
        from datetime import datetime
        return datetime.now().isoformat()

    def get_tasks_by_order(self, order_no: str) -> List[Dict[str, Any]]:
        """
        获取订单的所有任务

        Args:
            order_no: 订单号

        Returns:
            任务列表
        """
        if not self._integration_available:
            return []

        try:
            all_tasks = self._integration.get_all_tasks(limit=1000)
            order_tasks = [t for t in all_tasks if t.get('order_no') == order_no]
            return order_tasks
        except Exception as e:
            logger.error(f'[任务撤回] 获取订单任务失败: {e}')
            return []

    def get_recallable_tasks(self, order_no: str = '') -> List[Dict[str, Any]]:
        """
        获取可撤回的任务列表

        Args:
            order_no: 订单号（可选）

        Returns:
            可撤回任务列表
        """
        if order_no:
            tasks = self.get_tasks_by_order(order_no)
        else:
            if not self._integration_available:
                return []
            try:
                tasks = self._integration.get_all_tasks(limit=1000)
            except Exception:
                return []

        recallable = [t for t in tasks if t.get('status') in self.RECALLABLE_STATUSES]
        return recallable


_task_recall_service_instance: Optional['TaskRecallService'] = None


def get_task_recall_service() -> 'TaskRecallService':
    """
    获取全局任务撤回服务实例（单例）

    Returns:
        TaskRecallService实例
    """
    global _task_recall_service_instance
    if _task_recall_service_instance is None:
        _task_recall_service_instance = TaskRecallService()
    return _task_recall_service_instance


def reset_task_recall_service() -> None:
    """
    重置全局任务撤回服务实例
    """
    global _task_recall_service_instance
    _task_recall_service_instance = None


def demo() -> None:
    """
    演示用法
    """
    print('=' * 60)
    print('任务撤回服务演示')
    print('=' * 60)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    svc = get_task_recall_service()

    print(f'\n[1] 服务可用性: {svc.is_available()}')

    print('\n[2] 可撤回状态列表:')
    statuses = svc.get_recallable_statuses()
    print(f'   {statuses}')

    print('\n[3] 任务撤回服务演示完成')
    print('\n' + '=' * 60)


if __name__ == '__main__':
    demo()
