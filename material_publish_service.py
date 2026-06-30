# -*- coding: utf-8 -*-
"""
备料发布服务 - 处理材料备料完成后的用料需求发布

功能：
    - 收集已勾选的备料项
    - 发布用料需求到容器池
    - 管理备料勾选状态

使用方式：
    from material_publish_service import MaterialPublishService

    service = MaterialPublishService()

    # 发布用料需求
    result = service.publish_requirements(order_id=1, process_id=1)

    # 获取已备料物料
    materials = service.get_prepared_materials(order_id=1, process_id=1)
"""

import sys
import os
import json
import logging
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from datetime import datetime

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


class MaterialPublishService:
    """
    备料发布服务

    负责管理备料勾选状态，收集已勾选备料项并发布用料需求到容器池
    """

    def __init__(self, config=None):
        """
        初始化备料发布服务

        Args:
            config: 配置管理器实例，默认为 ModularConfig
        """
        self._config = config
        self._integration = None
        self._init_integration()
        logger.info("[MaterialPublish] 备料发布服务初始化完成")

    def _init_integration(self) -> None:
        """
        初始化桌面容器集成
        """
        try:
            # [Q-B6 v3.7.5 迁移 2026-06-25] 改用 dispatch_center.publisher
            from mobile_api_ai.dispatch_center.publisher import get_publisher
            self._integration = get_publisher('material')
            logger.info("[MaterialPublish] 容器集成初始化成功")
        except ImportError as e:
            logger.error(f"[MaterialPublish] 无法导入 get_publisher: {e}")
            self._integration = None
        except Exception as e:
            logger.error(f"[MaterialPublish] 容器集成初始化失败: {e}")
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

    def is_enabled(self) -> bool:
        """
        检查备料发布功能是否开启

        Returns:
            备料发布是否开启
        """
        try:
            enabled = self.config.get_material_publish_enabled()
            logger.debug(f"[MaterialPublish] 备料发布开关状态: {enabled}")
            return enabled
        except Exception as e:
            logger.error(f"[MaterialPublish] 获取备料发布开关失败: {e}")
            return True

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
            logger.warning("[MaterialPublish] PublishModeManager不可用，默认自动模式")
            return True
        except Exception as e:
            logger.warning(f"[MaterialPublish] 获取发布模式失败: {e}")
            return True

    def get_db_cursor(self):
        """
        获取数据库cursor

        Returns:
            数据库cursor和连接
        """
        try:
            from models.database import get_db_cursor as original_get_cursor
            return original_get_cursor()
        except ImportError:
            logger.warning("[MaterialPublish] 无法导入 get_db_cursor，使用备用方案")

        try:
            import sqlite3
            db_path = self._get_db_path()
            conn = sqlite3.connect(db_path)
            return conn.cursor(), conn
        except Exception as e:
            logger.error(f"[MaterialPublish] 数据库连接失败: {e}")
            raise

    def _get_db_path(self) -> str:
        """
        获取数据库路径

        Returns:
            数据库文件路径
        """
        env_path = os.getenv('CONTAINER_DB_PATH', '').strip()
        if env_path:
            return os.path.abspath(env_path)

        try:
            from modular_config import ModularConfig
            db_path = ModularConfig.get_container_db_path()
            return db_path
        except Exception:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_dir, 'mobile_api_ai', 'wechat_container.db')

    def get_prepared_materials(self, order_id: int,
                               process_id: int) -> List[Dict[str, Any]]:
        """
        获取已备料物料列表

        Args:
            order_id: 订单ID
            process_id: 工序ID

        Returns:
            备料物料列表
        """
        materials = []

        try:
            from models.database import get_db_cursor

            with get_db_cursor() as (cursor, conn):
                cursor.execute("""
                    SELECT id, material_name, required_qty, prepared_qty,
                           unit, is_selected, published, created_at
                    FROM production_material
                    WHERE order_id = %s AND process_id = %s
                    ORDER BY created_at DESC
                """, (order_id, process_id))

                rows = cursor.fetchall()
                columns = ['id', 'material_name', 'required_qty', 'prepared_qty',
                          'unit', 'is_selected', 'published', 'created_at']

                for row in rows:
                    material = dict(zip(columns, row))
                    materials.append(material)

        except Exception as e:
            logger.warning(f"[MaterialPublish] 从主数据库获取备料失败: {e}")

            try:
                import sqlite3
                db_path = self._get_db_path()
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, material_name, required_qty, prepared_qty,
                           unit, is_selected, published, created_at
                    FROM production_material
                    WHERE order_id = ? AND process_id = ?
                    ORDER BY created_at DESC
                """, (order_id, process_id))

                rows = cursor.fetchall()
                columns = ['id', 'material_name', 'required_qty', 'prepared_qty',
                          'unit', 'is_selected', 'published', 'created_at']

                for row in rows:
                    material = dict(zip(columns, row))
                    materials.append(material)

                conn.close()

            except Exception as e2:
                logger.error(f"[MaterialPublish] 从容器数据库获取备料也失败: {e2}")

        logger.info(f"[MaterialPublish] 获取备料物料: order_id={order_id}, count={len(materials)}")
        return materials

    def get_selected_materials(self, order_id: int,
                               process_id: int) -> List[Dict[str, Any]]:
        """
        获取已勾选的备料物料列表

        Args:
            order_id: 订单ID
            process_id: 工序ID

        Returns:
            已勾选的备料物料列表
        """
        all_materials = self.get_prepared_materials(order_id, process_id)
        selected = [m for m in all_materials if m.get('is_selected') == 1 or m.get('is_selected') == True]
        logger.debug(f"[MaterialPublish] 已勾选物料数: {len(selected)}")
        return selected

    def mark_material_selected(self, material_id: int, selected: bool) -> bool:
        """
        标记物料勾选状态

        Args:
            material_id: 物料记录ID
            selected: 是否勾选

        Returns:
            操作是否成功
        """
        try:
            from models.database import get_db_cursor

            with get_db_cursor() as (cursor, conn):
                cursor.execute("""
                    UPDATE production_material
                    SET is_selected = %s
                    WHERE id = %s
                """, (1 if selected else 0, material_id))

            logger.info(f"[MaterialPublish] 物料勾选状态已更新: id={material_id}, selected={selected}")
            return True

        except Exception as e:
            logger.error(f"[MaterialPublish] 更新物料勾选状态失败: {e}")
            return False

    def mark_materials_published(self, order_id: int, process_id: int) -> bool:
        """
        标记物料已发布状态

        Args:
            order_id: 订单ID
            process_id: 工序ID

        Returns:
            操作是否成功
        """
        try:
            from models.database import get_db_cursor

            with get_db_cursor() as (cursor, conn):
                cursor.execute("""
                    UPDATE production_material
                    SET published = 1, published_at = %s
                    WHERE order_id = %s AND process_id = %s AND is_selected = 1
                """, (datetime.now(), order_id, process_id))

            logger.info(f"[MaterialPublish] 物料已发布状态已更新: order_id={order_id}, process_id={process_id}")
            return True

        except Exception as e:
            logger.error(f"[MaterialPublish] 更新物料发布状态失败: {e}")
            return False

    def _prepare_order_info(self, order_id: int, process_id: int) -> Dict[str, Any]:
        """
        准备订单信息

        Args:
            order_id: 订单ID
            process_id: 工序ID

        Returns:
            订单信息字典
        """
        info = {
            'order_id': order_id,
            'process_id': process_id,
            'order_no': '',
            'order_no': '',
            'process_name': '',
        }

        try:
            from models.order import OrderDAO
            order = OrderDAO.get_by_id(order_id)
            if order:
                info['order_no'] = order.get('order_no', '')
                info['customer_name'] = order.get('customer_name', '')

            from models.production import ProductionDAO
            prod = ProductionDAO.get_production_by_order(order_id)
            if prod:
                info['order_no'] = prod.get('order_no', '')

            from models.process import ProcessDAO
            process = ProcessDAO.get_by_id(process_id)
            if process:
                info['process_name'] = process.get('process_name', '')

        except Exception as e:
            logger.warning(f"[MaterialPublish] 获取订单信息失败: {e}")

        return info

    def _prepare_material_content(self, materials: List[Dict],
                                  order_info: Dict) -> List[Dict[str, Any]]:
        """
        准备物料内容

        Args:
            materials: 物料列表
            order_info: 订单信息

        Returns:
            格式化的物料内容列表
        """
        content = []

        for m in materials:
            item = {
                'material_id': m.get('id'),
                'material_name': m.get('material_name', ''),
                'spec': m.get('spec', m.get('specification', '')),
                'required_qty': m.get('required_qty', 0),
                'prepared_qty': m.get('prepared_qty', 0),
                'unit': m.get('unit', ''),
                'status': '已备料' if m.get('prepared_qty', 0) >= m.get('required_qty', 0) else '备料中'
            }
            content.append(item)

        return content

    def publish_requirements(self, order_id: int,
                             process_id: int) -> Dict[str, Any]:
        """
        发布用料需求到容器池

        Args:
            order_id: 订单ID
            process_id: 工序ID

        Returns:
            包含发布结果的字典:
                - success: 是否成功
                - message: 结果消息
                - count: 发布的物料数量
                - task_id: 任务ID（如果成功）
        """
        if not self.is_available():
            logger.warning("[MaterialPublish] 服务不可用，跳过发布")
            return {
                'success': False,
                'message': '服务不可用',
                'count': 0,
                'task_id': None
            }

        selected_materials = self.get_selected_materials(order_id, process_id)

        if not selected_materials:
            logger.info("[MaterialPublish] 没有已勾选的备料项")
            return {
                'success': False,
                'message': '没有已勾选的备料项',
                'count': 0,
                'task_id': None
            }

        order_info = self._prepare_order_info(order_id, process_id)
        material_content = self._prepare_material_content(selected_materials, order_info)

        logger.info(f"[MaterialPublish] 开始发布用料需求: order_no={order_info['order_no']}, count={len(selected_materials)}")

        try:
            task_id = self._integration.publish_material_task(
                order_no=order_info.get('order_no', ''),
                process_name=order_info.get('process_name', ''),
                materials=material_content,
                order_id=order_id,
                process_id=process_id,
                customer_name=order_info.get('customer_name', ''),
                priority=self.config.get_config('material_publish.default_priority', 'normal')
            )

            if task_id:
                self.mark_materials_published(order_id, process_id)

                logger.info(f"[MaterialPublish] 用料需求发布成功: task_id={task_id}")

                self._on_publish_success(task_id, order_id, process_id, selected_materials)

                self._push_to_dispatch_center(order_info, material_content)

                return {
                    'success': True,
                    'message': f'已发布 {len(selected_materials)} 项用料需求',
                    'count': len(selected_materials),
                    'task_id': task_id
                }
            else:
                logger.warning("[MaterialPublish] 用料需求发布返回空任务ID")
                return {
                    'success': False,
                    'message': '发布失败：未获取到任务ID',
                    'count': len(selected_materials),
                    'task_id': None
                }

        except Exception as e:
            logger.error(f"[MaterialPublish] 发布用料需求异常: {e}")
            return {
                'success': False,
                'message': f'发布异常: {str(e)}',
                'count': len(selected_materials),
                'task_id': None
            }

    def _on_publish_success(self, task_id: str, order_id: int,
                           process_id: int, materials: List[Dict]) -> None:
        """
        发布成功回调

        Args:
            task_id: 任务ID
            order_id: 订单ID
            process_id: 工序ID
            materials: 物料列表
        """
        logger.info(f"[MaterialPublish] 发布成功回调: task_id={task_id}")

        if EVENT_AVAILABLE and EventBus:
            try:
                EventBus.publish(EventType.MATERIAL_PUBLISHED, {
                    'task_id': task_id,
                    'order_id': order_id,
                    'process_id': process_id,
                    'materials': materials,
                    'source': 'material_publish'
                })
            except Exception as e:
                logger.warning(f"[MaterialPublish] 发布成功事件失败: {e}")

    def _push_to_dispatch_center(self, order_info: Dict[str, Any],
                                  material_content: List[Dict[str, Any]]) -> None:
        """
        将物料需求推送至调度中心

        Args:
            order_info: 订单信息（含 order_no）
            material_content: 物料内容列表
        """
        dispatch_url = os.environ.get(
            'DISPATCH_CENTER_URL',
            'http://127.0.0.1:5003'
        )
        api_url = f'{dispatch_url}/api/dispatch-center/material/requirements'
        order_no = order_info.get('order_no', '')

        for item in material_content:
            payload = {
                'order_no': order_no,
                'material_id': str(item.get('material_id', '')),
                'material_name': item.get('material_name', ''),
                'spec': item.get('spec', ''),
                'required_qty': float(item.get('required_qty', 0)),
                'prepared_qty': float(item.get('prepared_qty', 0)),
                'unit': item.get('unit', '件'),
                'status': item.get('status', 'pending'),
                'source': 'main_publish',
            }
            try:
                data_bytes = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    api_url,
                    data=data_bytes,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                resp = urllib.request.urlopen(req, timeout=10)
                result = json.loads(resp.read().decode('utf-8'))
                if result.get('code') == 0:
                    logger.info(f"[MaterialPublish] 已推送物料需求到调度中心: {item.get('material_name')}")
                else:
                    logger.warning(f"[MaterialPublish] 调度中心返回异常: {result}")
            except Exception as e:
                logger.warning(f"[MaterialPublish] 推送物料需求到调度中心失败: {e}")

    def handle_material_prepared(self, event: str, data: dict) -> None:
        """
        处理备料完成事件

        Args:
            event: 事件名称
            data: 事件数据，包含:
                - order_id: 订单ID
                - process_id: 工序ID
                - materials: 物料列表（可选）
        """
        logger.info(f"[MaterialPublish] 收到备料完成事件: {data}")

        if not self.is_enabled():
            logger.info("[MaterialPublish] 备料发布功能未开启，跳过")
            return

        if not self._is_auto_mode():
            logger.info("[MaterialPublish] 当前为手动模式，不自动发布用料需求，等待手动触发")
            return

        order_id = data.get('order_id')
        process_id = data.get('process_id')

        if not all([order_id, process_id]):
            logger.error(f"[MaterialPublish] 事件数据不完整: {data}")
            return

        result = self.publish_requirements(order_id, process_id)

        logger.info(f"[MaterialPublish] 备料发布结果: {result}")

    def register_event_handler(self) -> bool:
        """
        注册事件处理器

        Returns:
            注册是否成功
        """
        if not EVENT_AVAILABLE or not EventBus:
            logger.warning("[MaterialPublish] 事件模块不可用，跳过注册")
            return False

        try:
            event_type = EventType.MATERIAL_PREPARED if EventType else 'material:prepared'
            EventBus.subscribe(event_type, self.handle_material_prepared)
            logger.info(f"[MaterialPublish] 已注册事件处理器: {event_type}")
            return True
        except Exception as e:
            logger.error(f"[MaterialPublish] 注册事件处理器失败: {e}")
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
            event_type = EventType.MATERIAL_PREPARED if EventType else 'material:prepared'
            EventBus.unsubscribe(event_type, self.handle_material_prepared)
            logger.info(f"[MaterialPublish] 已取消注册事件处理器: {event_type}")
            return True
        except Exception as e:
            logger.error(f"[MaterialPublish] 取消注册事件处理器失败: {e}")
            return False
