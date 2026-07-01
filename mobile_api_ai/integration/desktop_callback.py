# -*- coding: utf-8 -*-
"""
桌面端回调服务
容器中心通过此服务向桌面端发送回调通知
"""
import os
import requests
import json
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import threading
import time
from queue import Queue, Empty

from core.config import QUEUE_POLL_TIMEOUT

logger = logging.getLogger(__name__)


class DesktopCallbackManager:
    """
    桌面端回调管理器
    管理桌面端注册和回调分发
    """

    def __init__(self, container_center_url: str = None):
        self.container_center_url = container_center_url or os.getenv('CONTAINER_CENTER_URL', 'http://localhost:5002')
        self.registered_clients: Dict[str, Dict] = {}  # client_id -> {url, last_ping}
        self.callback_queue = Queue()
        self.running = False
        self.dispatch_thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []

    def start(self):
        """启动回调管理器"""
        if self.running:
            return
        self.running = True
        self.dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.dispatch_thread.start()
        logger.info('[DesktopCallbackManager] 已启动')

    def stop(self):
        """停止回调管理器"""
        self.running = False
        if self.dispatch_thread:
            self.dispatch_thread.join(timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '2')))
        logger.info('[DesktopCallbackManager] 已停止')

    def register_client(self, client_id: str, callback_url: str) -> bool:
        """
        注册桌面端

        Args:
            client_id: 客户端ID
            callback_url: 回调URL

        Returns:
            是否注册成功
        """
        self.registered_clients[client_id] = {
            'url': callback_url,
            'last_ping': datetime.now(),
            'registered_at': datetime.now()
        }
        logger.info(f'[DesktopCallbackManager] 客户端已注册: {client_id} -> {callback_url}')
        return True

    def unregister_client(self, client_id: str) -> bool:
        """
        注销桌面端

        Args:
            client_id: 客户端ID

        Returns:
            是否注销成功
        """
        if client_id in self.registered_clients:
            del self.registered_clients[client_id]
            logger.info(f'[DesktopCallbackManager] 客户端已注销: {client_id}')
            return True
        return False

    def client_ping(self, client_id: str) -> bool:
        """
        客户端心跳

        Args:
            client_id: 客户端ID

        Returns:
            是否成功
        """
        if client_id in self.registered_clients:
            self.registered_clients[client_id]['last_ping'] = datetime.now()
            return True
        return False

    def add_callback(self, callback: Callable):
        """添加回调函数"""
        self.callbacks.append(callback)

    def enqueue_callback(self, event_type: str, data: Dict):
        """
        将回调加入队列

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        callback_data = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.callback_queue.put(callback_data)

        # 调用本地回调
        for callback in self.callbacks:
            try:
                callback(callback_data)
            except Exception as e:
                logger.error(f'[DesktopCallbackManager] 本地回调失败: {e}')

    def _dispatch_loop(self):
        """分发循环"""
        while self.running:
            try:
                try:
                    callback_data = self.callback_queue.get(timeout=QUEUE_POLL_TIMEOUT)
                    self._dispatch_to_clients(callback_data)
                except Empty:
                    continue
            except Exception as e:
                logger.error(f'[DesktopCallbackManager] 分发异常: {e}')

    def _dispatch_to_clients(self, callback_data: Dict):
        """
        分发回调到所有注册的客户端

        Args:
            callback_data: 回调数据
        """
        for client_id, client_info in list(self.registered_clients.items()):
            try:
                url = client_info['url']
                response = requests.post(
                    url,
                    json=callback_data,
                    timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))
                )
                if response.status_code == 200:
                    logger.info(f'[DesktopCallbackManager] 回调成功: {client_id}')
                else:
                    logger.warning(f'[DesktopCallbackManager] 回调失败: {client_id} - {response.status_code}')
            except Exception as e:
                logger.error(f'[DesktopCallbackManager] 回调异常: {client_id} - {e}')

    def notify_task_assigned(self, task_id: str, operator_id: str,
                           task_title: str, related_order: str = None):
        """
        通知任务已分配

        Args:
            task_id: 任务ID
            operator_id: 操作员ID
            task_title: 任务标题
            related_order: 关联订单
        """
        self.enqueue_callback('task_assigned', {
            'task_id': task_id,
            'operator_id': operator_id,
            'task_title': task_title,
            'related_order': related_order
        })

    def notify_task_completed(self, task_id: str, operator_id: str,
                            task_title: str, result: Any = None):
        """
        通知任务已完成

        Args:
            task_id: 任务ID
            operator_id: 操作员ID
            task_title: 任务标题
            result: 结果
        """
        self.enqueue_callback('task_completed', {
            'task_id': task_id,
            'operator_id': operator_id,
            'task_title': task_title,
            'result': result
        })

    def notify_task_acknowledged(self, task_id: str, operator_id: str,
                                task_title: str):
        """
        通知任务已确认

        Args:
            task_id: 任务ID
            operator_id: 操作员ID
            task_title: 任务标题
        """
        self.enqueue_callback('task_acknowledged', {
            'task_id': task_id,
            'operator_id': operator_id,
            'task_title': task_title
        })

    def notify_data_collected(self, data_type: str, package_id: str,
                            related_order: str = None):
        """
        通知数据已收集

        Args:
            data_type: 数据类型
            package_id: 包ID
            related_order: 关联订单
        """
        self.enqueue_callback('data_collected', {
            'data_type': data_type,
            'package_id': package_id,
            'related_order': related_order
        })

    def notify_order_updated(self, order_no: str, updates: Dict):
        """
        通知订单已更新

        Args:
            order_no: 订单号
            updates: 更新内容
        """
        self.enqueue_callback('order_updated', {
            'order_no': order_no,
            'updates': updates
        })

    def get_status(self) -> Dict:
        """
        获取管理器状态

        Returns:
            状态字典
        """
        return {
            'running': self.running,
            'registered_clients': list(self.registered_clients.keys()),
            'queue_size': self.callback_queue.qsize(),
            'clients': {
                cid: {
                    'url': info['url'],
                    'last_ping': info['last_ping'].isoformat(),
                    'registered_at': info['registered_at'].isoformat()
                }
                for cid, info in self.registered_clients.items()
            }
        }


class DesktopClientListener:
    """
    桌面端回调监听器
    桌面端可以继承此类来监听回调
    """

    def __init__(self, callback_url: str = 'http://localhost:8888/callback'):
        self.callback_url = callback_url
        self.running = False

    def on_task_assigned(self, data: Dict):
        """任务分配回调"""
        logger.info(f'[DesktopClient] 任务已分配: {data}')

    def on_task_completed(self, data: Dict):
        """任务完成回调"""
        logger.info(f'[DesktopClient] 任务已完成: {data}')

    def on_task_acknowledged(self, data: Dict):
        """任务确认回调"""
        logger.info(f'[DesktopClient] 任务已确认: {data}')

    def on_data_collected(self, data: Dict):
        """数据收集回调"""
        logger.info(f'[DesktopClient] 数据已收集: {data}')

    def on_order_updated(self, data: Dict):
        """订单更新回调"""
        logger.info(f'[DesktopClient] 订单已更新: {data}')

    def on_material_stock_sufficient(self, data: Dict):
        """
        物料库存充足回调

        Args:
            data: {
                'package_id': str,
                'order_no': str,
                'material_name': str,
                'required_qty': float,
                'current_stock': float,
                'unit': str
            }
        """
        logger.info(f'[DesktopClient] 物料库存充足: {data.get("material_name")} 需求{data.get("required_qty")}{data.get("unit")} 库存{data.get("current_stock")}{data.get("unit")}')

    def on_material_stock_insufficient(self, data: Dict):
        """
        物料库存不足回调

        Args:
            data: {
                'package_id': str,
                'order_no': str,
                'material_name': str,
                'required_qty': float,
                'current_stock': float,
                'shortage': float,
                'unit': str
            }
        """
        logger.warning(f'[DesktopClient] 物料库存不足: {data.get("material_name")} 需求{data.get("required_qty")}{data.get("unit")} 库存{data.get("current_stock")}{data.get("unit")} 缺少{data.get("shortage")}{data.get("unit")}，已创建采购任务')

    def handle_callback(self, callback_data: Dict) -> bool:
        """
        处理回调

        Args:
            callback_data: 回调数据

        Returns:
            是否处理成功
        """
        event_type = callback_data.get('event_type')

        handlers = {
            'task_assigned': self.on_task_assigned,
            'task_completed': self.on_task_completed,
            'task_acknowledged': self.on_task_acknowledged,
            'data_collected': self.on_data_collected,
            'order_updated': self.on_order_updated,
            'material_stock_sufficient': self.on_material_stock_sufficient,
            'material_stock_insufficient': self.on_material_stock_insufficient
        }

        handler = handlers.get(event_type)
        if handler:
            try:
                handler(callback_data.get('data', {}))
                return True
            except Exception as e:
                logger.error(f'[DesktopClient] 回调处理失败: {e}')
                return False

        return False


# 全局实例
desktop_callback_manager = DesktopCallbackManager()
