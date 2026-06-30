# -*- coding: utf-8 -*-
"""
容器池事件监听器

通过监听系统事件，自动将任务发布到容器池

增强内容：
    - 集成 EventType 事件类型常量
    - 集成 AutoPublishService 自动发布服务
    - 集成 MaterialPublishService 备料发布服务
    - 订阅 PRODUCTION_CONFIRMED 排产确认事件
    - 订阅 MATERIAL_PREPARED 备料完成事件
    - 使用 logger 替代 print

使用方法：
    1. 在主程序启动时初始化：
        from container_event_listener import init_container_listener
        init_container_listener()

    2. 系统会自动监听事件并发布任务
"""
import sys
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.event_bus import EventBus, Events
    from core.events import EventType
    EVENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f'[容器监听器] core.event_bus 不可用: {e}')
    EVENT_AVAILABLE = False
    EventType = None

try:
    from models.order import OrderDAO
    from models.production import ProductionDAO
    from models.process import ProcessDAO
    MODEL_AVAILABLE = True
except ImportError as e:
    logger.warning(f'[容器监听器] models 模块不可用: {e}')
    MODEL_AVAILABLE = False

try:
    # [Q-B6 v3.7.5 迁移 2026-06-25] 改用 dispatch_center.publisher
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    CONTAINER_AVAILABLE = True
except ImportError as e:
    logger.warning(f'[容器监听器] 容器集成不可用: {e}')
    CONTAINER_AVAILABLE = False
    get_publisher = None


