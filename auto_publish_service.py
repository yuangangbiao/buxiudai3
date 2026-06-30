# -*- coding: utf-8 -*-
"""
自动发布服务 - 处理排产确认后的自动任务发布

功能：
    - 监听排产确认事件
    - 根据开关状态决定是否自动发布任务
    - 调用 DesktopContainerIntegration 发布任务到容器池

使用方式：
    from auto_publish_service import AutoPublishService

    service = AutoPublishService()

    # 手动触发发布
    task_id = service.publish_task(order_id=1, production_id=1, process_id=1)
"""

import sys
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.events import EventType, EventData
    from core.event_bus import EventBus
    EVENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"core.events 不可用: {e}")
    EVENT_AVAILABLE = False
    EventType = None
    EventData = None
    EventBus = None


class AutoPublishService:
    """
    自动发布服务

    负责监听排产确认事件，根据配置决定是否自动发布任务到容器池
    """

    def __init__(self, config=None):
        """
        初始化自动发布服务

        Args:
            config: 配置管理器实例，默认为 ModularConfig
        """
        self._config = config
        self._integration = None
        self._init_integration()
        logger.info("[AutoPublish] 自动发布服务初始化完成")

    def _init_integration(self) -> None:
        """
        初始化桌面容器集成
        """
        try:
            # [Q-B6 v3.7.5 迁移 2026-06-25] 改用 dispatch_center.publisher
            from mobile_api_ai.dispatch_center.publisher import get_publisher
            self._integration = get_publisher('report')
            logger.info("[AutoPublish] 容器集成初始化成功")
        except ImportError as e:
            logger.error(f"[AutoPublish] 无法导入 get_publisher: {e}")
            self._integration = None
        except Exception as e:
            logger.error(f"[AutoPublish] 容器集成初始化失败: {e}")
            self._integration = None

    @property
    def config(self):
        """获取配置管理器"""
        if self._config is None:
            from modular_config import ModularConfig
            self._config = ModularConfig()
        return self._config

    @property
    def integration(self):
        """获取容器集成实例"""
        return self._integration

    def is_available(self) -> bool:
        """
        检查服务是否可用

        Returns:
            服务是否可用
        """
        return self._integration is not None and self._integration.is_available

    def is_auto_publish_enabled(self) -> bool:
        """
        检查自动发布开关状态

        Returns:
            自动发布是否开启
        """
        try:
            enabled = self.config.get_auto_publish_enabled()
            logger.debug(f"[AutoPublish] 自动发布开关状态: {enabled}")
            return enabled
        except Exception as e:
            logger.error(f"[AutoPublish] 获取自动发布开关失败: {e}")
            return False

    def should_auto_publish(self, event_type: str) -> bool:
        """
        判断给定事件类型是否应该触发自动发布

        Args:
            event_type: 事件类型

        Returns:
            是否应该自动发布
        """
        if not self.is_auto_publish_enabled():
            return False

        if not self._is_auto_mode():
            return False

        auto_publish_events = [
            EventType.PRODUCTION_CONFIRMED if EVENT_AVAILABLE else 'production:confirmed',
            EventType.PROCESS_COMPLETED if EVENT_AVAILABLE else 'process:completed',
        ]

        return event_type in auto_publish_events

    def _is_auto_mode(self) -> bool:
        """
        检查当前是否为自动模式

        Returns:
            是否为自动模式
        """
        try:
            from publish_mode_manager import get_publish_mode_manager
            mgr = get_publish_mode_manager()
            return mgr.is_auto_mode()
        except ImportError:
            logger.warning("[AutoPublish] PublishModeManager不可用，默认自动模式")
            return True
        except Exception as e:
            logger.warning(f"[AutoPublish] 获取发布模式失败: {e}")
            return True

    def _get_retry_config(self) -> Dict[str, int]:
        """
        获取重试配置

        Returns:
            包含 retry_count 和 retry_interval 的字典
        """
        return {
            'retry_count': self.config.get_config('auto_publish.retry_count', 3),
            'retry_interval': self.config.get_config('auto_publish.retry_interval', 1)
        }

    def _prepare_task_data(self, order_id: int, production_id: int,
                          process_id: int, **kwargs) -> Dict[str, Any]:
        """
        准备任务发布数据

        Args:
            order_id: 订单ID
            production_id: 生产工单ID
            process_id: 工序ID
            **kwargs: 其他参数

        Returns:
            任务数据字典
        """
        task_data = {
            'order_id': order_id,
            'production_id': production_id,
            'process_id': process_id,
        }

        task_data.update(kwargs)

        try:
            from models.order import OrderDAO
            from models.production import ProductionDAO
            from models.process import ProcessDAO

            order = OrderDAO.get_by_id(order_id)
            if order:
                task_data['order_no'] = order.get('order_no', '')
                task_data['customer_name'] = order.get('customer_name', '')

            prod = ProductionDAO.get_by_id(production_id)
            if prod:
                task_data['order_no'] = prod.get('order_no', '')

            process = ProcessDAO.get_by_id(process_id)
            if process:
                task_data['process_name'] = process.get('process_name', '')
                task_data['planned_qty'] = process.get('planned_qty', 0)

        except Exception as e:
            logger.warning(f"[AutoPublish] 获取关联数据失败: {e}")

        return task_data

    def publish_task(self, order_id: int, production_id: int,
                    process_id: int, **kwargs) -> Optional[str]:
        """
        发布任务到容器池

        Args:
            order_id: 订单ID
            production_id: 生产工单ID
            process_id: 工序ID
            **kwargs: 其他参数

        Returns:
            任务ID，失败返回 None
        """
        if not self.is_available():
            logger.warning("[AutoPublish] 服务不可用，跳过发布")
            return None

        task_data = self._prepare_task_data(order_id, production_id, process_id, **kwargs)

        logger.info(f"[AutoPublish] 开始发布任务: {task_data}")

        retry_config = self._get_retry_config()
        task_id = None

        for attempt in range(retry_config['retry_count']):
            try:
                task_id = self._integration.publish_report_task(
                    order_no=task_data.get('order_no', ''),
                    process_name=task_data.get('process_name', ''),
                    customer_name=task_data.get('customer_name', ''),
                    product_type=task_data.get('product_type', ''),
                    quantity=task_data.get('quantity', 0),
                    unit=task_data.get('unit', ''),
                    planned_qty=task_data.get('planned_qty', 0),
                    process_status=task_data.get('process_status', '待开始'),
                    operator_id=task_data.get('operator_id', 'OP001'),
                    operator_name=task_data.get('operator_name', ''),
                    priority=task_data.get('priority', 'normal')
                )

                if task_id:
                    logger.info(f"[AutoPublish] 任务发布成功: {task_id}")
                    self._on_publish_success(task_id, task_data)
                    return task_id
                else:
                    logger.warning(f"[AutoPublish] 第 {attempt + 1} 次尝试发布返回空任务ID")

            except Exception as e:
                logger.error(f"[AutoPublish] 第 {attempt + 1} 次尝试发布失败: {e}")

            if attempt < retry_config['retry_count'] - 1:
                import time
                time.sleep(retry_config['retry_interval'])

        logger.error(f"[AutoPublish] 任务发布失败，已重试 {retry_config['retry_count']} 次")
        self._on_publish_failure(task_data)
        return None

    def _on_publish_success(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """
        发布成功回调

        Args:
            task_id: 任务ID
            task_data: 任务数据
        """
        logger.info(f"[AutoPublish] 发布成功回调: task_id={task_id}")

        if EVENT_AVAILABLE and EventBus:
            try:
                EventBus.publish(EventType.TASK_PUBLISHED, {
                    'task_id': task_id,
                    'task_data': task_data,
                    'source': 'auto_publish'
                })
            except Exception as e:
                logger.warning(f"[AutoPublish] 发布成功事件失败: {e}")

    def _on_publish_failure(self, task_data: Dict[str, Any]) -> None:
        """
        发布失败回调

        Args:
            task_data: 任务数据
        """
        logger.error(f"[AutoPublish] 发布失败回调: {task_data}")

        if EVENT_AVAILABLE and EventBus:
            try:
                EventBus.publish('task:publish_failed', {
                    'task_data': task_data,
                    'source': 'auto_publish'
                })
            except Exception as e:
                logger.warning(f"[AutoPublish] 发布失败事件失败: {e}")

    def handle_production_confirmed(self, event: str, data: dict) -> None:
        """
        处理排产确认事件

        Args:
            event: 事件名称
            data: 事件数据，包含:
                - order_id: 订单ID
                - production_id: 生产工单ID
                - process_id: 工序ID
                - 其他扩展数据
        """
        logger.info(f"[AutoPublish] 收到排产确认事件: {data}")

        if not self.is_auto_publish_enabled():
            logger.info("[AutoPublish] 自动发布开关未开启，跳过发布")
            return

        if not self._is_auto_mode():
            logger.info("[AutoPublish] 当前为手动模式，不自动发布，等待手动触发")
            return

        order_id = data.get('order_id')
        production_id = data.get('production_id')
        process_id = data.get('process_id')

        if not all([order_id, production_id, process_id]):
            logger.error(f"[AutoPublish] 事件数据不完整: {data}")
            return

        task_id = self.publish_task(order_id, production_id, process_id, **data)

        if task_id:
            logger.info(f"[AutoPublish] 自动发布成功: order_id={order_id}, task_id={task_id}")
        else:
            logger.warning(f"[AutoPublish] 自动发布失败: order_id={order_id}")

    def register_event_handler(self) -> bool:
        """
        注册事件处理器

        Returns:
            注册是否成功
        """
        if not EVENT_AVAILABLE or not EventBus:
            logger.warning("[AutoPublish] 事件模块不可用，跳过注册")
            return False

        try:
            event_type = EventType.PRODUCTION_CONFIRMED if EventType else 'production:confirmed'
            EventBus.subscribe(event_type, self.handle_production_confirmed)
            logger.info(f"[AutoPublish] 已注册事件处理器: {event_type}")
            return True
        except Exception as e:
            logger.error(f"[AutoPublish] 注册事件处理器失败: {e}")
            return False

    def unregister_event_handler(self) -> bool:
        """
        取消注册事件处理器

        Returns:
            取消注册是否成功
        """
        if not EVENT_AVAILABLE or not EventBus:
            return False

        try:
            event_type = EventType.PRODUCTION_CONFIRMED if EventType else 'production:confirmed'
            EventBus.unsubscribe(event_type, self.handle_production_confirmed)
            logger.info(f"[AutoPublish] 已取消注册事件处理器: {event_type}")
            return True
        except Exception as e:
            logger.error(f"[AutoPublish] 取消注册事件处理器失败: {e}")
            return False
