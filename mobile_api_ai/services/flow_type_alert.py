# -*- coding: utf-8 -*-
"""
T13 监控告警: flow_type 不匹配 5 中心埋点

监控目标 (5 中心):
  1. 调度中心 _core.py:  workorder.flow_type 与 process_records.flow_type 不一致
  2. 容器中心 API:        dispatch_task 写 process_sub_steps.flow_type 与已有记录不一致
  3. 容器中心 V5:         DataCollector.collect 推断的 flow_type 与显式入参冲突
  4. 移动端 dispatcher:   TaskPool.get_tasks_by_flow_type 索引 vs 实际 task_type 分布异常
  5. 移动端 sync_bridge:  process_records.flow_type 与 process_sub_steps.flow_type 跨表不一致

接收人: 苑岗彪 (wechat_userid 占位, 待运维提供实际 ID)

设计契约:
  - 单例 FlowTypeAlertMonitor (5 中心共享)
  - alert_flow_type_mismatch(center, order_no, expected, actual) → logger + 企微推送
  - 异常降级: 企微推送失败仅 logger.warning, 不阻断主业务
  - 去重: 同一 (center, order_no, alert_type) 5 分钟内不重复推送
"""
import os
import time
import logging
from collections import defaultdict
from typing import Dict, Set, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# 接收人 - 苑岗彪 (待运维提供实际 wechat_userid)
ALERT_RECEIVER_USERID = 'yuan_gang_biao'  # 苑岗彪
ALERT_DEDUPE_WINDOW = 300  # 5 分钟去重

# 5 中心告警点
CENTER_DISPATCH_CORE = 'dispatch_center'
CENTER_CONTAINER_API = 'container_api'
CENTER_CONTAINER_V5 = 'container_v5'
CENTER_MOBILE_DISPATCHER = 'mobile_dispatcher'
CENTER_MOBILE_SYNC = 'mobile_sync'

# 全局单例
_monitor_instance = None
_monitor_lock = Lock()


class FlowTypeAlertMonitor:
    """flow_type 不匹配告警监控器 (5 中心埋点)"""

    def __init__(self):
        self._dedup_cache: Dict[Tuple[str, str, str], float] = {}
        self._enabled = os.getenv('ENABLE_FLOW_TYPE_ALERT', 'true').lower() == 'true'
        self._lock = Lock()
        # 告警统计 (按中心)
        self._alert_counts: Dict[str, int] = defaultdict(int)

    def _is_duplicate(self, center: str, order_no: str, alert_type: str) -> bool:
        """去重: 同一 (center, order_no, alert_type) 5 分钟内不重复"""
        key = (center, order_no, alert_type)
        with self._lock:
            now = time.time()
            last_time = self._dedup_cache.get(key, 0)
            if now - last_time < ALERT_DEDUPE_WINDOW:
                return True
            self._dedup_cache[key] = now
            return False

    def _send_wechat_alert(self, message: str) -> bool:
        """企微推送 (降级: 失败仅 logger.warning)"""
        try:
            from services.notifier import WeChatNotifier
            notifier = WeChatNotifier()
            notifier.send_custom_message(
                user_ids=[ALERT_RECEIVER_USERID],
                content=message
            )
            return True
        except Exception as e:
            logger.warning(f'[T13 Alert] 企微推送失败: {e}')
            return False

    def alert_flow_type_mismatch(self, center: str, order_no: str,
                                   expected: str, actual: str,
                                   alert_type: str = 'mismatch') -> None:
        """flow_type 不匹配告警 (5 中心通用入口)

        Args:
            center: 5 中心之一 (CENTER_* 常量)
            order_no: 订单号
            expected: 期望的 flow_type
            actual: 实际的 flow_type
            alert_type: 告警子类型 (e.g. 'mismatch'/'missing'/'conflict')
        """
        if not self._enabled:
            return

        if expected == actual:
            return  # 不匹配才告警

        if self._is_duplicate(center, order_no, alert_type):
            return  # 去重: 5 分钟内同 (center, order_no, alert_type) 跳过

        with self._lock:
            self._alert_counts[center] += 1

        message = (
            f'🚨 [flow_type 不匹配] 中心={center} 订单={order_no} '
            f'期望={expected} 实际={actual} 类型={alert_type} '
            f'时间={time.strftime("%Y-%m-%d %H:%M:%S")}'
        )
        logger.warning(message)

        # 企微推送 (失败降级)
        self._send_wechat_alert(message)

    def get_alert_counts(self) -> Dict[str, int]:
        """获取告警统计 (供监控面板查询)"""
        with self._lock:
            return dict(self._alert_counts)

    def clear_dedup_cache(self) -> None:
        """清空去重缓存 (供测试用)"""
        with self._lock:
            self._dedup_cache.clear()


def get_monitor() -> FlowTypeAlertMonitor:
    """全局单例"""
    global _monitor_instance
    with _monitor_lock:
        if _monitor_instance is None:
            _monitor_instance = FlowTypeAlertMonitor()
        return _monitor_instance


# 5 中心专用告警函数 (埋点便捷接口)
def alert_dispatch_core(order_no, expected, actual):
    """1. 调度中心 _core.py 埋点"""
    get_monitor().alert_flow_type_mismatch(CENTER_DISPATCH_CORE, order_no, expected, actual, 'mismatch')


def alert_container_api(order_no, expected, actual):
    """2. 容器中心 API 埋点"""
    get_monitor().alert_flow_type_mismatch(CENTER_CONTAINER_API, order_no, expected, actual, 'mismatch')


def alert_container_v5(order_no, expected, actual):
    """3. 容器中心 V5 埋点"""
    get_monitor().alert_flow_type_mismatch(CENTER_CONTAINER_V5, order_no, expected, actual, 'conflict')


def alert_mobile_dispatcher(order_no, expected, actual):
    """4. 移动端 dispatcher 埋点"""
    get_monitor().alert_flow_type_mismatch(CENTER_MOBILE_DISPATCHER, order_no, expected, actual, 'missing')


def alert_mobile_sync(order_no, expected, actual):
    """5. 移动端 sync_bridge 埋点"""
    get_monitor().alert_flow_type_mismatch(CENTER_MOBILE_SYNC, order_no, expected, actual, 'mismatch')
