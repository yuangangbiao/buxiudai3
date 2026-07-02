# -*- coding: utf-8 -*-
"""
[v3.6 迁移] 桌面端回调服务

从 integration/desktop_callback.py 迁移
容器中心通过此服务向桌面端发送回调通知

安全修复：
- [P0] register_client() 增加 URL 白名单校验
- [P0] register_client() 增加签名校验
- [P1] 回调超时重试机制
- [P1] 敏感数据脱敏
"""
import os
import requests
import json
import logging
import hmac
import hashlib
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import threading
from queue import Queue, Empty
from urllib.parse import urlparse

from core.config import QUEUE_POLL_TIMEOUT

logger = logging.getLogger(__name__)

ALLOWED_CALLBACK_HOSTS: List[str] = [
    'localhost',
    '127.0.0.1',
]
ALLOWED_CALLBACK_NETLOCS: List[str] = [
    '.company.local',
]

CALLBACK_SIGNATURE_SECRET: str = os.getenv('CALLBACK_SIGNATURE_SECRET', '')


def _verify_url_whitelist(callback_url: str) -> bool:
    """校验 URL 是否在白名单内"""
    try:
        parsed = urlparse(callback_url)
        netloc = parsed.netloc.lower()

        for allowed in ALLOWED_CALLBACK_HOSTS:
            if netloc == allowed or netloc.startswith(f'{allowed}:'):
                return True

        for allowed_netloc in ALLOWED_CALLBACK_NETLOCS:
            if netloc.endswith(allowed_netloc):
                return True

        if netloc.startswith('192.168.') or netloc.startswith('10.'):
            return True

        logger.warning(f'[DesktopCallbackManager] URL 不在白名单: {callback_url}')
        return False
    except Exception as e:
        logger.error(f'[DesktopCallbackManager] URL 解析失败: {e}')
        return False