class ContainerEventListener:
    """
    容器池事件监听器

    负责监听系统事件并触发相应的容器池操作
    """

    def __init__(self):
        """
        初始化监听器
        """
        self.integration = None
        self._auto_publish_service = None
        self._material_publish_service = None
        self._initialized = False
        self._event_handlers_registered = False

        if CONTAINER_AVAILABLE:
            try:
                self.integration = get_integration()
                if self.integration and self.integration.is_available:
                    self._initialized = True
                    logger.info('[容器监听器] 容器集成初始化成功')
                else:
                    logger.warning('[容器监听器] 容器集成不可用')
            except Exception as e:
                logger.error(f'[容器监听器] 容器集成初始化失败: {e}')

        self._init_services()

    def _init_services(self) -> None:
        """
        初始化服务层
        """
        try:
            from auto_publish_service import AutoPublishService
            self._auto_publish_service = AutoPublishService()
            logger.info('[容器监听器] AutoPublishService 初始化完成')
        except Exception as e:
            logger.warning(f'[容器监听器] AutoPublishService 初始化失败: {e}')

        try:
            from material_publish_service import MaterialPublishService
            self._material_publish_service = MaterialPublishService()
            logger.info('[容器监听器] MaterialPublishService 初始化完成')
        except Exception as e:
            logger.warning(f'[容器监听器] MaterialPublishService 初始化失败: {e}')

    @property
    def is_ready(self) -> bool:
        """
        检查监听器是否就绪

        Returns:
            监听器是否可用
        """
        return self._initialized and self.integration and self.integration.is_available

    @property
    def auto_publish_service(self):
        """获取自动发布服务"""
        return self._auto_publish_service

    @property
    def material_publish_service(self):
        """获取备料发布服务"""
        return self._material_publish_service

    def on_order_created(self, event: str, data: dict) -> None:
        """
        订单创建事件处理

        Args:
            event: 事件名称
            data: 事件数据，包含:
                - order_id: 订单ID
                - order_no: 订单号
                - data: 完整订单数据
        """
        if not self.is_ready:
            logger.warning('[容器监听器] 监听器未就绪，跳过订单创建事件')
            return

        try:
            logger.info(f'[容器监听器] 收到订单创建事件: {data}')

            order_id = data.get('order_id')
            if not order_id:
                logger.warning('[容器监听器] 订单ID为空')
                return

            if not MODEL_AVAILABLE:
                logger.warning('[容器监听器] OrderDAO 不可用')
                return

            order = OrderDAO.get_by_id(order_id)
            if not order:
                logger.warning(f'[容器监听器] 找不到订单: {order_id}')
                return

            logger.info(f'[容器监听器] 订单 {order.get("order_no")} 已创建')

        except Exception as e:
            logger.error(f'[容器监听器] 处理订单创建事件失败: {e}')

    def on_process_created(self, event: str, data: dict) -> None:
        """
        工序创建事件处理

        Args:
            event: 事件名称
            data: 事件数据，包含:
                - order_id: 订单ID
                - production_id: 生产工单ID
                - process_id: 工序ID
                - process_data: 工序数据
        """
        if not self.is_ready:
            logger.warning('[容器监听器] 监听器未就绪，跳过工序创建事件')
            return

        try:
            logger.info(f'[容器监听器] 收到工序创建事件: {data}')

            order_id = data.get('order_id')
            production_id = data.get('production_id')
            process_data = data.get('process_data', {})

            if not all([order_id, production_id]):
                logger.warning(f'[容器监听器] 事件数据不完整: order_id={order_id}, production_id={production_id}')
                return

            if not MODEL_AVAILABLE:
                logger.warning('[容器监听器] OrderDAO 不可用')
                return

            order = OrderDAO.get_by_id(order_id)
            if not order:
                logger.warning(f'[容器监听器] 找不到订单: {order_id}')
                return

            prod = ProductionDAO.get_by_id(production_id)
            if not prod:
                logger.warning(f'[容器监听器] 找不到生产订单: {production_id}')
                return

            task_data = {
                'order_no': order.get('order_no', ''),
                'order_no': prod.get('order_no', ''),
                'process_name': process_data.get('process_name', ''),
                'customer_name': order.get('customer_name', ''),
                'product_type': order.get('product_type', ''),
                'quantity': order.get('quantity', 0),
                'unit': order.get('unit', ''),
                'planned_qty': process_data.get('planned_qty', 0),
                'process_status': '待开始',
                'operator_id': process_data.get('operator_id', 'OP001'),
                'operator_name': process_data.get('worker', ''),
                'priority': 'normal'
            }

            task_id = self.integration.publish_report_task(**task_data)

            if task_id:
                logger.info(f'[容器监听器] 工序任务已发布: {task_id}')

                if process_data.get('process_name') in ['编织', '定型']:
                    logger.info('[容器监听器] 自动发布质检任务')
                    self.integration.publish_quality_task(
                        order_no=order.get('order_no', ''),
                        customer_name=order.get('customer_name', ''),
                        product_type=order.get('product_type', ''),
                        inspection_type='终检',
                        operator_id='OP004',
                        operator_name='质检',
                        priority='high'
                    )
            else:
                logger.warning('[容器监听器] 任务发布失败')

        except Exception as e:
            logger.error(f'[容器监听器] 处理工序创建事件失败: {e}')

    def on_process_completed(self, event: str, data: dict) -> None:
        """
        工序完成事件处理

        Args:
            event: 事件名称
            data: 事件数据
        """
        if not self.is_ready:
            return

        try:
            logger.info(f'[容器监听器] 收到工序完成事件: {data}')

        except Exception as e:
            logger.error(f'[容器监听器] 处理工序完成事件失败: {e}')

    def on_production_confirmed(self, event: str, data: dict) -> None:
        """
        排产确认事件处理

        Args:
            event: 事件名称
            data: 事件数据，包含:
                - order_id: 订单ID
                - production_id: 生产工单ID
                - process_id: 工序ID
                - 其他扩展数据
        """
        logger.info(f'[容器监听器] 收到排产确认事件: {data}')

        if self._auto_publish_service:
            try:
                self._auto_publish_service.handle_production_confirmed(event, data)
            except Exception as e:
                logger.error(f'[容器监听器] AutoPublishService 处理失败: {e}')
        else:
            logger.warning('[容器监听器] AutoPublishService 不可用，尝试直接发布')

            if self.is_ready:
                self._direct_publish_from_production_confirmed(data)
            else:
                logger.warning('[容器监听器] 监听器未就绪，无法发布')

    def _direct_publish_from_production_confirmed(self, data: dict) -> None:
        """
        直接从排产确认事件发布任务（当服务不可用时的备用方案）

        Args:
            data: 事件数据
        """
        try:
            order_id = data.get('order_id')
            production_id = data.get('production_id')
            process_id = data.get('process_id')

            if not all([order_id, production_id, process_id]):
                logger.warning(f'[容器监听器] 事件数据不完整: {data}')
                return

            if not MODEL_AVAILABLE:
                logger.warning('[容器监听器] OrderDAO 不可用')
                return

            order = OrderDAO.get_by_id(order_id)
            prod = ProductionDAO.get_by_id(production_id)
            process = ProcessDAO.get_by_id(process_id)

            if not all([order, prod, process]):
                logger.warning('[容器监听器] 找不到相关数据')
                return

            task_data = {
                'order_no': order.get('order_no', ''),
                'order_no': prod.get('order_no', ''),
                'process_name': process.get('process_name', ''),
                'customer_name': order.get('customer_name', ''),
                'product_type': order.get('product_type', ''),
                'quantity': order.get('quantity', 0),
                'unit': order.get('unit', ''),
                'planned_qty': process.get('planned_qty', 0),
                'process_status': '待开始',
                'operator_id': data.get('operator_id', 'OP001'),
                'operator_name': data.get('operator_name', ''),
                'priority': data.get('priority', 'normal'),
                'is_outsource': bool(process.get('is_outsource', 0))
            }

            task_id = self.integration.publish_report_task(**task_data)

            if task_id:
                logger.info(f'[容器监听器] 排产确认任务发布成功: {task_id}')
            else:
                logger.warning('[容器监听器] 排产确认任务发布失败')

        except Exception as e:
            logger.error(f'[容器监听器] 直接发布失败: {e}')

    def on_material_prepared(self, event: str, data: dict) -> None:
        """
        备料完成事件处理

        Args:
            event: 事件名称
            data: 事件数据，包含:
                - order_id: 订单ID
                - process_id: 工序ID
                - materials: 物料列表（可选）
        """
        logger.info(f'[容器监听器] 收到备料完成事件: {data}')

        if self._material_publish_service:
            try:
                self._material_publish_service.handle_material_prepared(event, data)
            except Exception as e:
                logger.error(f'[容器监听器] MaterialPublishService 处理失败: {e}')
        else:
            logger.warning('[容器监听器] MaterialPublishService 不可用')

    def subscribe_all(self) -> bool:
        """
        订阅所有相关事件

        Returns:
            是否成功
        """
        if not EVENT_AVAILABLE:
            logger.warning('[容器监听器] EventBus 不可用，无法订阅事件')
            return False

        try:
            EventBus.subscribe(Events.ORDER_CREATED, self.on_order_created)
            logger.info('[容器监听器] 已订阅 ORDER_CREATED 事件')

            EventBus.subscribe(Events.PROCESS_COMPLETED, self.on_process_completed)
            logger.info('[容器监听器] 已订阅 PROCESS_COMPLETED 事件')

            if EventType:
                EventBus.subscribe(EventType.PRODUCTION_CONFIRMED, self.on_production_confirmed)
                logger.info(f'[容器监听器] 已订阅 PRODUCTION_CONFIRMED 事件')

                EventBus.subscribe(EventType.MATERIAL_PREPARED, self.on_material_prepared)
                logger.info(f'[容器监听器] 已订阅 MATERIAL_PREPARED 事件')

            EventBus.subscribe('process:created', self.on_process_created)
            logger.info('[容器监听器] 已订阅 process:created 事件')

            self._event_handlers_registered = True
            logger.info('[容器监听器] 已订阅所有事件')
            return True

        except Exception as e:
            logger.error(f'[容器监听器] 订阅事件失败: {e}')
            return False

    def unsubscribe_all(self) -> bool:
        """
        取消订阅所有事件

        Returns:
            是否成功
        """
        if not EVENT_AVAILABLE:
            return False

        try:
            EventBus.unsubscribe(Events.ORDER_CREATED, self.on_order_created)
            EventBus.unsubscribe(Events.PROCESS_COMPLETED, self.on_process_completed)
            EventBus.unsubscribe('process:created', self.on_process_created)

            if EventType:
                EventBus.unsubscribe(EventType.PRODUCTION_CONFIRMED, self.on_production_confirmed)
                EventBus.unsubscribe(EventType.MATERIAL_PREPARED, self.on_material_prepared)

            self._event_handlers_registered = False
            logger.info('[容器监听器] 已取消所有事件订阅')
            return True

        except Exception as e:
            logger.error(f'[容器监听器] 取消订阅失败: {e}')
            return False

    def show_status(self) -> None:
        """
        显示监听器状态
        """
        print(f'''
=====================================
容器池事件监听器状态
=====================================
监听器就绪: {self.is_ready}
事件处理注册: {self._event_handlers_registered}
AutoPublishService: {'可用' if self._auto_publish_service else '不可用'}
MaterialPublishService: {'可用' if self._material_publish_service else '不可用'}
容器集成: {'可用' if (self.integration and self.integration.is_available) else '不可用'}
=====================================
''')


