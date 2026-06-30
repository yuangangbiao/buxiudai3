# -*- coding: utf-8 -*-
"""
手动发布服务 - Manual Publish Service

处理手动发布任务的逻辑

使用方式：
    from manual_publish_service import ManualPublishService, get_manual_publish_service

    # 获取服务
    svc = get_manual_publish_service()

    # 发布单个工序任务
    success = svc.publish_single(
        order_no='ORD202604001',
        process_name='编织'
    )

    # 批量发布工序任务
    task_ids = svc.publish_batch(
        order_no='ORD202604001',
        process_list=['编织', '质检', '包装']
    )

    # 获取可发布的工序列表
    processable = svc.get_publishable_processes('ORD202604001')
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


class ManualPublishService:
    """
    手动发布服务

    职责：
        - 处理手动发布任务逻辑
        - 批量发布工序任务
        - 获取可发布的工序列表
    """

    def __init__(self):
        """
        初始化手动发布服务
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
            mp_config = config.get_config('manual_publish', {})
            self._enabled = mp_config.get('enabled', True)
            self._confirm_before = mp_config.get('confirm_before_publish', True)
        except Exception:
            self._enabled = True
            self._confirm_before = True

    def _init_integration(self) -> None:
        """
        初始化容器集成
        """
        try:
            # [Q-B6 v3.7.5 修复 2026-06-25] 改用 dispatch_center.publisher
            from mobile_api_ai.dispatch_center.publisher import get_publisher
            self._integration = get_publisher('report')
            self._integration_available = True
        except Exception as e:
            logger.warning(f'[手动发布] 容器集成不可用: {e}')
            self._integration = None
            self._integration_available = False

    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            是否可用
        """
        return self._enabled and self._integration_available

    def _check_mode(self) -> bool:
        """
        检查当前是否为手动模式

        Returns:
            是否手动模式
        """
        try:
            from publish_mode_manager import get_publish_mode_manager
            mgr = get_publish_mode_manager()
            if not mgr.is_manual_mode():
                logger.warning('[手动发布] 当前不是手动模式，拒绝发布')
                return False
            return True
        except ImportError:
            logger.warning('[手动发布] PublishModeManager不可用')
            return True

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
            logger.warning('[手动发布] EventBus不可用')
        except Exception as e:
            logger.warning(f'[手动发布] 事件通知失败: {e}')

    def publish_single(self,
                     order_no: str,
                     process_name: str,
                     customer_name: str = '',
                     product_type: str = '',
                     quantity: int = 0,
                     unit: str = '',
                     planned_qty: int = 0,
                     operator_id: str = 'OP001',
                     operator_name: str = '',
                     priority: str = 'normal',
                     **kwargs) -> bool:
        """
        发布单个工序任务

        Args:
            order_no: 订单号
            process_name: 工序名称
            order_no: 订单号
            customer_name: 客户名称
            product_type: 产品类型
            quantity: 数量
            unit: 单位
            planned_qty: 计划数量
            operator_id: 操作员ID
            operator_name: 操作员名称
            priority: 优先级
            **kwargs: 扩展参数

        Returns:
            是否成功
        """
        if not self._enabled:
            logger.warning('[手动发布] 功能未启用')
            return False

        if not self._check_mode():
            return False

        if not self._integration_available:
            logger.error('[手动发布] 容器集成不可用')
            return False

        try:
            logger.info(f'[手动发布] 发布单个任务: order={order_no}, process={process_name}')

            if not order_no:
                order_no = order_no

            task_id = self._integration.publish_report_task(
                order_no=order_no,
                process_name=process_name,
                customer_name=customer_name,
                product_type=product_type,
                quantity=quantity,
                unit=unit,
                planned_qty=planned_qty or quantity,
                operator_id=operator_id,
                operator_name=operator_name,
                priority=priority,
                **kwargs
            )

            if task_id:
                self._notify_event('MANUAL_PUBLISH_REQUESTED', {
                    'order_no': order_no,
                    'process_name': process_name,
                    'task_id': task_id,
                    'success': True
                })
                logger.info(f'[手动发布] 发布成功: task_id={task_id}')
                return True
            else:
                self._notify_event('MANUAL_PUBLISH_REQUESTED', {
                    'order_no': order_no,
                    'process_name': process_name,
                    'success': False
                })
                return False

        except Exception as e:
            logger.error(f'[手动发布] 发布失败: {e}')
            return False

    def publish_batch(self,
                    order_no: str,
                    process_list: List[str],
                    customer_name: str = '',
                    product_type: str = '',
                    quantity: int = 0,
                    unit: str = '',
                    planned_qty: int = 0,
                    operator_id: str = 'OP001',
                    operator_name: str = '',
                    priority: str = 'normal',
                    **kwargs) -> List[str]:
        """
        批量发布工序任务

        Args:
            order_no: 订单号
            process_list: 工序名称列表
            order_no: 订单号
            customer_name: 客户名称
            product_type: 产品类型
            quantity: 数量
            unit: 单位
            planned_qty: 计划数量
            operator_id: 操作员ID
            operator_name: 操作员名称
            priority: 优先级
            **kwargs: 扩展参数

        Returns:
            成功发布的任务ID列表
        """
        if not self._enabled:
            logger.warning('[手动发布] 功能未启用')
            return []

        if not self._check_mode():
            return []

        if not process_list:
            logger.warning('[手动发布] 工序列表为空')
            return []

        if not self._integration_available:
            logger.error('[手动发布] 容器集成不可用')
            return []

        task_ids = []
        failed = []

        for process_name in process_list:
            try:
                success = self.publish_single(
                    order_no=order_no,
                    process_name=process_name,
                    customer_name=customer_name,
                    product_type=product_type,
                    quantity=quantity,
                    unit=unit,
                    planned_qty=planned_qty or quantity,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    priority=priority,
                    **kwargs
                )

                if success:
                    logger.info(f'[手动发布] 工序发布成功: {process_name}')
                else:
                    failed.append(process_name)

            except Exception as e:
                logger.error(f'[手动发布] 工序发布异常: {process_name}, error={e}')
                failed.append(process_name)

        if failed:
            logger.warning(f'[手动发布] 部分工序发布失败: {failed}')

        logger.info(f'[手动发布] 批量发布完成: 成功={len(task_ids)}, 失败={len(failed)}')
        return task_ids

    def get_publishable_processes(self, order_no: str = '') -> List[Dict[str, Any]]:
        """
        获取可发布的工序列表

        Args:
            order_no: 订单号（可选）

        Returns:
            可发布工序列表
        """
        if not self._enabled:
            return []

        try:
            from process_tracker import get_process_tracker
            tracker = get_process_tracker()

            if order_no:
                processes = tracker.get_order_processes(order_no)
                pending_or_completed = [p for p in processes
                                       if p.get('status') in ['pending', 'completed']]
                return pending_or_completed
            else:
                pending = tracker.get_pending_processes()
                return pending

        except ImportError:
            logger.warning('[手动发布] ProcessTracker不可用')
            return []
        except Exception as e:
            logger.error(f'[手动发布] 获取可发布工序失败: {e}')
            return []

    def confirm_publish(self,
                      order_no: str,
                      process_name: str) -> bool:
        """
        确认发布（用于发布前确认）

        Args:
            order_no: 订单号
            process_name: 工序名称

        Returns:
            是否确认
        """
        if not self._confirm_before:
            return True

        logger.info(f'[手动发布] 发布确认: order={order_no}, process={process_name}')
        return True

    def cancel_publish(self,
                     order_no: str,
                     process_name: str) -> bool:
        """
        取消发布

        Args:
            order_no: 订单号
            process_name: 工序名称

        Returns:
            是否成功
        """
        logger.info(f'[手动发布] 取消发布: order={order_no}, process={process_name}')
        return True


_manual_publish_service_instance: Optional['ManualPublishService'] = None


def get_manual_publish_service() -> 'ManualPublishService':
    """
    获取全局手动发布服务实例（单例）

    Returns:
        ManualPublishService实例
    """
    global _manual_publish_service_instance
    if _manual_publish_service_instance is None:
        _manual_publish_service_instance = ManualPublishService()
    return _manual_publish_service_instance


def reset_manual_publish_service() -> None:
    """
    重置全局手动发布服务实例
    """
    global _manual_publish_service_instance
    _manual_publish_service_instance = None


def demo() -> None:
    """
    演示用法
    """
    print('=' * 60)
    print('手动发布服务演示')
    print('=' * 60)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    svc = get_manual_publish_service()

    print(f'\n[1] 服务可用性: {svc.is_available()}')

    print('\n[2] 尝试手动发布单个工序...')

    from publish_mode_manager import get_publish_mode_manager
    mgr = get_publish_mode_manager()
    mgr.set_mode('manual')
    print(f'   当前模式: {mgr.get_mode()}')

    success = svc.publish_single(
        order_no='ORD202604001',
        process_name='编织',
        customer_name='上海机械厂',
        product_type='不锈钢编织网',
        quantity=100,
        unit='米',
        planned_qty=100,
        operator_id='OP001',
        operator_name='张三',
        priority='high'
    )
    print(f'   发布结果: {"成功" if success else "失败"}')

    print('\n[3] 批量发布工序...')
    task_ids = svc.publish_batch(
        order_no='ORD202604002',
        process_list=['编织', '质检', '包装'],
        customer_name='北京钢材厂',
        quantity=200,
        unit='米'
    )
    print(f'   批量发布结果: {len(task_ids)} 个任务')

    print('\n' + '=' * 60)
    print('演示完成！')
    print('=' * 60)


if __name__ == '__main__':
    demo()