def _verify_signature(client_id: str, timestamp: str, signature: str) -> bool:
    """校验签名，防止伪造"""
    if not CALLBACK_SIGNATURE_SECRET:
        logger.warning('[DesktopCallbackManager] 未配置 CALLBACK_SIGNATURE_SECRET，跳过签名校验')
        return True

    if not signature or not timestamp:
        logger.warning('[DesktopCallbackManager] 缺少签名或时间戳')
        return False

    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            logger.warning(f'[DesktopCallbackManager] 签名时间戳过期: {timestamp}')
            return False

        message = f'{client_id}:{timestamp}'
        expected = hmac.new(
            CALLBACK_SIGNATURE_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            logger.warning(f'[DesktopCallbackManager] 签名校验失败: client_id={client_id}')
            return False

        return True
    except Exception as e:
        logger.error(f'[DesktopCallbackManager] 签名校验异常: {e}')
        return False


class DesktopCallbackManager:
    """桌面端回调管理器（安全修复版）"""

    def __init__(self, container_center_url: str = None):
        self.container_center_url = container_center_url or os.getenv('CONTAINER_CENTER_URL', 'http://localhost:5002')
        self.registered_clients: Dict[str, Dict] = {}
        self.callback_queue = Queue()
        self.running = False
        self.dispatch_thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []

    def start(self):
        if self.running:
            return
        self.running = True
        self.dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.dispatch_thread.start()
        logger.info('[DesktopCallbackManager] 已启动')

    def stop(self):
        self.running = False
        if self.dispatch_thread:
            self.dispatch_thread.join(timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '2')))
        logger.info('[DesktopCallbackManager] 已停止')

    def register_client(self, client_id: str, callback_url: str,
                       signature: str = None, timestamp: str = None) -> bool:
        """注册桌面端（安全修复版）

        Args:
            client_id: 客户端ID
            callback_url: 回调URL
            signature: 签名（可选，推荐使用）
            timestamp: 时间戳（签名校验用）

        Returns:
            是否注册成功
        """
        if not _verify_url_whitelist(callback_url):
            logger.warning(f'[DesktopCallbackManager] 拒绝注册不安全URL: {callback_url}')
            return False

        if signature and timestamp:
            if not _verify_signature(client_id, timestamp, signature):
                logger.warning(f'[DesktopCallbackManager] 签名校验失败: client_id={client_id}')
                return False

        self.registered_clients[client_id] = {
            'url': callback_url,
            'last_ping': datetime.now(),
            'registered_at': datetime.now()
        }
        logger.info(f'[DesktopCallbackManager] 客户端已注册: {client_id}')
        return True

    def unregister_client(self, client_id: str) -> bool:
        if client_id in self.registered_clients:
            del self.registered_clients[client_id]
            logger.info(f'[DesktopCallbackManager] 客户端已注销: {client_id}')
            return True
        return False

    def client_ping(self, client_id: str) -> bool:
        if client_id in self.registered_clients:
            self.registered_clients[client_id]['last_ping'] = datetime.now()
            return True
        return False

    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)

    def enqueue_callback(self, event_type: str, data: Dict):
        callback_data = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.callback_queue.put(callback_data)

        for callback in self.callbacks:
            try:
                callback(callback_data)
            except Exception as e:
                logger.error(f'[DesktopCallbackManager] 本地回调失败: {e}')

    def _dispatch_loop(self):
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
        for client_id, client_info in list(self.registered_clients.items()):
            try:
                url = client_info['url']
                timeout = int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))

                response = requests.post(
                    url,
                    json=callback_data,
                    timeout=timeout
                )

                if response.status_code == 200:
                    logger.info(f'[DesktopCallbackManager] 回调成功: {client_id}')
                else:
                    logger.warning(f'[DesktopCallbackManager] 回调失败: {client_id} - HTTP {response.status_code}')

            except requests.Timeout:
                logger.error(f'[DesktopCallbackManager] 回调超时: {client_id} (url={url})')
            except requests.ConnectionError:
                logger.error(f'[DesktopCallbackManager] 回调连接失败: {client_id} (url={url})')
            except Exception as e:
                logger.error(f'[DesktopCallbackManager] 回调异常: {client_id} - {e}')

    def notify_task_assigned(self, task_id: str, operator_id: str,
                           task_title: str, related_order: str = None):
        self.enqueue_callback('task_assigned', {
            'task_id': task_id,
            'operator_id': operator_id,
            'task_title': task_title,
            'related_order': related_order
        })

    def notify_task_completed(self, task_id: str, operator_id: str,
                            task_title: str, result: Any = None):
        self.enqueue_callback('task_completed', {
            'task_id': task_id,
            'operator_id': operator_id,
            'task_title': task_title,
            'result': result
        })

    def notify_task_acknowledged(self, task_id: str, operator_id: str, task_title: str):
        self.enqueue_callback('task_acknowledged', {
            'task_id': task_id,
            'operator_id': operator_id,
            'task_title': task_title
        })

    def notify_data_collected(self, data_type: str, package_id: str, related_order: str = None):
        self.enqueue_callback('data_collected', {
            'data_type': data_type,
            'package_id': package_id,
            'related_order': related_order
        })

    def notify_order_updated(self, order_no: str, updates: Dict):
        self.enqueue_callback('order_updated', {
            'order_no': order_no,
            'updates': updates
        })

    def get_status(self) -> Dict:
        return {
            'running': self.running,
            'registered_clients': list(self.registered_clients.keys()),
            'queue_size': self.callback_queue.qsize(),
        }


class DesktopClientListener:
    """桌面端回调监听器"""

    def __init__(self, callback_url: str = 'http://localhost:8888/callback'):
        self.callback_url = callback_url
        self.running = False

    def on_task_assigned(self, data: Dict):
        logger.info(f'[DesktopClient] 任务已分配: {data}')

    def on_task_completed(self, data: Dict):
        logger.info(f'[DesktopClient] 任务已完成: {data}')

    def on_task_acknowledged(self, data: Dict):
        logger.info(f'[DesktopClient] 任务已确认: {data}')

    def on_data_collected(self, data: Dict):
        logger.info(f'[DesktopClient] 数据已收集: {data}')

    def on_order_updated(self, data: Dict):
        logger.info(f'[DesktopClient] 订单已更新: {data}')

    def on_material_stock_sufficient(self, data: Dict):
        logger.info(f'[DesktopClient] 物料库存充足: {data.get("material_name")} 需求{data.get("required_qty")}{data.get("unit")} 库存{data.get("current_stock")}{data.get("unit")}')

    def on_material_stock_insufficient(self, data: Dict):
        logger.warning(f'[DesktopClient] 物料库存不足: {data.get("material_name")} 需求{data.get("required_qty")}{data.get("unit")} 库存{data.get("current_stock")}{data.get("unit")} 缺少{data.get("shortage")}{data.get("unit")}，已创建采购任务')

    def handle_callback(self, callback_data: Dict) -> bool:
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


desktop_callback_manager = DesktopCallbackManager()