_listener_instance: Optional['ContainerEventListener'] = None


def init_container_listener() -> 'ContainerEventListener':
    """
    初始化容器监听器（在主程序启动时调用）

    Returns:
        监听器实例
    """
    global _listener_instance

    if _listener_instance is None:
        _listener_instance = ContainerEventListener()
        _listener_instance.subscribe_all()
        logger.info('[容器监听器] 全局监听器已初始化')
    else:
        logger.info('[容器监听器] 全局监听器已存在')

    return _listener_instance


def get_container_listener() -> Optional['ContainerEventListener']:
    """
    获取全局监听器实例

    Returns:
        监听器实例，如果未初始化返回 None
    """
    return _listener_instance


def publish_process_created_event(order_id: int, production_id: int,
                                  process_id: int, process_data: dict) -> None:
    """
    发布工序创建事件（在工序视图中调用）

    Args:
        order_id: 订单ID
        production_id: 生产工单ID
        process_id: 工序ID
        process_data: 工序数据
    """
    if not EVENT_AVAILABLE:
        logger.warning('[容器事件] EventBus 不可用')
        return

    event_data = {
        'order_id': order_id,
        'production_id': production_id,
        'process_id': process_id,
        'process_data': process_data
    }

    EventBus.publish('process:created', event_data)
    logger.info(f'[容器事件] 已发布工序创建事件: order_id={order_id}')


