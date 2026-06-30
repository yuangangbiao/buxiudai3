# -*- coding: utf-8 -*-
"""
生产与库存系统联通服务
当订单物料备齐后，自动通知库存系统

[历史遗留声明 2026-06-09]
本文件内容来源于归档目录 _archive/services/inventory_notifier.py（9079 字节），
2026-06-09 因主项目原 9591 字节版本损坏且无 git 备份，由用户决策接受归档版本为现实。
详细违规记录见 d:\\yuan\\归档备份\\违规记录_inventory_notifier_2026-06-09.md

⚠️ 物理上与 _archive 同名文件相同，但已被主项目接管。
⚠️ 后续修改不得反向同步回 _archive 目录，归档目录永久冻结。
"""
import json
import logging
import threading
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from db_config import INVENTORY_SYSTEM_CONFIG

# P0-3: 可注入的 HTTP 客户端（测试时可替换为 mock）
_http_factory = None


def set_http_factory(factory):
    """注入自定义 HTTP 客户端工厂。传入 None 恢复默认 urlopen。"""
    global _http_factory
    _http_factory = factory


def _do_http_request(req, timeout):
    """执行 HTTP 请求。优先使用注入的工厂。"""
    if _http_factory:
        return _http_factory(req, timeout)
    from urllib.request import urlopen
    return urlopen(req, timeout=timeout)

# QA-015: 熔断器集成
try:
    from core.circuit_breaker import CircuitBreaker
    _cb = CircuitBreaker('inventory_notifier', failure_threshold=3, timeout=30)
except ImportError:
    _cb = None

logger = logging.getLogger("inventory_notifier")


class InventoryNotifier:
    """库存系统通知器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._enabled = False
                    cls._instance._config = None
        return cls._instance

    def init(self, config=None):
        """初始化通知器配置"""
        if config is None:
            config = INVENTORY_SYSTEM_CONFIG
        self._config = config
        self._enabled = config.get("enabled", False)
        logger.info(f"库存通知器初始化: enabled={self._enabled}, host={config.get('host')}")

    def _make_request(self, endpoint, method="GET", data=None):
        """发送HTTP请求到库存系统"""
        if not self._enabled or not self._config:
            return None

        base_url = f"http://{self._config['host']}:{self._config['port']}"
        url = f"{base_url}{endpoint}"
        timeout = self._config.get("timeout", 10)
        api_key = self._config.get("api_key", "")

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }

        try:
            if method == "GET":
                req = Request(url, headers=headers)
            else:
                req = Request(url, data=json.dumps(data).encode("utf-8"),
                             headers=headers, method=method)

            with _do_http_request(req, timeout) as response:
                result = response.read().decode("utf-8")
                logger.info(f"库存系统响应: {endpoint} -> {response.status}")
                return json.loads(result) if result else {"status": "ok"}

        except HTTPError as e:
            logger.warning(
                f"库存系统HTTP错误: {endpoint} -> {e.code} {e.reason}",
                extra={"endpoint": endpoint, "http_status": e.code}
            )
            return {"error": f"HTTP {e.code}", "message": e.reason}
        except URLError as e:
            logger.warning(
                f"库存系统连接失败: {endpoint} -> {e.reason}",
                extra={"endpoint": endpoint, "error_type": "connection_failed"}
            )
            return {"error": "connection_failed", "message": str(e.reason)}
        except Exception as e:
            logger.error(
                f"库存系统请求异常: {endpoint} -> {e}",
                extra={"endpoint": endpoint, "error_type": "unknown"}
            )
            return {"error": "unknown", "message": str(e)}

    def notify_material_prepared(self, order_no, customer_name, materials, deadline=None):
        """
        通知库存系统：订单物料已备齐，需要出库

        参数:
            order_no: 订单号
            customer_name: 客户名称
            materials: 物料列表 [{"name": "不锈钢网带", "spec": "304", "qty": 100, "unit": "米"}, ...]
            deadline: 需求期限（可选）

        返回:
            通知结果字典
        """
        if not self._enabled:
            logger.debug("库存通知已禁用，跳过通知")
            return {"status": "disabled"}

        payload = {
            "source_system": "steel_belt_tracking",
            "event_type": "material_prepared",
            "order_no": order_no,
            "customer_name": customer_name,
            "materials": materials,
            "deadline": deadline,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"发送物料备齐通知: 订单={order_no}, 物料数={len(materials)}")
        return self._make_request("/api/material-demand", method="POST", data=payload)

    def notify_order_started(self, order_no, customer_name, materials, delivery_date):
        """
        通知库存系统：订单已开工，物料需求确认

        参数:
            order_no: 订单号
            customer_name: 客户名称
            materials: 物料列表
            delivery_date: 交货日期
        """
        if not self._enabled:
            return {"status": "disabled"}

        payload = {
            "source_system": "steel_belt_tracking",
            "event_type": "order_started",
            "order_no": order_no,
            "customer_name": customer_name,
            "materials": materials,
            "delivery_date": delivery_date,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"发送订单开工通知: 订单={order_no}")
        return self._make_request("/api/material-demand", method="POST", data=payload)

    def check_connection(self):
        """检查与库存系统的连接状态"""
        result = self._make_request("/api/health", method="GET")
        if result and "error" not in result:
            return True, "连接正常"
        return False, result.get("message", "连接失败") if result else "连接失败"

    def wait_for_response(self, notification_id, timeout=30, poll_interval=2):
        """
        轮询等待库存系统的响应结果

        参数:
            notification_id: 通知ID
            timeout: 超时时间（秒），默认300秒（5分钟）
            poll_interval: 轮询间隔（秒），默认2秒

        返回:
            响应结果字典，包含:
            - status: confirmed/rejected/partial_confirmed/pending/timeout
            - inventory_check: 库存检查详情列表
            - summary: 汇总信息
        """
        if not self._enabled:
            return {"status": "disabled"}

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            result = self._make_request(f"/api/response/{notification_id}", method="GET")

            if result and "error" not in result:
                status = result.get("status")
                if status != "pending":
                    logger.info(f"收到库存响应: notification_id={notification_id}, status={status}")
                    return result

            time.sleep(poll_interval)

        logger.warning(
            f"等待库存响应超时: notification_id={notification_id}",
            extra={"notification_id": notification_id, "entity_type": "inventory_notification"}
        )
        return {"status": "timeout", "message": "等待响应超时"}

    def get_response(self, notification_id):
        """
        获取库存系统的响应结果（非阻塞）

        参数:
            notification_id: 通知ID

        返回:
            响应结果字典
        """
        if not self._enabled:
            return {"status": "disabled"}

        result = self._make_request(f"/api/response/{notification_id}", method="GET")
        return result

    def is_enabled(self):
        """检查通知器是否启用"""
        return self._enabled


_inventory_notifier = None


def get_inventory_notifier():
    """获取库存通知器单例"""
    global _inventory_notifier
    if _inventory_notifier is None:
        _inventory_notifier = InventoryNotifier()
        _inventory_notifier.init()
    return _inventory_notifier


def notify_material_prepared(order_no, customer_name, materials, deadline=None):
    """快捷函数：通知物料备齐"""
    return get_inventory_notifier().notify_material_prepared(
        order_no, customer_name, materials, deadline
    )


def notify_order_started(order_no, customer_name, materials, delivery_date):
    """快捷函数：通知订单开工"""
    return get_inventory_notifier().notify_order_started(
        order_no, customer_name, materials, delivery_date
    )