def publish_production_confirmed_event(order_id: int, production_id: int,
                                       process_id: int, **kwargs) -> None:
    """
    发布排产确认事件

    Args:
        order_id: 订单ID
        production_id: 生产工单ID
        process_id: 工序ID
        **kwargs: 其他扩展数据
    """
    if not EVENT_AVAILABLE:
        logger.warning('[容器事件] EventBus 不可用')
        return

    event_type = EventType.PRODUCTION_CONFIRMED if EventType else 'production:confirmed'

    event_data = {
        'order_id': order_id,
        'production_id': production_id,
        'process_id': process_id,
        **kwargs
    }

    EventBus.publish(event_type, event_data)
    logger.info(f'[容器事件] 已发布排产确认事件: order_id={order_id}')


def publish_material_prepared_event(order_id: int, process_id: int,
                                    materials: list = None) -> None:
    """
    发布备料完成事件

    Args:
        order_id: 订单ID
        process_id: 工序ID
        materials: 物料列表（可选）
    """
    if not EVENT_AVAILABLE:
        logger.warning('[容器事件] EventBus 不可用')
        return

    event_type = EventType.MATERIAL_PREPARED if EventType else 'material:prepared'

    event_data = {
        'order_id': order_id,
        'process_id': process_id,
        'materials': materials or []
    }

    EventBus.publish(event_type, event_data)
    logger.info(f'[容器事件] 已发布备料完成事件: order_id={order_id}')


if __name__ == '__main__':
    print('=' * 60)
    print('容器池事件监听器测试')
    print('=' * 60)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    listener = init_container_listener()

    if listener.is_ready:
        print('\n[OK] 监听器初始化成功')
        listener.show_status()
    else:
        print('\n[WARN] 监听器不可用')

    print('\n' + '=' * 60)
    print('测试完成')
    print('=' * 60)
