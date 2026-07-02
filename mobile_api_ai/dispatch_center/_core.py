# -*- coding: utf-8 -*-
"""
调度中心模块 - 统一的任务/消息/流程调度枢纽（MySQL 版）

功能:
1. 任务调度看板: 可视化派单、转派、负载均衡
2. 消息调度中心: 多渠道消息发送、模板管理
3. 流程调度引擎: 排产-物料-采购-审批流程编排
4. 监控看板: 全局状态、告警、统计

数据库: MySQL container_center 库

╔══════════════════════════════════════════════════════════════════════════════╗
║                        代码分区索引（修正版 2026-06-20）                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Part 1:   导入与初始化 (行 164~181)                                     (行 139~156) ║
║  Part 2:   核心类与上下文 (行 182~219)                                  (行 157~223) ║
║  Part 3:   服务层函数 (行 220~1227)                                  (行 224~1427) ║
║  Part 4:   通知与消息路由 (行 1228~1389)                              (行 1428~1629) ║
║  Part 5:   流程任务路由 (行 1390~1557)                               (行 1630~1799) ║
║  Part 6:   模板管理路由 (行 1558~1832)                               (行 1800~2074) ║
║  Part 7:   违规与配置路由 (行 1833~2224)                              (行 2075~2466) ║
║  Part 8:   任务管理路由 (行 2225~2607)                               (行 2467~2888) ║
║  Part 9:   操作员管理路由 (行 2608~3440)                              (行 2889~3721) ║
║  Part 10:  消息模板路由 (行 3441~3542)                               (行 3722~3823) ║
║  Part 11:  流程管理路由 (行 3543~4776)                               (行 3824~5057) ║
║  Part 19.5:统一订单全流程状态接口 (v3.6.1)                               (行 4777~5417) ║
║  Part 20:  回归测试 API (v3.6.1)                                  (行 5418~5664) ║
║  Part 12:  业务统计路由 (行 5665~5887)                               (行 5946~6168) ║
║  Part 13:  定时任务控制器 (行 5888~6151)                              (行 6169~6432) ║
║  Part 14:  同步接口 (行 6152~6238)                                 (行 6433~6519) ║
║  Part 15:  质检与工单同步 (行 6239~7110)                              (行 6520~7393) ║
║  Part 19:  统一任务查询接口 (行 7111~7980)                               (行 7394~8264) ║
║  Part 16:  质检与成本同步 (行 7981~8270)                              (行 8265~8554) ║
║  Part 17:  报工与同步接口 (行 8271~8653)                              (行 8555~8922) ║
║  Part 18:  同步接口 (行 8654~8731)                                 (行 8923~9000) ║
║  Part 20b: 配置接口 (行 8732~8784)                              (行 9001~9053) ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import os
import json
import uuid
import time
import threading
import logging
import subprocess
import signal
import pymysql

# [H2 修复 2026-06-13] 集成 thread_lifecycle.py
# 详见 docs/模块化改造/THREAD_LIFECYCLE.md
try:
    from thread_lifecycle import (
        register_thread,
        unregister_thread,
        list_threads,
        shutdown_all,
        create_daemon_thread,
        is_shutting_down,
        init_graceful_shutdown,
    )
    _THREAD_LIFECYCLE_AVAILABLE = True
except ImportError:
    _THREAD_LIFECYCLE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning('[H2] thread_lifecycle 不可用，使用原生 threading')

# 初始化优雅关闭
if _THREAD_LIFECYCLE_AVAILABLE:
    try:
        init_graceful_shutdown(timeout=10.0)
    except Exception as e:
        logger.warning(f'[H2] 初始化 graceful_shutdown 失败: {e}')

# data_type 严格分类契约 v1.0 (docs/DATA_TYPE_CONTRACT.md)
from utils.data_type_contract import (  # noqa: E402
    CARD_GROUPS,
    LEGACY_TO_NEW,
    NEW_DATA_TYPES,
    classify_pkg,
    classify_payloads,
    get_flow_step_names_set,
)

# 加载 .env（必须在 ContainerCenter 初始化之前）
# 优先项目根 .env（WECHAT_CLOUD_API_KEY 在项目根），再加载 mobile_api_ai/.env 作为子模块覆盖
from dotenv import load_dotenv
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BASE_DIR)
load_dotenv(os.path.join(_ROOT_DIR, '.env'))
load_dotenv(os.path.join(_BASE_DIR, '.env'))
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from flask import Blueprint, jsonify, request, render_template
from models.database import get_connection_context
from template_engine import (
    VARIABLE_CN_TO_EN, VAR_EN_TO_CN, MESSAGE_TEMPLATES_DEFAULT,
    _resolve_variables, _render_template, _send_wechat_message,
)

import sys as _sys
logger = logging.getLogger(__name__)

_OUTER_SQL_ALLOWED = frozenset({
    'id', 'order_no', 'product_name', 'spec', 'quantity', 'unit', 'status',
    'priority', 'operator', 'inspector', 'assigned_to', 'supplier',
    'purchaser', 'created_at', 'updated_at', 'expected_date', 'actual_date',
    'notes', 'remarks', 'description', 'category', 'source', 'target',
    'location', 'contact', 'phone', 'email', 'department', 'team',
    'process_code', 'step_name', 'step_code', 'process_name',
})
_MATERIAL_SQL_ALLOWED = frozenset({
    'id', 'order_no', 'material_name', 'spec', 'quantity', 'unit',
    'prep_status', 'required_qty', 'prepared_qty', 'prepared_by',
    'supplier', 'expected_delivery', 'actual_delivery', 'quality_status',
    'warehouse_location', 'remark', 'created_at', 'updated_at',
})
_REPAIR_SQL_ALLOWED = frozenset({
    'id', 'order_no', 'product_name', 'issue_type', 'description',
    'assigned_to', 'repair_status', 'priority', 'start_time', 'end_time',
    'result', 'cost', 'technician', 'created_at', 'updated_at',
})
_QUALITY_SQL_ALLOWED = frozenset({
    'id', 'order_no', 'step_name', 'process_name', 'result', 'inspector',
    'inspection_type', 'quantity', 'qualified_qty', 'defect_qty',
    'defect_type', 'defect_reason', 'remark', 'equipment', 'operator',
    'created_at', 'updated_at',
})

from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT, DISPATCH_DATA_FILE, ENV_FILE, BASE_DIR, DB_PATHS
# 三端统一状态真值源（手机端/桌面端/调度中心 共用）
try:
    from api.step_status_helper import compute_step_statuses
except ImportError:
    compute_step_statuses = None  # 兜底：导入失败时走旧逻辑，不阻断调度中心
# V5CompatibleClient 延迟导入防止循环依赖
V5CompatibleClient = None

# ── steel_belt 连接池辅助 ──
def get_steelbelt_cursor():
    from db.steelbelt_pool import cursor as _sbc
    return _sbc()

def get_steelbelt_connection():
    from db.steelbelt_pool import get_conn
    return get_conn()


# [N2 修复 2026-06-13] 补全 _get_mysql_connection 函数
# 之前：_get_mysql_connection 未定义，调用会 NameError
# 之后：返回 container_center 本地连接（消除跨库直查）
#
# [v3.6.1 重构 2026-06-20] 函数已抽取到 _db.py 统一管理
# 删除本地定义，改从 ._db 导入（避免 schedule_routes.py 重复定义）
from ._db import _get_mysql_connection  # noqa: F401
from ._db import _get_container_center, _get_storage  # noqa: F401
from ._db import get_dispatch_cache, _dispatch_cache  # noqa: F401
from ._db import _ssot_cache_get, _ssot_cache_set, _ssot_cache_clear  # noqa: F401
from ._db import _proxy_to_container_ssot  # noqa: F401

# [v3.6.1 重构 2026-06-20] 通知层函数已抽取到 _notify.py
# 优先从 _notify 导入（推荐新代码使用）
from ._notify import (  # noqa: F401
    _send_wechat_message, _send_wechat_app_message,
    _render_template, build_confirmation_variables,
    notify_with_template, notify_process_event,
    send_simple_message, send_to_department,
)

# [v3.6.1 重构 2026-06-20] 操作员层函数已抽取到 _operators.py
# 优先从 _operators 导入（推荐新代码使用）
from ._operators import (  # noqa: F401
    get_operators, get_operator_info, get_operators_by_department,
    get_department_members, list_departments,
    get_customer_group_for_order,
    clear_operators_cache, clear_customer_group_cache,
)

# [v3.6.1 重构 2026-06-20] 同步层函数已抽取到 _sync.py
# 优先从 _sync 导入（推荐新代码使用）
from ._sync import (  # noqa: F401
    sync_work_order_status, sync_to_mysql, sync_schedule_to_container,
    get_cached_work_orders, get_doc_data,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Part 1: 导入与初始化 (行 139~156)
# ═══════════════════════════════════════════════════════════════════════════════

from ._constants import (
    STATUS_KEY_TO_MYSQL,
    DISPATCH_RULES_DEFAULT,
    FLOW_MATCHING_RULES_DEFAULT,
    PRODUCT_TYPE_NAMES,
    PROCESS_FLOW_TEMPLATES,
    PROCESS_TEMPLATE_DEFAULTS,
    CONFIRMATION_REQUIRED_STEPS,
    CONFIRMATION_REPLY_KEYWORDS,
    DISPATCH_DOC_ID,
    DISPATCH_DOC_TYPE,
    CUSTOMER_GROUP_CACHE_TTL,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Part 2: 核心类与上下文 (行 157~223)
# ═══════════════════════════════════════════════════════════════════════════════


# ── [T4 2026-06-16] 订阅 SSOT EventBus, 状态变更后清本地缓存 ─────────
def _on_ssot_status_changed(event, data):
    """订单状态变更后清本地缓存 (processes list + workorder detail)"""
    global _processes_cache
    try:
        order_no = (data or {}).get('order_no', 'unknown')
        logger.info(f'[T4] 收到状态变更事件 order_no={order_no}, 清缓存')
        _processes_cache['data'] = None
        _processes_cache['time'] = 0
    except Exception as e:
        logger.warning(f'[T4] 清缓存失败: {e}')


try:
    from core.event_bus import EventBus, Events
    EventBus.subscribe(Events.ORDER_STATUS_CHANGED, _on_ssot_status_changed)
    logger.info('[T4] 已订阅 EventBus.ORDER_STATUS_CHANGED (清缓存)')
except ImportError as e:
    logger.warning(f'[T4] EventBus 不可用, 状态变更后缓存需等 TTL 过期: {e}')




def _get_customer_group_for_order(order_no: str) -> str:
    """从本地表 orders_local 查询客户群(customer_group), 进程内缓存 5 分钟

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_operators.py
    保留此函数作为向后兼容 shim，内部调用 _operators.get_customer_group_for_order
    """
    from ._operators import get_customer_group_for_order as _impl
    return _impl(order_no)


# ═══════════════════════════════════════════════════════════════════════════════
# Part 3: 服务层函数 (行 224~1427)
# ═══════════════════════════════════════════════════════════════════════════════

def invalidate_customer_group_cache(order_no: str = None) -> int:
    """失效 customer_group 缓存
    客户群调整后调用, 立即生效
    - order_no: 指定订单失效 (精准)
    - None: 全量失效 (兜底)
    返回失效条数
    """
    ctx_cache = DispatchContext.get_instance().customer_group_cache
    if order_no:
        return 1 if ctx_cache.pop(order_no, None) is not None else 0
    n = len(ctx_cache)
    ctx_cache.clear()
    return n


def _is_cloud_reachable() -> bool:
    """检查云端是否可达"""
    try:
        import cloud_poller
        return cloud_poller.is_reachable()
    except Exception:
        return False


def _is_mysql_reachable() -> bool:
    """检查MySQL是否可达"""
    try:
        conn = _get_mysql_connection()
        conn.ping(reconnect=True)
        conn.close()
        return True
    except Exception:
        return False


def _get_alert_engine_health() -> dict:
    """获取告警引擎健康状态"""
    try:
        eng = DispatchContext.get_instance().alert_engine
        if eng is None:
            return {'status': 'unavailable', 'message': '引擎未初始化'}
        stats = eng.get_stats()
        return {'status': 'healthy', 'today_fired': stats.get('today_fired', 0)}
    except Exception as e:
        return {'status': 'error', 'message': '操作失败，请稍后重试'}


class _UnavailableClient:
    """容器中心不可用时的哨兵客户端标记"""
    pass


class DispatchContext:
    """调度中心上下文 - 单例

    统一管理 ContainerCenterClient、本地 ContainerCenter 实例及工单缓存。
    取代模块级全局变量模式，提供线程安全的双检锁初始化。
    """
    _instance = None
    _instance_lock = threading.RLock()

    def __init__(self):
        self.cc_client = None
        self.cc_client_lock = threading.RLock()
        self.cc_available = True
        self.cc_available_until = 0
        self.work_order_cache = {'data': [], 'time': 0, 'ttl': 10}
        self.cache_lock = threading.RLock()
        self.cache_loading_lock = threading.RLock()
        self.operator_cache = {'data': [], 'time': 0, 'ttl': 60}
        self.operator_cache_lock = threading.RLock()
        self.container_center_instance = None
        self.container_center_lock = threading.RLock()
        self.v5_client = None
        self.v5_client_lock = threading.RLock()
        # ── 全局状态 : 原模块级 global 变量收归此处 ──
        self.alert_engine = None
        self.cost_checker_thread = None
        self.cost_checker_running = False
        self.cost_checker_gen = 0
        self.outbox_running = False
        self.customer_group_cache: dict = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = DispatchContext()
        return cls._instance

    def is_cc_reachable(self) -> bool:
        now = time.time()
        if now < self.cc_available_until:
            return self.cc_available
        return True

    def mark_cc_unavailable(self):
        self.cc_available = False
        self.cc_available_until = time.time() + 30

    def mark_cc_available(self):
        self.cc_available = True
        self.cc_available_until = time.time() + 30

    def get_v5_client(self):
        global V5CompatibleClient
        if V5CompatibleClient is None:
            from container_center.v5_compatible_client import V5CompatibleClient as _V5
            V5CompatibleClient = _V5
        if self.v5_client is None:
            with self.v5_client_lock:
                if self.v5_client is None:
                    cc = self.get_container_center()
                    http_client = None
                    try:
                        url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
                        secret = os.environ.get('CONTAINER_CENTER_SECRET', '')
                        http_client = ContainerCenterClient(base_url=url, secret=secret)
                    except Exception:
                        pass
                    self.v5_client = V5CompatibleClient(container_center=cc, http_client=http_client)
        return self.v5_client

    def get_client(self) -> Any:
        return self.get_v5_client()

    def get_container_center(self):
        if self.container_center_instance is None:
            with self.container_center_lock:
                if self.container_center_instance is None:
                    try:
                        from core.config import DB_PATHS
                        from container_center_v5 import ContainerCenter
                        self.container_center_instance = ContainerCenter()
                        config_file = DB_PATHS.get('cloud_config', '')
                        if config_file and os.path.exists(config_file):
                            with open(config_file, 'r', encoding='utf-8') as f:
                                cloud_cfg = json.load(f)
                            cc = self.container_center_instance
                            cc.enable_notification(cloud_cfg.get('enable_notification', True))
                            cc.enable_group_notification(cloud_cfg.get('enable_group_notification', True))
                            cc.enable_distribution(cloud_cfg.get('enable_distribution', True))
                            tmpl = cloud_cfg.get('notification_template', '')
                            if tmpl:
                                cc.set_notification_template(tmpl)
                    except Exception:
                        logger.warning('ContainerCenter 初始化失败，使用空实例')
                        self.container_center_instance = None
        return self.container_center_instance

    def get_cached_work_orders(self, page=1, size=2000, data_type=None):
        # [优化 2026-06-12] 性能日志埋点
        perf_start = time.time()
        now = time.time()

        with self.cache_lock:
            if self.work_order_cache['data'] is not None and now - self.work_order_cache['time'] < self.work_order_cache['ttl']:
                elapsed = (time.time() - perf_start) * 1000
                logger.info(f"[性能] list_tasks 缓存命中，返回 {len(self.work_order_cache['data'])} 条，耗时 {elapsed:.1f}ms")
                return self.work_order_cache['data']

        acquired = self.cache_loading_lock.acquire(timeout=5)
        if not acquired:
            with self.cache_lock:
                if self.work_order_cache['data'] is not None:
                    elapsed = (time.time() - perf_start) * 1000
                    logger.warning(f'[性能] 缓存加载锁超时，返回旧缓存 {len(self.work_order_cache["data"])} 条，耗时 {elapsed:.1f}ms')
                    return self.work_order_cache['data']
                return []

        try:
            with self.cache_lock:
                if self.work_order_cache['data'] is not None and now - self.work_order_cache['time'] < self.work_order_cache['ttl']:
                    elapsed = (time.time() - perf_start) * 1000
                    logger.info(f"[性能] list_tasks 缓存命中，耗时 {elapsed:.1f}ms")
                    return self.work_order_cache['data']

            client = self.get_client()
            if isinstance(client, _UnavailableClient):
                self.work_order_cache['time'] = time.time()
                if self.work_order_cache['data'] is None:
                    self.work_order_cache['data'] = []
                elapsed = (time.time() - perf_start) * 1000
                logger.warning(f'[性能] Container Center 不可用，返回空/缓存，耗时 {elapsed:.1f}ms')
                return self.work_order_cache['data']

            try:
                result = client.query_documents(data_type, page=page, size=size)
                elapsed = (time.time() - perf_start) * 1000
                logger.info(f'[性能] query_documents 返回 {len(result) if result else 0} 条，耗时 {elapsed:.1f}ms')
            except Exception as e:
                self.mark_cc_unavailable()
                self.work_order_cache['time'] = time.time()
                elapsed = (time.time() - perf_start) * 1000
                logger.warning(f'[性能] 查询失败: {e}，耗时 {elapsed:.1f}ms')
                if self.work_order_cache['data'] is not None:
                    return self.work_order_cache['data']
                self.work_order_cache['data'] = []
                self.work_order_cache['time'] = 0
                return self.work_order_cache['data']

            self.mark_cc_available()
            self.work_order_cache['data'] = result
            self.work_order_cache['time'] = time.time()
            return result
        finally:
            self.cache_loading_lock.release()

    def invalidate_operator_cache(self):
        """清除操作员缓存（新增/编辑/删除操作员后调用）"""
        with self.operator_cache_lock:
            self.operator_cache['data'] = None
            self.operator_cache['time'] = 0

    def invalidate_work_order_cache(self):
        """清除工单缓存（查询为空时降级重试调用）"""
        with self.cache_lock:
            self.work_order_cache['data'] = []
            self.work_order_cache['time'] = 0

    def get_cached_operators(self):
        now = time.time()
        with self.operator_cache_lock:
            if self.operator_cache['data'] and now - self.operator_cache['time'] < self.operator_cache['ttl']:
                return self.operator_cache['data']

        cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
        resp = requests.get(f'{cc_url}/api/operators', timeout=5)
        if resp.status_code != 200:
            raise RuntimeError(f'容器中心 5002 不可达: HTTP {resp.status_code}')
        resp_data = resp.json().get('data', [])
        if isinstance(resp_data, dict):
            operators = resp_data.get('operators', [])
        else:
            operators = resp_data if isinstance(resp_data, list) else []
        with self.operator_cache_lock:
            self.operator_cache['data'] = operators
            self.operator_cache['time'] = time.time()
        return operators

    def _probe_cc_availability(self):
        """用短超时探测容器中心是否可达，不可达则立即标记降级"""
        try:
            import requests
            url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
            requests.get(f'{url}/api/v4/work_order?page=1&size=1',
                         timeout=(2, 3))
        except Exception:
            logger.warning('CC 探测失败，标记为不可达')
            self.mark_cc_unavailable()


def _get_client() -> Any:
    return DispatchContext.get_instance().get_client()

def _get_container_center():
    return DispatchContext.get_instance().get_container_center()

def _get_cached_work_orders(page=1, size=2000, data_type=None):
    """获取缓存的工单列表

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_sync.py
    保留此函数作为向后兼容 shim，内部调用 _sync.get_cached_work_orders
    """
    from ._sync import get_cached_work_orders as _impl
    return _impl(page, size, data_type)

def _is_test_order(order_no):
    if not order_no:
        return False
    if order_no.startswith('ATTEND_') or order_no.startswith('ORD-SCAN-'):
        return True
    return False


# 修补 F15 (TASK-15): 删除 _get_process_names_set 函数
# 根因: F6 P9 2026-06-10 已 DROP container_center.process_names 表
#       (见 .workbuddy/memory/MEMORY.md L20 跨库历史表清理)
#       原函数仍 SELECT 该表, 触发 MySQL 1146 WARNING + 5min 空集合缓存污染
# 修复: 改用 _dispatch_cache.get_data()['process_departments'].keys() 作为工序集来源
#       (process_departments 来自 process_records 真实数据, 不依赖被 DROP 的字典表)
#
# R11 双源降级: cache 优先 + SSOT 兜底
#       原实现仅 cache 单源, 冷启动时 dispatch_cache 尚未 build 完成,
#       导致 _get_process_names_set() 返回空集合 → classify_pkg 把 P01~P16
#       全部误判为 __contract_violation__ → 任务丢失
# 修复: cache 失败/空时降级到 utils.data_type_contract.get_process_names_set()
#       (其内部读 core.PROCESS_CODES, 启动期即可用, 永远非空)


def _get_process_names_set() -> set:
    """R11 双源降级: 优先 dispatch_cache, 降级 SSOT(core.PROCESS_CODES)

    优先级:
      1. ``_dispatch_cache.get_data()['process_departments']`` (运行时真实数据)
      2. ``utils.data_type_contract.get_process_names_set()`` (SSOT 兜底)
      3. 空集合 (由 classify_pkg 处理为 ``__contract_violation__``, 不阻塞调用)

    Returns
    -------
    set[str]
        工序名集合;空集合表示 SSOT 与 cache 都不可用。
    """
    # ── 1. cache 优先 (运行时真实数据) ──
    try:
        if _dispatch_cache:
            cache_data = _dispatch_cache.get_data() or {}
            process_departments = cache_data.get('process_departments', {}) or {}
            if process_departments:
                return set(process_departments.keys())
    except Exception as _e:
        logger.debug(f'[_get_process_names_set] cache 读取失败,降级 SSOT: {_e}')

    # ── 2. SSOT 兜底 (core.PROCESS_CODES, 启动期即可用) ──
    try:
        from utils.data_type_contract import get_process_names_set
        ssot_names = get_process_names_set()
        if ssot_names:
            return ssot_names
    except Exception as _e:
        logger.debug(f'[_get_process_names_set] SSOT 兜底失败,返回空集: {_e}')

    # ── 3. 实在没有,返回空集(分类器会标 violation) ──
    return set()


def _normalize_process_steps(steps):
    if not steps or not isinstance(steps, list):
        return None
    if not steps:
        return []

DISPATCH_RULES_DEFAULT = {
    'max_operator_tasks': {'label': '操作员最大并发任务', 'key': 'MAX_OPERATOR_TASKS', 'value': 10, 'type': 'number'},
    'enable_auto_dispatch': {'label': '启用自动派单', 'key': 'ENABLE_AUTO_DISPATCH', 'value': True, 'type': 'boolean'},
    'enable_reminder': {'label': '启用超时提醒', 'key': 'ENABLE_REMINDER', 'value': True, 'type': 'boolean'},
    'urgent_priority_boost': {'label': '紧急任务优先派单', 'key': 'URGENT_PRIORITY_BOOST', 'value': True, 'type': 'boolean'},
    'repair_notification_enabled': {'label': '启用报修通知', 'key': 'REPAIR_NOTIFICATION_ENABLED', 'value': True, 'type': 'boolean'},
}

FLOW_MATCHING_RULES_DEFAULT = [
    {'id': 'fmr_production_1', 'name': '不锈钢网带→生产流程', 'field': 'product_type', 'value': '不锈钢网带', 'flow_type': 'production', 'priority': 10, 'enabled': True},
    {'id': 'fmr_production_2', 'name': '不锈钢丝→生产流程', 'field': 'product_type', 'value': '不锈钢丝', 'flow_type': 'production', 'priority': 10, 'enabled': True},
    {'id': 'fmr_material', 'name': '物料→物料采购流程', 'field': 'product_type', 'value': '物料', 'flow_type': 'material_purchase', 'priority': 10, 'enabled': True},
    {'id': 'fmr_quality', 'name': '质检→质检流程', 'field': 'product_type', 'value': '质检委托', 'flow_type': 'quality', 'priority': 10, 'enabled': True},
    {'id': 'fmr_repair', 'name': '设备报修→维修流程', 'field': 'product_type', 'value': '设备维修', 'flow_type': 'repair', 'priority': 10, 'enabled': True},
]

def match_flow_type(work_order_data: dict, rules: list = None) -> str:
    """根据工单数据匹配流程模板

    Args:
        work_order_data: 工单数据字典，包含 product_type/order_no 等字段
        rules: 匹配规则列表，默认从缓存加载

    Returns:
        匹配到的流程类型，默认 'production'
    """
    # 优先使用工单数据中显式传入的 flow_type
    explicit = work_order_data.get('flow_type', '')
    if explicit:
        return explicit

    if rules is None:
        data = _dispatch_cache.get_data()
        rules = data.get('flow_matching_rules', FLOW_MATCHING_RULES_DEFAULT)

    sorted_rules = sorted(
        [r for r in rules if r.get('enabled', True)],
        key=lambda r: r.get('priority', 0), reverse=True
    )

    for rule in sorted_rules:
        field = rule.get('field', '')
        expected = rule.get('value', '')
        actual = work_order_data.get(field, '')
        if actual == expected:
            flow_type = rule.get('flow_type', 'production')
            logger.debug("[FlowMatch] %s=%s → %s (规则: %s)", field, actual, flow_type, rule.get('id', ''))
            return flow_type

PROCESS_TEMPLATE_DEFAULTS = {
    'process_advance': 'tmpl_process_advance',
    'process_reject': 'tmpl_process_reject',
    'task_assigned': 'tmpl_task_assigned',
    'task_reassign': 'tmpl_task_transfer',
}

CONFIRMATION_REQUIRED_STEPS = {
    'scheduled': 'tmpl_schedule_notify',
    'confirmed': 'tmpl_schedule_complete',
    'reported': 'tmpl_schedule_complete',
    'qc_passed': 'tmpl_process_complete',
    'completed': 'tmpl_process_complete',
}

CONFIRMATION_REPLY_KEYWORDS = ['确认', '收到', '好的', 'ok', 'yes', 'y', 'OK', '收到']

_process_confirmation_callbacks = []

def register_process_confirmation_callback(callback):
    _process_confirmation_callbacks.append(callback)

def trigger_process_confirmation(process_id: str, user_id: str, user_name: str, content: str) -> dict:
    for callback in _process_confirmation_callbacks:
        try:
            result = callback(process_id, user_id, user_name, content)
            if result:
                return result
        except Exception as e:
            logger.warning(f"[确认回调] 回调执行失败: {e}")
    return None

def check_and_trigger_auto_confirmation(process_id: str, user_id: str, user_name: str, content: str) -> dict:
    content_lower = content.lower().strip()
    for keyword in CONFIRMATION_REPLY_KEYWORDS:
        if keyword.lower() in content_lower or content_lower == keyword.lower():
            data = _dispatch_cache.get_data()
            processes = data.get('processes', [])
            process = next((p for p in processes if p.get('order_no') == order_no), None)
            if process and process.get('awaiting_confirmation'):
                confirm_result = confirm_process_step(order_no)
                return {'confirmed': True, 'process_id': process_id, 'message': '流程已确认推进'}
            return {'confirmed': False, 'reason': '流程无需确认'}
    return {'confirmed': False, 'reason': '未识别到确认关键词'}

PROCESS_EVENT_LABELS = {
    'process_advance': '流程推进',
    'process_reject': '流程退回',
    'task_assigned': '任务分配',
    'task_reassign': '任务转派',
}

class DispatchStatus(Enum):
    PENDING = 'pending'
    DISPATCHED = 'dispatched'
    ACKNOWLEDGED = 'acknowledged'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    FAILED = 'failed'

class AlertLevel(Enum):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'




class DispatchDataCache:
    """调度中心数据缓存管理器 - 支持内存缓存、线程安全、原子写入、写入节流、自动清理"""

    def __init__(self, data_file: str, ttl: int = 30):
        self.data_file = data_file
        self.ttl = ttl
        self._cache: Optional[Dict] = None
        self._cache_time: float = 0
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._pending_write = False
        self._last_write_time = 0
        self._persist_thread: Optional[threading.Thread] = None
        self._min_write_interval = float(os.getenv('DISPATCH_MIN_WRITE_INTERVAL', '2'))
        self._doc_store = None
        self._doc_migrated = False

    def _init_doc_store(self):
        if self._doc_store is not None:
            return
        try:
            from container_center.storage import DocumentStore
            self._doc_store = DocumentStore()
        except Exception as e:
            logger.warning(f'DocumentStore 初始化失败，降级到文件存储: {e}')
            self._doc_store = False

    def _get_default_data(self) -> Dict:
        return {'rules': {}, 'templates': [], 'messages': [], 'processes': [], 'alerts': [], 'dispatch_log': [], 'flow_matching_rules': []}

    def _load_from_file(self) -> Dict:
        self._init_doc_store()
        if self._doc_store and self._doc_store is not False:
            try:
                doc = self._doc_store.get(DISPATCH_DOC_ID, DISPATCH_DOC_TYPE)
                if doc:
                    self._doc_migrated = True
                    return doc.get('doc_data', self._get_default_data())
            except Exception as e:
                logger.warning(f'从 DocumentStore 加载调度数据失败: {e}')
        if not os.path.exists(self.data_file):
            return self._get_default_data()
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if self._doc_store and self._doc_store is not False and not self._doc_migrated:
                self._migrate_to_doc_store(data)
            return data
        except (json.JSONDecodeError, IOError):
            return self._get_default_data()

    def _migrate_to_doc_store(self, data: Dict):
        try:
            existing = self._doc_store.get(DISPATCH_DOC_ID, DISPATCH_DOC_TYPE)
            if existing:
                self._doc_store.update(DISPATCH_DOC_ID, data, DISPATCH_DOC_TYPE)
            else:
                self._doc_store.create(DISPATCH_DOC_TYPE, data, doc_id=DISPATCH_DOC_ID, status='active')
            self._doc_migrated = True
            logger.info(f'调度数据已迁移到 DocumentStore ({len(data)} 个键)')
        except Exception as e:
            logger.error(f'调度数据迁移失败: {e}')

    def _save_to_file(self, data: Dict) -> bool:
        with self._write_lock:
            try:
                data = self._auto_cleanup(data)
                # processes 不持久化到JSON（从SQLite读取）
                if 'processes' in data:
                    data = {k: v for k, v in data.items() if k != 'processes'}
                temp_file = self.data_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                os.replace(temp_file, self.data_file)
                self._save_to_doc_store(data)
                return True
            except IOError as e:
                logger.error(f'保存调度数据失败: {e}')
                return False

    def _save_to_doc_store(self, data: Dict):
        self._init_doc_store()
        if not self._doc_store or self._doc_store is False:
            return
        try:
            existing = self._doc_store.get(DISPATCH_DOC_ID, DISPATCH_DOC_TYPE)
            if existing:
                self._doc_store.update(DISPATCH_DOC_ID, data, DISPATCH_DOC_TYPE)
            else:
                self._doc_store.create(DISPATCH_DOC_TYPE, data, doc_id=DISPATCH_DOC_ID, status='active')
        except Exception as e:
            logger.warning(f'持久化调度数据到 DocumentStore 失败: {e}')

    def _auto_cleanup(self, data: Dict) -> Dict:
        max_alerts = int(os.getenv('DISPATCH_MAX_ALERTS', '500'))
        max_processes = int(os.getenv('DISPATCH_MAX_PROCESSES', '2000'))
        alert_retention_days = int(os.getenv('DISPATCH_ALERT_RETENTION_DAYS', '30'))

        alerts = data.get('alerts', [])
        if len(alerts) > max_alerts:
            data['alerts'] = alerts[-max_alerts:]

        processes = data.get('processes', [])
        if len(processes) > max_processes:
            active = [p for p in processes if p.get('status') != 'completed']
            completed = [p for p in processes if p.get('status') == 'completed']
            completed = completed[-max(max_processes // 2, 1):]
            data['processes'] = active + completed

        return data

    def _is_cache_valid(self) -> bool:
        if self._cache is None:
            return False
        if time.time() - self._cache_time > self.ttl:
            return False
        return True

    def get_data(self, force_refresh: bool = False) -> Dict:
        with self._lock:
            if not force_refresh and self._is_cache_valid():
                return self._cache
            self._cache = self._load_from_file()
            # 从容器中心同步 processes（已迁移到 MySQL）
            self._cache['processes'] = self._load_processes_from_db()
            self._cache_time = time.time()
            return self._cache

    def _load_processes_from_db(self) -> list:
        """从容器中心读取流程列表（MySQL 迁移版），按 order_no 去重"""
        try:
            cc = _get_container_center()
            if not cc:
                return []
            records = cc.storage.get_process_records(limit=500)
            seen = {}
            for d in records:
                if isinstance(d.get('steps'), str):
                    try: d['steps'] = json.loads(d['steps'])
                    except Exception: d["steps"] = []
                if isinstance(d.get('content'), str):
                    try: d['content'] = json.loads(d['content'])
                    except Exception: d["content"] = {}
                    d['content'] = {}
                order_no = d.get('order_no', '')
                # 按 order_no 去重：优先保留 in_production > 其他状态 > 有 product_name 的
                if order_no not in seen:
                    seen[order_no] = d
                else:
                    existing = seen[order_no]
                    # in_production 优先级最高
                    if d.get('status') == 'in_production' and existing.get('status') != 'in_production':
                        seen[order_no] = d
                    elif (d.get('product_name') or d.get('customer_name')) and \
                         not (existing.get('product_name') or existing.get('customer_name')):
                        seen[order_no] = d
            return list(seen.values())
        except Exception as e:
            logger.warning(f'从SQLite加载processes失败: {e}')
            return []

    def update_data(self, updater: Callable[[Dict], None], sync: bool = False) -> bool:
        import traceback
        with self._lock:
            data = self.get_data(force_refresh=False)
            if data is None:
                logger.error('[update_data] get_data() 返回 None，缓存可能未初始化')
                return False
            try:
                updater(data)
            except Exception as e:
                logger.error(f'[update_data] updater 异常: {type(e).__name__}: {e}\n{"".join(traceback.format_exception(type(e), e, e.__traceback__))}')
                return False
            self._cache = data
            self._cache_time = time.time()
        if self._pending_write:
            # 已有正在排队的写入，直接加入（会被后续 throttle 覆盖）
            pass
        elif sync:
            # 关键操作同步落盘，不等 throttle
            self._save_to_file(data)
        else:
            self._pending_write = True
            if self._persist_thread is not None and self._persist_thread.is_alive():
                pass
            else:
                self._persist_thread = threading.Thread(target=self._throttled_persist, daemon=True)
                self._persist_thread.start()
        # 同步 processes 到 MySQL
        self._sync_processes_to_db(data.get('processes', []))
        return True

    def _sync_processes_to_db(self, processes: list):
        """[P2-6] 将 processes 同步到容器中心 MySQL（仅插入新记录，不覆盖已有数据）
        优化：批量预加载已存在记录，消除 N+1 查询
        """
        if not processes:
            return
        try:
            cc = _get_container_center()
            if not cc:
                return
            pids = [str(p.get('id', '')) for p in processes if p.get('id')]
            keys = [(p.get('order_no', ''), p.get('product_name', '')) for p in processes]
            existing_ids: set = set()
            if pids:
                placeholders = ','.join(['%s'] * len(pids))
                rows = cc.storage.fetch_all(
                    f"SELECT id FROM process_records WHERE id IN ({placeholders})", pids)
                existing_ids = {str(r['id']) for r in rows}
            existing_keys: set = set()
            valid_keys = [(k[0], k[1]) for k in keys if k[0] and k[1]]
            if valid_keys:
                placeholders = ','.join(['(%s,%s)'] * len(valid_keys))
                params = [item for pair in valid_keys for item in pair]
                rows = cc.storage.fetch_all(
                    f"SELECT order_no, product_name FROM process_records WHERE (order_no, product_name) IN ({placeholders})",
                    params)
                existing_keys = {(r['order_no'], r['product_name']) for r in rows}
            for p in processes:
                pid = str(p.get('id', ''))
                if not pid:
                    continue
                if pid in existing_ids:
                    continue
                key = (p.get('order_no', ''), p.get('product_name', ''))
                if key in existing_keys:
                    continue
                cc.storage.save_process_record(p)
        except Exception as e:
            logger.warning(f'Sync processes to MySQL failed: {e}')

    def _throttled_persist(self):
        now = time.time()
        wait = max(0, self._min_write_interval - (now - self._last_write_time))
        if wait > 0:
            time.sleep(wait)
        with self._lock:
            data = self._cache
        self._save_to_file(data)
        self._last_write_time = time.time()
        self._pending_write = False
        self._persist_thread = None

    def _persist(self, data):
        try:
            self._save_to_file(data)
        except Exception as e:
            logger.error(f'异步持久化数据失败: {e}')

    def invalidate(self):
        with self._lock:
            self._cache = None
            self._cache_time = 0


_dispatch_cache: "DispatchDataCache" = DispatchDataCache(DISPATCH_DATA_FILE)


def _init_defaults():
    data = _dispatch_cache.get_data()
    # 启动时从 MySQL 同步 processes
    data['processes'] = _dispatch_cache._load_processes_from_db()
    changed = True
    if not data.get('rules'):
        data['rules'] = {k: v['value'] for k, v in DISPATCH_RULES_DEFAULT.items()}
        changed = True
    if not data.get('templates'):
        data['templates'] = MESSAGE_TEMPLATES_DEFAULT
        changed = True
    if not data.get('flow_matching_rules'):
        data['flow_matching_rules'] = FLOW_MATCHING_RULES_DEFAULT
        changed = True
    if changed:
        _dispatch_cache.update_data(lambda d: d.update(data))

    # ─── 延迟预热：移到首次请求时执行（避免启动时 MySQL 连接慢导致失败）───
    # 注释掉启动时预热，改为在 Flask before_request 中懒加载
    # _preload_operators_from_mysql()
    # ─── 预热 container_config（避免首次请求时冷导入 container_center_v5） ───
    try:
        from container_config import container_config as _cc
        _cc.get_all_operators()
        logger.info('[启动] container_config 预热完成')
    except Exception as _e:
        logger.warning(f'[启动] container_config 预热失败: {_e}')
    return data


def warmup_operators():
    """延迟预热操作员数据（在首次请求时调用）"""
    _preload_operators_from_mysql()

def _preload_operators_from_mysql():
    """服务器启动时从 container_center MySQL 自动加载操作员到调度中心缓存"""
    try:
        cc = _get_container_center()
        es = cc.load_enterprise_structure()
        if not es:
            logger.warning('[操作员预加载] enterprise_structure 为空')
            return
        users = es.get('users', [])
        if not users:
            logger.warning('[操作员预加载] 无用户数据')
            return
        operators = []
        for u in users:
            operators.append({
                'id': u.get('userid', u.get('id', '')),
                'name': u.get('name', ''),
                'role': '操作员',
                'department': ', '.join(u.get('department_name', [])) if isinstance(u.get('department_name'), list) else u.get('department_name', ''),
                'enabled': True,
                'notify_enabled': True,
                'max_tasks': 10,
                'wechat_userid': u.get('userid', ''),
            })
        ctx = DispatchContext.get_instance()
        with ctx.operator_cache_lock:
            ctx.operator_cache['data'] = operators
            ctx.operator_cache['time'] = time.time()
        logger.info(f'[操作员预加载] 从 MySQL 加载 {len(operators)} 名操作员')
    except Exception as e:
        logger.warning(f'[操作员预加载] 失败: {e}')

_init_defaults()


def _append_message_log(data: Dict, msg_log: dict):
    data.setdefault('messages', []).append(msg_log)
    if len(data['messages']) > 500:
        data['messages'] = data['messages'][-500:]


_operators_cache = {'data': None, 'time': 0}
_OPERATORS_CACHE_TTL = 300


def _get_operators():
    """获取操作员列表（带内存缓存，TTL=300s）

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_operators.py
    保留此函数作为向后兼容 shim，内部调用 _operators.get_operators
    """
    from ._operators import get_operators as _impl
    return _impl()

def _get_process_template_bindings(process: dict) -> dict:
    bindings = process.get('template_bindings', {})
    defaults = dict(PROCESS_TEMPLATE_DEFAULTS)
    defaults.update(bindings)
    return defaults


def _sync_work_order_status(order_no: str, status_key: str, current_step: int = 0, process_id: str = ''):
    """同步流程状态到容器中心工单

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_sync.py
    保留此函数作为向后兼容 shim，内部调用 _sync.sync_work_order_status
    """
    from ._sync import sync_work_order_status as _impl
    _impl(order_no, status_key, current_step, process_id)


def _sync_to_mysql(order_no: str, completed_step_status: str, lead_time: int = None):
    """同步流程状态到 MySQL production_orders 和 orders 表

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_sync.py
    保留此函数作为向后兼容 shim，内部调用 _sync.sync_to_mysql
    """
    from ._sync import sync_to_mysql as _impl
    _impl(order_no, completed_step_status, lead_time)


def _sync_schedule_to_container(order_no: str, process: dict, lead_time: int, operator_name: str):
    """同步排产数据到容器中心的 schedule_records 和 process_records"""
    try:
        cc = _get_container_center()
        if not cc or not hasattr(cc, 'storage'):
            logger.warning("[容器中心同步] 获取容器中心实例失败")
            return

        storage = cc.storage
        now = datetime.now().isoformat()
        plan_start = datetime.now().strftime('%Y-%m-%d')
        plan_end = (datetime.now() + timedelta(days=int(lead_time))).strftime('%Y-%m-%d')

        schedule_id = f"SCH-{uuid.uuid4().hex[:8].upper()}"
        record = {
            'schedule_id': schedule_id,
            'order_no': order_no,
            'status': 'confirmed',
            'product_name': process.get('product_name', ''),
            'quantity': process.get('quantity', 0),
            'delivery_date': plan_end,
            'priority': process.get('priority', 'normal'),
            'source': 'dispatch_center',
            'schedule_data': json.dumps({
                'plan_start': plan_start,
                'plan_end': plan_end,
                'lead_time': lead_time,
                'order_no': process.get('order_no', order_no),
            }, ensure_ascii=False),
            'confirmed_at': now,
            'confirmed_by': operator_name,
            'confirm_comments': process.get('schedule_remark', f'已确认排产，工期{lead_time}天'),
            'created_at': now,
            'updated_at': now,
        }
        storage.save_schedule_record(record)
        logger.info(f"[容器中心同步] 排产记录已保存: schedule_id={schedule_id}, order_no={order_no}, plan={plan_start}~{plan_end}")

        existing = storage.get_process_record_by_order(order_no)
        if existing:
            customer_group = _get_customer_group_for_order(order_no)
            existing['customer_name'] = customer_group or existing.get('customer_name', '')
            # [F6 P9 2026-06-10] 同步补写 customer_group 字段, 修复手机端 customerGroup 显示空 bug
            # 手机端 [schedule_routes.py:943] 读 r.get('customer_group'), 之前漏写导致永远空
            existing['customer_group'] = customer_group or existing.get('customer_group', '')
            existing['delivery_date'] = plan_end
            existing['updated_at'] = now
            storage.save_process_record(existing)
            logger.info(f"[容器中心同步] process_records 已更新: order_no={order_no}, delivery_date={plan_end}")

        cc.sync_schedule_to_mysql(
            order_no=order_no,
            lead_time=lead_time,
            completed_step_status='confirmed'
        )
    except Exception as e:
        logger.warning(f"[容器中心同步] 排产数据同步失败: {e}")


def _build_confirmation_variables(process: dict, next_step: dict, flow_template: dict, operator_name: str) -> dict:
    order_no = process.get('order_no', '')
    variables = {
        '订单号': order_no,
        '流程名称': flow_template.get('name', process.get('flow_type', '')),
        '当前步骤': next_step.get('name', ''),
        '执行人': operator_name,
    }
    if order_no:
        try:
            cc_packages = _get_cached_work_orders(page=1, size=2000) or []
            cc_items = cc_packages if isinstance(cc_packages, list) else (cc_packages.get('items', cc_packages.get('data', [])) if isinstance(cc_packages, dict) else [])
            for item in cc_items:
                if not isinstance(item, dict):
                    continue
                item_data = _get_doc_data(item)
                item_order_no = item_data.get('order_no', item.get('order_no', ''))
                item_related = item_data.get('related_order', item.get('related_order', ''))
                if item_order_no == order_no or item_related == order_no:
                    variables['产品'] = item_data.get('product_name', item.get('product_name', ''))
                    variables['数量'] = item_data.get('quantity', 0)
                    break
        except Exception as e:
            logger.warning(f"[确认通知] 获取工单 {order_no} 详情失败: {e}")
    return variables


def _notify_with_template(process_id: str, template_id: str, variables: dict,
                         target_operator: str = '', send_to_group: bool = True) -> (bool, str):
    """模板通知

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_notify.py
    保留此函数作为向后兼容 shim，内部调用 _notify.notify_with_template
    """
    from ._notify import notify_with_template as _impl
    return _impl(
        template_id=template_id,
        variables=variables,
        target_operator=target_operator,
        send_to_group=send_to_group
    )


def _notify_process_event(order_no: str, event_type: str, variables: dict,
                         target_operator: str = '', send_to_group: bool = True) -> (bool, str):
    """流程事件通知

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_notify.py
    保留此函数作为向后兼容 shim，模板绑定逻辑仍保留在 _core.py 中
    """
    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    process = next((p for p in processes if p.get('order_no') == order_no), None)
    if not process:
        return False, f"流程不存在: {order_no}"
    bindings = _get_process_template_bindings(process)
    template_id = bindings.get(event_type)
    if not template_id:
        return False, f"事件 {event_type} 未绑定模板"

    from ._notify import notify_process_event as _impl
    return _impl(
        template_id=template_id,
        variables=variables,
        order_no=order_no,
        target_operator=target_operator,
        send_to_group=send_to_group
    )


def _send_wechat_app_message(content: str, operator_id: str = None):
    """发送应用消息到微信（仅通过云端 relay）

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_notify.py
    保留此函数作为向后兼容 shim，内部调用 _notify._send_wechat_app_message
    """
    from ._notify import _send_wechat_app_message as _impl
    return _impl(content, operator_id)


def _send_to_department_members(department: str, content: str, msg_type: str = 'text') -> Dict[str, Any]:
    """
    发送给部门所有成员

    Args:
        department: 部门名称
        content: 消息内容
        msg_type: 消息类型 (text/markdown)

    Returns:
        发送结果统计 {'success': 成功数, 'failed': 失败数, 'total': 总数}
    """
    try:
        dept_operators = _get_client().get_operators(department=department)
        if not dept_operators:
            logger.warning(f"部门 '{department}' 没有成员")
            return {'success': 0, 'failed': 0, 'total': 0}

        success_count = 0
        fail_count = 0

        for op in dept_operators:
            if not op.get('notify_enabled', True):
                continue
            try:
                ok, _ = _send_wechat_app_message(content, op.get('id'))
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"发送给部门成员 {op.get('id', 'unknown')} 失败: {e}")
                fail_count += 1

        logger.info(f"部门 '{department}' 消息发送完成: 成功 {success_count}, 失败 {fail_count}")
        return {'success': success_count, 'failed': fail_count, 'total': len(dept_operators)}

    except Exception as e:
        logger.error(f"发送部门消息异常: {e}")
        return {'success': 0, 'failed': 0, 'total': 0}

def _send_desktop_callback(event_type: str, data: Dict):
    try:
        from container_center.desktop_callback import desktop_callback_manager
        if hasattr(desktop_callback_manager, 'enqueue_callback'):
            desktop_callback_manager.enqueue_callback(event_type, data)
            return True
    except (ImportError, AttributeError):
        pass
    return False


dispatch_center_bp = Blueprint('dispatch_center', __name__, url_prefix='/api/dispatch-center')

# ───── 全局异常兜底 ─────
@dispatch_center_bp.errorhandler(Exception)
def _handle_unhandled(e):
    import traceback, logging
    logging.getLogger('dispatch_center').exception(f'[UNHANDLED] {request.path}')
    return jsonify({'code': 500, 'message': '内部错误，已记录'}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Part 4: 通知与消息路由 (行 1428~1629)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/task-notify', methods=['POST'])
def task_notify():
    body = request.get_json(force=True, silent=True) or {}
    event_type = body.get('event_type', 'unknown')
    order_no = body.get('order_no', '')
    order_no = body.get('order_no', '')
    task_id = body.get('task_id', '')
    source = body.get('source', '')
    process = body.get('process', '')
    operator_id = body.get('operator_id', '')
    operator_name = body.get('operator_name', '')
    quantity = body.get('quantity', 0)
    timestamp = body.get('timestamp', datetime.now().isoformat())

    logger.info(f'[task-notify] 收到新任务通知: event={event_type}, order={order_no}, '
                f'work_order={order_no}, task_id={task_id}, source={source}')

    task_record = {
        'task_id': task_id or str(uuid.uuid4())[:8].upper(),
        'process': process,
        'operator_id': operator_id,
        'operator_name': operator_name,
        'quantity': quantity,
        'status': 'pending',
        'source': source,
        'event_type': event_type,
        'created_at': datetime.now().isoformat(),
        'published_at': None,
        'received_at': datetime.now().isoformat(),
    }

    # 写入 process_packages — operator_id 是标记(谁提交的), 不是指派
    target_op = operator_id or ''
    try:
        cc = _get_container_center()
        if cc and hasattr(cc, 'storage'):
            cc.storage.insert('process_packages', {
                'id': task_record['task_id'],
                'title': f"{order_no} - {process}",
                'status': 'pending',
                'flow_type': 'production',
                'order_no': order_no,
                'related_order': order_no,
                'related_process': process,
                'process_name': process,
                'target_operator': target_op,
                'source': source,
                'content': json.dumps(task_record, ensure_ascii=False),
                'created_at': task_record['created_at'],
            })
    except Exception as e:
        logger.warning(f'[task-notify] 持久化到 process_packages 失败: {e}')

    data = _dispatch_cache.get_data()
    auto_send = data.get('auto_send', True)

    if auto_send:
        logger.info(f'[task-notify] 自动发送已开启，执行发送')
        _do_send_process_task(task_record)
    else:
        logger.info(f'[task-notify] 自动发送已关闭，等待手动发送')

    # 紧急任务 / 延期任务 通知
    try:
        if event_type == 'urgent':
            msg = _render_template('tmpl_task_urgent', {
                '标题': f'{order_no} - {process}',
                '订单号': order_no,
                '数量': quantity,
            })
            _send_wechat_message(msg, 'markdown')
        elif event_type == 'delay':
            msg = _render_template('tmpl_task_delay', {
                '标题': f'{order_no} - {process}',
                '订单号': order_no,
            })
            _send_wechat_message(msg, 'markdown')
    except Exception as e:
        logger.warning(f'[task-notify] 任务通知发送失败: {e}')

    return jsonify({'code': 0, 'message': '任务已接收', 'task_id': task_record['task_id'], 'auto_sent': auto_send})


def _get_department_members(department_name: str):
    """获取部门成员

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_operators.py
    保留此函数作为向后兼容 shim，内部调用 _operators.get_department_members
    """
    from ._operators import get_department_members as _impl
    return _impl(department_name)


def _do_send_process_task(task_record: dict):
    """发送工序任务通知

    接收人规则：
    - 指定任务（有 target_operator）：只发给指定人
    - 全员任务（无 target_operator）：只发群
    """
    data = _dispatch_cache.get_data()

    # 获取任务负责人
    target_operator = task_record.get('target_operator', '')
    is_assigned_task = bool(target_operator)

    try:
        operator_name = task_record.get('operator_name', task_record.get('operator_id', ''))
        content = _render_template('tmpl_task_assigned', {
            '操作员': operator_name,
            '任务标题': task_record.get('process', ''),
            '订单号': task_record.get('order_no', ''),
            '工序': task_record.get('process', ''),
            '数量': task_record.get('quantity', ''),
        })
    except Exception as e:
        logger.warning(f'[发送] 模板格式化失败: {e}')
        content = str(task_record.get('process', ''))

    process = task_record.get('process', '')
    task_id = task_record.get('task_id', '')

    if is_assigned_task:
        # 指定任务：只发给任务负责人
        recipients = [target_operator]
        ok, err = _send_wechat_app_message(content, target_operator)
        if ok:
            logger.info(f'[发送] 指定任务已发送: task_id={task_id}, 负责人={target_operator}')
        else:
            logger.warning(f'[发送] 指定任务发送失败: {err}')
    else:
        # 全员任务：只发群
        recipients = ['@all']
        ok, err = _send_wechat_message(content, 'markdown')
        if ok:
            logger.info(f'[发送] 全员任务已发群: task_id={task_id}')
        else:
            logger.warning(f'[发送] 全员任务发群失败: {err}')

    _dispatch_cache.update_data(lambda d: [
        (t.update({'status': 'sent', 'published_at': datetime.now().isoformat(), 'recipients': recipients}))
        for t in d.get('process_tasks', []) if t.get('task_id') == task_id
    ])

    # 同步更新 process_packages 状态
    try:
        cc = _get_container_center()
        if cc and hasattr(cc, 'storage') and hasattr(cc.storage, 'update'):
            cc.storage.update('process_packages', {
                'status': 'distributed', 'distributed_at': datetime.now().isoformat(),
            }, 'id=%s', (task_id,))
    except Exception as e:
        logger.warning(f'[发送] 更新 process_packages 状态失败: {e}')

    logger.info(f'[发送] 工序任务已发送，类型: {"指定" if is_assigned_task else "全员"}，目标: {recipients}')
    return True, ''


# ═══════════════════════════════════════════════════════════════════════════════
# Part 5: 流程任务路由 (行 1630~1799)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/process-tasks', methods=['GET'])
def get_process_tasks():
    data = _dispatch_cache.get_data()
    tasks = data.get('process_tasks', [])
    process_filter = request.args.get('process', '')
    status_filter = request.args.get('status', '')
    if process_filter:
        tasks = [t for t in tasks if t.get('process') == process_filter]
    if status_filter:
        tasks = [t for t in tasks if t.get('status') == status_filter]
    return jsonify({'code': 0, 'data': tasks})


@dispatch_center_bp.route('/process-tasks/<task_id>', methods=['DELETE'])
def delete_process_task(task_id):
    _dispatch_cache.update_data(lambda d: [
        d['process_tasks'].remove(t) for t in d.get('process_tasks', [])
        if t.get('task_id') == task_id
    ])
    return jsonify({'code': 0, 'message': '任务已删除'})


@dispatch_center_bp.route('/process-tasks/<task_id>/send', methods=['POST'])
def send_process_task(task_id):
    data = _dispatch_cache.get_data()
    task = None
    for t in data.get('process_tasks', []):
        if t.get('task_id') == task_id:
            task = t
            break
    if not task:
        return jsonify({'code': 1, 'message': '任务不存在'}), 404
    ok, err = _do_send_process_task(task)
    if ok:
        return jsonify({'code': 0, 'message': '发送成功'})
    else:
        return jsonify({'code': 1, 'message': f'发送失败: {err}'}), 500


@dispatch_center_bp.route('/process-tasks/send-all-pending', methods=['POST'])
def send_all_pending():
    """全员派发 — 从 data_packages (MySQL) 读取待发送任务"""
    try:
        result = _get_cached_work_orders(page=1, size=2000)
        packages = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])
        pending = [p for p in packages if isinstance(p, dict) and p.get('status') == 'pending']
    except Exception:
        pending = []
    sent_count = 0
    for pkg in pending:
        # 将 data_packages 字段转换为 _do_send_process_task 所需格式
        task = {
            'order_no': pkg.get('related_order', ''),
            'process': pkg.get('related_process', ''),
            'operator_id': pkg.get('target_operator', ''),
            'operator_name': pkg.get('target_operator', ''),
            'quantity': pkg.get('content', {}).get('quantity', 0) if isinstance(pkg.get('content'), dict) else 0,
            'source': pkg.get('source', ''),
            'created_at': pkg.get('created_at', ''),
            'task_id': pkg.get('id', ''),
        }
        ok, _ = _do_send_process_task(task)
        if ok:
            sent_count += 1
    # 更新受影响订单的 process_records 状态
    affected_orders = set(p.get('related_order', '') for p in pending if isinstance(p, dict))
    try:
        cc = _get_container_center()
        if cc and hasattr(cc, 'storage'):
            for order_no in affected_orders:
                if order_no:
                    cc.storage.update('process_records',
                        {'status': 'dispatched', 'updated_at': datetime.now().isoformat()},
                        'order_no=%s', (order_no,))
    except Exception:
        pass

    # 新流程启动通知 — 每个新订单发一条
    for order_no in affected_orders:
        if not order_no:
            continue
        try:
            order_pkgs = [p for p in pending if p.get('related_order') == order_no]
            first = order_pkgs[0] if order_pkgs else {}
            content = first.get('content', {}) if isinstance(first.get('content'), dict) else {}
            product = content.get('product_name', content.get('product_type', content.get('product', '')))
            processes = [p.get('related_process', '') for p in order_pkgs if p.get('related_process')]
            creator = first.get('source', '') or content.get('creator', '') or '系统'
            msg = _render_template('tmpl_process_start', {
                '流程名称': '、'.join(processes[:3]) + ('等' if len(processes) > 3 else ''),
                '订单号': order_no,
                '产品': product,
                '发起人': creator,
            })
            _send_wechat_message(msg, 'markdown')
        except Exception as e:
            logger.warning(f'[流程启动] 通知发送失败 order={order_no}: {e}')

    return jsonify({'code': 0, 'message': f'已发送 {sent_count}/{len(pending)} 个任务'})


@dispatch_center_bp.route('/process-names', methods=['GET'])
def get_process_names():
    data = _dispatch_cache.get_data()
    tasks = data.get('process_tasks', [])
    process_departments = data.get('process_departments', {})
    process_names = set()

    for t in tasks:
        p = t.get('process', '')
        if p:
            process_names.add(p)
    for p in process_departments.keys():
        if p:
            process_names.add(p)

    # T9 迁移完成: 工序名来源改为 process_sub_steps 表，不再查询 data_packages
    # 架构依据: ARCHITECTURE_v3.6.md 1.10.2 节
    try:
        import pymysql
        from pymysql.cursors import DictCursor
        from storage.mysql_storage import MySQLStorage
        conn = MySQLStorage.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT step_name FROM process_sub_steps WHERE step_name IS NOT NULL AND step_name != ''")
            for row in cursor.fetchall():
                if row.get('step_name'):
                    process_names.add(row['step_name'])
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'[process-names] 从 process_sub_steps 获取工序失败: {e}')

    try:
        cc = _get_container_center()
        if cc and hasattr(cc, 'storage') and cc.storage:
            proc_records = cc.storage.get_all_process_records()
            for rec in proc_records:
                steps = rec.get('steps', [])
                if isinstance(steps, list):
                    for step in steps:
                        if isinstance(step, dict):
                            name = step.get('name', '')
                        elif isinstance(step, str):
                            name = step
                        else:
                            continue
                        if name:
                            process_names.add(name)
    except Exception as e:
        logger.warning(f'[process-names] 从 process_records 获取工序名称失败: {e}')

    # 从 MySQL process_names 获取 display_seq 用于排序
    try:
        from core.config import get_display_seq_map
        seq_map = get_display_seq_map()
        sorted_names = [n for n in sorted(list(process_names), key=lambda n: seq_map.get(n, 99))]
    except Exception:
        sorted_names = sorted(list(process_names))

    return jsonify({'code': 0, 'data': sorted_names})


# ═══════════════════════════════════════════════════════════════════════════════
# Part 6: 模板管理路由 (行 1800~2074)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/templates', methods=['GET'])
def get_templates():
    data = _dispatch_cache.get_data()
    templates = data.get('templates', [])
    current_template = data.get('message_template', '')
    return jsonify({'code': 0, 'data': {'templates': templates, 'current': current_template}})


@dispatch_center_bp.route('/templates', methods=['POST'])
def save_template():
    """新增自定义模板 — 统一写入 MySQL"""
    import time
    body = request.get_json(force=True, silent=True) or {}
    tid = body.get('id') or ('custom_' + str(int(time.time())))
    return update_template(tid)


@dispatch_center_bp.route('/templates/<path:template_id>', methods=['PUT'])
def update_template(template_id):
    """修改模板 — 内置模板不可改, 乐观锁"""
    body = request.get_json(force=True, silent=True) or {}
    content = (body.get('content') or '').strip()
    client_version = body.get('version', 0)
    is_builtin = any(t['id'] == template_id for t in MESSAGE_TEMPLATES_DEFAULT)
    if is_builtin:
        return jsonify({'code': 403, 'message': '内置模板不可修改'}), 403
    force_by_assignee = body.get('force_by_assignee', False)
    try:
        c = _get_mysql_connection()
        cur = c.cursor()
        cur.execute('SELECT version FROM message_templates WHERE id=%s', (template_id,))
        row = cur.fetchone()
        if row and row[0] and client_version != row[0]:
            c.close()
            return jsonify({'code': 409, 'message': '版本冲突'}), 409
        if not content or len(content) < 10:
            c.close()
            return jsonify({'code': 400, 'message': '模板内容不能为空且至少10字符'}), 400
        cur.execute('''INSERT INTO message_templates (id, name, category, content, version)
                       VALUES (%s,%s,%s,%s,1) ON DUPLICATE KEY UPDATE
                       content=VALUES(content), version=version+1, updated_at=NOW()''',
                    (template_id, body.get('name', ''), body.get('category', 'custom'), content))
        c.commit()
        if force_by_assignee:
            import json as _json
            cur.execute('''INSERT INTO notification_recipient_preset (scenario, receivers, enabled, force_by_assignee)
                           VALUES (%s, %s, 1, 1)
                           ON DUPLICATE KEY UPDATE force_by_assignee=1, enabled=1''',
                        (template_id, _json.dumps([], ensure_ascii=False)))
            c.commit()
        c.close()
        return jsonify({'code': 0, 'message': '模板已更新'})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/templates/<path:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """软删模板 — 内置模板禁止"""
    # 内置模板从内存判断，在 DB 连接前直接拒绝
    if any(t['id'] == template_id for t in MESSAGE_TEMPLATES_DEFAULT):
        return jsonify({'code': 403, 'message': '内置模板不可删除'}), 403
    try:
        c = _get_mysql_connection()
        cur = c.cursor()
        cur.execute('UPDATE message_templates SET is_active=0 WHERE id=%s', (template_id,))
        c.commit()
        c.close()
        return jsonify({'code': 0, 'message': '模板已停用'})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/templates/<path:template_id>/reset', methods=['POST'])
def reset_template(template_id):
    """恢复内置默认 — 从 MESSAGE_TEMPLATES_DEFAULT 重新加载"""
    template = next((t for t in MESSAGE_TEMPLATES_DEFAULT if t.get('id') == template_id), None)
    if not template:
        return jsonify({'code': 404, 'message': '模板不存在'}), 404
    try:
        c = _get_mysql_connection()
        cur = c.cursor()
        cur.execute('''INSERT INTO message_templates (id, name, category, content, is_builtin, is_active, version)
                       VALUES (%s,%s,%s,%s,1,1,1) ON DUPLICATE KEY UPDATE
                       content=VALUES(content), is_active=1, version=version+1, updated_at=NOW()''',
                    (template_id, template['name'], template['category'], template['content']))
        c.commit()
        c.close()
        return jsonify({'code': 0, 'message': '模板已恢复默认'})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/templates/emergency-fallback', methods=['GET'])
def emergency_fallback():
    """紧急降级开关 — 运行时切换, 无需重启"""
    import template_engine
    current = getattr(template_engine, '_fallback_only', False)
    new_state = not current
    template_engine._fallback_only = new_state
    return jsonify({'code': 0, 'message': f'已切换: fallback_only={new_state}'})


@dispatch_center_bp.route('/templates/status', methods=['GET'])
def templates_status():
    """模板系统状态"""
    import template_engine
    fallback = getattr(template_engine, '_fallback_only', False)
    return jsonify({'code': 0, 'data': {
        'mode': 'builtin_only' if fallback else 'mysql_priority',
        'builtin_count': len(MESSAGE_TEMPLATES_DEFAULT),
        'fallback_active': fallback,
    }})


def _get_violation_conn():
    """获取 violation_log 数据库连接

    [P0-1 修复 2026-06-13] 改读 container_center.violations_local
    镜像表同步：通过 8008 sync_bridge 双写
    """
    return _get_mysql_connection()  # [T4 2026-06-14] 走连接池


@dispatch_center_bp.route('/violations', methods=['GET'])
def list_violations():
    """[R13 T13] 查询违规日志列表"""
    import pymysql
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    scenario = request.args.get('scenario', '')
    severity = request.args.get('severity', '')
    offset = (page - 1) * page_size
    try:
        conn = _get_violation_conn()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        where = 'WHERE 1=1'
        params = []
        if scenario:
            where += ' AND scenario=%s'
            params.append(scenario)
        if severity:
            where += ' AND severity=%s'
            params.append(severity)
        cur.execute(f'SELECT id, scenario, violation_type, severity, order_no, detail, created_at FROM violations_local {where} ORDER BY id DESC LIMIT %s OFFSET %s', params + [page_size, offset])
        rows = cur.fetchall()
        cur.execute(f'SELECT COUNT(*) as total FROM violations_local {where}', params)
        total = cur.fetchone()['total']
        cur.close(); conn.close()
        return jsonify({'code': 0, 'data': {'rows': rows, 'total': total, 'page': page, 'page_size': page_size}})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/violations/stats', methods=['GET'])
def violation_stats():
    """[R13 T13] 违规统计"""
    import pymysql
    try:
        conn = _get_violation_conn()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute('SELECT violation_type, COUNT(*) as cnt FROM violations_local GROUP BY violation_type ORDER BY cnt DESC')
        by_type = [{'type': r['violation_type'], 'count': r['cnt']} for r in cur.fetchall()]
        cur.execute('SELECT severity, COUNT(*) as cnt FROM violations_local GROUP BY severity')
        by_severity = [{'severity': r['severity'], 'count': r['cnt']} for r in cur.fetchall()]
        cur.execute('SELECT COUNT(*) as total FROM violations_local')
        total = cur.fetchone()['total']
        cur.execute('SELECT COUNT(*) as today FROM violations_local WHERE DATE(created_at)=CURDATE()')
        today = cur.fetchone()['today']
        cur.close(); conn.close()
        return jsonify({'code': 0, 'data': {'total': total, 'today': today, 'by_type': by_type, 'by_severity': by_severity}})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/violations/recent', methods=['GET'])
def recent_violations():
    """[R13 T13] 最近违规（最近 20 条）"""
    import pymysql
    limit = request.args.get('limit', 20, type=int)
    try:
        conn = _get_violation_conn()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute('SELECT id, scenario, violation_type, severity, order_no, detail, created_at FROM violation_log ORDER BY id DESC LIMIT %s', (limit,))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify({'code': 0, 'data': rows})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/violations', methods=['DELETE'])
def clear_violations():
    """[R13 T13] 清空违规日志"""
    try:
        conn = _get_violation_conn()
        cur = conn.cursor()
        cur.execute('TRUNCATE TABLE violation_log')
        conn.commit()
        cur.close(); conn.close()
        return jsonify({'code': 0, 'message': '违规日志已清空'})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/notification/presets', methods=['GET'])
def list_notification_presets():
    """[R13 T12/T13] 查询所有通知接收人预设"""
    try:
        from mobile_api_ai.notification_preset_service import NotificationPresetService
        svc = NotificationPresetService()
        presets = svc.list_all_presets()
        return jsonify({'code': 0, 'data': presets})
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/notification/presets/<scenario>', methods=['PUT'])
def update_notification_preset(scenario):
    """[R13 T12/T13] 更新某场景的接收人预设"""
    body = request.get_json(force=True, silent=True) or {}
    receivers = body.get('receivers', [])
    enabled = body.get('enabled', True)
    force_by_assignee = body.get('force_by_assignee', False)
    try:
        from mobile_api_ai.notification_preset_service import NotificationPresetService
        svc = NotificationPresetService()
        ok = svc.set_receivers_for_scenario(scenario, receivers, enabled, force_by_assignee)
        if ok:
            return jsonify({'code': 0, 'message': '预设已更新'})
        return jsonify({'code': 1, 'message': '更新失败'}), 500
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/notification/presets/<scenario>', methods=['DELETE'])
def delete_notification_preset(scenario):
    """[R13 T12/T13] 删除某场景的接收人预设"""
    try:
        from mobile_api_ai.notification_preset_service import NotificationPresetService
        svc = NotificationPresetService()
        ok = svc.delete_preset(scenario)
        if ok:
            return jsonify({'code': 0, 'message': '预设已删除'})
        return jsonify({'code': 1, 'message': '删除失败'}), 500
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/notification/presets/<scenario>/toggle', methods=['POST'])
def toggle_notification_preset(scenario):
    """[R13 T12/T13] 启用/禁用某场景预设"""
    body = request.get_json(force=True, silent=True) or {}
    enabled = body.get('enabled', True)
    try:
        from mobile_api_ai.notification_preset_service import NotificationPresetService
        svc = NotificationPresetService()
        ok = svc.toggle_enabled(scenario, enabled)
        if ok:
            return jsonify({'code': 0, 'message': f'预设已{"启用" if enabled else "禁用"}'})
        return jsonify({'code': 1, 'message': '操作失败'}), 500
    except Exception as e:
        return jsonify({'code': 1, 'message': "操作失败，请稍后重试"}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Part 7: 违规与配置路由 (行 2075~2466)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/global-config', methods=['GET'])
def get_global_config():
    data = _dispatch_cache.get_data()
    config = {
        'auto_send': data.get('auto_send', True),
        'message_template': data.get('message_template', ''),
        'process_departments': data.get('process_departments', {}),
        'department_managers': data.get('department_managers', {}),
        'default_to_all': data.get('default_to_all', True),
    }
    return jsonify({'code': 0, 'data': config})


# ───── 容器中心代理 ─────
CC_BASE: str = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
# [Bug Fix 2026-06-20] 优先级扩展为 CONTAINER_CENTER_API_KEY > API_KEY > WECHAT_CLOUD_API_KEY
# 之前只读前两个，但 .env 中只有 WECHAT_CLOUD_API_KEY，导致 5002 401 拒绝
_CC_API_KEY: str = (
    os.environ.get('CONTAINER_CENTER_API_KEY', '')
    or os.environ.get('API_KEY', '')
    or os.environ.get('WECHAT_CLOUD_API_KEY', '')
)


def _cc_headers() -> dict:
    """容器中心 API 请求头（含鉴权）"""
    headers = {'Content-Type': 'application/json'}
    if _CC_API_KEY:
        headers['X-API-Key'] = _CC_API_KEY
    return headers


@dispatch_center_bp.route('/cc-api/process-names', methods=['GET'])
def cc_proxy_process_names():
    try:
        resp = requests.get(f'{CC_BASE}/api/process_names', headers=_cc_headers(), timeout=3)
        return jsonify(resp.json())
    except Exception:
        return jsonify({'code': 0, 'data': {}})

_pd_cache = {'data': {}, 'time': 0}
_PD_CACHE_TTL = 300


@dispatch_center_bp.route('/cc-api/process-departments', methods=['GET'])
def cc_proxy_process_depts():
    now = time.time()
    if _pd_cache['data'] and (now - _pd_cache['time']) < _PD_CACHE_TTL:
        try:
            data = _dispatch_cache.get_data()
            local_data = (data or {}).get('process_departments', {})
        except Exception:
            local_data = {}
        return jsonify({'code': 0, 'data': {**_pd_cache['data'], **local_data}})
    try:
        resp = requests.get(f'{CC_BASE}/api/process_departments', headers=_cc_headers(), timeout=3)
        cc_data = resp.json().get('data', {})
    except Exception:
        cc_data = {}
    _pd_cache['data'] = cc_data
    _pd_cache['time'] = now
    try:
        data = _dispatch_cache.get_data()
        local_data = (data or {}).get('process_departments', {})
    except Exception:
        local_data = {}
    merged = {**cc_data, **local_data}
    return jsonify({'code': 0, 'data': merged})

@dispatch_center_bp.route('/cc-api/process-departments/<path:code>', methods=['POST', 'PUT', 'DELETE'])
def cc_proxy_process_dept_op(code):
    try:
        headers = _cc_headers()
        if request.method == 'DELETE':
            resp = requests.delete(f'{CC_BASE}/api/process_departments/{code}', headers=headers, timeout=3)
        else:
            body = request.get_json(force=True, silent=True) or {}
            resp = requests.post(f'{CC_BASE}/api/process_departments/{code}', json=body, headers=headers, timeout=3)
        return jsonify(resp.json())
    except Exception: return jsonify({"code": 1})

@dispatch_center_bp.route('/global-config', methods=['PUT', 'POST'])
def save_global_config():
    body = request.get_json(force=True, silent=True) or {}

    def update_config(data):
        if 'auto_send' in body:
            data['auto_send'] = body['auto_send']
        if 'message_template' in body:
            data['message_template'] = body['message_template']
        if 'process_departments' in body:
            data['process_departments'] = body['process_departments']
        if 'department_managers' in body:
            data['department_managers'] = body['department_managers']
        if 'default_to_all' in body:
            data['default_to_all'] = body['default_to_all']
        if 'dispatch_mode' in body:
            data['dispatch_mode'] = body['dispatch_mode']
        if 'dispatch_dept' in body:
            data['dispatch_dept'] = body['dispatch_dept']
        data['config_updated_at'] = datetime.now().isoformat()
        return data

    _dispatch_cache.update_data(update_config)
    return jsonify({'code': 0, 'message': '全局配置已保存'})


@dispatch_center_bp.route('/departments', methods=['GET'])
def get_departments():
    try:
        structure_file = DB_PATHS['enterprise_structure']
        with open(structure_file, 'r', encoding='utf-8') as f:
            structure = json.load(f)
        departments = structure.get('departments', [])
        dept_list = [{'id': d.get('id'), 'name': d.get('name'), 'parentid': d.get('parentid')} for d in departments]
        return jsonify({'code': 0, 'data': dept_list})
    except Exception as e:
        logger.warning(f'[departments] 获取部门失败: {e}')
        return jsonify({'code': 0, 'data': []})


@dispatch_center_bp.route('/all-departments-flat', methods=['GET'])
def get_all_departments_flat():
    """获取所有部门（包含子部门的完整路径名称）"""
    try:
        structure_file = DB_PATHS['enterprise_structure']
        with open(structure_file, 'r', encoding='utf-8') as f:
            structure = json.load(f)
        departments = structure.get('departments', [])
        if not isinstance(departments, list):
            departments = []
        dept_map = {d.get('id'): d.get('name', '') for d in departments if isinstance(d, dict)}
        def build_path(dept):
            if not isinstance(dept, dict):
                return ''
            name = dept.get('name', '')
            pid = dept.get('parentid')
            if pid and pid in dept_map:
                parent = next((d for d in departments if d.get('id') == pid), None)
                if parent:
                    return build_path(parent) + ' / ' + name
            return name
        flat_list = []
        for d in departments:
            if isinstance(d, dict):
                full_path = build_path(d)
                flat_list.append({
                    'id': d.get('id'),
                    'name': d.get('name', ''),
                    'full_path': full_path,
                    'parentid': d.get('parentid', 0)
                })
        return jsonify({'code': 0, 'data': flat_list})
    except Exception as e:
        logger.warning(f'[all-departments-flat] 获取部门失败: {e}')
        return jsonify({'code': 0, 'data': []})


@dispatch_center_bp.route('/departments/<department>/managers', methods=['GET'])
def get_department_managers(department):
    data = _dispatch_cache.get_data()
    managers = data.get('department_managers', {}).get(department, [])
    return jsonify({'code': 0, 'data': managers})


@dispatch_center_bp.route('/departments/<department>/managers', methods=['PUT', 'POST'])
def save_department_managers(department):
    body = request.get_json(force=True, silent=True) or {}
    managers = body.get('managers', [])
    _dispatch_cache.update_data(lambda d: d.setdefault('department_managers', {}).update({
        department: managers
    }))
    return jsonify({'code': 0, 'message': f'部门"{department}"负责人已保存'})



@dispatch_center_bp.route('/process-departments/<process>', methods=['PUT', 'POST'])
def save_process_department(process):
    body = request.get_json(force=True, silent=True) or {}
    department = body.get('department', '')
    _dispatch_cache.update_data(lambda d: d.setdefault('process_departments', {}).update({
        process: department
    }), sync=True)
    # 同步保存到容器中心
    try:
        requests.post(f'{CC_BASE}/api/process_departments/{process}', json={'department': department}, timeout=3)
    except Exception:
        pass
    return jsonify({'code': 0, 'message': f'工序"{process}"已绑定部门"{department}"'})


@dispatch_center_bp.route('/process-departments/<process>', methods=['DELETE'])
def delete_process_department(process):
    try:
        _dispatch_cache.update_data(lambda d: d.get('process_departments', {}).pop(process, None))
        # 同步删除容器中心（不可达时不阻塞本地操作）
        try:
            requests.delete(f'{CC_BASE}/api/process_departments/{process}', timeout=3)
        except Exception:
            pass
        return jsonify({'code': 0, 'message': f'工序"{process}"绑定已删除'})
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500



@dispatch_center_bp.route('/pending-warehousing', methods=['GET'])
def pending_warehousing():
    """返回待入库工单列表 — 已完成生产但未确认入库的工单"""
    try:
        data = _dispatch_cache.get_data()
        processes = data.get('processes', [])
        warehousing_list = []
        for p in processes:
            if not isinstance(p, dict):
                continue
            status = p.get('status', '')
            # 已完成的流程视为待入库
            if status in ('completed', '已入库'):
                continue  # 已入库的跳过
            # 检查是否有完工入库步骤且已完成
            steps = p.get('steps', [])
            has_warehousing = any(
                (s.get('name', '') if isinstance(s, dict) else '') in ('完工入库', '')
                and (s.get('status', '') if isinstance(s, dict) else '') == 'completed'
                for s in steps
            )
            if not has_warehousing:
                # 简单规则：状态为 in_production 且工序全完成的视为待入库
                all_done = all(
                    (s.get('status', '') if isinstance(s, dict) else '') in ('completed', '已完成')
                    for s in steps
                ) if steps else False
                if not all_done:
                    continue
            warehousing_list.append({
                'order_no': p.get('order_no', ''),
                'product_name': p.get('product_name', ''),
                'quantity': p.get('quantity', 0),
                'unit': p.get('unit', '米'),
                'customer_name': p.get('customer_name', ''),
            })
        # 补充：从 work_orders_local 表查询已完成生产待入库的单
        # [N2 修复 2026-06-13] 改读本地表（消除跨库直查）
        try:
            conn = _get_mysql_connection()
            if conn:
                try:
                    c = conn.cursor()
                    c.execute("SELECT order_no, customer_name, product_name, quantity FROM work_orders_local WHERE status IN ('生产完成','completed') AND is_deleted=0")
                    for row in c.fetchall():
                        if not any(w['order_no'] == row['order_no'] for w in warehousing_list):
                            warehousing_list.append({
                                'order_no': row['order_no'] or '',
                                'customer_name': row['customer_name'] or '',
                                'product_name': row['product_name'] or '',
                                'quantity': row['quantity'] or 0,
                                'unit': '米',
                            })
                finally:
                    conn.close()
        except Exception:
            pass
        return jsonify({'code': 0, 'data': warehousing_list})
    except Exception as e:
        logger.warning(f'[pending-warehousing] 查询失败: {e}')
        return jsonify({'code': 0, 'data': []})


@dispatch_center_bp.route('/')
def index():
    from flask import request
    return render_template('dispatch_center.html',
        WECHAT_CLOUD_API_KEY=os.getenv('WECHAT_CLOUD_API_KEY', ''),
        container_center_url=request.url_root.rstrip('/'))


@dispatch_center_bp.route('/container-stats')
def container_stats_proxy():
    """反向代理：同源前端 → 5002 容器中心，避免 CORS"""
    import requests as _req
    try:
        key = os.getenv('WECHAT_CLOUD_API_KEY', '')
        resp = _req.get(
            'http://127.0.0.1:5002/container/api/stats',
            headers={'X-API-Key': key},
            timeout=15
        )
        return resp.text, resp.status_code, {'Content-Type': 'application/json'}
    except _req.exceptions.Timeout:
        logger.warning('[container-stats proxy] 5002 超时')
        return jsonify({'code': -1, 'message': '容器中心响应超时'}), 504
    except Exception as e:
        logger.warning(f'[container-stats proxy] 失败: {e}')
        return jsonify({'code': -1, 'message': '请求失败，请稍后重试'}), 502


@dispatch_center_bp.route('/status')
def get_status():
    data = _dispatch_cache.get_data()
    stats = {'tasks': {'pending': 0, 'dispatched': 0, 'in_progress': 0, 'completed': 0, 'overdue': 0},
             'operators': [], 'processes': [], 'alerts': []}

    try:
        result = _get_cached_work_orders(page=1, size=2000)
        packages = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])
        for pkg in packages:
            if not isinstance(pkg, dict):
                continue
            status = pkg.get('status', 'pending')
            if status in stats['tasks']:
                stats['tasks'][status] += 1
            else:
                stats['tasks']['pending'] += 1
    except Exception as e:
        logger.error(f'获取存储统计失败: {e}')

    pending_count = stats['tasks']['pending']
    dispatched_count = stats['tasks']['dispatched']
    in_progress_count = stats['tasks']['in_progress']
    completed_count = stats['tasks']['completed']
    overdue_count = stats['tasks']['overdue']
    total = pending_count + dispatched_count + in_progress_count + completed_count + overdue_count

    operators = _get_operators()
    operator_stats = []
    # 从 packages 和 processes 计算真实负载
    op_active = {}; op_completed = {}
    for pkg in packages:
        if not isinstance(pkg, dict): continue
        op = (pkg.get('target_operator') or '').strip()
        if not op: continue
        st = pkg.get('status', '')
        if st in ('distributed', 'in_progress', 'pending'):
            op_active[op] = op_active.get(op, 0) + 1
        elif st == 'completed':
            op_completed[op] = op_completed.get(op, 0) + 1
    for op_id, op_info in operators.items():
        operator_stats.append({
            'id': op_id,
            'name': op_info.get('name', op_id),
            'role': op_info.get('role', ''),
            'active_tasks': op_active.get(op_id, 0),
            'completed_today': op_completed.get(op_id, 0),
        })

    # 从引擎统计读取真实告警数（优先），否则回退 dispatch_cache
    active_alerts = 0
    try:
        eng = DispatchContext.get_instance().alert_engine
        if eng is not None:
            active_alerts = eng.get_stats().get('today_fired', 0)
    except Exception:
        active_alerts = len(data.get('alerts', []))
    # 计算待入库数量
    pending_wh = 0
    for p in data.get('processes', []):
        if not isinstance(p, dict): continue
        if p.get('status') in ('completed', '已完成'):
            pending_wh += 1

    return jsonify({
        'code': 0,
        'data': {
            'summary': {
                'total': total,
                'pending': pending_count,
                'dispatched': dispatched_count,
                'in_progress': in_progress_count,
                'completed': completed_count,
                'overdue': overdue_count,
                'completion_rate': round(completed_count / total * 100, 1) if total > 0 else 0,
            },
            'operators': operator_stats,
            'active_processes': len(data.get('processes', [])),
            'active_alerts': active_alerts,
            'total_templates': len(data.get('templates', [])),
            'pending_warehousing': pending_wh,
            'system_health': {
                'cloud_connected': _is_cloud_reachable(),
                'container_center_connected': DispatchContext.get_instance().is_cc_reachable(),
                'mysql_connected': _is_mysql_reachable(),
                'alert_engine': _get_alert_engine_health(),
            },
        }
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Part 8: 任务管理路由 (行 2467~2888)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """任务列表 — 数据源: 独立任务表 (v3.6.1 重构)

    从 data_packages 迁移到独立任务表：
    - process_sub_steps (生产工序)
    - quality_records (质检记录)
    - repair_records (维修记录)
    - outsource_records (外协记录)
    - material_records (物料记录)
    """
    status_filter = request.args.get('status')
    operator_filter = request.args.get('operator')
    task_type_filter = request.args.get('type')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    offset = (page - 1) * page_size

    tasks = []
    total = 0

    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()

        # 任务类型到表的映射（含时间字段名）
        TYPE_TABLE_MAP = {
            'report':   ('process_sub_steps', 'operator', 'step_name', 'created_at'),
            'process':  ('process_sub_steps', 'operator', 'step_name', 'created_at'),
            'quality':  ('quality_records',   'inspector','process_name','record_date'),
            'material': ('material_records',  'target_operator','material_name','created_at'),
            'repair':   ('repair_records',    'target_operator','title','created_at'),
            'outsource':('outsource_records', 'target_operator','title','created_at'),
        }

        # 决定查询哪些表
        if task_type_filter and task_type_filter in TYPE_TABLE_MAP:
            tables_to_query = [(task_type_filter, *TYPE_TABLE_MAP[task_type_filter])]
        else:
            tables_to_query = [(name, *cfg) for name, cfg in TYPE_TABLE_MAP.items()]

        for type_name, table, operator_field, title_field, time_field in tables_to_query:
            where_clauses = []
            params = []
            if status_filter:
                where_clauses.append("status=%s")
                params.append(status_filter)
            if operator_filter:
                where_clauses.append(f"{operator_field}=%s")
                params.append(operator_filter)
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 查询总数
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_sql}", params)
            total += cur.fetchone()[0]

            # 查询数据（用表专属时间字段）
            cur.execute(
                f"SELECT id, order_no, {title_field} as title, {operator_field} as operator, "
                f"status, {time_field} as created_at FROM {table} WHERE {where_sql} "
                f"ORDER BY {time_field} DESC LIMIT %s OFFSET %s",
                params + [page_size, offset])
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                row_dict = dict(zip(cols, row))
                tasks.append({
                    'id': row_dict.get('id', ''),
                    'type': type_name,
                    'title': row_dict.get('title', ''),
                    'status': row_dict.get('status', 'pending'),
                    'priority': 'normal',
                    'order_no': row_dict.get('order_no', ''),
                    'process': row_dict.get('title', ''),
                    'process_code': '',
                    'operator': row_dict.get('operator', ''),
                    'dispatched_to': '-',
                    'source': '',
                    'created_at': str(row_dict.get('created_at', ''))[:19],
                    'distributed_at': '',
                    'acknowledged_at': '',
                    'completed_at': '',
                })

        conn.close()
    except Exception as e:
        logger.error(f'获取任务列表失败: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500

    # 按创建时间倒序
    tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return jsonify({'code': 0, 'data': {'tasks': tasks, 'total': total, 'page': page, 'page_size': page_size}})


@dispatch_center_bp.route('/material/requirements', methods=['GET'])
def list_material_requirements():
    """物料短缺列表 — 数据源: steel_belt.order_materials (有 spec/unit 字段, 16 条)

    [P0 修复 2026-06-18 Bug #5] 原代码查 container_center.data_packages, 引用了不存在的
    字段 (title/content/data_type), 端点直接 500 报错. 实际数据源是 steel_belt.order_materials.

    [P0 修复 2026-06-18 Bug #5] 原代码 _get_mysql_connection() 连的是 container_center 库,
    注释说"本地表"误导. order_materials 在 steel_belt 库, 需要开新连接.
    """
    import pymysql
    from pymysql.cursors import DictCursor
    from core.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    try:
        # [P0 修复 2026-06-18] steel_belt 库新连接（order_materials 在 steel_belt, 不在 container_center）
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT,
            user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE, charset='utf8mb4',
            connect_timeout=5)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        # [P0 修复 2026-06-18] order_materials 有 spec/unit 字段
        cur.execute("""
            SELECT om.id, om.order_id, om.material_name, om.spec, om.unit,
                   om.required_qty, om.prepared_qty, om.prep_status,
                   om.warehouse, om.remark, om.created_at, om.updated_at,
                   o.order_no
            FROM order_materials om
            LEFT JOIN orders o ON o.id = om.order_id
            WHERE om.prep_status IN ('待备料', '备料中', '已备料')
            ORDER BY om.created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        records = []
        for r in rows:
            order_no = r.get('order_no') or ''
            material_name = r.get('material_name') or '(未命名)'
            spec = r.get('spec') or ''
            unit = r.get('unit') or ''
            try:
                required_qty = float(r.get('required_qty') or 0)
            except (TypeError, ValueError):
                required_qty = 0.0
            try:
                prepared_qty = float(r.get('prepared_qty') or 0)
            except (TypeError, ValueError):
                prepared_qty = 0.0
            shortage_qty = max(0.0, required_qty - prepared_qty)
            updated = r.get('updated_at') or r.get('created_at')
            if hasattr(updated, 'isoformat'):
                updated = updated.isoformat(sep=' ', timespec='minutes')
            else:
                updated = str(updated or '')
            records.append({
                'order_no': order_no,
                'material_name': material_name,
                'spec': spec,
                'required_qty': required_qty,
                'prepared_qty': prepared_qty,
                'shortage_qty': shortage_qty,
                'unit': unit,
                'updated_at': updated,
                'status': r.get('prep_status', ''),
                'task_id': str(r.get('id', '')),
            })
        logger.info(f'[material/requirements] 缺料 {len(records)} 条 (源 steel_belt.order_materials)')
        return jsonify({'code': 0, 'data': records})
    except Exception as e:
        logger.error(f'获取物料短缺列表失败: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/tasks/<task_id>/assign', methods=['POST'])
def assign_task(task_id):
    body = request.get_json(force=True, silent=True) or {}
    operator_id = body.get('operator_id')
    if not operator_id:
        return jsonify({'code': 400, 'message': '缺少 operator_id'}), 400

    try:
        result = _get_client().distribute(task_id, operator_id)
        if result and result.get('distributed'):
            operators = _get_operators()
            op_info = operators.get(operator_id, {})
            op_name = op_info.get('name', operator_id)
            op_department = op_info.get('department', '')

            pkg_dict = _get_client().get_document('work_order', task_id)
            order_no = pkg_dict.get('related_order', '') if pkg_dict else ''
            title = pkg_dict.get('title', '') if pkg_dict else ''
            raw_c = pkg_dict.get('content', {}) if pkg_dict else {}
            c = json.loads(raw_c) if isinstance(raw_c, str) else (raw_c or {})
            process = c.get('process', '')

            # 使用模板渲染通知内容
            rendered = _render_template('tmpl_task_assigned', {
                '操作员': op_name,
                '任务标题': title,
                '订单号': order_no,
                '工序': process,
                '数量': '',
            })
            # 确定部门：如果指定人没有部门，回退到发送给全员
            if op_department:
                dept_notify_result = _send_to_department_members(
                    op_department,
                    rendered,
                    msg_type='markdown'
                )
                logger.info(f"部门全员通知结果: {dept_notify_result}")
                notify_msg = f"已通知 {op_department} 部门全员 ({dept_notify_result.get('success', 0)}/{dept_notify_result.get('total', 0)})"
            else:
                _send_wechat_message(rendered, msg_type='markdown')
                notify_msg = "已通知全员"

            _send_desktop_callback('task_assigned', {
                'task_id': task_id, 'operator_id': operator_id,
                'task_title': title, 'related_order': order_no,
                'department': op_department,
            })

            if order_no:
                dc_data = _dispatch_cache.get_data()
                processes = dc_data.get('processes', [])
                target = next((p for p in processes if p.get('order_no') == order_no), None)
                if target:
                    target['operator_id'] = operator_id
                    target['operator_name'] = op_name
                    target['operator_department'] = op_department
                    target['updated_at'] = datetime.now().isoformat()
                    _dispatch_cache.set_data(dc_data)
                    _dispatch_cache.persist()

            log_entry = {
                'id': str(uuid.uuid4())[:8],
                'type': 'task_assign',
                'task_id': task_id,
                'operator_id': operator_id,
                'department': op_department,
                'timestamp': datetime.now().isoformat(),
                'result': 'success',
            }
            _dispatch_cache.update_data(lambda d: d.setdefault('dispatch_log', []).append(log_entry))

            return jsonify({
                'code': 0,
                'message': f'任务已分配给 {op_name}，{notify_msg}'
            })
        return jsonify({'code': 500, 'message': '任务分发失败'}), 500
    except Exception as e:
        logger.error(f'分配任务失败: {e}')
        return jsonify({'code': 500, 'message': f'分配失败: {e}'}), 500


@dispatch_center_bp.route('/tasks/<task_id>/reassign', methods=['POST'])
def reassign_task(task_id):
    body = request.get_json(force=True, silent=True) or {}
    new_operator_id = body.get('operator_id')
    reason = body.get('reason', '人工转派')
    if not new_operator_id:
        return jsonify({'code': 400, 'message': '缺少 operator_id'}), 400

    try:
        pkg_dict = _get_client().get_document('work_order', task_id)
        if not pkg_dict:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404

        old_operator = pkg_dict.get('target_operator', '')
        _get_client().update_document('work_order', task_id, {
            'target_operator': new_operator_id,
            'status': 'pending',
            'distributed_at': None
        })

        operators = _get_operators()
        new_name = operators.get(new_operator_id, {}).get('name', new_operator_id)
        old_name = operators.get(old_operator, {}).get('name', old_operator) if old_operator else '未分配'

        rendered = _render_template('tmpl_task_transfer', {
            '任务标题': pkg_dict.get("title", ""),
            '订单号': pkg_dict.get("related_order", ""),
            '原负责人': old_name,
            '新负责人': new_name,
        })
        _send_wechat_message(rendered, msg_type='markdown')

        order_no = pkg_dict.get('related_order', '')
        if order_no:
            dc_data = _dispatch_cache.get_data()
            processes = dc_data.get('processes', [])
            target = next((p for p in processes if p.get('order_no') == order_no or p.get('order_no') == order_no), None)
            if target:
                target['operator_id'] = new_operator_id
                target['operator_name'] = new_name
                target['updated_at'] = datetime.now().isoformat()
                _dispatch_cache.set_data(dc_data)
                _dispatch_cache.persist()

        log_entry = {
            'id': str(uuid.uuid4())[:8],
            'type': 'task_reassign',
            'task_id': task_id,
            'from_operator': old_operator,
            'to_operator': new_operator_id,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
        }
        _dispatch_cache.update_data(lambda d: d.setdefault('dispatch_log', []).append(log_entry))

        return jsonify({'code': 0, 'message': f'任务已从 {old_name} 转派给 {new_name}'})
    except Exception as e:
        logger.error(f'转派任务失败: {e}')
        return jsonify({'code': 500, 'message': f'转派失败: {e}'}), 500


@dispatch_center_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    try:
        pkg_dict = _get_client().get_document('work_order', task_id)
        if not pkg_dict:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404

        _get_client().update_document_status('work_order', task_id, 'cancelled')

        _send_wechat_message(
            _render_template('tmpl_task_cancelled', {
                '任务标题': pkg_dict.get('title', ''),
                '订单号': pkg_dict.get('related_order', ''),
            }),
            msg_type='markdown'
        )

        return jsonify({'code': 0, 'message': '任务已取消'})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'取消失败: {e}'}), 500


@dispatch_center_bp.route('/tasks/batch-assign', methods=['POST'])
def batch_assign():
    body = request.get_json(force=True, silent=True) or {}
    task_ids = body.get('task_ids', [])
    operator_id = body.get('operator_id')
    if not task_ids or not operator_id:
        return jsonify({'code': 400, 'message': '缺少 task_ids 或 operator_id'}), 400

    success_count = 0
    errors = []
    for task_id in task_ids:
        try:
            result = _get_client().distribute(task_id, operator_id)
            if result and result.get('distributed'):
                success_count += 1
            else:
                errors.append({'task_id': task_id, 'error': '分发失败'})
        except Exception as e:
            errors.append({'task_id': task_id, 'error': '分发失败，请稍后重试'})

    operators = _get_operators()
    op_name = operators.get(operator_id, {}).get('name', operator_id)

    _dispatch_cache.update_data(lambda d: d.setdefault('dispatch_log', []).append({
        'id': str(uuid.uuid4())[:8],
        'type': 'batch_assign',
        'task_ids': task_ids,
        'operator_id': operator_id,
        'success_count': success_count,
        'total': len(task_ids),
        'timestamp': datetime.now().isoformat(),
    }))

    _send_wechat_message(
        _render_template('tmpl_batch_assign', {
            '操作员': op_name,
            '成功数': success_count,
            '总数': len(task_ids),
        }),
        msg_type='markdown'
    )

    return jsonify({'code': 0 if success_count > 0 else 500, 'message': f'批量派单完成: {success_count}/{len(task_ids)}', 'data': {'success': success_count, 'errors': errors}})


# ═══════════════════════════════════════════════════════════════════════════════
# Part 9: 操作员管理路由 (行 2889~3721)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/operators', methods=['GET'])
def list_operators():
    try:
        operators = DispatchContext.get_instance().get_cached_operators() or []
    except Exception as e:
        logger.error(f'容器中心 5002 不可达，操作员列表不可用: {e}')
        return jsonify({'code': 503, 'message': '容器中心服务暂不可用，请稍后重试'}), 503
    operators_list = [{
        'auto_id': op.get('auto_id', 0) if isinstance(op, dict) else 0,
        'id': op.get('id') or op.get('operator_id', '') if isinstance(op, dict) else str(op) if op else '',
        'enterprise_id': op.get('enterprise_id', '') or (op.get('id') if isinstance(op, dict) else '') or '',
        'name': op.get('name', '') if isinstance(op, dict) else str(op) if op else '',
        'role': op.get('role', '') if isinstance(op, dict) else '',
        'department': op.get('department', '') or op.get('team_name', '') if isinstance(op, dict) else '',
        'enabled': op.get('enabled', True) if isinstance(op, dict) else True,
        'can_receive_wechat': op.get('can_receive_wechat', False) if isinstance(op, dict) else False,
        'can_send_wechat': op.get('can_send_wechat', False) if isinstance(op, dict) else False,
        'max_tasks': op.get('max_tasks', 0) if isinstance(op, dict) else 0,
        'wechat_userid': op.get('wechat_userid', '') if isinstance(op, dict) else '',
        'phone': op.get('phone', '') if isinstance(op, dict) else '',
        'created_at': op.get('created_at', '') if isinstance(op, dict) else '',
        'updated_at': op.get('updated_at', '') if isinstance(op, dict) else '',
    } for op in operators]
    return jsonify({'code': 0, 'data': operators_list})

@dispatch_center_bp.route('/operators', methods=['POST'])
def create_operator():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name')
    if not name:
        return jsonify({'code': 400, 'message': '姓名不能为空'}), 400

    from container_config import container_config, OperatorConfig

    # 自动生成系统自增ID
    existing_ids = [int(op.id[2:]) for op in container_config.get_all_operators()
                    if op.id.startswith('OP') and op.id[2:].isdigit()]
    next_num = max(existing_ids) + 1 if existing_ids else 1
    operator_id = f'OP{next_num:03d}'

    wechat_userid = body.get('wechat_userid', '')

    op = OperatorConfig(
        id=operator_id,
        name=name,
        role=body.get('role', '操作员'),
        department=body.get('department', ''),
        enabled=body.get('enabled', True),
        can_receive_wechat=body.get('can_receive_wechat', False),
        can_send_wechat=body.get('can_send_wechat', False),
        max_tasks=body.get('max_tasks', 10),
        wechat_userid=wechat_userid,
        phone=body.get('phone', ''),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    try:
        if container_config.add_operator(op):
            DispatchContext.get_instance().invalidate_operator_cache()
            logger.info(f"添加操作员成功: {operator_id} ({name}, wx={wechat_userid})")
            return jsonify({'code': 0, 'message': f'操作员 {name} 添加成功', 'data': {'id': operator_id}})
        else:
            return jsonify({'code': 500, 'message': f'操作员 ID {operator_id} 已存在'}), 500
    except Exception as e:
        logger.error(f'添加操作员失败 {operator_id}: {e}')
        return jsonify({'code': 500, 'message': f'保存失败: {e}'}), 500


ENTERPRISE_CACHE_PATH = DB_PATHS['enterprise_structure']


def _save_enterprise_to_cache(departments, users, updated_at):
    """保存企业架构到 MySQL（云端推送版 — 覆盖部门，追加新人员）"""
    # 去重
    cloud_users = {}
    for u in users:
        uid = u.get('userid', '')
        if uid and uid not in cloud_users:
            cloud_users[uid] = u

    # 从 MySQL 读取已有数据
    try:
        cc = _get_container_center()
        existing = cc.storage.get_enterprise_structure() if cc else None
    except (AttributeError, pymysql.err.Error) as e:
        logger.warning('[企业架构] 读取失败: %s', e)
        existing = None

    existing_users = {}
    if existing:
        for u in (existing.get('users') or []):
            uid = u.get('userid', '')
            if uid:
                existing_users[uid] = u

    # 合并用户：已有用户保持，新增来自云端
    merged_users = dict(existing_users)  # 保留已有
    added = 0
    for uid, u in cloud_users.items():
        if uid not in merged_users:
            merged_users[uid] = u
            added += 1

    result = list(merged_users.values())
    logger.info(f'[企业架构] 云端 {len(cloud_users)} 人 → 合并后 {len(result)} 人 (新增 {added})')

    data = {'departments': departments, 'users': result, 'updated_at': updated_at}
    # 写 JSON
    try:
        os.makedirs(os.path.dirname(ENTERPRISE_CACHE_PATH), exist_ok=True)
        with open(ENTERPRISE_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f'[企业架构] 文件保存失败: {e}')
    # 通知容器中心同步（通过 API，不直连 MySQL）
    try:
        cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
        requests.post(f'{cc_url}/api/flow-map/sync',
                       json={'mappings': [{'product_type_id': 0, 'flow_type': 'production'}]}, timeout=5)
    except Exception:
        pass
    except Exception as e:
        logger.warning(f'[企业架构] MySQL 保存失败: {e}')


def _build_dept_tree_from_raw(departments, users):
    """
    从原始部门/用户数据构建部门树

    Args:
        departments: 原始部门列表 [{"id":1, "name":"...", "parentid":0, ...}]
        users: 原始用户列表 [{"userid":"...", "name":"...", "department":[1,2], ...}]

    Returns:
        (roots, flat_count): 树根列表和部门总数
    """
    if not departments:
        return [], 0
    # 过滤非法类型（云端或缓存中可能混入字符串/数字）
    departments = [d for d in departments if isinstance(d, dict)]
    users = [u for u in users if isinstance(u, dict)]
    deduped_users = {}
    for u in users:
        uid = u.get('userid', '')
        if not uid:
            continue
        if uid not in deduped_users:
            deduped_users[uid] = {**u, '_dept_ids': set()}
        for did in (u.get('department') or []):
            deduped_users[uid]['_dept_ids'].add(did)
    dept_members = {}
    for uid, u in deduped_users.items():
        for did in u['_dept_ids']:
            dept_members.setdefault(did, []).append({
                'userid': uid,
                'name': u.get('name', '')
            })
    dept_map = {}
    for d in departments:
        did = d.get('id')
        dept_map[did] = {
            'id': did,
            'name': d.get('name', ''),
            'parentid': d.get('parentid', 0),
            'order': d.get('order', 0),
            'members': dept_members.get(did, []),
            'children': []
        }
    roots = []
    for did, node in dept_map.items():
        pid = node['parentid']
        if pid == 0 or pid not in dept_map:
            roots.append(node)
        else:
            dept_map[pid]['children'].append(node)

    def sort_tree(nodes):
        nodes.sort(key=lambda x: (x['order'], x['id']))
        for n in nodes:
            sort_tree(n['children'])
    sort_tree(roots)
    return roots, len(departments)


def _require_cloud_config():
    """
    获取云端 5006 配置，两项任一缺失则返回可直接返回的 500 响应。

    Returns:
        tuple: 成功 (cloud_host, cloud_key, None) — 调用方直接用 host/key
               失败 (None, None, werkzeug.wrappers.Response) — 调用方 return err_resp
    """
    cloud_host = os.environ.get('WECHAT_CLOUD_HOST', '').rstrip('/')
    cloud_key = os.environ.get('WECHAT_CLOUD_API_KEY', '')
    if not cloud_host:
        return None, None, jsonify({'code': 500, 'message': '云端地址未配置（WECHAT_CLOUD_HOST）'}), 500
    if not cloud_key:
        return None, None, jsonify({'code': 500, 'message': '云端凭据未配置（WECHAT_CLOUD_API_KEY）'}), 500
    return cloud_host, cloud_key, None


@dispatch_center_bp.route('/operators/wechat-departments', methods=['GET'])
def get_wechat_departments():
    """
    获取企业微信部门架构（含各部门人员）

    查询参数:
        - force_cloud: 1 | 0（默认0），为1时通过容器中心从云端同步最新数据

    数据来源（按优先级）:
        1. force_cloud=0: 容器中心数据库缓存 → 降级到本地JSON文件
        2. force_cloud=1: 容器中心从云端同步

    调度中心不再直接拉取云端API，只消费容器中心提供的数据。

    Returns:
        {
            "code": 0,
            "data": {
                "departments": [{ id, name, parentid, order, members: [{userid, name}], children: [...] }],
                "flat_count": int,
                "source": "cache" | "local_cache" | "cloud_sync",
                "updated_at": "..."
            }
        }
    """
    import requests
    force_cloud = request.args.get('force_cloud', '0') == '1'
    cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')

    if force_cloud:
        try:
            # 调度中心直连云端 5006 拉取企业架构
            cloud_host, cloud_key, err_resp = _require_cloud_config()
            if err_resp is not None:
                return err_resp

            logger.info('[部门架构] 直连云端拉取企业架构...')
            sync_resp = requests.get(
                f'{cloud_host}/api/wechat/users',
                headers={'X-API-Key': cloud_key},
                timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '30'))
            )
            if sync_resp.status_code != 200:
                return jsonify({'code': 500, 'message': f'云端请求失败: HTTP {sync_resp.status_code}'}), 500

            cloud_data = sync_resp.json()
            if cloud_data.get('code') != 0:
                return jsonify({'code': 500, 'message': f'云端返回错误: {cloud_data.get("message")}'}), 500

            departments = cloud_data.get('departments', [])
            users = cloud_data.get('users', [])
            if isinstance(departments, str):
                try:
                    departments = json.loads(departments)
                except (json.JSONDecodeError, TypeError):
                    departments = []
            if isinstance(users, str):
                try:
                    users = json.loads(users)
                except (json.JSONDecodeError, TypeError):
                    users = []
            if not departments:
                return jsonify({'code': 500, 'message': '云端返回部门列表为空'}), 500

            # 保存到本地缓存
            updated_at = datetime.now().isoformat()
            _save_enterprise_to_cache(departments, users, updated_at)

            # ─── 云端同步后自动推送操作员数据到界面 ───
            try:
                DispatchContext.get_instance().invalidate_operator_cache()
                _preload_operators_from_mysql()
                logger.info('[部门架构] 已刷新操作员缓存')
            except Exception as pe:
                logger.warning(f'[部门架构] 操作员缓存刷新失败: {pe}')

            logger.info(f'[部门架构] 云端同步完成: {len(departments)} 部门, {len(users)} 用户')
            roots, flat_count = _build_dept_tree_from_raw(departments, users)
            return jsonify({
                'code': 0,
                'data': {
                    'departments': roots,
                    'flat_count': flat_count,
                    'source': 'cloud_direct',
                    'updated_at': updated_at
                }
            })
        except requests.exceptions.ConnectionError:
            return jsonify({'code': 500, 'message': '云端不可达（无法连接5006）'}), 500
        except Exception as e:
            logger.warning(f'[部门架构] 云端同步异常: {e}')
            return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500

    try:
        cc_resp = requests.get(
            f'{cc_url}/api/enterprise/structure',
            timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '3'))
        )
        if cc_resp.status_code == 200:
            cc_data = cc_resp.json()
            if cc_data.get('code') == 0:
                cached = cc_data.get('data', {})
                cc_depts = cached.get('departments', [])
                cc_users = cached.get('users', [])
                if isinstance(cc_depts, str):
                    try:
                        cc_depts = json.loads(cc_depts)
                    except (json.JSONDecodeError, TypeError):
                        cc_depts = []
                if isinstance(cc_users, str):
                    try:
                        cc_users = json.loads(cc_users)
                    except (json.JSONDecodeError, TypeError):
                        cc_users = []
                if cc_depts:
                    logger.info(f'[部门架构] 从容器中心读取缓存: {len(cc_depts)} 个部门, {len(cc_users)} 名用户')
                    roots, flat_count = _build_dept_tree_from_raw(cc_depts, cc_users)
                    return jsonify({
                        'code': 0,
                        'data': {
                            'departments': roots,
                            'flat_count': flat_count,
                            'source': 'cache',
                            'updated_at': cached.get('updated_at', '')
                        }
                    })
    except requests.exceptions.ConnectionError:
        logger.warning('[部门架构] 容器中心不可达，降级到本地缓存文件')
    except Exception as e:
        logger.warning(f'[部门架构] 读取容器中心缓存异常: {e}')

    try:
        cache_path = DB_PATHS['enterprise_structure']
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                local_data = json.load(f)
            local_depts = local_data.get('departments', [])
            local_users = local_data.get('users', [])
            if local_depts:
                logger.info(f'[部门架构] 从本地缓存文件读取: {len(local_depts)} 个部门, {len(local_users)} 名用户')
                roots, flat_count = _build_dept_tree_from_raw(local_depts, local_users)
                return jsonify({
                    'code': 0,
                    'data': {
                        'departments': roots,
                        'flat_count': flat_count,
                        'source': 'local_cache',
                        'updated_at': local_data.get('updated_at', '')
                    }
                })
    except Exception as e:
        logger.warning(f'[部门架构] 读取本地缓存文件异常: {e}')

    return jsonify({'code': 500, 'message': '无法获取企业架构数据（容器中心不可达且无本地缓存）'}), 500


@dispatch_center_bp.route('/api/enterprise/structure/push', methods=['POST'])
def handle_enterprise_structure_push():
    """
    接收容器中心推送的企业架构更新通知

    容器中心保存新企业架构数据后，通过此端点通知调度中心，
    调度中心清除本地缓存，下次请求时重新从容器中心读取最新数据。

    Request Body:
        {"source": "container_center", "type": "enterprise_structure_updated"}

    Returns:
        {"code": 0, "message": "缓存已清除"}
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        source = body.get('source', '')
        event_type = body.get('type', '')
        logger.info(f'[企业架构推送] 收到推送: source={source}, type={event_type}')

        return jsonify({'code': 0, 'message': '已收到企业架构更新通知'})
    except Exception as e:
        logger.error(f'[企业架构推送] 处理异常: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/operators/wechat-form-data', methods=['GET'])
def get_wechat_form_data():
    """
    操作员新增界面下拉数据源（从容器中心 5002 统一数据源读取）
    [F17 修复 2026-06-16] 改为调用容器中心 API，不再读本地 JSON
      - 原因：本地 JSON 文件被容器中心初始化时清空，且 operators 字段未保存
      - 数据源：
        * departments/users ← /api/enterprise/structure
        * operators          ← /api/operators (MySQL workers 表)

    Returns:
        {
            "code": 0,
            "data": {
                "departments": [{ "name": "生产部", "users": [...], "user_count": 5 }],
                "roles": ["管理员", "主管", "操作员", "质检员", "维修工"],
                "next_auto_id": "OP016"
            }
        }
    """
    import requests as _requests
    cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')

    # 1. 从容器中心读企业架构（departments + users）
    depts_raw = []
    users_raw = []
    try:
        resp = _requests.get(f'{cc_url}/api/enterprise/structure', timeout=5)
        if resp.status_code == 200:
            payload = resp.json().get('data') or {}
            depts_raw = payload.get('departments', []) or []
            users_raw = payload.get('users', []) or []
    except Exception as e:
        logger.warning(f'[wechat-form-data] 容器中心企业架构不可达: {e}')

    # 2. 从容器中心读 operators（workers 表，统一数据源）
    operators_raw = []
    try:
        resp = _requests.get(f'{cc_url}/api/operators', timeout=5)
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            if isinstance(data, list):
                operators_raw = data
            elif isinstance(data, dict) and 'operators' in data:
                operators_raw = list(data['operators'].values()) if isinstance(data['operators'], dict) else data['operators']
    except Exception as e:
        logger.warning(f'[wechat-form-data] 容器中心操作员不可达: {e}')

    try:
        # 3. 按部门名称建立用户映射
        # 优先用容器中心的 users（企业微信同步的最新数据）
        dept_user_map = {}
        for u in (users_raw or []):
            if not isinstance(u, dict):
                continue
            dept_name = u.get('department_name') or u.get('department') or ''
            userid = u.get('userid', '')
            name = u.get('name', '')
            if not userid:
                continue
            dept_user_map.setdefault(dept_name, []).append({
                'userid': userid,
                'name': name
            })

        # 4. operators 也补充进对应部门（避免有操作员但没在 users 列表中）
        for op in operators_raw:
            if not isinstance(op, dict):
                continue
            dept_name = op.get('department', '') or ''
            if not dept_name:
                continue
            userid = op.get('wechat_userid') or op.get('enterprise_id') or op.get('id', '')
            name = op.get('name', '')
            if not userid:
                continue
            existing_users = dept_user_map.setdefault(dept_name, [])
            if not any(u['userid'] == userid for u in existing_users):
                existing_users.append({'userid': userid, 'name': name})

        # 5. 构造 departments 列表
        departments = []
        for d in depts_raw:
            if not isinstance(d, dict):
                continue
            dname = d.get('name', '')
            if not dname:
                continue
            dept_users = dept_user_map.get(dname, [])
            departments.append({
                'id': d.get('id'),
                'name': dname,
                'parent': d.get('parentid', 0),
                'users': dept_users,
                'user_count': len(dept_users)
            })

        # 6. 兜底：depts_raw 为空但 operators 有数据时，按 operators.department 聚合部门
        if not departments and operators_raw:
            seen = set()
            for op in operators_raw:
                if not isinstance(op, dict):
                    continue
                dname = op.get('department', '') or '未分配'
                if dname in seen:
                    continue
                seen.add(dname)
                users = dept_user_map.get(dname, [])
                departments.append({
                    'id': None,
                    'name': dname,
                    'parent': 0,
                    'users': users,
                    'user_count': len(users)
                })

        # 7. 计算下一个自增 ID（基于容器中心 operators）
        existing_ids = []
        for op in operators_raw:
            if not isinstance(op, dict):
                continue
            op_id = op.get('id', '') or ''
            if op_id.startswith('OP') and op_id[2:].isdigit():
                existing_ids.append(int(op_id[2:]))
        next_num = max(existing_ids) + 1 if existing_ids else 1
        next_auto_id = f'OP{next_num:03d}'

        # 8. 角色列表
        roles = ['管理员', '主管', '操作员', '质检员', '维修工', '仓管员']

        logger.info(f'[wechat-form-data] departments={len(departments)}, '
                    f'operators={len(operators_raw)}, next_id={next_auto_id}')

        return jsonify({
            'code': 0,
            'data': {
                'departments': departments,
                'roles': roles,
                'next_auto_id': next_auto_id
            }
        })
    except Exception as e:
        logger.error(f'获取表单数据失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/operators/<operator_id>', methods=['PUT'])
def update_operator(operator_id):
    body = request.get_json(force=True, silent=True) or {}

    from container_config import container_config
    update_fields = {}
    if 'name' in body: update_fields['name'] = body['name']
    if 'role' in body: update_fields['role'] = body['role']
    if 'department' in body: update_fields['department'] = body['department']
    if 'enabled' in body: update_fields['enabled'] = body['enabled']
    if 'can_receive_wechat' in body: update_fields['can_receive_wechat'] = body['can_receive_wechat']
    if 'can_send_wechat' in body: update_fields['can_send_wechat'] = body['can_send_wechat']
    if 'max_tasks' in body: update_fields['max_tasks'] = body['max_tasks']
    if 'wechat_userid' in body: update_fields['wechat_userid'] = body['wechat_userid']
    if 'phone' in body: update_fields['phone'] = body['phone']

    update_fields['updated_at'] = datetime.now().isoformat()

    try:
        if container_config.update_operator(operator_id, **update_fields):
            DispatchContext.get_instance().invalidate_operator_cache()
            logger.info(f"更新操作员成功: {operator_id}")
            return jsonify({'code': 0, 'message': f'操作员更新成功'})
        else:
            return jsonify({'code': 404, 'message': f'操作员 {operator_id} 不存在'}), 404
    except Exception as e:
        logger.error(f'更新操作员失败 {operator_id}: {e}')
        return jsonify({'code': 500, 'message': f'保存失败: {e}'}), 500

@dispatch_center_bp.route('/operators/<operator_id>', methods=['DELETE'])
def delete_operator(operator_id):
    from container_config import container_config
    try:
        if container_config.remove_operator(operator_id):
            DispatchContext.get_instance().invalidate_operator_cache()
            logger.info(f"删除操作员成功: {operator_id}")
            return jsonify({'code': 0, 'message': f'操作员删除成功'})
        else:
            return jsonify({'code': 404, 'message': f'操作员 {operator_id} 不存在'}), 404
    except Exception as e:
        logger.error(f'删除操作员失败 {operator_id}: {e}')
        return jsonify({'code': 500, 'message': f'删除失败: {e}'}), 500


@dispatch_center_bp.route('/operators/<operator_id>/tasks', methods=['GET'])
def get_operator_tasks(operator_id):
    status_filter = request.args.get('status')

    tasks = []
    try:
        packages = _get_cached_work_orders(page=1, size=2000)
        for pkg in (packages or []):
            if not isinstance(pkg, dict):
                continue
            if status_filter and pkg.get('status') != status_filter:
                continue
            tasks.append({
                'id': pkg.get('id', ''),
                'type': pkg.get('data_type', ''),
                'title': pkg.get('title', ''),
                'status': pkg.get('status', ''),
                'priority': pkg.get('priority', 'normal'),
                'order_no': pkg.get('related_order', ''),
                'created_at': pkg.get('created_at', ''),
                'distributed_at': pkg.get('distributed_at', ''),
                'acknowledged_at': pkg.get('acknowledged_at', ''),
                'completed_at': pkg.get('completed_at', ''),
            })
    except Exception as e:
        logger.error(f'获取操作员任务失败: {e}')

    active = sum(1 for t in tasks if t['status'] in ('pending', 'dispatched', 'in_progress'))
    completed = sum(1 for t in tasks if t['status'] == 'completed')

    return jsonify({'code': 0, 'data': {'operator_id': operator_id, 'tasks': tasks, 'active_count': active, 'completed_count': completed}})



@dispatch_center_bp.route('/wechat/users', methods=['GET'])
def list_wechat_users():
    """
    获取微信用户列表（通过云端）

    Query参数:
        - source: 'cloud' (默认) | 'local'
            cloud: 从云端API获取
            local: 从本地app_bot获取

    Returns:
        微信用户列表
    """
    try:
        source = request.args.get('source', 'cloud')

        if source == 'cloud':
            import requests
            cloud_host, cloud_api_key, err_resp = _require_cloud_config()
            if err_resp is not None:
                return err_resp

            url = f"{cloud_host}/api/wechat/users"
            headers = {'X-API-Key': cloud_api_key}
            resp = requests.get(url, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '15')))
            if resp.status_code == 200:
                data = resp.json()
                return jsonify({
                    'code': 0,
                    'data': data.get('users', []),
                    'departments': data.get('departments', []),
                    'count': data.get('count', 0)
                })

        from wechat_app_bot import WeChatAppBot
        from core.config import Config

        bot = WeChatAppBot(
            Config.WECHAT_CORP_ID,
            Config.WECHAT_AGENT_ID,
            Config.WECHAT_SECRET
        )
        users = bot.get_all_users()
        return jsonify({'code': 0, 'data': users, 'count': len(users)})

    except Exception as e:
        logger.error(f"[WeChat用户] 获取异常: {e}")
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/devices', methods=['GET'])
def list_devices():
    """获取设备列表（预留设备运转监测模块）"""
    devices_map = {}

    try:
        packages = _get_cached_work_orders(page=1, size=2000)
        for pkg in (packages or []):
            device_id = pkg.get('device_id', '')
            if device_id:
                if device_id not in devices_map:
                    devices_map[device_id] = {
                        'device_id': device_id,
                        'task_count': 0,
                        'active_tasks': 0,
                        'completed_tasks': 0,
                        'operators': set()
                    }
                devices_map[device_id]['task_count'] += 1
                status = pkg.get('status', '')
                if status in ('pending', 'distributed', 'in_progress', 'acknowledged'):
                    devices_map[device_id]['active_tasks'] += 1
                elif status == 'completed':
                    devices_map[device_id]['completed_tasks'] += 1
                op = pkg.get('target_operator')
                if op:
                    devices_map[device_id]['operators'].add(op)

        for dev in devices_map.values():
            dev['operators'] = list(dev['operators'])
    except Exception as e:
        logger.error(f'获取设备列表失败: {e}')

    devices_list = [
        {
            'device_id': dev['device_id'],
            'task_count': dev['task_count'],
            'active_tasks': dev['active_tasks'],
            'completed_tasks': dev['completed_tasks'],
            'operators': dev['operators']
        }
        for dev in devices_map.values()
    ]

    return jsonify({'code': 0, 'data': devices_list})


@dispatch_center_bp.route('/devices/<device_id>/tasks', methods=['GET'])
def get_device_tasks(device_id):
    """获取设备关联的任务（预留设备运转监测模块）"""
    status_filter = request.args.get('status')

    tasks = []

    try:
        packages = _get_cached_work_orders(page=1, size=2000)
        for pkg in packages:
            if status_filter and pkg.get('status') != status_filter:
                continue
            tasks.append({
                'id': pkg.get('id', ''),
                'type': pkg.get('data_type', ''),
                'title': pkg.get('title', ''),
                'status': pkg.get('status', ''),
                'priority': pkg.get('priority', 'normal'),
                'order_no': pkg.get('related_order', ''),
                'process_name': pkg.get('related_process', ''),
                'operator_id': pkg.get('target_operator', ''),
                'created_at': pkg.get('created_at', ''),
                'distributed_at': pkg.get('distributed_at', ''),
            })
    except Exception as e:
        logger.error(f'获取设备任务失败: {e}')

    active = sum(1 for t in tasks if t['status'] in ('pending', 'distributed', 'in_progress', 'acknowledged'))
    completed = sum(1 for t in tasks if t['status'] == 'completed')

    return jsonify({'code': 0, 'data': {'device_id': device_id, 'tasks': tasks, 'active_count': active, 'completed_count': completed}})


@dispatch_center_bp.route('/messages/templates', methods=['GET'])
def list_templates():
    """模板列表 — MySQL 自定义 + 内置合并"""
    builtin = [{'id': t['id'], 'name': t['name'], 'category': t['category'],
                'content': t['content'], 'is_builtin': True} for t in MESSAGE_TEMPLATES_DEFAULT]
    try:
        import pymysql
        c = _get_mysql_connection()
        cur = c.cursor()
        cur.execute('SELECT id, name, category, content, version, is_builtin FROM message_templates WHERE is_active=1')
        custom = cur.fetchall()
        cur.execute('SELECT scenario, force_by_assignee FROM notification_recipient_preset WHERE force_by_assignee=1')
        force_by_assignee_map = {row[0]: True for row in cur.fetchall()}
        c.close()
    except Exception:
        custom = []
        force_by_assignee_map = {}
    for t in builtin:
        t['force_by_assignee'] = force_by_assignee_map.get(t['id'], False)
    for t in custom:
        if isinstance(t, dict):
            t['force_by_assignee'] = force_by_assignee_map.get(t.get('id'), False)
    all_templates = list(builtin) + list(custom)
    return jsonify({'code': 0, 'data': all_templates, 'info': {'builtin': len(builtin), 'custom': len(custom)}})


@dispatch_center_bp.route('/messages/templates', methods=['POST'])
def create_template():
    body = request.get_json(force=True, silent=True) or {}
    tid = body.get('id') or ('custom_' + str(uuid.uuid4())[:8])
    return update_template(tid)


@dispatch_center_bp.route('/messages/templates/preference', methods=['GET'])
def get_template_preference():
    data = _dispatch_cache.get_data()
    return jsonify({'code': 0, 'data': data.get('template_preference', {})})


@dispatch_center_bp.route('/messages/templates/preference', methods=['POST'])
def save_template_preference():
    body = request.get_json(force=True, silent=True) or {}
    cat = body.get('category', '')
    tid = body.get('template_id', '')
    if not cat:
        return jsonify({'code': 400, 'message': '缺少 category'}), 400
    _dispatch_cache.update_data(lambda d: d.setdefault('template_preference', {}).__setitem__(cat, tid))
    return jsonify({'code': 0, 'message': '已保存'})


@dispatch_center_bp.route('/messages/templates/defaults', methods=['GET'])
def get_default_templates():
    return jsonify({'code': 0, 'data': MESSAGE_TEMPLATES_DEFAULT})


@dispatch_center_bp.route('/messages/templates/variables', methods=['GET'])
def get_template_variables():
    from template_engine import VARIABLE_CN_TO_EN
    var_list = [{'cn': k, 'en': v} for k, v in sorted(VARIABLE_CN_TO_EN.items())]
    return jsonify({'code': 0, 'data': var_list})


@dispatch_center_bp.route('/messages/templates/<template_id>', methods=['PUT'])
def update_message_template(template_id):
    return update_template(template_id)


@dispatch_center_bp.route('/messages/templates/<template_id>', methods=['DELETE'])
def delete_message_template(template_id):
    return delete_template(template_id)

def _resolve_receivers(receivers) -> list:
    """解析消息接收人列表
    参数: receivers -- @all字符串/列表/字典/None
    返回: 操作员ID列表
    """
    """解析接收人列表：@all→全部操作员, dict→展开值, list→直接返回"""
    if not receivers: return []
    if isinstance(receivers, str) and receivers == '@all':
        try: return list(_get_operators().keys())
        except Exception: return []
    if isinstance(receivers, list): return receivers
    if isinstance(receivers, dict):
        targets = []
        for val in receivers.values():
            if isinstance(val, list): targets.extend(val)
            else: targets.append(val)
        return targets
    return [receivers]


# ═══════════════════════════════════════════════════════════════════════════════
# Part 10: 消息模板路由 (行 3722~3823)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/messages/send', methods=['POST'])
def send_message():
    body = request.get_json(force=True, silent=True) or {}
    template_id = body.get('template_id')
    content = body.get('content')
    channels = body.get('channels', ['wechat_group'])
    variables = body.get('variables', {})
    receivers = body.get('receivers', {})
    operator_id = body.get('operator_id')

    tmpl_receivers = None
    if template_id:
        data = _dispatch_cache.get_data()
        templates = data.get('templates', [])
        tmpl = next((t for t in templates if t.get('id') == template_id), None)
        if not tmpl:
            tmpl = next((t for t in MESSAGE_TEMPLATES_DEFAULT if t.get('id') == template_id), None)
        if tmpl:
            content = tmpl.get('content', '')
            channels = body.get('channels', tmpl.get('channels', ['wechat_group']))
            tmpl_receivers = tmpl.get('receivers')
            resolved = _resolve_variables(variables)
            for key, value in resolved.items():
                content = content.replace('{' + key + '}', str(value))

    if not content:
        return jsonify({'code': 400, 'message': '缺少消息内容'}), 400

    if (receivers is None or (not receivers)) and tmpl_receivers is not None:
        receivers = tmpl_receivers

    target_operators = _resolve_receivers(receivers)
    logger.info(f"[消息发送] 目标接收人: {target_operators}, 渠道: {channels}")

    results = {}
    errors = []
    for channel in channels:
        if channel == 'wechat_group':
            ok, err = _send_wechat_message(content, 'markdown')
            results['wechat_group'] = ok
            if err:
                errors.append(f'微信群:{err}')
        elif channel == 'wechat_app':
            success_count = 0
            fail_count = 0
            for op_id in target_operators:
                ok, err = _send_wechat_app_message(content, op_id)
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
                    if err:
                        errors.append(f'应用消息->{op_id}:{err}')
            results['wechat_app'] = {'success': success_count, 'failed': fail_count}
        elif channel == 'desktop':
            success_count = 0
            fail_count = 0
            for op_id in target_operators:
                ok = _send_desktop_callback('message', {'content': content, 'operator_id': op_id})
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            results['desktop'] = {'success': success_count, 'failed': fail_count}

    msg_log = {
        'id': str(uuid.uuid4())[:8],
        'template_id': template_id or '',
        'content_preview': content[:50],
        'channels': channels,
        'receivers': {
            'send_all': (receivers.get('send_all', False) if isinstance(receivers, dict) else False),
            'operator_ids': (receivers.get('operator_ids', []) if isinstance(receivers, dict) else []),
            'department_ids': (receivers.get('department_ids', []) if isinstance(receivers, dict) else []),
            'resolved': target_operators,
        },
        'results': results,
        'errors': errors,
        'timestamp': datetime.now().isoformat(),
    }
    _dispatch_cache.update_data(lambda d: _append_message_log(d, msg_log))

    success = any(r.get('success', r) if isinstance(r, dict) else r for r in results.values())
    msg = '消息已发送' if success else '所有渠道发送失败'
    if errors:
        msg += ' (' + '; '.join(errors[:3]) + ('...' if len(errors) > 3 else '') + ')'
    return jsonify({'code': 0 if success else 500, 'message': msg, 'data': {'results': results, 'errors': errors}})


@dispatch_center_bp.route('/messages/history', methods=['GET'])
def message_history():
    data = _dispatch_cache.get_data()
    messages = data.get('messages', [])
    limit = int(request.args.get('limit', 50))
    messages = messages[-limit:][::-1]
    return jsonify({'code': 0, 'data': messages, 'total': len(messages)})


# ═══════════════════════════════════════════════════════════════════════════════
# Part 11: 流程管理路由 (行 3824~5057)
# ═══════════════════════════════════════════════════════════════════════════════

_processes_cache = {'data': None, 'time': 0}
_PROCESSES_CACHE_TTL = 30

@dispatch_center_bp.route('/processes', methods=['GET'])
def list_processes():
    global _processes_cache
    
    now = time.time()
    if _processes_cache['data'] is not None and now - _processes_cache['time'] < _PROCESSES_CACHE_TTL:
        logger.info(f"[性能] list_processes 缓存命中，返回 {len(_processes_cache['data'])} 条")
        return jsonify({'code': 0, 'data': _processes_cache['data']})
    
    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    processes = [p for p in processes if not _is_test_order(p.get('order_no', ''))]

    # 预加载 process_records 用于去重和步骤提取
    proc_records = []
    proc_record_orders = set()
    try:
        cc = _get_container_center()
        proc_records = cc.storage.get_all_process_records()
        for rec in proc_records:
            if rec.get('order_no'):
                proc_record_orders.add(rec['order_no'])
            if rec.get('order_no'):
                proc_record_orders.add(rec['order_no'])
    except Exception as e:
        logger.warning(f"预加载 process_records 失败: {e}")

    # [优化 2026-06-15] 预加载工单数据，避免重复调用
    _cached_orders = None
    try:
        _cached_orders = _get_cached_work_orders(page=1, size=2000)
        records = _extract_items(_cached_orders)

        order_task_count = {}
        order_completed_count = {}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            rel_order = rec.get('order_no', rec.get('related_order', ''))
            if _is_test_order(rel_order):
                continue
            if rel_order:
                order_task_count[rel_order] = order_task_count.get(rel_order, 0) + 1
                if rec.get('status') == 'completed':
                    order_completed_count[rel_order] = order_completed_count.get(rel_order, 0) + 1

        for p in processes:
            p_order = p.get('order_no', '')
            p['task_count'] = order_task_count.get(p_order, 0)
            p['completed_task_count'] = order_completed_count.get(p_order, 0)

        for record in records:
            doc_data = _get_doc_data(record)
            order_no = doc_data.get('order_no', record.get('order_no', ''))
            if not order_no:
                continue
            if _is_test_order(order_no):
                continue
            # process_records 已覆盖，跳过避免重复
            if order_no in proc_record_orders:
                continue
            existing = next((p for p in processes if p.get('order_no') == order_no or p.get('order_no') == order_no), None)
            if not existing:
                flow_type = match_flow_type(doc_data)
                flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
                product_name = doc_data.get('product_name', '')
                quantity = doc_data.get('quantity', 0)
                if not product_name:
                    product_name, quantity = _get_process_product_fallback(order_no, product_name, quantity)
                processes.append({
                    'id': record.get('id', str(uuid.uuid4())[:8]),
                    'order_no': doc_data.get('order_no', record.get('order_no', '')),
                    'product_name': product_name,
                    'quantity': quantity,
                    'customer_name': _get_customer_group_for_order(order_no) or doc_data.get('customer_name', record.get('customer_name', '')),
                    'delivery_date': doc_data.get('delivery_date', record.get('delivery_date', '')),
                    'unit': doc_data.get('unit', record.get('unit', '米')),
                    'priority': doc_data.get('priority', record.get('priority', 'normal')),
                    'status': record.get('status', 'created'),
                    'flow_type': flow_type,
                    'current_step': doc_data.get('current_step', 0),
                    'steps': flow_template['steps'],
                    'task_count': order_task_count.get(order_no, 0),
                    'completed_task_count': order_completed_count.get(order_no, 0),
                    'created_at': record.get('created_at', ''),
                    'updated_at': record.get('updated_at', ''),
                })
    except Exception as e:
        logger.warning(f"获取生产流程记录异常: {e}")

    # 兜底: 从 process_records 表读取(使用实际步骤)
    try:
        existing_nos = set()
        for p in processes:
            if p.get('order_no'):
                existing_nos.add(p['order_no'])
            if p.get('order_no'):
                existing_nos.add(p['order_no'])
        for rec in proc_records:
            wo_no = rec.get('order_no', '')
            if not wo_no or wo_no in existing_nos:
                continue
            if _is_test_order(wo_no):
                existing_nos.add(wo_no)
                continue
            # 也检查 order_no 是否已存在于现有流程
            if rec.get('order_no') and rec['order_no'] in existing_nos:
                continue
            # 使用 process_records 中的实际步骤
            steps = _normalize_process_steps(rec.get('steps'))
            if not steps:
                flow_template = PROCESS_FLOW_TEMPLATES.get(rec.get('flow_type', 'production'), PROCESS_FLOW_TEMPLATES['production'])
                steps = flow_template['steps']
            processes.append({
                'id': rec.get('id', str(uuid.uuid4())[:8]),
                'order_no': rec.get('order_no', ''),
                'product_name': rec.get('product_name', ''),
                'quantity': rec.get('quantity', 0),
                'customer_name': _get_customer_group_for_order(wo_no) or rec.get('customer_name', ''),
                'delivery_date': rec.get('delivery_date', ''),
                'unit': rec.get('unit', '米'),
                'priority': rec.get('priority', 'normal'),
                'status': rec.get('status', 'created'),
                'flow_type': rec.get('flow_type', 'production'),
                'current_step': rec.get('current_step', 0),
                'steps': steps,
                'task_count': order_task_count.get(wo_no, 0),
                'completed_task_count': order_completed_count.get(wo_no, 0),
                'created_at': rec.get('created_at', ''),
                'updated_at': rec.get('updated_at', ''),
                'source': 'process_records',
            })
            existing_nos.add(wo_no)
            if rec.get('order_no'):
                existing_nos.add(rec['order_no'])
    except Exception as e:
        logger.warning(f"从 process_records 兜底读取失败: {e}")

    try:
        cc = _get_container_center()
        if cc and hasattr(cc, 'storage') and cc.storage:
            order_nos = [p.get('order_no', '') for p in processes if p.get('order_no')]
            if order_nos:
                try:
                    summary_map = cc.get_sub_step_summary_batch(order_nos)
                    for p in processes:
                        ono = p.get('order_no', '')
                        if ono and ono in summary_map:
                            s = summary_map[ono]
                            p['completed_qty'] = s.get('completed_qty', 0)
                            p['required_qty'] = s.get('order_qty', 0)
                            p['shipped_qty'] = s.get('shipped_qty', 0)
                except Exception as e:
                    logger.warning(f"批量获取 completed_qty 失败: {e}")
    except Exception as e:
        logger.warning(f"计算 completed_qty 失败: {e}")

    # [优化 2026-06-15] 复用预加载的工单数据，避免重复查询
    packages = _cached_orders if isinstance(_cached_orders, list) else (_cached_orders.get('items', _cached_orders.get('data', [])) if isinstance(_cached_orders, dict) else [])
    # 降级重试：首次查询为空时，清除缓存重试一次
    if not packages and _cached_orders is None:
        ctx = DispatchContext.get_instance()
        ctx.invalidate_work_order_cache()
        logger.info('[list_processes] 首次查询为空，已清除缓存并重试')
        _cached_orders = _get_cached_work_orders(page=1, size=2000)
        packages = _cached_orders if isinstance(_cached_orders, list) else (_cached_orders.get('items', _cached_orders.get('data', [])) if isinstance(_cached_orders, dict) else [])
    # ── data_type 契约 v1.0 归类 (详见 docs/DATA_TYPE_CONTRACT.md) ──
    # [优化 2026-06-12] 哈希分组 O(n+m)，替代原 O(n*m) 嵌套循环
    process_set = _get_process_names_set()
    flow_step_set = get_flow_step_names_set()
    from collections import defaultdict
    pkg_by_order = defaultdict(list)
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        pkg_by_order[pkg.get('related_order', '')].append(pkg)
    for p in processes:
            order_no = p.get('order_no', '')
            p['process_tasks'] = []   # 物理工序报工
            p['flow_steps'] = []      # 流程步骤占位 (新)
            p['material_tasks'] = []
            p['quality_tasks'] = []
            p['repair_tasks'] = []
            p['outsource_tasks'] = []
            p['flow_production'] = []  # 排产发布 (新)
            done = 0
            for pkg in pkg_by_order.get(order_no, []):
                new_type = classify_pkg(pkg, process_set, flow_step_set)
                if new_type == 'process_report':
                    c = pkg.get('content', {})
                    if isinstance(c, str):
                        try: c = json.loads(c)
                        except Exception: c = {}
                    pkg['completed_qty'] = c.get('completed_qty', 0) if isinstance(c, dict) else 0
                    pkg['planned_qty'] = c.get('quantity', 0) if isinstance(c, dict) else 0
                    production_status = c.get('status', '') if isinstance(c, dict) else ''
                    pkg['display_status'] = production_status or '生产中' if pkg.get('status') == 'distributed' else pkg.get('status', 'pending')
                    p['process_tasks'].append(pkg)
                    if pkg.get('status') in ('已完成', 'completed'):
                        done += 1
                elif new_type == 'flow_step':
                    p['flow_steps'].append(pkg)
                elif new_type == 'flow_production':
                    p['flow_production'].append(pkg)
                elif new_type in ('material_request', 'material_pickup', 'material_buy'):
                    p['material_tasks'].append(pkg)
                elif new_type == 'quality_task':
                    p['quality_tasks'].append(pkg)
                elif new_type == 'equipment_repair':
                    p['repair_tasks'].append(pkg)
                elif new_type == 'outsource_task':
                    p['outsource_tasks'].append(pkg)
            p['task_count'] = len(p['process_tasks'])
            p['completed_task_count'] = done
            # [修复 2026-06-15] 添加 process_code 和 process_name 字段
            if not p.get('process_code') or not p.get('process_name'):
                try:
                    from core._config_domain import get_process_code
                    current_step = p.get('current_step', '')
                    p['process_code'] = get_process_code(str(current_step)) if current_step else ''
                    p['process_name'] = str(current_step)
                except Exception:
                    p['process_code'] = ''
                    p['process_name'] = str(p.get('current_step', ''))

    processes.sort(key=lambda p: str(p.get('updated_at') or p.get('created_at') or ''), reverse=True)
    _processes_cache['data'] = processes
    _processes_cache['time'] = time.time()
    return jsonify({'code': 0, 'data': processes})


@dispatch_center_bp.route('/processes', methods=['POST'])
def create_process():
    body = request.get_json(force=True, silent=True) or {}
    flow_type = body.get('flow_type', 'production')
    order_no = body.get('order_no', '').strip()
    order_no = body.get('order_no', '').strip() or order_no
    product_name = body.get('product_name', '').strip()
    quantity = body.get('quantity', 0)
    remark = body.get('remark', '')

    if not flow_type or not PROCESS_FLOW_TEMPLATES.get(flow_type):
        return jsonify({'code': 400, 'message': '无效的流程类型'}), 400

    if not order_no:
        return jsonify({'code': 400, 'message': '订单号不能为空'}), 400

    process_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    flow_template = PROCESS_FLOW_TEMPLATES[flow_type]
    created = {'process_id': None}

    def _create_updater(d):
        processes = d.get('processes', [])
        existing = next((p for p in processes if p.get('order_no') == order_no), None)
        if existing:
            created['process_id'] = existing['id']
            return
        new_process = {
            'id': process_id,
            'order_no': order_no,
            'product_name': product_name,
            'quantity': quantity,
            'remark': remark,
            'status': 'created',
            'flow_type': flow_type,
            'current_step': 0,
            'steps': flow_template['steps'],
            'created_at': now,
            'updated_at': now,
        }
        processes.append(new_process)
        created['process_id'] = process_id

    _dispatch_cache.update_data(_create_updater)

    if created['process_id'] != process_id:
        return jsonify({'code': 0, 'message': f'订单号 {order_no} 已存在流程', 'data': {'process_id': created['process_id']}})

    _send_wechat_message(
        f'📋 **流程已创建**\n━━━━━━━━━━━━━━━━━━━━\n订单: {order_no}\n产品: {product_name}\n数量: {quantity}\n━━━━━━━━━━━━━━━━━━━━',
        msg_type='markdown'
    )

    return jsonify({'code': 0, 'message': '流程已创建', 'data': {'process_id': process_id}})


def _query_cc_work_orders_fast(page=1, size=2000):
    """用 V5 存储快速查询工单"""
    max_size = int(os.getenv('DISPATCH_MAX_PAGE_SIZE', '2000'))
    capped = min(size, max_size)
    if capped != size:
        logger.warning(f'[分页] _query_cc_work_orders_fast size={size} 超过上限({max_size}), 截断为 {capped}')
    try:
        cc = _get_container_center()
        packages = cc.storage.get_packages(limit=capped)
        return {'items': packages, 'data': packages, 'total': len(packages), 'page': page, 'size': capped}
    except Exception as e:
        logger.warning(f"快速查询工单失败: {e}")
        return None


@dispatch_center_bp.route('/debug/cc-workorders', methods=['GET'])
def debug_cc_workorders():
    try:
        result = _query_cc_work_orders_fast(page=1, size=2000)
        items = _extract_items(result) if result else []
        sample = items[:3] if items else []
        return jsonify({'code': 0, 'total': len(items), 'sample': sample})
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


def _get_process_product_fallback(order_no: str, default_product: str = '', default_quantity=0):
    """回退查询 product_name/quantity（当 data_packages 中缺失时）"""
    if not order_no:
        return default_product, default_quantity
    try:
        cc = _get_container_center()
        proc_record = cc.storage.get_process_record_by_order(order_no)
        if proc_record:
            pn = proc_record.get('product_name', '') or ''
            if pn:
                return pn, proc_record.get('quantity', default_quantity) or default_quantity
        proc_records = cc.storage.get_all_process_records()
        for rec in proc_records:
            if rec.get('order_no') == order_no:
                pn = rec.get('product_name', '') or ''
                if pn:
                    return pn, rec.get('quantity', default_quantity) or default_quantity
    except Exception as e:
        logger.warning(f"回退查询 process_records 失败(order_no={order_no}): {e}")
    return default_product, default_quantity


@dispatch_center_bp.route('/processes/backfill', methods=['POST'])
def backfill_processes():
    try:
        result = _query_cc_work_orders_fast(page=1, size=2000)
        if result is None:
            return jsonify({'code': 503, 'message': '容器中心(CC)不可用，请先启动容器中心服务后重试'})

        all_items = _extract_items(result)
        created_count = 0
        skipped_count = 0
        details = []

        existing_processes = _dispatch_cache.get_data().get('processes', [])
        existing_order_nos = {p.get('order_no') for p in existing_processes if isinstance(p, dict)}

        wo_group = {}
        for item in all_items:
            if not isinstance(item, dict):
                continue
            source = item.get('source', '')
            if source == 'desktop':
                continue

            doc_data = _get_doc_data(item)
            order_no = doc_data.get('order_no', item.get('order_no', ''))
            if not order_no or order_no.startswith('TEST-'):
                continue

            order_no = doc_data.get('order_no', '')
            if order_no:
                key = order_no
            else:
                key = order_no

            item_time = item.get('created_at', '')
            if key not in wo_group or item_time > wo_group[key][1].get('created_at', ''):
                wo_group[key] = (order_no, item)

        for key, (order_no, item) in wo_group.items():
            if order_no in existing_order_nos:
                skipped_count += 1
                continue

            doc_data = _get_doc_data(item)
            flow_type = match_flow_type(doc_data)
            flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
            process_id = str(uuid.uuid4())[:8]
            now = datetime.now().isoformat()
            product_name = doc_data.get('product_name', item.get('product_name', ''))
            quantity = doc_data.get('quantity', item.get('quantity', 0))
            if not product_name:
                product_name, quantity = _get_process_product_fallback(order_no, product_name, quantity)
            order_no = doc_data.get('order_no', '')

            def _backfill_updater(d, _order_no=order_no, _pid=process_id, _fn=flow_type, _ft=flow_template, _pn=product_name, _qty=quantity, _now=now, _won=order_no):
                processes = d.get('processes', [])
                dup = next((p for p in processes if p.get('order_no') == _order_no), None)
                if dup:
                    return
                processes.append({
                    'id': _pid,
                    'order_no': _order_no or _won,
                    'product_name': _pn,
                    'quantity': _qty,
                    'status': 'created',
                    'flow_type': _fn,
                    'current_step': 0,
                    'steps': _ft['steps'],
                    'created_at': _now,
                    'updated_at': _now,
                })

            _dispatch_cache.update_data(_backfill_updater)
            created_count += 1
            existing_order_nos.add(order_no)
            details.append({'order_no': order_no, 'process_id': process_id, 'product_name': product_name})

        logger.info(f"流程补齐完成: 新建={created_count}, 已存在={skipped_count}")
        return jsonify({
            'code': 0,
            'message': f'补齐完成，新建 {created_count} 个流程，已跳过 {skipped_count} 个',
            'data': {'created': created_count, 'skipped': skipped_count, 'details': details},
        })

    except Exception as e:
        logger.error(f"backfill_processes error: {e}")
        return jsonify({'code': 500, 'message': '补齐失败失败，请稍后重试'})


@dispatch_center_bp.route('/processes/repair-products', methods=['POST'])
def repair_process_products():
    """修复 dispatch cache 中缺失 product_name/quantity 的流程记录"""
    try:
        fixed_count = 0
        details = []

        def _repair_updater(d):
            nonlocal fixed_count, details
            processes = d.get('processes', [])
            for proc in processes:
                if not isinstance(proc, dict):
                    continue
                if proc.get('product_name'):
                    continue
                order_no = proc.get('order_no', '')
                if not order_no:
                    continue
                product_name, quantity = _get_process_product_fallback(order_no)
                if product_name:
                    proc['product_name'] = product_name
                    proc['quantity'] = quantity
                    fixed_count += 1
                    details.append({'order_no': order_no, 'product_name': product_name, 'quantity': quantity})

        _dispatch_cache.update_data(_repair_updater)

        logger.info(f"产品名称修复完成: 修复={fixed_count}")
        return jsonify({
            'code': 0,
            'message': f'修复完成，已修复 {fixed_count} 个流程记录',
            'data': {'fixed': fixed_count, 'details': details},
        })

    except Exception as e:
        logger.error(f"repair_process_products error: {e}")
        return jsonify({'code': 500, 'message': '修复失败失败，请稍后重试'})


@dispatch_center_bp.route('/processes/<order_no>', methods=['GET'])
def get_process_detail(order_no):
    try:
        data = _dispatch_cache.get_data()
        process = next((p for p in data.get('processes', []) if p.get('order_no') == order_no), None)

        if not process:
            process = {'order_no': order_no, 'name': order_no}

        if not process:
            try:
                cc = _get_container_center()
                proc_records = cc.storage.get_all_process_records()
                record = next((r for r in proc_records if r.get('order_no') == order_no), None)
                if record:
                    flow_type = record.get('flow_type', 'production') or 'production'
                    flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
                    steps = _normalize_process_steps(record.get('steps')) or flow_template['steps']
                    process = {
                        'id': record['id'],
                        'order_no': record.get('order_no', ''),
                        'product_name': record.get('product_name', ''),
                        'quantity': record.get('quantity', 0),
                        'customer_name': _get_customer_group_for_order(record.get('order_no', '')) or record.get('customer_name', ''),
                        'delivery_date': record.get('delivery_date', ''),
                        'unit': record.get('unit', '米'),
                        'priority': record.get('priority', 'normal'),
                        'status': record.get('status', 'created'),
                        'flow_type': flow_type,
                        'current_step': record.get('current_step', 0),
                        'steps': steps,
                        'created_at': record.get('created_at', ''),
                        'updated_at': record.get('updated_at', ''),
                        'source': 'process_records',
                    }
            except Exception as e:
                logger.warning(f"从 process_records 获取流程详情失败: {e}")

        if not process:
            return jsonify({'code': 404, 'message': '流程不存在'}), 404

        flow_type = process.get('flow_type', 'production') or 'production'
        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
        steps = process.get('steps') or flow_template['steps']
        current_step = process.get('current_step', 0)

        normalized = _normalize_process_steps(steps)
        if normalized is None:
            normalized = flow_template['steps']
        steps = normalized

        # 三端统一：报工数量 + current_step 联合判定（修问题 A：调度员忘推进时不卡死）
        required_qty = float(process.get('quantity', 0) or 0)
        unified_statuses = None
        if compute_step_statuses:
            try:
                cc = _get_container_center()
                sub_step_qty_map = {}
                sub_step_latest_map = {}
                if cc:
                    all_sub = cc.get_sub_steps(order_no) or []
                    for ss in all_sub:
                        sn = (ss.get('step_name', '') or '').strip()
                        q = float(ss.get('quantity', 0) or 0)
                        sub_step_qty_map[sn] = sub_step_qty_map.get(sn, 0) + q
                        sub_step_latest_map[sn] = ss
                unified_statuses = compute_step_statuses(
                    steps_list=steps,
                    sub_step_qty_map=sub_step_qty_map,
                    current_step=current_step,
                    required_qty=required_qty,
                    sub_step_latest_map=sub_step_latest_map,
                )
            except Exception as e:
                logger.warning(f'compute_step_statuses 失败，回退旧逻辑: {e}')
                unified_statuses = None

        step_details = []
        for i, step in enumerate(steps):
            # 优先用统一真值源，否则回退旧逻辑
            if unified_statuses and i < len(unified_statuses):
                st = unified_statuses[i]
                # 中英映射：中文状态 → 英文 (dispatch_center.viewProcess 用 'completed'/'active'/'pending')
                if st['is_completed']:
                    status_en = 'completed'
                elif st['is_current']:
                    status_en = 'active'
                else:
                    status_en = 'pending'
            else:
                status_en = 'completed' if i < current_step else ('active' if i == current_step else 'pending')
            step_details.append({
                'index': i,
                'name': step['name'],
                'role': step.get('role', ''),
                'status': status_en,
                'completed_qty': unified_statuses[i]['completed_qty'] if unified_statuses and i < len(unified_statuses) else 0,
                'last_report_operator': unified_statuses[i]['last_report_operator'] if unified_statuses and i < len(unified_statuses) else '',
                'completed_at': process.get('completed_at_' + str(i), None),
                'completed_by': process.get('completed_by_' + str(i), None),
            })

        return jsonify({
            'code': 0,
            'data': {
                'process': process,
                'flow_template': flow_template,
                'steps': step_details,
                'current_step': current_step,
                'total_steps': len(steps),
                'progress': round(current_step / len(steps) * 100, 1),
            },
        })
    except Exception as e:
        logger.exception(f"[ProcessDetail] 获取流程详情异常: process_id={process_id}")
        return jsonify({'code': 500, 'message': '获取流程详情失败失败，请稍后重试'}), 500


@dispatch_center_bp.route('/processes/<order_no>/step-notify', methods=['POST'])
def notify_process_step(order_no):
    body = request.get_json(force=True, silent=True) or {}
    step_name = body.get('step_name', '')
    if not step_name:
        return jsonify({'code': 1, 'message': '缺少工序名称'})

    data = _dispatch_cache.get_data()
    process = next((p for p in data.get('processes', []) if p.get('order_no') == order_no), None)

    if not process:
        try:
            record = _get_client().get_document('schedule', order_no)
            if record:
                process = record
        except Exception as e:
            logger.warning(f"获取流程详情异常: {e}")

    if not process:
        return jsonify({'code': 404, 'message': '流程不存在'}), 404

    order_no = process.get('order_no', '')
    product_name = process.get('product_name', '')
    quantity = process.get('quantity', 0)

    content = _render_template('tmpl_process_advance', {
        '订单号': order_no,
        '执行人': step_name,
        '产品': product_name,
        '数量': quantity,
    })

    process_departments = data.get('process_departments', {})
    department = process_departments.get(step_name, '')
    default_to_all = data.get('default_to_all', True)

    recipients = []
    if department:
        recipients = _get_department_members(department)
        if recipients:
            logger.info(f'[步骤通知] 工序"{step_name}" → 部门"{department}" → {recipients}')
    if not recipients and default_to_all:
        recipients = ['@all']

    for recipient in recipients:
        ok, err = _send_wechat_message(content, 'markdown')
        if not ok:
            logger.warning(f'[步骤通知] 发送给 {recipient} 失败: {err}')

    if not recipients:
        return jsonify({'code': 0, 'message': '未发送：无匹配部门成员'})
    return jsonify({'code': 0, 'message': f'已发送工序通知"{step_name}"' if not department else f'已发送给部门"{department}"'})


@dispatch_center_bp.route('/processes/<order_no>', methods=['DELETE'])
def delete_process(order_no):
    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    process = next((p for p in processes if p.get('order_no') == order_no), None)
    if not process:
        return jsonify({'code': 404, 'message': '流程不存在'}), 404

    processes.remove(process)

    def _delete_updater(d):
        d['processes'] = processes

    _dispatch_cache.update_data(_delete_updater)

    order_no = process.get('order_no', '')
    if order_no:
        threading.Thread(target=_sync_work_order_status, args=(order_no, 'cancelled', 0), daemon=True).start()
        threading.Thread(target=_sync_to_mysql, args=(order_no, 'cancelled'), kwargs={'order_no': order_no}, daemon=True).start()

    _send_wechat_message(
        f'🗑️ **流程删除**\n━━━━━━━━━━━━━━━━━━━━\n订单: {process.get("order_no", "")}\n流程类型: {process.get("flow_type", "")}\n━━━━━━━━━━━━━━━━━━━━',
        msg_type='markdown'
    )

    return jsonify({'code': 0, 'message': '流程已删除'})


def _find_process_with_fallback(order_no):
    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    process = next((p for p in processes if p.get('order_no') == order_no), None)
    if not process:
        try:
            record = _get_client().get_document('schedule', order_no)
            if record:
                process = record
        except Exception as e:
            logger.warning(f"[find_process] 容器中心查找 {order_no} 异常: {e}")
    return process


@dispatch_center_bp.route('/processes/<order_no>/template-bindings', methods=['GET'])
def get_process_template_bindings(order_no):
    process = _find_process_with_fallback(process_id)
    if not process:
        return jsonify({'code': 1, 'message': '流程不存在'}), 404
    data = _dispatch_cache.get_data()
    templates = data.get('templates', MESSAGE_TEMPLATES_DEFAULT)
    process_templates = [t for t in templates if t.get('id', '').startswith('tmpl_process_') or t.get('id', '').startswith('tmpl_task_')]
    current_bindings = _get_process_template_bindings(process)
    return jsonify({
        'code': 0,
        'data': {
            'bindings': current_bindings,
            'event_labels': PROCESS_EVENT_LABELS,
            'available_templates': process_templates,
            'defaults': dict(PROCESS_TEMPLATE_DEFAULTS),
        },
    })


@dispatch_center_bp.route('/processes/<order_no>/template-bindings', methods=['PUT'])
def update_process_template_bindings(order_no):
    process = _find_process_with_fallback(process_id)
    if not process:
        return jsonify({'code': 1, 'message': '流程不存在'}), 404
    body = request.get_json(force=True, silent=True) or {}
    update_bindings = body.get('bindings', {})
    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    cache_process = next((p for p in processes if p.get('order_no') == order_no), None)
    if not cache_process:
        cache_process = dict(process)
        cache_process.setdefault('template_bindings', {})
        processes.append(cache_process)
        _dispatch_cache.update_data(lambda d: None)
    current_bindings = cache_process.get('template_bindings', {})
    current_bindings.update(update_bindings)
    cache_process['template_bindings'] = current_bindings
    success = _dispatch_cache.update_data(lambda d: None)
    if success:
        return jsonify({'code': 0, 'message': '消息模板绑定已更新'})
    return jsonify({'code': 1, 'message': '保存失败'}), 500


@dispatch_center_bp.route('/processes/<order_no>/template-bindings/reset', methods=['POST'])
def reset_process_template_bindings(order_no):
    process = _find_process_with_fallback(process_id)
    if not process:
        return jsonify({'code': 1, 'message': '流程不存在'}), 404
    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    cache_process = next((p for p in processes if p.get('order_no') == order_no), None)
    if not cache_process:
        cache_process = dict(process)
        processes.append(cache_process)
        _dispatch_cache.update_data(lambda d: None)
    cache_process.pop('template_bindings', None)
    success = _dispatch_cache.update_data(lambda d: None)
    if success:
        return jsonify({'code': 0, 'message': '已重置为默认模板'})
    return jsonify({'code': 1, 'message': '保存失败'}), 500


@dispatch_center_bp.route('/processes/<order_no>/advance', methods=['POST'])
def advance_process(order_no):
    body = request.get_json(force=True, silent=True) or {}
    operator_id = body.get('operator_id', 'system')
    operator_name = body.get('operator_name', '系统')
    force_confirm = body.get('force_confirm', False)

    result = {'error': None, 'process_data': None, 'needs_confirmation': False, 'confirmation_template': None}

    def updater(data):
        import traceback as _tb
        logger.info(f'[advance updater] 开始 order_no={order_no}')
        processes = data.get('processes', [])
        process = next((p for p in processes if p.get('order_no') == order_no), None)
        if not process:
            result['error'] = ('not_found',)
            return

        if process.get('awaiting_confirmation') and not force_confirm:
            result['error'] = ('awaiting_confirmation',)
            return

        flow_type = process.get('flow_type', 'production')
        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
        steps = process.get('steps') or flow_template['steps']
        current_step = process.get('current_step', 0)

        if current_step >= len(steps):
            result['error'] = ('completed',)
            return

        next_step_index = current_step + 1
        if next_step_index >= len(steps):
            result['error'] = ('completed',)
            return

        next_step = steps[next_step_index]
        next_step_status_key = next_step.get('status_key', 'pending')

        if next_step_status_key in CONFIRMATION_REQUIRED_STEPS and not force_confirm:
            process['awaiting_confirmation'] = True
            process['awaiting_step'] = next_step_index
            process['awaiting_step_status'] = next_step_status_key
            process['awaiting_since'] = datetime.now().isoformat()
            process['awaiting_operator'] = operator_name
            process['updated_at'] = datetime.now().isoformat()

            result['needs_confirmation'] = True
            result['confirmation_template'] = CONFIRMATION_REQUIRED_STEPS[next_step_status_key]
            result['process_data'] = (process, steps, current_step, next_step, flow_template, flow_type, operator_name, next_step_status_key)
            return

        step = steps[current_step]
        process['current_step'] = next_step_index
        process['completed_at_' + str(current_step)] = datetime.now().isoformat()
        process['completed_by_' + str(current_step)] = operator_name
        process['updated_at'] = datetime.now().isoformat()
        process['awaiting_confirmation'] = False
        process.pop('awaiting_step', None)
        process.pop('awaiting_step_status', None)
        process.pop('awaiting_since', None)
        process.pop('awaiting_operator', None)

        if next_step_index >= len(steps):
            process['status'] = 'completed'
        else:
            process['status'] = next_step.get('status_key', 'in_progress')

        result['process_data'] = (process, steps, step, current_step, flow_template, flow_type, operator_name, next_step.get('status_key', 'in_progress'))

    try:
        ok = _dispatch_cache.update_data(updater)
    except Exception as e:
        logger.error(f'[advance] update_data 抛出异常 order_no={order_no}: {type(e).__name__}: {e}')
        return jsonify({'code': 500, 'message': '更新失败失败，请稍后重试'}), 500
    if not ok:
        logger.error(f'[advance] 缓存更新失败，order_no={order_no}')
        return jsonify({'code': 500, 'message': '缓存更新失败，请重试'}), 500

    if result['error']:
        error_type = result['error'][0]
        if error_type == 'not_found':
            return jsonify({'code': 404, 'message': '流程不存在'}), 404
        if error_type == 'completed':
            return jsonify({'code': 400, 'message': '流程已全部完成'}), 400
        if error_type == 'awaiting_confirmation':
            return jsonify({'code': 400, 'message': '当前流程等待确认中，请先确认后再推进'}), 400

    process, steps, step_or_next, current_step, flow_template, flow_type, operator_name, status_key = result['process_data']

    order_no = process.get('order_no', '')

    if result['needs_confirmation']:
        confirmation_template = result['confirmation_template']
        next_step = result['process_data'][3]
        confirmation_vars = _build_confirmation_variables(process, next_step, flow_template, operator_name)
        # 工序确认通知：发送给任务负责人（指定任务）还是发群（全员任务）
        target_op = next_step.get('target_operator', '') or process.get('target_operator', '')
        if target_op:
            notify_ok, notify_err = _notify_with_template(order_no, confirmation_template, confirmation_vars,
                                                        target_operator=target_op, send_to_group=False)
        else:
            notify_ok, notify_err = _notify_with_template(order_no, confirmation_template, confirmation_vars)

        msg = f'已发送{next_step.get("name", "下一步")}通知，等待确认后推进'
        if not notify_ok:
            msg += f'（通知发送失败: {notify_err}）'
        return jsonify({
            'code': 0,
            'message': msg,
            'data': {
                'awaiting_confirmation': True,
                'awaiting_step': process.get('awaiting_step'),
                'step_name': next_step.get('name', ''),
                'template': confirmation_template
            }
        })

    _sync_work_order_status(order_no, status_key, process.get('current_step'))

    _sync_to_mysql(order_no, steps[process['current_step']].get('status_key', ''), process.get('order_no', ''))

    notify_ok, notify_err = _notify_process_event(order_no, 'process_advance', {
        '流程名称': flow_template.get('name', flow_type),
        '订单号': order_no,
        '当前步骤': step_or_next.get('name', ''),
        '下一步骤': steps[process['current_step'] + 1]["name"] if process['current_step'] < len(steps) - 1 else "流程结束",
        '执行人': operator_name,
    })

    msg = f'流程已推进到第 {process["current_step"]} 步'
    if not notify_ok:
        msg += f'（通知发送失败: {notify_err}）'
    return jsonify({'code': 0, 'message': msg, 'data': {'current_step': process['current_step'], 'total_steps': len(steps), 'status': process['status']}})


@dispatch_center_bp.route('/processes/confirm-by-reply', methods=['POST'])
def confirm_by_wechat_reply():
    body = request.get_json(force=True, silent=True) or {}
    process_id = body.get('process_id')
    user_id = body.get('user_id', '')
    user_name = body.get('user_name', '微信用户')
    content = body.get('content', '')

    if not process_id:
        return jsonify({'code': 1, 'message': '缺少 process_id'}), 400

    data = _dispatch_cache.get_data()
    processes = data.get('processes', [])
    process = next((p for p in processes if p.get('order_no') == process_id), None)
    if not process:
        return jsonify({'code': 404, 'message': '流程不存在'}), 404

    if not process.get('awaiting_confirmation'):
        return jsonify({'code': 400, 'message': '当前流程无需确认'}), 400

    content_lower = content.lower().strip()
    confirmed = False
    for keyword in CONFIRMATION_REPLY_KEYWORDS:
        if keyword.lower() in content_lower or content_lower == keyword.lower():
            confirmed = True
            break

    if not confirmed:
        return jsonify({'code': 400, 'message': '未识别到确认关键词'}), 400

    confirm_result = _do_confirm_process(process_id, user_name)
    return confirm_result


def _do_confirm_process(process_id: str, operator_name: str, lead_time: int = None):
    result = {'error': None, 'process_data': None}

    def updater(data):
        processes = data.get('processes', [])
        process = next((p for p in processes if p.get('order_no') == process_id), None)
        if not process:
            result['error'] = 'not_found'
            return

        if not process.get('awaiting_confirmation'):
            result['error'] = 'not_awaiting'
            return

        flow_type = process.get('flow_type', 'production')
        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
        steps = process.get('steps') or flow_template['steps']

        awaiting_step = process.get('awaiting_step', 0)
        awaiting_step_status = process.get('awaiting_step_status', 'pending')

        if awaiting_step >= len(steps):
            result['error'] = 'invalid_step'
            return

        current_step = process.get('current_step', 0)
        step = steps[current_step]

        if lead_time is not None and lead_time > 0:
            process['lead_time'] = lead_time
            process['lead_time_unit'] = '天'
            process['schedule_confirmed'] = True
            process['schedule_confirmed_at'] = datetime.now().isoformat()
            process['schedule_remark'] = f'已确认排产，工期{lead_time}天'

        process['current_step'] = awaiting_step
        process['completed_at_' + str(current_step)] = datetime.now().isoformat()
        process['completed_by_' + str(current_step)] = operator_name
        process['updated_at'] = datetime.now().isoformat()
        process['awaiting_confirmation'] = False
        process.pop('awaiting_step', None)
        process.pop('awaiting_step_status', None)
        process.pop('awaiting_since', None)
        process.pop('awaiting_operator', None)

        if awaiting_step >= len(steps) - 1:
            process['status'] = 'completed'
        else:
            process['status'] = steps[awaiting_step].get('status_key', 'in_progress')

        result['process_data'] = (process, steps, step, current_step, flow_template, flow_type, operator_name, awaiting_step_status)

    _dispatch_cache.update_data(updater)

    if result['error']:
        if result['error'] == 'not_found':
            return jsonify({'code': 404, 'message': '流程不存在'}), 404
        if result['error'] == 'not_awaiting':
            return jsonify({'code': 400, 'message': '当前流程无需确认，可直接推进'}), 400
        if result['error'] == 'invalid_step':
            return jsonify({'code': 400, 'message': '流程步骤无效'}), 400

    process, steps, step, current_step, flow_template, flow_type, operator_name, status_key = result['process_data']

    order_no = process.get('order_no', '')

    def _async_post_confirm():
        _sync_work_order_status(order_no, status_key, process.get('current_step'))
        if lead_time and lead_time > 0:
            _sync_schedule_to_container(order_no, process, lead_time, operator_name)
        next_step_name = steps[process['current_step'] + 1]["name"] if process['current_step'] < len(steps) - 1 else "流程结束"
        _notify_process_event(order_no, 'process_advance', {
            '流程名称': flow_template.get('name', flow_type),
            '订单号': order_no,
            '当前步骤': step.get('name', ''),
            '下一步骤': next_step_name,
            '执行人': operator_name,
        })

    threading.Thread(target=_async_post_confirm, daemon=True).start()

    msg = f'已确认，当前流程已推进到第 {process["current_step"]} 步'
    return jsonify({'code': 0, 'message': msg, 'data': {'current_step': process['current_step'], 'total_steps': len(steps), 'status': process['status']}})


@dispatch_center_bp.route('/processes/<order_no>/confirm', methods=['POST'])
def confirm_process_step(order_no):
    body = request.get_json(force=True, silent=True) or {}
    operator_name = body.get('operator_name', '系统')
    lead_time = body.get('lead_time')
    if lead_time is not None:
        try:
            lead_time = int(lead_time)
        except (ValueError, TypeError):
            lead_time = None
    return _do_confirm_process(order_no, operator_name, lead_time=lead_time)


@dispatch_center_bp.route('/processes/<order_no>/reject', methods=['POST'])
def reject_process_step(order_no):
    body = request.get_json(force=True, silent=True) or {}
    reason = body.get('reason', '未通过审核')
    operator_name = body.get('operator_name', '系统')

    result = {'error': None, 'process_data': None}

    def updater(data):
        process = next((p for p in data.get('processes', []) if p.get('order_no') == order_no), None)
        if not process:
            result['error'] = 'not_found'
            return

        flow_type = process.get('flow_type', 'production')
        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
        steps = process.get('steps') or flow_template['steps']
        current_step = process.get('current_step', 0)

        if current_step <= 0:
            result['error'] = 'first_step'
            return

        prev_step = current_step - 1
        process['current_step'] = prev_step
        process['status'] = steps[prev_step].get('status_key', 'pending')
        process['updated_at'] = datetime.now().isoformat()

        result['process_data'] = (process, steps, prev_step, operator_name)

    _dispatch_cache.update_data(updater)

    if result['error']:
        if result['error'] == 'not_found':
            return jsonify({'code': 404, 'message': '流程不存在'}), 404
        return jsonify({'code': 400, 'message': '已是第一步，无法回退'}), 400

    process, steps, prev_step, operator_name = result['process_data']

    order_no = process.get('order_no', '')

    def _async_post_reject():
        if order_no:
            prev_step_status = steps[prev_step].get('status_key', 'pending') if prev_step < len(steps) else 'pending'
            cc_status = 'dispatched' if prev_step_status == 'published' else 'pending'
            _sync_work_order_status(order_no, cc_status, process['current_step'])
            _sync_to_mysql(order_no, cc_status, order_no)

        notify_ok, notify_err = _notify_process_event(order_no, 'process_reject', {
            '订单号': order_no,
            '退回步骤': steps[prev_step]["name"],
            '退回原因': reason,
            '操作人': operator_name,
        })
        if not notify_ok:
            logger.warning(f"流程 {order_no} reject 通知失败: {notify_err}")

    threading.Thread(target=_async_post_reject, daemon=True).start()

    msg = f'流程已退回到第 {prev_step + 1} 步: {steps[prev_step]["name"]}'
    return jsonify({'code': 0, 'message': msg})


@dispatch_center_bp.route('/rules', methods=['GET'])
def list_rules():
    data = _dispatch_cache.get_data()
    rules_data = data.get('rules', {})
    rules_with_meta = []
    for key, meta in DISPATCH_RULES_DEFAULT.items():
        rules_with_meta.append({
            'key': key,
            'label': meta['label'],
            'env_key': meta['key'],
            'value': rules_data.get(key, meta['value']),
            'type': meta['type'],
        })
    return jsonify({'code': 0, 'data': rules_with_meta})


@dispatch_center_bp.route('/rules', methods=['POST'])
def save_rules():
    body = request.get_json(force=True, silent=True) or {}
    rules_update = body.get('rules', {})

    def updater(data):
        current_rules = data.get('rules', {})
        for key, value in rules_update.items():
            if key in DISPATCH_RULES_DEFAULT:
                current_rules[key] = value
                env_key = DISPATCH_RULES_DEFAULT[key]['key']
                try:
                    from dotenv import set_key
                    set_key(ENV_FILE, env_key, str(value))
                    os.environ[env_key] = str(value)
                except Exception as e:
                    logger.warning(f'更新环境变量 {env_key} 失败: {e}')
        data['rules'] = current_rules

    _dispatch_cache.update_data(updater)

    return jsonify({'code': 0, 'message': '调度规则已保存'})


@dispatch_center_bp.route('/flow-matching-rules', methods=['GET'])
def list_flow_matching_rules():
    """获取流程匹配规则列表"""
    data = _dispatch_cache.get_data()
    rules = data.get('flow_matching_rules', FLOW_MATCHING_RULES_DEFAULT)
    return jsonify({'code': 0, 'data': rules})


@dispatch_center_bp.route('/flow-matching-rules', methods=['POST'])
def save_flow_matching_rules():
    """保存流程匹配规则（全量替换）"""
    body = request.get_json(force=True, silent=True) or {}
    rules = body.get('rules', [])

    if not isinstance(rules, list):
        return jsonify({'code': 400, 'message': 'rules 必须为数组'})

    def updater(data):
        data['flow_matching_rules'] = rules

    _dispatch_cache.update_data(updater)
    logger.info(f"[FlowMatch] 流程匹配规则已更新，共 {len(rules)} 条")
    return jsonify({'code': 0, 'message': f'流程匹配规则已保存（{len(rules)} 条）'})


@dispatch_center_bp.route('/repair-categories', methods=['GET'])
def list_repair_categories():
    from container_config import container_config
    cats = container_config.get_all_repair_categories()
    return jsonify({'code': 0, 'data': [
        {'id': c.id, 'name': c.name, 'icon': c.icon,
         'assigned_operator_id': c.assigned_operator_id, 'description': c.description}
        for c in cats
    ]})


@dispatch_center_bp.route('/repair-categories', methods=['POST'])
def add_repair_category():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name', '').strip()
    assigned_operator_id = body.get('assigned_operator_id', '').strip()
    description = body.get('description', '').strip()
    if not name or not assigned_operator_id:
        return jsonify({'code': 400, 'message': '名称和负责人不能为空'})
    from container_config import container_config
    cat = container_config.add_repair_category(name, assigned_operator_id, description)
    if not cat:
        return jsonify({'code': 400, 'message': f'种类 [{name}] 已存在'})
    return jsonify({'code': 0, 'message': f'种类 [{name}] 已添加', 'data': {
        'id': cat.id, 'name': cat.name, 'icon': cat.icon,
        'assigned_operator_id': cat.assigned_operator_id, 'description': cat.description
    }})


@dispatch_center_bp.route('/repair-categories/<cat_id>', methods=['DELETE'])
def delete_repair_category(cat_id):
    from container_config import container_config
    if not container_config.remove_repair_category(cat_id):
        return jsonify({'code': 404, 'message': '种类不存在'})
    return jsonify({'code': 0, 'message': '删除成功'})


@dispatch_center_bp.route('/repair-records', methods=['GET'])
def list_repair_records():
    try:
        records = []
        result = _get_cached_work_orders(page=1, size=1000)
        all_pkgs = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])
        for pkg_dict in all_pkgs:
            if pkg_dict.get('data_type') == 'repair':
                try:
                    content = pkg_dict.get('content', {})
                    records.append({
                        'id': pkg_dict.get('id', ''),
                        'category_id': content.get('category_id', '') if isinstance(content, dict) else '',
                        'category_name': content.get('category_name', '') if isinstance(content, dict) else '',
                        'description': content.get('description', '') if isinstance(content, dict) else '',
                        'reporter_id': pkg_dict.get('operator_id') or '',
                        'status': pkg_dict.get('status', 'pending') or 'pending',
                        'target_operator': pkg_dict.get('target_operator') or '',
                        'created_at': pkg_dict.get('created_at', ''),
                    })
                except Exception:
                    pass
        records.sort(key=lambda r: str(r.get('created_at') or ''), reverse=True)
        return jsonify({'code': 0, 'data': records})
    except Exception as e:
        logger.error(f'list_repair_records error: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/repair-records/<record_id>/complete', methods=['POST'])
def complete_repair_record(record_id):
    result = _get_cached_work_orders(page=1, size=1000)
    pkg_dicts = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])
    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'repair'), None)
    if not target:
        return jsonify({'code': 404, 'message': '报修记录不存在'})
    _get_client().update_document_status('work_order', record_id, 'completed')

    # 维修完成微信通知
    try:
        content = target.get('content', {}) if isinstance(target.get('content'), dict) else {}
        msg = _render_template('tmpl_repair_complete', {
            '设备名称': content.get('device_name', target.get('title', '')),
            '维修人': target.get('target_operator', ''),
            '完成时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
            '耗时(小时)': content.get('repair_hours', 0),
        })
        _send_wechat_message(msg, 'markdown')
    except Exception as e:
        logger.warning(f'[维修完成] 通知发送失败: {e}')

    return jsonify({'code': 0, 'message': '已标记完成'})


# ═══════════════════════════════════════════════════════════════════════════════
# Part 19.5: 统一订单全流程状态接口 (v3.6.1)
# 分两个入口：桌面端 + 容器中心
# ═══════════════════════════════════════════════════════════════════════════════

def _collect_order_full_status(cur, order_no):
    """核心函数：聚合订单全流程状态（桌面端 + 容器中心共用）"""
    result = {
        'order_no': order_no,
        'order_status': 'unknown',
        'order_status_label': '未知',
        'order_basic': {},
        'processes': {'total': 0, 'completed': 0, 'in_progress': 0, 'distributed': 0, 'pending': 0, 'withdrawn': 0},
        'quality': {'total': 0, 'passed': 0, 'failed': 0, 'pending': 0, 'in_progress': 0},
        'material': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'withdrawn': 0},
        'repair': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0},
        'outsource': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'sent': 0},
        'schedule': {'total': 0, 'in_progress': 0, 'scheduled': 0, 'completed': 0},
    }

    # 1. 订单主表
    cur.execute(
        "SELECT id, order_no, product_name, customer_name, quantity, unit, "
        "status, priority, delivery_date, created_at, updated_at "
        "FROM process_records WHERE order_no=%s LIMIT 1",
        (order_no,))
    order_row = cur.fetchone()
    if order_row:
        cols = [d[0] for d in cur.description]
        order_dict = dict(zip(cols, order_row))
        for k in ['created_at', 'updated_at', 'delivery_date']:
            if order_dict.get(k) and hasattr(order_dict[k], 'isoformat'):
                order_dict[k] = order_dict[k].isoformat()
        result['order_basic'] = order_dict
        status = order_dict.get('status', 'unknown')
        result['order_status'] = status
        STATUS_LABELS = {
            'created': '已创建', 'planning': '排产中', 'processing': '进行中',
            'in_progress': '进行中', 'partial_completed': '部分完成',
            'completed': '已完成', 'cancelled': '已取消', 'withdrawn': '已撤回'
        }
        result['order_status_label'] = STATUS_LABELS.get(status, status)

    # 2-7. 各流程状态统计
    cur.execute(
        "SELECT status, COUNT(*) as cnt, SUM(completed_qty) as done, SUM(quantity) as total "
        "FROM process_sub_steps WHERE order_no=%s AND status NOT IN ('withdrawn') "
        "GROUP BY status",
        (order_no,))
    total_qty = 0
    done_qty = 0
    for row in cur.fetchall():
        status, cnt = row[0], row[1]
        result['processes']['total'] += cnt
        if status in result['processes']:
            result['processes'][status] = cnt
        total_qty += float(row[3] or 0)
        done_qty += float(row[2] or 0)

    cur.execute(
        "SELECT status, result, COUNT(*) as cnt "
        "FROM quality_records WHERE order_no=%s GROUP BY status, result",
        (order_no,))
    for row in cur.fetchall():
        status, res, cnt = row[0], row[1], row[2]
        result['quality']['total'] += cnt
        if status == 'completed':
            if res in ('pass', 'qualified'):
                result['quality']['passed'] += cnt
            elif res in ('fail', 'unqualified'):
                result['quality']['failed'] += cnt
        elif status in ('pending', 'distributed'):
            result['quality']['pending'] += cnt
        elif status == 'in_progress':
            result['quality']['in_progress'] += cnt

    cur.execute(
        "SELECT status, COUNT(*) as cnt FROM material_records WHERE order_no=%s GROUP BY status",
        (order_no,))
    for row in cur.fetchall():
        status, cnt = row[0], row[1]
        result['material']['total'] += cnt
        if status in result['material']:
            result['material'][status] = cnt

    cur.execute(
        "SELECT status, COUNT(*) as cnt FROM repair_records WHERE order_no=%s GROUP BY status",
        (order_no,))
    for row in cur.fetchall():
        status, cnt = row[0], row[1]
        result['repair']['total'] += cnt
        if status in result['repair']:
            result['repair'][status] = cnt

    cur.execute(
        "SELECT status, COUNT(*) as cnt FROM outsource_records WHERE order_no=%s GROUP BY status",
        (order_no,))
    for row in cur.fetchall():
        status, cnt = row[0], row[1]
        result['outsource']['total'] += cnt
        if status in result['outsource']:
            result['outsource'][status] = cnt

    cur.execute(
        "SELECT status, COUNT(*) as cnt FROM schedule_records WHERE order_no=%s "
        "AND (is_deleted = 0 OR is_deleted IS NULL) GROUP BY status",
        (order_no,))
    for row in cur.fetchall():
        status, cnt = row[0], row[1]
        result['schedule']['total'] += cnt
        if status in result['schedule']:
            result['schedule'][status] = cnt

    # 8. 整体进度
    result['overall_progress'] = round(min(1.0, done_qty / total_qty), 2) if total_qty > 0 else 0

    # 9. 阻塞判定
    is_blocked = False
    block_reasons = []
    if result['material']['total'] > 0 and result['material']['completed'] < result['material']['total']:
        mp = result['material']['pending'] + result['material']['in_progress']
        if mp > 0:
            is_blocked = True
            block_reasons.append(f"物料待办 {mp} 个")
    if result['quality']['failed'] > 0:
        is_blocked = True
        block_reasons.append(f"质检不合格 {result['quality']['failed']} 个")
    if result['outsource']['total'] > 0 and result['outsource']['completed'] < result['outsource']['total']:
        op = result['outsource']['pending'] + result['outsource']['sent']
        if op > 0:
            is_blocked = True
            block_reasons.append(f"外协待办 {op} 个")
    result['is_blocked'] = is_blocked
    result['block_reasons'] = block_reasons

    # 10. 综合状态兜底
    if not order_row:
        if result['processes']['total'] == 0:
            result['order_status'] = 'unknown'
            result['order_status_label'] = '订单不存在或无工序'
        elif result['processes']['completed'] == result['processes']['total']:
            result['order_status'] = 'completed'
            result['order_status_label'] = '已完成'
        elif result['processes']['in_progress'] > 0 or result['processes']['distributed'] > 0:
            result['order_status'] = 'processing'
            result['order_status_label'] = '进行中'
    return result


def _attach_order_status_sync(cur, rows, order_field='order_no'):
    """同步附加统一订单状态字段到列表项

    给各回归接口（质检/物料/外协/排产）的列表项附加：
    - _order_status: 订单级状态
    - _order_progress: 订单整体进度 0~1
    - _is_blocked: 订单是否阻塞
    """
    cache = {}
    for row in rows:
        ono = row.get(order_field)
        if not ono:
            continue
        if ono not in cache:
            try:
                st = _collect_order_full_status(cur, ono)
                cache[ono] = {
                    '_order_status': st.get('order_status'),
                    '_order_status_label': st.get('order_status_label'),
                    '_order_progress': st.get('overall_progress'),
                    '_is_blocked': st.get('is_blocked'),
                    '_block_reasons': st.get('block_reasons'),
                }
            except Exception:
                cache[ono] = {}
        row.update(cache[ono])


# ─────────────────────────────────────────────────────────────────
# 入口 A：桌面端统一订单状态查询（直接读数据库）
# ─────────────────────────────────────────────────────────────────
@dispatch_center_bp.route('/desktop/order-status/<order_no>', methods=['GET'])
def desktop_order_status(order_no):
    """桌面端统一订单全流程状态查询（直接读数据库）

    路径: /api/dispatch-center/desktop/order-status/<order_no>
    """
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()
        result = _collect_order_full_status(cur, order_no)
        result['source'] = 'desktop_direct_db'
        conn.close()
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        logger.exception('桌面端订单状态查询失败')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/desktop/order-status-list', methods=['GET'])
def desktop_order_status_list():
    """桌面端订单列表状态汇总（直接读数据库）"""
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status_filter', 'all')

        cur.execute(
            "SELECT order_no FROM process_records WHERE is_archived = 0 "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,))
        order_nos = [r[0] for r in cur.fetchall() if r[0]]

        result_orders = []
        for ono in order_nos:
            summary = _collect_order_full_status(cur, ono)
            result_orders.append({
                'order_no': ono,
                'order_status': summary['order_status'],
                'order_status_label': summary['order_status_label'],
                'overall_progress': summary['overall_progress'],
                'is_blocked': summary['is_blocked'],
                'block_reasons': summary['block_reasons'],
                'product_name': summary['order_basic'].get('product_name', ''),
                'customer_name': summary['order_basic'].get('customer_name', ''),
                'proc_total': summary['processes']['total'],
                'proc_completed': summary['processes']['completed'],
                'quality_failed': summary['quality']['failed'],
                'material_pending': summary['material']['pending'] + summary['material']['in_progress'],
            })
        conn.close()

        if status_filter == 'blocked':
            result_orders = [o for o in result_orders if o['is_blocked']]
        elif status_filter == 'processing':
            result_orders = [o for o in result_orders if o['order_status'] in ('processing', 'in_progress') and not o['is_blocked']]
        elif status_filter == 'completed':
            result_orders = [o for o in result_orders if o['order_status'] == 'completed']

        return jsonify({'code': 0, 'data': {'orders': result_orders, 'total': len(result_orders), 'source': 'desktop_direct_db'}})
    except Exception as e:
        logger.exception('桌面端订单状态列表查询失败')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


# ─────────────────────────────────────────────────────────────────
# 入口 B：容器中心/移动端/调度中心 → 全部调用容器中心 SSOT 端点
# ─────────────────────────────────────────────────────────────────
def _proxy_to_container_ssot(path):
    """统一代理到容器中心 SSOT 端点

    容器中心 URL 从环境变量读取，默认 http://127.0.0.1:5002
    v3.6.1 增强：添加内存缓存（TTL=10s）+ retry + fallback
    """
    import requests as _req
    from core.config import CONTAINER_CENTER_URL
    url = f'{CONTAINER_CENTER_URL}{path}'

    # [v3.6.1] 内存缓存：避免每次请求都查 7 张表
    cache_key = f'ssot:{url}'
    cached = _ssot_cache_get(cache_key)
    if cached is not None:
        return cached

    # [Bug Fix 2026-06-20] 5002 要求 X-API-Key header，否则 1003 拒绝
    # 复用已有 _cc_headers() 辅助函数（含鉴权头）
    _proxy_headers = _cc_headers()

    # 重试 2 次
    result = None
    for attempt in range(2):
        try:
            resp = _req.get(url, headers=_proxy_headers, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                break
            logger.error(f'容器中心返回非200: {url} -> {resp.status_code} {resp.text[:200]}')
            result = {'code': resp.status_code, 'message': f'容器中心返回 {resp.status_code}: {resp.text[:100]}'}
        except _req.exceptions.Timeout:
            logger.error(f'容器中心超时(尝试{attempt+1}/2): {url}')
            result = {'code': 504, 'message': '容器中心响应超时'}
        except _req.exceptions.ConnectionError:
            logger.error(f'容器中心连接失败(尝试{attempt+1}/2): {url}')
            result = {'code': 503, 'message': '容器中心连接失败（端口可能未启动）'}
        except Exception as e:
            logger.exception(f'代理到容器中心异常: {url}')
            result = {'code': 503, 'message': '容器中心不可用失败，请稍后重试'}
            break
        if attempt == 0:
            import time; time.sleep(0.5)

    if result and result.get('code') == 0:
        _ssot_cache_set(cache_key, result, ttl=10)
    return result


_ssot_cache = {}
_ssot_cache_ts = {}
SSOT_CACHE_TTL = 10  # 秒

def _ssot_cache_get(key):
    import time
    ts = _ssot_cache_ts.get(key, 0)
    if time.time() - ts < SSOT_CACHE_TTL:
        return _ssot_cache.get(key)
    return None

def _ssot_cache_set(key, value, ttl=10):
    _ssot_cache[key] = value
    _ssot_cache_ts[key] = __import__('time').time()
    # 简单清理：缓存项超过 100 个时清理过期项
    if len(_ssot_cache) > 100:
        import time
        now = time.time()
        expired = [k for k, t in _ssot_cache_ts.items() if now - t >= SSOT_CACHE_TTL]
        for k in expired:
            _ssot_cache.pop(k, None)
            _ssot_cache_ts.pop(k, None)


@dispatch_center_bp.route('/container/order-status/<order_no>', methods=['GET'])
def container_order_status(order_no):
    """通过容器中心 SSOT 获取订单状态

    路径: /api/dispatch-center/container/order-status/<order_no>
    调用: http://5002/api/orders/full-status/<order_no>
    """
    result = _proxy_to_container_ssot(f'/api/orders/full-status/{order_no}')
    if isinstance(result, dict) and result.get('code') == 0:
        result.setdefault('data', {})['source'] = 'container_center_ssot_via_dispatch'
    return jsonify(result)


@dispatch_center_bp.route('/container/order-status-list', methods=['GET'])
def container_order_status_list():
    """通过容器中心 SSOT 获取订单状态列表"""
    limit = request.args.get('limit', 50)
    status_filter = request.args.get('status_filter', 'all')
    result = _proxy_to_container_ssot(f'/api/orders/full-status-list?limit={limit}&status_filter={status_filter}')
    if isinstance(result, dict) and result.get('code') == 0:
        result.setdefault('data', {})['source'] = 'container_center_ssot_via_dispatch'
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────
# 兼容：保留原 /order-status 端点（向后兼容）
# ─────────────────────────────────────────────────────────────────
@dispatch_center_bp.route('/order-status/<order_no>', methods=['GET'])
def order_full_status(order_no):
    """统一订单全流程状态汇总接口

    聚合查询同一订单下所有流程的状态：
    - 订单主表（process_records）
    - 生产工序（process_sub_steps）
    - 质检（quality_records）
    - 物料（material_records）
    - 维修（repair_records）
    - 外协（outsource_records）
    - 排产（schedule_records）

    返回数据示例:
    {
      "code": 0,
      "data": {
        "order_no": "ORD2026001",
        "order_status": "processing",
        "order_status_label": "进行中",
        "order_basic": {...},
        "processes": {"total": 5, "completed": 2, "in_progress": 1, "pending": 2, ...},
        "quality": {"total": 3, "passed": 2, "failed": 1, "pending": 0},
        "material": {"total": 4, "completed": 3, "pending": 1},
        "repair": {"total": 1, "completed": 0, "pending": 1},
        "outsource": {"total": 2, "completed": 1, "pending": 1},
        "schedule": {"total": 1, "in_progress": 1},
        "overall_progress": 0.65,
        "is_blocked": false
      }
    }
    """
    try:
        from core.db_compat import get_conn
        conn = get_conn()
        cur = conn.cursor()
        result = {
            'order_no': order_no,
            'order_status': 'unknown',
            'order_status_label': '未知',
            'order_basic': {},
            'processes': {'total': 0, 'completed': 0, 'in_progress': 0, 'distributed': 0, 'pending': 0, 'withdrawn': 0},
            'quality': {'total': 0, 'passed': 0, 'failed': 0, 'pending': 0, 'in_progress': 0},
            'material': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'withdrawn': 0},
            'repair': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0},
            'outsource': {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0, 'sent': 0},
            'schedule': {'total': 0, 'in_progress': 0, 'scheduled': 0, 'completed': 0},
        }

        # 1. 订单主表
        cur.execute(
            "SELECT id, order_no, product_name, customer_name, quantity, unit, "
            "status, priority, delivery_date, created_at, updated_at "
            "FROM process_records WHERE order_no=%s LIMIT 1",
            (order_no,))
        order_row = cur.fetchone()
        if order_row:
            cols = [d[0] for d in cur.description]
            order_dict = dict(zip(cols, order_row))
            for k in ['created_at', 'updated_at', 'delivery_date']:
                if order_dict.get(k) and hasattr(order_dict[k], 'isoformat'):
                    order_dict[k] = order_dict[k].isoformat()
            result['order_basic'] = order_dict
            status = order_dict.get('status', 'unknown')
            result['order_status'] = status
            STATUS_LABELS = {
                'created': '已创建', 'planning': '排产中', 'processing': '进行中',
                'in_progress': '进行中', 'partial_completed': '部分完成',
                'completed': '已完成', 'cancelled': '已取消', 'withdrawn': '已撤回'
            }
            result['order_status_label'] = STATUS_LABELS.get(status, status)

        # 2. 生产工序状态统计
        cur.execute(
            "SELECT status, COUNT(*) as cnt, SUM(completed_qty) as done, SUM(quantity) as total "
            "FROM process_sub_steps WHERE order_no=%s AND status NOT IN ('withdrawn') "
            "GROUP BY status",
            (order_no,))
        total_qty = 0
        done_qty = 0
        for row in cur.fetchall():
            status, cnt, qty_done, qty_total = row[0], row[1], float(row[2] or 0), float(row[3] or 0)
            result['processes']['total'] += cnt
            if status in result['processes']:
                result['processes'][status] = cnt
            total_qty += qty_total
            done_qty += qty_done

        # 3. 质检状态统计
        cur.execute(
            "SELECT status, result, COUNT(*) as cnt "
            "FROM quality_records WHERE order_no=%s "
            "GROUP BY status, result",
            (order_no,))
        for row in cur.fetchall():
            status, res, cnt = row[0], row[1], row[2]
            result['quality']['total'] += cnt
            if status == 'completed':
                if res in ('pass', 'qualified'):
                    result['quality']['passed'] += cnt
                elif res in ('fail', 'unqualified'):
                    result['quality']['failed'] += cnt
            elif status in ('pending', 'distributed'):
                result['quality']['pending'] += cnt
            elif status == 'in_progress':
                result['quality']['in_progress'] += cnt

        # 4. 物料状态统计
        cur.execute(
            "SELECT status, COUNT(*) as cnt, SUM(quantity) as qty, SUM(completed_qty) as done "
            "FROM material_records WHERE order_no=%s "
            "GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['material']['total'] += cnt
            if status in result['material']:
                result['material'][status] = cnt

        # 5. 维修状态统计
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM repair_records WHERE order_no=%s GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['repair']['total'] += cnt
            if status in result['repair']:
                result['repair'][status] = cnt

        # 6. 外协状态统计
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM outsource_records WHERE order_no=%s GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['outsource']['total'] += cnt
            if status in result['outsource']:
                result['outsource'][status] = cnt

        # 7. 排产状态统计
        cur.execute(
            "SELECT status, COUNT(*) as cnt FROM schedule_records WHERE order_no=%s "
            "AND (is_deleted = 0 OR is_deleted IS NULL) GROUP BY status",
            (order_no,))
        for row in cur.fetchall():
            status, cnt = row[0], row[1]
            result['schedule']['total'] += cnt
            if status in result['schedule']:
                result['schedule'][status] = cnt

        # 8. 计算整体进度和阻塞状态
        if total_qty > 0:
            result['overall_progress'] = round(min(1.0, done_qty / total_qty), 2)
        else:
            result['overall_progress'] = 0

        # 阻塞判定：物料/质检任一关键流程卡住
        is_blocked = False
        block_reasons = []
        if result['material']['total'] > 0 and result['material']['completed'] < result['material']['total']:
            material_pending = result['material']['pending'] + result['material']['in_progress']
            if material_pending > 0:
                is_blocked = True
                block_reasons.append(f"物料待办 {material_pending} 个")
        if result['quality']['failed'] > 0:
            is_blocked = True
            block_reasons.append(f"质检不合格 {result['quality']['failed']} 个")
        if result['outsource']['total'] > 0 and result['outsource']['completed'] < result['outsource']['total']:
            outsource_pending = result['outsource']['pending'] + result['outsource']['sent']
            if outsource_pending > 0:
                is_blocked = True
                block_reasons.append(f"外协待办 {outsource_pending} 个")

        result['is_blocked'] = is_blocked
        result['block_reasons'] = block_reasons

        # 9. 综合状态判定（如果订单主表状态不准确，以流程汇总为准）
        if not order_row:
            # 订单不存在，从工序完成情况反推
            if result['processes']['total'] == 0:
                result['order_status'] = 'unknown'
                result['order_status_label'] = '订单不存在或无工序'
            elif result['processes']['completed'] == result['processes']['total']:
                result['order_status'] = 'completed'
                result['order_status_label'] = '已完成'
            elif result['processes']['in_progress'] > 0 or result['processes']['distributed'] > 0:
                result['order_status'] = 'processing'
                result['order_status_label'] = '进行中'

        conn.close()
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        logger.exception('订单全流程状态查询失败')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/order-status-list', methods=['GET'])
def order_status_list():
    """批量查询订单全流程状态（仪表盘用）

    参数:
      - limit: 限制条数，默认 50
      - status_filter: 状态过滤 (processing/completed/blocked/all)

    返回订单列表 + 每个订单的全流程状态汇总
    """
    # 鉴权：只接受 JWT Bearer Token，旧协议 hex token 必须拒绝
    ok, err = _check_jwt_auth()
    if not ok:
        return err
    try:
        from core.db_compat import get_conn
        conn = get_conn()
        cur = conn.cursor()
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status_filter', 'all')

        # 获取最近订单
        cur.execute(
            "SELECT order_no, product_name, status, quantity, delivery_date, customer_name "
            "FROM process_records WHERE is_archived = 0 "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,))
        cols = [d[0] for d in cur.description]
        orders = [dict(zip(cols, r)) for r in cur.fetchall()]

        result_orders = []
        for o in orders:
            ono = o['order_no']
            if not ono:
                continue
            if o.get('delivery_date') and hasattr(o['delivery_date'], 'isoformat'):
                o['delivery_date'] = o['delivery_date'].isoformat()

            # 工序完成度
            cur.execute(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed, "
                "SUM(quantity) as qty_total, SUM(completed_qty) as qty_done "
                "FROM process_sub_steps WHERE order_no=%s AND status != 'withdrawn'",
                (ono,))
            ps = cur.fetchone()
            proc_total = int(ps[0] or 0)
            proc_done = int(ps[1] or 0)
            qty_total = float(ps[2] or 0)
            qty_done = float(ps[3] or 0)

            # 质检不合格
            cur.execute(
                "SELECT COUNT(*) FROM quality_records WHERE order_no=%s "
                "AND status='completed' AND result IN ('fail', 'unqualified')",
                (ono,))
            q_failed = cur.fetchone()[0]

            # 物料未完成
            cur.execute(
                "SELECT COUNT(*) FROM material_records WHERE order_no=%s "
                "AND status NOT IN ('completed', 'withdrawn')",
                (ono,))
            m_pending = cur.fetchone()[0]

            # 阻塞判定
            is_blocked = q_failed > 0 or m_pending > 0

            progress = round(qty_done / qty_total, 2) if qty_total > 0 else 0

            summary = {
                'order_no': ono,
                'product_name': o.get('product_name', ''),
                'customer_name': o.get('customer_name', ''),
                'order_status': o.get('status', 'unknown'),
                'quantity': qty_total,
                'completed_qty': qty_done,
                'progress': progress,
                'proc_total': proc_total,
                'proc_completed': proc_done,
                'quality_failed': q_failed,
                'material_pending': m_pending,
                'is_blocked': is_blocked,
                'delivery_date': o.get('delivery_date', ''),
            }
            result_orders.append(summary)

        # 过滤
        if status_filter == 'blocked':
            result_orders = [o for o in result_orders if o['is_blocked']]
        elif status_filter == 'processing':
            result_orders = [o for o in result_orders if o['order_status'] in ('processing', 'in_progress') and not o['is_blocked']]
        elif status_filter == 'completed':
            result_orders = [o for o in result_orders if o['order_status'] == 'completed']

        conn.close()
        return jsonify({'code': 0, 'data': {'orders': result_orders, 'total': len(result_orders)}})
    except Exception as e:
        logger.exception('订单状态列表查询失败')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Part 20: 回归测试 API (v3.6.1)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/quality-regression', methods=['GET'])
def quality_regression():
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, order_no, inspection_type, result, inspector, status, record_date "
            "FROM container_center.quality_records "
            "WHERE (status IS NULL OR status NOT IN ('withdrawn')) ORDER BY record_date DESC LIMIT 100")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        # [v3.6.1 同步] 附加统一订单状态字段
        _attach_order_status_sync(cur, rows, 'order_no')
        conn.close()
        return jsonify({'code': 0, 'data': {'items': rows}})
    except Exception as e:
        logger.exception('质检回归查询失败')
        return jsonify({'code': 0, 'data': {'items': []}})


@dispatch_center_bp.route('/material-regression', methods=['GET'])
def material_regression():
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, order_no, material_name, target_operator, status, created_at "
            "FROM container_center.material_records "
            "WHERE (status IS NULL OR status NOT IN ('withdrawn')) ORDER BY created_at DESC LIMIT 100")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        # [v3.6.1 同步] 附加统一订单状态字段
        _attach_order_status_sync(cur, rows, 'order_no')
        conn.close()
        return jsonify({'code': 0, 'data': {'items': rows}})
    except Exception as e:
        logger.exception('物料回归查询失败')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/outsource-regression', methods=['GET'])
def outsource_regression():
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, order_no, title, supplier_name, status, created_at "
            "FROM container_center.outsource_records "
            "WHERE (status IS NULL OR status NOT IN ('withdrawn')) ORDER BY created_at DESC LIMIT 100")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        # [v3.6.1 同步] 附加统一订单状态字段
        _attach_order_status_sync(cur, rows, 'order_no')
        conn.close()
        return jsonify({'code': 0, 'data': {'items': rows}})
    except Exception as e:
        logger.exception('外协回归查询失败')
        return jsonify({'code': 0, 'data': {'items': []}})


@dispatch_center_bp.route('/schedule-regression', methods=['GET'])
def schedule_regression():
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, order_no, status, created_at "
            "FROM container_center.schedule_records "
            "WHERE (status IS NULL OR status NOT IN ('withdrawn')) ORDER BY created_at DESC LIMIT 100")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        # [v3.6.1 同步] 附加统一订单状态字段
        _attach_order_status_sync(cur, rows, 'order_no')
        conn.close()
        return jsonify({'code': 0, 'data': {'items': rows}})
    except Exception as e:
        logger.exception('排产回归查询失败')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


def _get_outsource_records(status=None):
    result = _get_cached_work_orders(page=1, size=2000)
    pkg_dicts = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])
    return [p for p in pkg_dicts if p.get('data_type') == 'outsource'
            and (status is None or p.get('status') == status)]


@dispatch_center_bp.route('/outsource-records', methods=['GET'])
def list_outsource_records():
    status = request.args.get('status')
    records = _get_outsource_records(status)
    records.sort(key=lambda r: str(r.get('created_at') or ''), reverse=True)
    return jsonify({'code': 0, 'data': records})


@dispatch_center_bp.route('/outsource-records', methods=['POST'])
def create_outsource_record():
    body = request.get_json(force=True, silent=True) or {}
    order_no = body.get('order_no', '').strip()
    process_name = body.get('process_name', '').strip()
    process_seq = body.get('process_seq', 1)
    planned_qty = body.get('planned_qty', 0)
    outsource_remark = body.get('outsource_remark', '').strip()
    operator_id = body.get('operator_id', '').strip()
    if not order_no or not process_name:
        return jsonify({'code': 400, 'message': '订单号和工序名不能为空'})
    try:
        outsource_data = {
            'data_type': 'outsource',
            'order_no': order_no,
            'process_name': process_name,
            'process_seq': process_seq,
            'planned_qty': planned_qty,
            'outsource_remark': outsource_remark,
            'target_operator': operator_id,
        }
        pkg = _get_client().create_document('work_order', outsource_data)
        pkg_id = pkg.get('id')
        if pkg_id:
            _get_client().distribute(pkg_id, operator_id)

        # 外协发出微信通知
        try:
            msg = _render_template('tmpl_outsource_send', {
                '供应商': process_name,
                '物料名称': body.get('material_name', ''),
                '数量': planned_qty,
            })
            _send_wechat_message(msg, 'markdown')
        except Exception as e:
            logger.warning(f'[外协发出] 通知失败: {e}')

        return jsonify({'code': 0, 'message': '外协任务已创建', 'data': {'id': pkg_id}})
    except Exception as e:
        logger.error(f'create_outsource_record error: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/outsource-records/<record_id>', methods=['GET'])
def get_outsource_record(record_id):
    pkg_dicts = _get_cached_work_orders(page=1, size=2000) or []
    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)
    if not target:
        return jsonify({'code': 404, 'message': '未找到外协记录'})
    return jsonify({'code': 0, 'data': target})


@dispatch_center_bp.route('/outsource-records/<record_id>/assign', methods=['POST'])
def assign_outsource_record(record_id):
    body = request.get_json(force=True, silent=True) or {}
    operator_id = body.get('operator_id', '').strip()
    if not operator_id:
        return jsonify({'code': 400, 'message': '负责人不能为空'})
    pkg_dicts = _get_cached_work_orders(page=1, size=2000) or []
    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)
    if not target:
        return jsonify({'code': 404, 'message': '未找到外协记录'})
    return jsonify({'code': 0, 'message': _get_client().assign_task_operator('work_order', record_id, operator_id)})


def _update_outsource_extra(record_id, status, **extra):
    pkg_dicts = _get_cached_work_orders(page=1, size=2000) or []
    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)
    if not target:
        return None
    content = target.get('content', '{}')
    if isinstance(content, str):
        content = json.loads(content)
    content.update(extra)
    _get_client().update_document('work_order', record_id, {'content': content, 'status': status})
    return target


@dispatch_center_bp.route('/outsource-records/<record_id>/feedback', methods=['POST'])
def feedback_outsource_record(record_id):
    body = request.get_json(force=True, silent=True) or {}
    promised_days = body.get('promised_days')
    if promised_days is None:
        return jsonify({'code': 400, 'message': '承诺天数不能为空'})
    promised_days = int(promised_days)
    promised_date = (datetime.now() + timedelta(days=promised_days)).strftime('%Y-%m-%d %H:%M:%S')
    result = _update_outsource_extra(record_id, 'processing',
        promised_days=promised_days,
        promised_date=promised_date,
        feedback_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    if not result:
        return jsonify({'code': 404, 'message': '记录不存在'})
    return jsonify({'code': 0, 'message': f'已反馈：承诺 {promised_days} 天后完成'})

@dispatch_center_bp.route('/outsource-records/<record_id>/complete', methods=['POST'])
def complete_outsource_record(record_id):
    result = _update_outsource_extra(record_id, 'completed',
        completed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    if not result:
        return jsonify({'code': 404, 'message': '记录不存在'})
    return jsonify({'code': 0, 'message': '外协任务已完成'})

@dispatch_center_bp.route('/outsource-records/<record_id>/receive', methods=['POST'])
def receive_outsource_record(record_id):
    result = _update_outsource_extra(record_id, 'received',
        received_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    if not result:
        return jsonify({'code': 404, 'message': '记录不存在'})

    # 外协收货微信通知
    try:
        pkg_dicts = _get_cached_work_orders(page=1, size=2000) or []
        pkg = next((p for p in pkg_dicts if p.get('id') == record_id), {})
        content = pkg.get('content', {}) if isinstance(pkg.get('content'), dict) else {}
        msg = _render_template('tmpl_outsource_receive', {
            '物料名称': content.get('material_name', pkg.get('title', '')),
            '数量': content.get('planned_qty', 0),
        })
        _send_wechat_message(msg, 'markdown')
    except Exception as e:
        logger.warning(f'[外协收货] 通知失败: {e}')

    return jsonify({'code': 0, 'message': '已确认收货入库'})


@dispatch_center_bp.route('/outsource-config', methods=['GET'])
def get_outsource_config():
    from container_config import container_config
    cfg = container_config.get_outsourc_config()
    return jsonify({'code': 0, 'data': {
        'enabled': cfg.enabled,
        'default_operator_id': cfg.default_operator_id,
        'remind_days': cfg.remind_days,
        'overdue_remind_times': cfg.overdue_remind_times,
    }})


@dispatch_center_bp.route('/outsource-config', methods=['POST'])
def update_outsource_config():
    body = request.get_json(force=True, silent=True) or {}
    from container_config import container_config
    container_config.update_outsourc_config(**body)
    return jsonify({'code': 0, 'message': '配置已更新'})


# ═══════════════════════════════════════════════════════════════════════════════
# Part 12: 业务统计路由 (行 5946~6168)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/stats', methods=['GET'])
def get_stats():
    period = request.args.get('period', 'today')

    task_stats = {'report': 0, 'quality': 0, 'material': 0, 'approval': 0}
    status_stats = {}
    today_completed = 0
    today_created = 0

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        result = _get_client().query_documents('work_order', all=True)
        packages = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])
        for pkg in packages:
                dtype = pkg.get('data_type', 'other')
                task_stats[dtype] = task_stats.get(dtype, 0) + 1

                status = pkg.get('status', 'unknown')
                status_stats[status] = status_stats.get(status, 0) + 1

                created_at = pkg.get('created_at', '')
                if created_at:
                    try:
                        ct = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
                        if ct >= today_start:
                            today_created += 1
                    except (ValueError, TypeError):
                        pass

                completed_at = pkg.get('completed_at', '')
                if completed_at:
                    try:
                        cpt = datetime.fromisoformat(completed_at) if isinstance(completed_at, str) else completed_at
                        if cpt >= today_start:
                            today_completed += 1
                    except (ValueError, TypeError):
                        pass
    except Exception as e:
        logger.error(f'获取统计失败: {e}')

    # [修复 2026-06-15] 增强兜底逻辑：同时处理 task_stats 和 status_stats
    if not status_stats or not any(task_stats.values()):
        try:
            cc = _get_container_center()
            if cc and hasattr(cc, 'storage') and cc.storage:
                proc_records = cc.storage.get_process_records(limit=5000)
                for rec in proc_records:
                    status = rec.get('status', 'unknown')
                    status_stats[status] = status_stats.get(status, 0) + 1
                    # 从 process_records 的 flow_type 推断 task_type
                    flow_type = rec.get('flow_type', 'production')
                    if flow_type in ('report', 'process_report'):
                        task_stats['report'] = task_stats.get('report', 0) + 1
                    elif flow_type in ('quality', 'quality_check'):
                        task_stats['quality'] = task_stats.get('quality', 0) + 1
                    elif flow_type in ('material', 'material_request'):
                        task_stats['material'] = task_stats.get('material', 0) + 1
                    elif flow_type in ('approval', 'outsource'):
                        task_stats['approval'] = task_stats.get('approval', 0) + 1
                    else:
                        task_stats['report'] = task_stats.get('report', 0) + 1  # 默认归类为报工
        except Exception as e:
            logger.warning(f'从 process_records 获取状态统计失败: {e}')

    dispatch_log = _dispatch_cache.get_data().get('dispatch_log', [])
    today_assigns = sum(1 for log in dispatch_log if log.get('timestamp', '').startswith(today_start.strftime('%Y-%m-%d')))

    return jsonify({
        'code': 0,
        'data': {
            'task_by_type': task_stats,
            'task_by_status': status_stats,
            'today_created': today_created,
            'today_completed': today_completed,
            'today_assigns': today_assigns,
            'total_tasks': sum(task_stats.values()),
        },
    })


@dispatch_center_bp.route('/alerts', methods=['GET'])
def list_alerts():
    data = _dispatch_cache.get_data()
    alerts = data.get('alerts', [])
    limit = int(request.args.get('limit', 50))
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    if unread_only:
        alerts = [a for a in alerts if not a.get('dismissed')]

    day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    overdue_tasks = []
    try:
        packages = _get_cached_work_orders(page=1, size=2000)
        now = datetime.now()
        for pkg in packages:
            if not isinstance(pkg, dict):
                continue
            if pkg.get('status') in ('pending', 'dispatched'):
                created_at = pkg.get('created_at', '')
                try:
                    ct = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
                    elapsed = (now - ct).total_seconds() / 60
                    if elapsed > 120:
                        overdue_tasks.append({
                            'task_id': pkg.get('id'),
                            'title': pkg.get('title', ''),
                            'elapsed_minutes': int(elapsed),
                            'operator': pkg.get('target_operator', ''),
                        })
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        logger.warning(f"获取逾期任务异常: {e}")

    return jsonify({'code': 0, 'data': {'alerts': alerts[-limit:][::-1], 'overdue_tasks': overdue_tasks[:20], 'total': len(alerts)}})


@dispatch_center_bp.route('/alerts/<alert_id>/dismiss', methods=['POST'])
def dismiss_alert(alert_id):
    result = {'found': False}

    def updater(data):
        for alert in data.get('alerts', []):
            if alert.get('id') == alert_id:
                alert['dismissed'] = True
                alert['dismissed_at'] = datetime.now().isoformat()
                result['found'] = True
                return

    _dispatch_cache.update_data(updater)
    # 同步 dismiss 到容器中心 AlertStore
    try:
        _get_container_center().alert_store.dismiss(alert_id)
    except Exception:
        pass
    if result['found']:
        return jsonify({'code': 0, 'message': '告警已忽略'})
    return jsonify({'code': 404, 'message': '告警不存在'}), 404


@dispatch_center_bp.route('/alerts/stats', methods=['GET'])
def get_alert_stats():
    """告警统计：按类型/严重度/时间汇总"""
    try:
        ctx = DispatchContext.get_instance()
        engine = ctx.alert_engine
        engine_stats = engine.get_stats() if engine else {}
        alerts = _dispatch_cache.get_data().get('alerts', [])
        by_type = {}; by_level = {}
        now = datetime.now()
        today_count = 0
        for a in alerts:
            t = a.get('alert_type', 'unknown')
            l = a.get('level', 'INFO')
            by_type[t] = by_type.get(t, 0) + 1
            by_level[l] = by_level.get(l, 0) + 1
            try:
                ca = datetime.fromisoformat(a.get('created_at','')) if isinstance(a.get('created_at'),str) else a.get('created_at')
                if ca and (now - ca).days == 0:
                    today_count += 1
            except Exception: pass
        return jsonify({'code': 0, 'data': {
            'total': len(alerts),
            'today': today_count,
            'active': sum(1 for a in alerts if not a.get('dismissed')),
            'by_type': by_type,
            'by_level': by_level,
            'engine': {
                **engine_stats,
                'health': engine.health_check() if engine else {'status': 'NOT_RUNNING'},
            },
        }})
    except Exception as e:
        return jsonify({'code': 0, 'data': {}})


@dispatch_center_bp.route('/alerts/<alert_id>/ack', methods=['POST'])
def acknowledge_alert(alert_id):
    """确认告警"""
    try:
        from container_center.storage import AlertStore
        store = AlertStore()
        if store.acknowledge(alert_id, request.args.get('operator', '')):
            return jsonify({'code': 0, 'message': '告警已确认'})
        return jsonify({'code': 404, 'message': '告警不存在'}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/alerts/<alert_id>/snooze', methods=['POST'])
def snooze_alert(alert_id):
    """临时静默告警 N 小时"""
    try:
        hours = int(request.args.get('hours', 4))
        snoozed_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        from container_center.storage import AlertStore
        store = AlertStore()
        if store.update(alert_id, {'snoozed_until': snoozed_until}):
            return jsonify({'code': 0, 'message': f'告警已静默 {hours} 小时'})
        return jsonify({'code': 404, 'message': '告警不存在'}), 404
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/dispatch-log', methods=['GET'])
def get_dispatch_log():
    data = _dispatch_cache.get_data()
    logs = data.get('dispatch_log', [])
    limit = int(request.args.get('limit', 100))
    return jsonify({'code': 0, 'data': logs[-limit:][::-1], 'total': len(logs)})





# === 定时任务统一管理器 ===

# ═══════════════════════════════════════════════════════════════════════════════
# Part 13: 定时任务控制器 (行 6169~6432)
# ═══════════════════════════════════════════════════════════════════════════════

import sqlite3 as _sqlite3

_SCHEDULER_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
_SCHEDULER_DB_PATH = DB_PATHS['scheduler_configs']


class SchedulerController:
    """定时任务控制器基类"""
    def get_name(self): raise NotImplementedError
    def get_description(self): raise NotImplementedError
    def is_available(self): return True
    def is_running(self): raise NotImplementedError
    def start(self, interval_seconds=None): raise NotImplementedError
    def stop(self): raise NotImplementedError
    def set_interval(self, seconds): raise NotImplementedError
    def get_current_interval(self): return 3600


class _AlertEngineController(SchedulerController):
    def get_name(self): return 'alert_engine'
    def get_description(self): return '告警引擎 - 检查超时未处理任务并发送微信提醒'
    def is_running(self):
        return DispatchContext.get_instance().alert_engine is not None and hasattr(DispatchContext.get_instance().alert_engine, '_thread') and DispatchContext.get_instance().alert_engine._thread is not None and DispatchContext.get_instance().alert_engine._thread.is_alive()
    def get_current_interval(self): return _ALERT_ENGINE_INTERVAL
    def start(self, interval_seconds=None):
        # [removed] global DispatchContext.get_instance().alert_engine
        if DispatchContext.get_instance().alert_engine is None or not self.is_running():
            if DispatchContext.get_instance().alert_engine is not None and not self.is_running():
                DispatchContext.get_instance().alert_engine = None
            start_background_scheduler(interval_seconds or _ALERT_ENGINE_INTERVAL)
    def stop(self):
        if DispatchContext.get_instance().alert_engine is not None:
            DispatchContext.get_instance().alert_engine.stop()
    def set_interval(self, seconds):
        # [removed] global DispatchContext.get_instance().alert_engine, _ALERT_ENGINE_INTERVAL
        _ALERT_ENGINE_INTERVAL = seconds
        if DispatchContext.get_instance().alert_engine is not None:
            DispatchContext.get_instance().alert_engine.stop()
            DispatchContext.get_instance().alert_engine = None
        start_background_scheduler(seconds)


class _CostCheckerController(SchedulerController):
    def get_name(self): return 'cost_checker'
    def get_description(self): return '成本检查 - 定期检查订单利润率并触发告警'
    def is_running(self):
        return DispatchContext.get_instance().cost_checker_thread is not None and DispatchContext.get_instance().cost_checker_thread.is_alive()
    def get_current_interval(self): return int(os.getenv('COST_CHECKER_INTERVAL', '3600'))
    def start(self, interval_seconds=None):
        cfg = _scheduler_manager._get_config('cost_checker')
        interval = interval_seconds or (cfg['interval_seconds'] if cfg else 3600)
        start_cost_checker(interval)
    def stop(self):
        # [removed] global DispatchContext.get_instance().cost_checker_running, DispatchContext.get_instance().cost_checker_gen
        DispatchContext.get_instance().cost_checker_running = False
        DispatchContext.get_instance().cost_checker_gen += 1
    def set_interval(self, seconds):
        # [removed] global DispatchContext.get_instance().cost_checker_running, DispatchContext.get_instance().cost_checker_gen
        DispatchContext.get_instance().cost_checker_running = False
        DispatchContext.get_instance().cost_checker_gen += 1
        if DispatchContext.get_instance().cost_checker_thread:
            DispatchContext.get_instance().cost_checker_thread.join(timeout=3)
        os.environ['COST_CHECKER_INTERVAL'] = str(seconds)
        start_cost_checker(seconds)


class _ReportSchedulerController(SchedulerController):
    def get_name(self): return 'report_scheduler'
    def get_description(self): return '报表调度 - 按 cron 计划自动生成报表'
    def __init__(self):
        self._mod = None
    def _get_mod(self):
        if self._mod is None:
            try:
                from services import scheduler as m
                self._mod = m
            except ImportError:
                pass
        return self._mod
    def is_available(self):
        mod = self._get_mod()
        return mod is not None and mod._scheduler_instance is not None
    def is_running(self):
        mod = self._get_mod()
        if mod is None or mod._scheduler_instance is None:
            return False
        return mod._scheduler_instance._thread is not None and mod._scheduler_instance._thread.is_alive()
    def get_current_interval(self):
        mod = self._get_mod()
        if mod and mod._scheduler_instance:
            return mod._scheduler_instance.check_interval
        return 60
    def start(self, interval_seconds=None):
        mod = self._get_mod()
        if mod and mod._scheduler_instance:
            if interval_seconds:
                mod._scheduler_instance.check_interval = interval_seconds
            mod._scheduler_instance.start()
    def stop(self):
        mod = self._get_mod()
        if mod and mod._scheduler_instance:
            mod._scheduler_instance.stop()
    def set_interval(self, seconds):
        self.stop()
        mod = self._get_mod()
        if mod and mod._scheduler_instance:
            mod._scheduler_instance.check_interval = seconds
            mod._scheduler_instance.start()


class _FaceCheckinController(SchedulerController):
    def get_name(self): return 'face_checkin'
    def get_description(self): return '人脸签到 - 定时自动导出签到数据'
    def __init__(self):
        self._mod = None
    def _get_mod(self):
        if self._mod is None:
            try:
                import face_checkin as m
                self._mod = m
            except ImportError:
                pass
        return self._mod
    def is_available(self): return self._get_mod() is not None
    def is_running(self):
        mod = self._get_mod()
        if mod is None: return False
        return mod._scheduler_thread is not None and mod._scheduler_thread.is_alive()
    def get_current_interval(self): return 60
    def start(self, interval_seconds=None):
        mod = self._get_mod()
        if mod and not self.is_running():
            mod._scheduler_stop.clear()
            t = threading.Thread(target=mod._scheduler_loop, daemon=True)
            t.start()
            mod._scheduler_thread = t
    def stop(self):
        mod = self._get_mod()
        if mod:
            mod._scheduler_stop.set()
    def set_interval(self, seconds):
        pass


class SchedulerManager:
    """统一定时任务管理器，支持 SQLite 持久化和运行时启停"""
    def __init__(self, db_path=None):
        self._controllers = {}
        self._db_path = db_path or _SCHEDULER_DB_PATH
        self._init_db()

    def register(self, controller):
        name = controller.get_name()
        self._controllers[name] = controller
        config = self._get_config(name)
        if config:
            enabled = config.get('enabled', True)
            interval = config.get('interval_seconds', controller.get_current_interval())
            if enabled:
                if not controller.is_running():
                    controller.start(interval)
            else:
                if controller.is_running():
                    controller.stop()
        else:
            if controller.is_available() and not controller.is_running():
                controller.start(controller.get_current_interval())
            self._save_config(name, True, controller.get_current_interval())

    def get_status_all(self):
        result = []
        for name, ctrl in sorted(self._controllers.items()):
            config = self._get_config(name) or {}
            result.append({
                'name': name,
                'description': ctrl.get_description(),
                'available': ctrl.is_available(),
                'running': ctrl.is_running() if ctrl.is_available() else False,
                'enabled': bool(config.get('enabled', True)) if config else True,
                'interval_seconds': config.get('interval_seconds', ctrl.get_current_interval()) if config else ctrl.get_current_interval(),
            })
        return result

    def toggle(self, name, enabled):
        ctrl = self._controllers.get(name)
        if not ctrl:
            return False, '未知定时任务'
        if not ctrl.is_available():
            return False, '该定时任务在当前运行模式下不可用'
        if enabled:
            if not ctrl.is_running():
                ctrl.start()
        else:
            if ctrl.is_running():
                ctrl.stop()
        self._save_config(name, enabled, None)
        return True, 'ok'

    def set_interval(self, name, interval):
        ctrl = self._controllers.get(name)
        if not ctrl:
            return False, '未知定时任务'
        if not ctrl.is_available():
            return False, '该定时任务在当前运行模式下不可用'
        ctrl.set_interval(interval)
        config = self._get_config(name) or {}
        self._save_config(name, config.get('enabled', True), interval)
        return True, 'ok'

    def _init_db(self):
        try:
            os.makedirs(_SCHEDULER_DB_DIR, exist_ok=True)
            conn = _sqlite3.connect(self._db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS scheduler_configs (
                name TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                interval_seconds INTEGER NOT NULL DEFAULT 3600,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f'[SchedulerManager] 初始化数据库失败: {e}')

    def _get_config(self, name):
        try:
            conn = _sqlite3.connect(self._db_path)
            row = conn.execute(
                'SELECT enabled, interval_seconds FROM scheduler_configs WHERE name = ?', (name,)
            ).fetchone()
            conn.close()
            if row:
                return {'enabled': bool(row[0]), 'interval_seconds': row[1]}
        except Exception as e:
            logger.warning(f'[SchedulerManager] 读取配置失败: {e}')
        return None

    def _save_config(self, name, enabled, interval):
        try:
            conn = _sqlite3.connect(self._db_path)
            existing = conn.execute(
                'SELECT enabled, interval_seconds FROM scheduler_configs WHERE name = ?', (name,)
            ).fetchone()
            if existing:
                en = enabled if enabled is not None else bool(existing[0])
                iv = interval if interval is not None else existing[1]
            else:
                en = enabled if enabled is not None else True
                iv = interval if interval is not None else 3600
            conn.execute(
                'INSERT INTO scheduler_configs (name, enabled, interval_seconds, updated_at) VALUES (?, ?, ?, datetime(\'now\')) '
                'ON CONFLICT(name) DO UPDATE SET enabled=excluded.enabled, interval_seconds=excluded.interval_seconds, updated_at=datetime(\'now\')',
                (name, 1 if en else 0, iv)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f'[SchedulerManager] 保存配置失败: {e}')


# ═══════════════════════════════════════════════════════════════════════════════
# Part 14: 同步接口 (行 6433~6519)
# ═══════════════════════════════════════════════════════════════════════════════

_scheduler_manager = SchedulerManager()
_ALERT_ENGINE_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', '60'))


def _check_order_cost_alerts():
    import os as _os
    low_margin_threshold = float(_os.getenv('COST_LOW_MARGIN_THRESHOLD', '10'))
    high_margin_threshold = float(_os.getenv('COST_HIGH_MARGIN_THRESHOLD', '50'))
    try:
        from services.cost_service import CostService
        from storage_layer import StorageFactory, StorageType, resolve_storage_type
        st = resolve_storage_type()
        storage = StorageFactory.get_instance(st)
        if not storage:
            storage = StorageFactory.create(st)
        service = CostService(storage)
        result = service.get_all_order_costs(status=None, page=1, page_size=200)
        items = result.get('items', [])
        for item in items:
            revenue = item.get('revenue', 0) or 0
            total_cost = item.get('total_cost', 0) or 0
            margin_rate = item.get('margin_rate', 0) or 0
            order_no = item.get('order_no', '')
            if revenue > 0 and total_cost > 0:
                if revenue < total_cost:
                    loss = total_cost - revenue
                    content = _render_template('tmpl_cost_loss_warning', {
                        '订单号': order_no,
                        '客户': _get_customer_group_for_order(order_no) or item.get('customer_name', ''),
                        '产品': item.get('product_name', ''),
                        '总成本': total_cost,
                        '收入': revenue,
                        '亏损额': loss,
                    })
                    if content:
                        _send_wechat_message(content)
                        logger.warning(f"[成本告警] 订单 {order_no} 亏损 {loss:.2f}")
                elif margin_rate < low_margin_threshold:
                    content = _render_template('tmpl_cost_low_margin', {
                        '订单号': order_no,
                        '客户': _get_customer_group_for_order(order_no) or item.get('customer_name', ''),
                        '利润率': margin_rate,
                        '利润': item.get('profit', 0),
                    })
                    if content:
                        _send_wechat_message(content)
                        logger.info(f"[成本提醒] 订单 {order_no} 低利润率 {margin_rate:.1f}%")
                elif margin_rate > high_margin_threshold:
                    content = _render_template('tmpl_cost_profitable', {
                        '订单号': order_no,
                        '客户': _get_customer_group_for_order(order_no) or item.get('customer_name', ''),
                        '产品': item.get('product_name', ''),
                        '利润率': margin_rate,
                        '利润': item.get('profit', 0),
                    })
                    if content:
                        _send_wechat_message(content)
                        logger.info(f"[成本提醒] 订单 {order_no} 高利润率 {margin_rate:.1f}%")
    except Exception as e:
        logger.error(f"[成本告警] 检查失败: {e}")


def start_cost_checker(interval_seconds: int = 3600):
    # [removed] global DispatchContext.get_instance().cost_checker_thread, DispatchContext.get_instance().cost_checker_running, DispatchContext.get_instance().cost_checker_gen
    DispatchContext.get_instance().cost_checker_running = True
    DispatchContext.get_instance().cost_checker_gen += 1
    _my_gen = DispatchContext.get_instance().cost_checker_gen
    def _run():
        logger.info(f'[DispatchCenter] CostChecker[{_my_gen}] 启动, 间隔 {interval_seconds}秒')
        while DispatchContext.get_instance().cost_checker_running and DispatchContext.get_instance().cost_checker_gen == _my_gen:
            time.sleep(interval_seconds)
            if not DispatchContext.get_instance().cost_checker_running or DispatchContext.get_instance().cost_checker_gen != _my_gen:
                break
            try:
                _check_order_cost_alerts()
            except Exception as e:
                logger.exception(f'[DispatchCenter] CostChecker 检查成本告警异常: {e}')
        logger.info(f'[DispatchCenter] CostChecker[{_my_gen}] 已停止')
    DispatchContext.get_instance().cost_checker_thread = threading.Thread(target=_run, daemon=True, name='cost-checker')
    DispatchContext.get_instance().cost_checker_thread.start()
    logger.info(f'[DispatchCenter] CostChecker[{_my_gen}] 线程已启动')


# ═══════════════════════════════════════════════════════════════════════════════
# Part 15: 质检与工单同步 (行 6520~7393)
# ═══════════════════════════════════════════════════════════════════════════════

def start_background_scheduler(interval_seconds: int = None):
    if interval_seconds is None:
        import os as _os
        interval_seconds = int(_os.getenv('SCHEDULER_INTERVAL', '60'))
        # 读取用户保存的配置覆盖默认值
        saved = _scheduler_manager._get_config('alert_engine') if hasattr(_scheduler_manager, '_get_config') else None
        if saved and saved.get('interval_seconds'):
            interval_seconds = saved['interval_seconds']

    # [removed] global DispatchContext.get_instance().alert_engine
    if DispatchContext.get_instance().alert_engine is not None and hasattr(DispatchContext.get_instance().alert_engine, '_thread') and DispatchContext.get_instance().alert_engine._thread is not None and DispatchContext.get_instance().alert_engine._thread.is_alive():
        logger.warning('[DispatchCenter] AlertEngine 已在运行')
        return DispatchContext.get_instance().alert_engine

    from container_center import DocumentStore, AlertStore, ConfigStore, AlertEngine

    doc_store = DocumentStore()
    alt_store = AlertStore()
    cfg_store = ConfigStore()

    DispatchContext.get_instance().alert_engine = AlertEngine(
        document_store=doc_store,
        alert_store=alt_store,
        config_store=cfg_store,
        send_message=_send_wechat_message,
        get_operators=_get_operators,
    )
    DispatchContext.get_instance().alert_engine.start(interval_seconds)

    # 注册到统一管理器
    _scheduler_manager.register(_AlertEngineController())
    _scheduler_manager.register(_CostCheckerController())
    _scheduler_manager.register(_ReportSchedulerController())
    _scheduler_manager.register(_FaceCheckinController())

    return DispatchContext.get_instance().alert_engine


def _extract_items(result):
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get('items', result.get('data', []))
    return []


def _get_doc_data(item):
    """从容器中心文档项中提取数据

    [v3.6.1 重构 2026-06-20] 已抽取到 dispatch_center/_sync.py
    保留此函数作为向后兼容 shim，内部调用 _sync.get_doc_data
    """
    from ._sync import get_doc_data as _impl
    return _impl(item)


@dispatch_center_bp.route('/ssot-stats', methods=['GET'])
def ssot_stats():
    """[T6 2026-06-16] SSOT 监控接口 (独立路径, 不影响业务路由)"""
    try:
        from mobile_api_ai.core.order_status_contract import (
            USE_SSOT_STATUS, get_ssot_stats,
        )
        from mobile_api_ai.core.task_classify_contract import (
            USE_SSOT_CLASSIFY, get_classify_stats,
        )
        return jsonify({
            'code': 0,
            'data': {
                'status_ssot': {
                    'enabled': USE_SSOT_STATUS,
                    'stats': get_ssot_stats(),
                },
                'classify_ssot': {
                    'enabled': USE_SSOT_CLASSIFY,
                    'stats': get_classify_stats(),
                },
                'timestamp': datetime.now().isoformat(),
            }
        })
    except Exception as e:
        logger.error(f'[SSOT] 监控接口异常: {e}')
        return jsonify({'code': -1, 'message': '系统错误，请联系管理员'}), 500


@dispatch_center_bp.route('/workorder/stats', methods=['GET'])
def workorder_stats():
    try:
        total_orders = 0
        in_progress = 0
        completed = 0
        total_tasks = 0
        completed_tasks = 0
        seen_orders = set()

        local_data = _dispatch_cache.get_data()
        for proc in local_data.get('processes', []):
            if not isinstance(proc, dict):
                continue
            order_no = proc.get('order_no', '')
            if _is_test_order(order_no):
                continue
            if order_no and order_no not in seen_orders:
                seen_orders.add(order_no)
                total_orders += 1
                status = proc.get('status', '')
                if status in ('completed', 'done'):
                    completed += 1
                elif status in ('in_progress', 'dispatched', 'acknowledged', 'confirmed', 'scheduled', 'created'):
                    in_progress += 1

        result = _get_cached_work_orders(page=1, size=2000)
        all_items = _extract_items(result)
        for item in all_items:
            if isinstance(item, dict):
                doc_data = _get_doc_data(item)
                order_no = doc_data.get('order_no', '') or doc_data.get('related_order', '')
                if _is_test_order(order_no):
                    continue
                if order_no and order_no not in seen_orders:
                    seen_orders.add(order_no)
                    total_orders += 1
                    status = item.get('status', '')
                    if status in ('completed', 'done'):
                        completed += 1
                    elif status in ('in_progress', 'dispatched', 'acknowledged'):
                        in_progress += 1
                total_tasks += 1
                if item.get('status') in ('completed', 'done'):
                    completed_tasks += 1
        return jsonify({
            'code': 0,
            'data': {
                'total_orders': total_orders,
                'in_progress': in_progress,
                'completed': completed,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
            }
        })
    except Exception as e:
        logger.error(f'workorder_stats error: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/workorder/<order_no>', methods=['GET'])
def workorder_detail(order_no):
    try:
        result = _get_cached_work_orders(page=1, size=2000)
        all_items = _extract_items(result)
        order_items = []
        for item in all_items:
            if not isinstance(item, dict):
                continue
            doc_data = _get_doc_data(item)
            # 双层匹配: 优先 item 顶层 (与 list_processes 一致), 兜底 doc_data
            item_order_no = (
                item.get('order_no', '')
                or item.get('related_order', '')
                or doc_data.get('order_no', '')
            )
            item_related = (
                item.get('related_order', '')
                or item.get('order_no', '')
                or doc_data.get('related_order', '')
                or doc_data.get('order_no', '')
            )
            if item_order_no == order_no or item_related == order_no:
                order_items.append((item, doc_data))
        if not order_items:
            # 兜底: 从 process_records 表查找(调度中心注册失败时的数据恢复)
            try:
                cc = _get_container_center()
                proc_records = cc.storage.get_all_process_records(fields='*')
                for rec in proc_records:
                    rec_wo = rec.get('order_no', '')
                    if rec_wo == order_no:
                        flow_type = rec.get('flow_type', 'production')
                        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
                        steps = []
                        for i, step in enumerate(flow_template.get('steps', [])):
                            step_status = 'completed' if i < rec.get('current_step', 0) else ('active' if i == rec.get('current_step', 0) else 'pending')
                            steps.append({
                                'name': step.get('name', ''),
                                'role': step.get('role', ''),
                                'status': step_status,
                            })
                        return jsonify({
                            'code': 0,
                            'data': {
                                'order_no': rec.get('order_no', ''),
                                'product_name': rec.get('product_name', ''),
                                'quantity': rec.get('quantity', 0),
                                'unit': rec.get('unit', '米'),
                                'status': rec.get('status', 'created'),
                                'flow_type': flow_type,
                                'current_step': rec.get('current_step', 0),
                                'process': rec,
                                'steps': steps,
                                'material_tasks': [],
                                'process_tasks': [],
                                'quality_tasks': [],
                                'repair_tasks': [],
                                'outsource_tasks': [],
                                'other_tasks': [],
                                'stats': {'total_tasks': 0, 'completed_tasks': 0},
                            }
                        })
            except Exception as fb_e:
                logger.warning(f"process_records 兜底查询失败: {fb_e}")
            return jsonify({'code': 404, 'message': f'工单 {order_no} 不存在'})

        first, first_data = order_items[0]
        process_data = _dispatch_cache.get_data().get('processes', [])
        matched_process = None
        for p in process_data:
            if isinstance(p, dict) and p.get('order_no') == order_no:
                matched_process = p
                break

        steps = []
        if matched_process and isinstance(matched_process, dict):
            for i, step in enumerate(matched_process.get('steps', [])):
                step_status = 'completed' if i < matched_process.get('current_step', 0) else ('active' if i == matched_process.get('current_step', 0) else 'pending')
                steps.append({
                    'name': step.get('name', ''),
                    'role': step.get('role', ''),
                    'status': step_status,
                })

        material_tasks = []
        process_tasks = []
        quality_tasks = []
        repair_tasks = []
        outsource_tasks = []
        flow_steps = []         # data_type 契约 v1.0 新增
        flow_production = []    # data_type 契约 v1.0 新增
        other_tasks = []

        # [2026-06-15] 按 process_code 分类的任务列表（与手机报工分类方式一致）
        production_tasks = []    # P 系列 (P01-P16)
        material_tasks_v2 = []   # M 系列 (M01-M99)
        quality_tasks_v2 = []    # Q 系列 (Q01-Q99)
        warehousing_tasks = []   # STOCK_IN
        ignored_tasks = []       # PX*/N/A/DBG
        # [T3 2026-06-16] 外协分类 (OUTSOURCE/WX/OS-)
        outsource_tasks_v2 = []  # OUTSOURCE 系列

        # data_type 契约 v1.0: 用新契约归类
        process_set = _get_process_names_set()
        flow_step_set = get_flow_step_names_set()

        # 延迟导入 process_code_classifier（避免循环依赖）
        try:
            from mobile_api_ai.core_lib.process_code_classifier import (
                is_production_code, is_material_code, is_quality_code,
                is_warehousing_code, is_outsource_code, is_ignored_code
            )
        except ImportError:
            is_production_code = is_material_code = is_quality_code = None
            is_warehousing_code = is_outsource_code = is_ignored_code = None

        for item, doc_data in order_items:
            data_type = item.get('data_type') or doc_data.get('data_type', 'other')
            # RE-007 修复: 优先取 process_name 字段(content JSON 里),而不是 title
            # 顺序: process_name > process > related_process > title
            related_process = (
                doc_data.get('process_name', '')
                or doc_data.get('process', '')
                or doc_data.get('related_process', '')
                or doc_data.get('title', '')
                or item.get('related_process', '')
                or item.get('title', '')
            )
            task_item = {
                'id': item.get('id', ''),
                'title': doc_data.get('title', item.get('title', '')),
                'related_process': related_process,
                'process_code': (item.get('process_code') or doc_data.get('process_code') or '').strip().upper(),
                'planned_qty': doc_data.get('planned_qty', doc_data.get('quantity', '')),
                'completed_qty': item.get('completed_qty', doc_data.get('completed_qty', 0)),
                'operator_name': doc_data.get('operator', doc_data.get('operator_name', '')),
                'target_operator': item.get('target_operator', ''),
                'status': item.get('status', 'pending'),
                'created_at': item.get('created_at', ''),
                'data_type': data_type,
            }
            new_type = classify_pkg(item, process_set, flow_step_set)
            if new_type == 'process_report':
                process_tasks.append(task_item)
            elif new_type == 'flow_step':
                flow_steps.append(task_item)
            elif new_type == 'flow_production':
                flow_production.append(task_item)
            elif new_type in ('material_request', 'material_pickup', 'material_buy'):
                material_tasks.append(task_item)
            elif new_type == 'quality_task':
                quality_tasks.append(task_item)
            elif new_type == 'equipment_repair':
                repair_tasks.append(task_item)
            elif new_type == 'outsource_task':
                outsource_tasks.append(task_item)
            else:
                other_tasks.append(task_item)

            # [2026-06-15] 按 process_code 二次分类（与手机报工一致）
            # [T3 2026-06-16] 加 outsource 分类
            pc = task_item.get('process_code', '') or ''
            if pc:
                try:
                    if is_ignored_code and is_ignored_code(pc):
                        ignored_tasks.append(task_item)
                    elif is_production_code and is_production_code(pc):
                        production_tasks.append(task_item)
                    elif is_material_code and is_material_code(pc):
                        material_tasks_v2.append(task_item)
                    elif is_quality_code and is_quality_code(pc):
                        quality_tasks_v2.append(task_item)
                    elif is_warehousing_code and is_warehousing_code(pc):
                        warehousing_tasks.append(task_item)
                    elif is_outsource_code and is_outsource_code(pc):
                        outsource_tasks_v2.append(task_item)  # [T3]
                    else:
                        ignored_tasks.append(task_item)
                except Exception:
                    ignored_tasks.append(task_item)

        # RE-007 修复: 工序按 process_names 字典顺序排
        try:
            from utils.data_type_contract import get_process_names_list
            process_order = {p: i for i, p in enumerate(get_process_names_list())}
            process_tasks.sort(key=lambda t: (
                process_order.get(t.get('related_process', ''), 999),
                t.get('created_at', '')
            ))
        except Exception as sort_e:
            logger.debug(f'工序排序失败,降级原序: {sort_e}')

        # [2026-06-16] 按 process_code 排序（统一排序函数，支持 P03-A1 等自定义工序）
        from mobile_api_ai.core_lib.process_code_classifier import process_code_sort_key
        try:
            production_tasks.sort(key=lambda t: process_code_sort_key(t.get('process_code', '')))
            material_tasks_v2.sort(key=lambda t: process_code_sort_key(t.get('process_code', '')))
            quality_tasks_v2.sort(key=lambda t: process_code_sort_key(t.get('process_code', '')))
        except Exception as pc_sort_e:
            logger.debug(f'process_code 排序失败,降级原序: {pc_sort_e}')

        # RE-007 修复: completed_tasks 统计(用 all_items 而非 doc_data)
        all_task_items = (process_tasks + material_tasks + quality_tasks
                          + repair_tasks + outsource_tasks + flow_steps + flow_production)
        completed_count = sum(1 for it in all_task_items
                              if it.get('status') in ('completed', 'done'))
        total_count = len(all_task_items)

        # RE-008 全字典中文化: API 返回前递归翻译 status/data_type/priority
        try:
            from utils.i18n_zh import translate_payload
            payload = {
                'order_no': order_no,
                'product_name': first_data.get('product_name', first_data.get('title', '')),
                'quantity': first_data.get('quantity', first_data.get('planned_qty', '')),
                'status': first.get('status', ''),
                'process': matched_process or {'order_no': order_no},
                'steps': steps,
                'material_tasks': material_tasks,
                'process_tasks': process_tasks,
                'quality_tasks': quality_tasks,
                'repair_tasks': repair_tasks,
                'outsource_tasks': outsource_tasks,
                'flow_steps': flow_steps,
                'flow_production': flow_production,
                'other_tasks': other_tasks,
                # [2026-06-15] 按 process_code 分类的 5 个新字段（与手机报工分类方式一致）
                # [T3 2026-06-16] 加 outsource_tasks_v2
                'production_tasks': production_tasks,      # P系列 (P01-P16)
                'material_tasks_v2': material_tasks_v2,     # M系列 (M01-M99)
                'quality_tasks_v2': quality_tasks_v2,       # Q系列 (Q01-Q99)
                'warehousing_tasks': warehousing_tasks,     # STOCK_IN
                'outsource_tasks_v2': outsource_tasks_v2,   # OUTSOURCE (T3 新增)
                'ignored_tasks': ignored_tasks,             # PX*/N/A/DBG
                'stats': {
                    'total_tasks': total_count,
                    'completed_tasks': completed_count,
                },
            }
            translate_payload(payload)
            return jsonify({'code': 0, 'data': payload})
        except Exception as i18n_e:
            logger.debug(f'中文化失败,降级英文: {i18n_e}')

        return jsonify({
            'code': 0,
            'data': {
                'order_no': order_no,
                'product_name': first_data.get('product_name', first_data.get('title', '')),
                'quantity': first_data.get('quantity', first_data.get('planned_qty', '')),
                'status': first.get('status', ''),
                'process': matched_process or {'order_no': order_no},
                'steps': steps,
                'material_tasks': material_tasks,
                'process_tasks': process_tasks,
                'quality_tasks': quality_tasks,
                'repair_tasks': repair_tasks,
                'outsource_tasks': outsource_tasks,
                'flow_steps': flow_steps,         # data_type 契约 v1.0
                'flow_production': flow_production,  # data_type 契约 v1.0
                'other_tasks': other_tasks,
                # [2026-06-15] 按 process_code 分类的 5 个新字段（与手机报工分类方式一致）
                # [T3 2026-06-16] 加 outsource_tasks_v2
                'production_tasks': production_tasks,      # P系列 (P01-P16)
                'material_tasks_v2': material_tasks_v2,     # M系列 (M01-M99)
                'quality_tasks_v2': quality_tasks_v2,       # Q系列 (Q01-Q99)
                'warehousing_tasks': warehousing_tasks,     # STOCK_IN
                'outsource_tasks_v2': outsource_tasks_v2,   # OUTSOURCE (T3 新增)
                'ignored_tasks': ignored_tasks,             # PX*/N/A/DBG
                'stats': {
                    'total_tasks': total_count,
                    'completed_tasks': completed_count,
                },
            }
        })
    except Exception as e:
        logger.error(f'workorder_detail error: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/workorder/<order_no>/refresh', methods=['POST'])
def refresh_workorder_status(order_no):
    try:
        result = _get_cached_work_orders(page=1, size=2000)
        all_items = _extract_items(result)
        matched_ids = []
        for item in all_items:
            if not isinstance(item, dict):
                continue
            doc_data = _get_doc_data(item)
            item_order_no = doc_data.get('order_no', '')
            item_related = doc_data.get('related_order', '')
            if item_order_no == order_no or item_related == order_no:
                matched_ids.append(item.get('id', ''))

        if not matched_ids:
            try:
                cc = _get_container_center()
                proc_records = cc.storage.get_all_process_records()
                for rec in proc_records:
                    rec_wo = rec.get('order_no', '')
                    if rec_wo == order_no:
                        dc_data = _dispatch_cache.get_data()
                        processes = dc_data.get('processes', [])
                        exists = any(p.get('order_no') == rec_wo or p.get('id') == rec_wo for p in processes)
                        if not exists:
                            processes.append({
                                'id': str(uuid.uuid4())[:8],
                                'order_no': rec.get('order_no', ''),
                                'product_name': rec.get('product_name', ''),
                                'quantity': rec.get('quantity', 0),
                                'status': rec.get('status', 'created'),
                                'flow_type': rec.get('flow_type', 'production'),
                                'current_step': rec.get('current_step', 0),
                                'created_at': rec.get('created_at', ''),
                                'updated_at': datetime.now().isoformat(),
                            })
                            dc_data['processes'] = processes
                            _dispatch_cache.set_data(dc_data)
                            _dispatch_cache.persist()
                        return jsonify({'code': 0, 'message': '工单状态已刷新'})
            except Exception as fb_e:
                logger.warning(f"process_records 兜底恢复失败: {fb_e}")
            return jsonify({'code': 404, 'message': f'工单 {order_no} 不存在'})

        dc_data = _dispatch_cache.get_data()
        processes = dc_data.get('processes', [])
        matched_process = next((p for p in processes if p.get('order_no') == order_no), None)
        if not matched_process:
            processes.append({
                'id': str(uuid.uuid4())[:8],
                'order_no': order_no,
                'product_name': '',
                'quantity': 0,
                'status': 'in_progress',
                'flow_type': 'production',
                'current_step': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            })
            dc_data['processes'] = processes
            _dispatch_cache.set_data(dc_data)
            _dispatch_cache.persist()

        return jsonify({'code': 0, 'message': '工单状态已刷新'})
    except Exception as e:
        logger.error(f'refresh_workorder_status error: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/workorder/<order_no>', methods=['DELETE'])
def delete_workorder(order_no):
    try:
        result = _get_cached_work_orders(page=1, size=2000)
        all_items = _extract_items(result)
        matched_ids = []
        for item in all_items:
            if not isinstance(item, dict):
                continue
            doc_data = _get_doc_data(item)
            item_order_no = doc_data.get('order_no', '')
            item_related = doc_data.get('related_order', '')
            if item_order_no == order_no or item_related == order_no:
                matched_ids.append(item.get('id', ''))
        if not matched_ids:
            return jsonify({'code': 404, 'message': f'工单 {order_no} 下无子项可删除'})
        deleted_count = 0
        for doc_id in matched_ids:
            try:
                if _get_client().delete_document('work_order', doc_id):
                    deleted_count += 1
            except Exception as e:
                logger.warning(f'删除工单子项 {doc_id} 失败: {e}')
        dc_data = _dispatch_cache.get_data()
        processes = dc_data.get('processes', [])
        before = len(processes)
        processes = [p for p in processes if p.get('order_no') != order_no]
        if len(processes) < before:
            dc_data['processes'] = processes
            _dispatch_cache.set_data(dc_data)
            _dispatch_cache.persist()
            logger.info(f'同步清理 dispatch_cache 流程: 移除 {before - len(processes)} 条')
        logger.info(f'删除工单 {order_no} 子项: 共 {len(matched_ids)} 项, 成功 {deleted_count} 项')
        return jsonify({'code': 0, 'message': f'已删除 {deleted_count}/{len(matched_ids)} 个子项', 'data': {'deleted': deleted_count, 'total': len(matched_ids)}})
    except Exception as e:
        logger.error(f'delete_workorder error: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/workorder/change-delivery-date', methods=['POST'])
def change_delivery_date():
    """
    主软件通知交货日期变更

    请求体:
    {
        "order_no": "WO001",
        "old_delivery_date": "2026-05-20",
        "new_delivery_date": "2026-06-10",
        "change_reason": "客户要求延期",
        "operator": "张三"
    }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = data.get('order_no', '')
        old_delivery = data.get('old_delivery_date', '')
        new_delivery = data.get('new_delivery_date', '')
        reason = data.get('change_reason', '')
        operator = data.get('operator', '')

        if not order_no or not new_delivery:
            return jsonify({'code': 400, 'message': 'order_no 和 new_delivery_date 必填'}), 400

        dc_data = _dispatch_cache.get_data()
        processes = dc_data.get('processes', [])

        process = next((p for p in processes if p.get('order_no') == order_no), None)
        if not process:
            return jsonify({'code': 404, 'message': f'工单 {order_no} 流程不存在'}), 404

        old_value = old_delivery or process.get('delivery_date', '')
        now = datetime.now().isoformat()
        process['delivery_date'] = new_delivery
        process['old_delivery_date'] = old_value
        process['change_reason'] = reason
        process['changed_by'] = operator
        process['changed_at'] = now
        process['updated_at'] = now

        _dispatch_cache.set_data(dc_data)
        _dispatch_cache.persist()

        change_log = {
            'order_no': order_no,
            'old_delivery_date': old_value,
            'new_delivery_date': new_delivery,
            'change_reason': reason,
            'operator': operator,
            'changed_at': now
        }
        logger.info(f"[交期变更] {order_no}: {old_value} → {new_delivery}, 原因: {reason}, 操作人: {operator}")

        rendered = _render_template('tmpl_schedule_change', {
            '订单号': order_no,
            '原排产计划': old_value,
            '新排产计划': new_delivery,
            '变更原因': reason or '未填写',
        })
        if rendered:
            _send_wechat_message(rendered)

        return jsonify({'code': 0, 'message': '交期变更已通知', 'data': change_log})

    except Exception as e:
        logger.error(f"change_delivery_date error: {e}")
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/workorder/register', methods=['POST'])
def register_workorder():
    """注册工单并自动创建流程编排
    读取 POST JSON 中的 order_no/product_name/quantity/flow_type，
    匹配 PROCESS_FLOW_TEMPLATES 生成流程步骤，写入 dispatch_cache。
    返回: flask.Response (JSON) {"code": 0, "process_id": "..."}
    异常: 任何错误返回 500
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        order_no = data.get('order_no', '').strip()
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no 必填'}), 400

        # 防重复：检查订单是否真实存在（避免已删除订单被重复发布）
        # [P0-1 修复 2026-06-13] 改读本地表 orders_local
        try:
            import pymysql
            from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
            conn = _get_mysql_connection()  # [T4 2026-06-14] 走连接池
            try:
                c = conn.cursor()
                c.execute("SELECT 1 FROM orders_local WHERE order_no=%s LIMIT 1", (order_no,))
                if not c.fetchone():
                    return jsonify({'code': 404, 'message': f'订单 {order_no} 不存在，请先在桌面端创建'}), 404
            finally:
                conn.close()
        except Exception:
            pass  # 本地表不可达时不阻塞，走后续流程

        customer_group = _get_customer_group_for_order(order_no)

        doc_data = {
            'order_no': data.get('order_no', order_no),
            'flow_type': data.get('flow_type', 'production'),
            'customer_name': customer_group or data.get('customer_name', ''),
            # [F6 P9 2026-06-10] 同步补写 customer_group 字段, 修复手机端 customerGroup 显示空 bug
            'customer_group': customer_group or data.get('customer_group', ''),
            'product_name': data.get('product_name', ''),
            'quantity': data.get('quantity', 1),
            'unit': data.get('unit', '米'),
            'delivery_date': data.get('delivery_date', ''),
            'priority': data.get('priority', 'normal'),
            'status': 'created',
        }

        _get_client().create_document('work_order', doc_data)

        DispatchContext.get_instance().work_order_cache['time'] = 0

        # 自动创建流程编排
        flow_type = data.get('flow_type', 'production')
        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
        product_name = data.get('product_name', '').strip()
        quantity = int(data.get('quantity', 1))

        process_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        def _register_wo_updater(d):
            processes = d.get('processes', [])
            existing = next((p for p in processes if p.get('order_no') == order_no or p.get('order_no') == (data.get('order_no', order_no))), None)
            if existing:
                # 现状 (T3 审计后): 行为已正确, 'or' 写法对 falsy 值 (空字符串/0) 自动回退到 existing
                # 与 L5566-5569 风格一致, 无需修改
                # 前测: mobile_api_ai/dispatch_center/__pre_tests__/test_register_workorder_product_name.py
                #       9 用例验证空 product_name / 0 quantity 都不覆盖
                existing['product_name'] = product_name or existing.get('product_name', '')
                existing['quantity'] = quantity or existing.get('quantity', 0)
                existing['customer_name'] = customer_group or data.get('customer_name', '') or existing.get('customer_name', '')
                existing['delivery_date'] = data.get('delivery_date', '') or existing.get('delivery_date', '')
                existing['unit'] = data.get('unit', '米') or existing.get('unit', '米')
                existing['priority'] = data.get('priority', 'normal') or existing.get('priority', 'normal')
                existing['updated_at'] = now
                return
            processes.append({
                'id': process_id,
                'order_no': data.get('order_no', order_no),
                'product_name': product_name,
                'quantity': quantity,
                'customer_name': customer_group or data.get('customer_name', ''),
                'delivery_date': data.get('delivery_date', ''),
                'unit': data.get('unit', '米'),
                'priority': data.get('priority', 'normal'),
                'status': 'created',
                'flow_type': flow_type,
                'current_step': 0,
                'steps': flow_template['steps'],
                'created_at': now,
                'updated_at': now,
            })

        _dispatch_cache.update_data(_register_wo_updater)

        # 全员/按部门自动派工
        try:
            data_cache = _dispatch_cache.get_data()
            dispatch_mode = data_cache.get('dispatch_mode', 'all')
            dispatch_dept = str(data_cache.get('dispatch_dept', ''))
            process_departments = data_cache.get('process_departments', {})
            operators = _get_operators()
            dispatched = 0
            cc_base = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')

            def _dispatch(targets, process_name, process_code='', is_public=True, is_broadcast=False):
                """派发任务到容器中心。

                Args:
                    targets: 操作员列表（保留参数，兼容历史）
                    process_name: 工序名
                    process_code: 工序编码
                    is_public: True=公共任务（全员可见，领取制）
                    is_broadcast: True=M2 全员广播（工序配置触发的群里通知）

                Returns:
                    bool: 是否成功
                """
                # [Bug 1 Fix 2026-06-19] 必须传 X-API-Key header，否则容器中心 1003 拒绝
                # 优先级：CONTAINER_CENTER_API_KEY > API_KEY > WECHAT_CLOUD_API_KEY
                # 实测 2026-06-19 18:25：5002 用 .env 里的 WECHAT_CLOUD_API_KEY 作主 key
                cc_api_key = (
                    os.environ.get('CONTAINER_CENTER_API_KEY')
                    or os.environ.get('API_KEY')
                    or os.environ.get('WECHAT_CLOUD_API_KEY')
                    or ''
                )
                dispatch_headers = {'X-API-Key': cc_api_key} if cc_api_key else {}
                operator_id = '' if is_public else (targets[0] if targets else '')
                try:
                    resp = requests.post(f'{cc_base}/api/wechat/dispatch', json={
                        'order_no': order_no, 'process_name': process_name,
                        'operator_id': operator_id, 'quantity': quantity,
                        'source': 'dispatch_center', 'priority': data.get('priority', 'high'),
                        'process_code': process_code,
                        'is_public': is_public, 'is_broadcast': is_broadcast,
                        'flow_type': flow_type,
                    }, headers=dispatch_headers, timeout=5)
                    if resp.ok and resp.json().get('code') == 0:
                        return True
                    return False
                except Exception as e:
                    logger.warning(f'[派工] {process_name}({operator_id or "全员"})失败: {e}')
                    return False

            def _dispatch_to_member(member, process_name, process_code=''):
                """M2 派工（保留，暂未使用）：给指定操作员发一条 is_public=False 的任务。"""
                nonlocal dispatched
                if _dispatch([member], process_name, process_code=process_code, is_public=False, is_broadcast=False):
                    dispatched += 1

            # 从容器中心获取工序编码映射+部门绑定
            # 优先级：本地 dispatch_cache > 5002 /api/process_departments
            code_map = {}
            process_departments = {}

            # [Bug 3 Fix 2026-06-19] 优先从本地 dispatch_cache 拿 process_departments（避免循环调用）
            try:
                _cache_data = _dispatch_cache.get_data()
                if _cache_data and isinstance(_cache_data, dict):
                    process_departments = _cache_data.get('process_departments', {}) or {}
            except Exception: pass

            # [Bug 3 Fix 2026-06-19] 调 5002 /api/process_names 加 X-API-Key header
            cc_api_key_inner = (
                os.environ.get('CONTAINER_CENTER_API_KEY')
                or os.environ.get('API_KEY')
                or os.environ.get('WECHAT_CLOUD_API_KEY')
                or ''
            )
            _cc_inner_headers = {'X-API-Key': cc_api_key_inner} if cc_api_key_inner else {}
            try:
                resp = requests.get(f'{cc_base}/api/process_names?include_dept=1', headers=_cc_inner_headers, timeout=3)
                if resp.ok:
                    resp_json = resp.json()
                    full = resp_json.get('data', []) if resp_json.get('data') is not None else {}
                    if isinstance(full, list):
                        for r in full:
                            if r.get('process_code'):
                                code_map[r['process_code']] = r['process_name']
                            # 仅在 dispatch_cache 没有时用 5002 返回的 department
                            if r.get('department') and not process_departments:
                                process_departments[r['process_code']] = r['department']
                    else:
                        code_map = full
                # 兼容：再从 process_departments API 读取（5002 端可能从 dispatch_cache 拉）
                if not process_departments:
                    resp2 = requests.get(f'{cc_base}/api/process_departments', headers=_cc_inner_headers, timeout=3)
                    if resp2.ok:
                        process_departments = resp2.json().get('data', {}) or {}
            except Exception: pass

            # [Bug 1 Fix 2026-06-19 + M2 Fix 2026-06-19] 三元派工架构
            # M1: dispatch_mode='all' → 全员派工（创建公共任务，不指定操作员）
            # M2: dispatch_mode='specific' + process_departments 命中 → 按工序配置派工（部门全员）
            # M3: dispatch_mode='specific' + 无配置 → 手动派工（跳过自动派工）
            if dispatch_mode == 'all':
                # M1 全员派工：为流程每个步骤创建公共任务
                # 使用 code_map 转换 process_code 为 process_name
                for step in flow_template['steps']:
                    step_name = step.get('name', '')
                    step_code = step.get('process_code', '')
                    # 优先用 code_map 转换（更准确）
                    if step_code and step_code in code_map:
                        step_name = code_map[step_code]
                    if step_name:
                        _dispatch([], step_name, process_code=step_code, is_public=True)
                logger.info(f'[工单注册] M1 全员派工完成: {dispatched}个任务 (mode=all)')
            elif dispatch_mode == 'specific' and process_departments:
                # M2 按工序配置派工：每个工序按 process_departments 找到部门 → 部门全员
                m2_dispatched_processes = 0
                m2_skipped_processes = []
                for step in flow_template['steps']:
                    step_name = step.get('name', '')
                    step_code = step.get('process_code', '')
                    if step_code and step_code in code_map:
                        step_name = code_map[step_code]
                    if not step_name:
                        continue
                    # 查工序的部门（按 process_code 或 process_name 查）
                    dept_name = process_departments.get(step_code) or process_departments.get(step_name)
                    if not dept_name:
                        m2_skipped_processes.append(step_name)
                        logger.info(f'[工单注册] 工序{step_name}无部门配置，跳过自动派工（M3 手动派工）')
                        continue
                    members = _get_department_members(dept_name)
                    if not members:
                        # 部门无成员 → 回退为全员公共任务
                        logger.warning(f'[工单注册] 部门{dept_name}无成员，回退为全员广播: {step_name}')
                        if _dispatch([], step_name, process_code=step_code, is_public=True, is_broadcast=True):
                            dispatched += 1
                            m2_dispatched_processes += 1
                    else:
                        # [M2 广播改造 2026-06-19] 部门有成员 → 也只发 1 条广播任务 (is_broadcast=1)
                        # 群里发 1 遍通知，前端/后端见到 is_broadcast 标记放行（部门全员可见，按需领取）
                        if _dispatch([], step_name, process_code=step_code, is_public=True, is_broadcast=True):
                            dispatched += 1
                            m2_dispatched_processes += 1
                            logger.info(f'[工单注册] M2 工序{step_name} → 部门{dept_name} → 广播派工 (部门{len(members)}人可见)')
                logger.info(f'[工单注册] M2 工序配置派工完成: {dispatched}个任务, {m2_dispatched_processes}工序派工, {len(m2_skipped_processes)}工序待手动派工')
            else:
                # M3 手动派工模式，跳过自动派工
                logger.info(f'[工单注册] M3 手动派工模式，跳过自动派工 (mode={dispatch_mode}, process_departments={len(process_departments)}条)')
        except Exception as e:
            logger.warning(f'[工单注册] 全员派工失败(非致命): {e}')

        logger.info(f"工单注册成功(含流程): {order_no}, process_id={process_id}")

        # [修改 2026-06-13] "新工单流程已创建"消息移至 _on_distribute，
        # 由派工时发给个人工人，register_workorder 不再发群消息

        # 同步主软件订单状态为 已发布
        try:
            _sync_to_mysql(order_no, 'published', data.get('order_no', order_no))
        except Exception as sync_e:
            logger.warning(f"[工单注册] MySQL状态同步异常: {sync_e}")

        return jsonify({'code': 0, 'message': '工单注册成功', 'data': {'order_no': order_no, 'process_id': process_id}})

    except Exception as e:
        logger.error(f"register_workorder error: {e}")
        return jsonify({'code': 500, 'message': '工单注册失败失败，请稍后重试'})


# ═══════════════════════════════════════════════════════════════════════════════
# Part 19: 统一任务查询接口 (v3.6.1 新增)
# ═══════════════════════════════════════════════════════════════════════════════

def _check_jwt_auth():
    """JWT Bearer Token 认证检查，返回 (is_ok, error_response)"""
    from flask import request
    from core.config import JWT_SECRET_KEY
    try:
        import jwt
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return False, (jsonify({'code': 401, 'message': '缺少认证令牌'}), 401)
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            request.user_role = payload.get('role', 'user')
        except jwt.ExpiredSignatureError:
            return False, (jsonify({'code': 401, 'message': '令牌已过期'}), 401)
        except jwt.InvalidTokenError:
            return False, (jsonify({'code': 401, 'message': '无效的令牌'}), 401)
    except ImportError:
        return False, (jsonify({'code': 500, 'message': 'JWT模块未安装'}), 500)
    return True, None


def _check_rate_limit(ip: str, key: str = 'unified_tasks', max_req: int = 60, window: int = 60):
    """Redis 滑动窗口限流，超限返回 (is_ok, error_response)。"""
    try:
        from cache import redis_client
        if redis_client is None:
            return True, None
        import time
        now = int(time.time() * 1000)
        window_start = now - window * 1000
        redis_key = f'ratelimit:dispatch:{key}:{ip}'
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, window)
        counts = pipe.execute()
        if counts[1] >= max_req:
            logger.warning('[DispatchCenter] 限流: ip=%s key=%s count=%d', ip, key, counts[1])
            return False, (jsonify({'code': 429, 'message': f'请求过于频繁，请{window}秒后重试'}), 429)
        return True, None
    except Exception:
        return True, None


@dispatch_center_bp.route('/unified-tasks', methods=['GET'])
def list_unified_tasks():
    """统一任务查询 - 整合所有任务表的数据

    任务类型与存储表对应关系：
    - process:  process_sub_steps (生产工序)
    - quality:  quality_records (质检记录)
    - repair:   repair_records (维修记录)
    - outsource: outsource_records (外协记录)
    - material: material_records (物料记录)

    Query参数:
    - type: 任务类型 (process/quality/repair/outsource/material/all)
    - status: 状态筛选
    - operator: 操作员筛选
    - page/page_size: 分页
    """
    ok, err = _check_jwt_auth()
    if not ok:
        return err

    ip = request.remote_addr or '127.0.0.1'
    ok, err = _check_rate_limit(ip)
    if not ok:
        return err

    task_type = request.args.get('type', 'all')
    status_filter = request.args.get('status', '')
    operator_filter = request.args.get('operator', '')
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        if page < 1 or page_size < 1 or page_size > 100:
            return jsonify({'code': 400, 'message': '分页参数超出范围'}), 200
        offset = (page - 1) * page_size
        if offset < 0:
            return jsonify({'code': 400, 'message': 'offset 不能为负数'}), 200
    except ValueError:
        return jsonify({'code': 400, 'message': '分页参数必须是整数'}), 200

    all_tasks = []
    total = 0

    conn = _get_mysql_connection()
    try:
        cur = conn.cursor()

        if task_type in ('all', 'process'):
            _params = []
            _where = ""
            if status_filter:
                _where += " AND status=%s"
                _params.append(status_filter)
            if operator_filter:
                _where += " AND operator=%s"
                _params.append(operator_filter)
            cur.execute(f"""
                SELECT 'process' as type, id, order_no, step_name as title, operator,
                       status, quantity, completed_qty, batch_no, created_at, updated_at
                FROM process_sub_steps
                WHERE 1=1{_where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, _params + [page_size, offset])
            for row in cur.fetchall():
                all_tasks.append({
                    'type': 'process',
                    'id': row[1], 'order_no': row[2], 'title': row[3],
                    'operator': row[4], 'status': row[5],
                    'quantity': float(row[6] or 0), 'completed_qty': float(row[7] or 0),
                    'batch_no': row[8], 'created_at': str(row[9])[:19] if row[9] else '',
                    'updated_at': str(row[10])[:19] if row[10] else ''
                })

        if task_type in ('all', 'quality'):
            _params = []
            _where = ""
            if status_filter:
                _where += " AND status=%s"
                _params.append(status_filter)
            if operator_filter:
                _where += " AND inspector=%s"
                _params.append(operator_filter)
            cur.execute(f"""
                SELECT 'quality' as type, id, order_no, process_name as title, inspector as operator,
                       status, quantity, completed_qty, batch_no, created_at, updated_at
                FROM quality_records
                WHERE 1=1{_where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, _params + [page_size, offset])
            for row in cur.fetchall():
                all_tasks.append({
                    'type': 'quality',
                    'id': row[1], 'order_no': row[2], 'title': row[3],
                    'operator': row[4], 'status': row[5],
                    'quantity': float(row[6] or 0), 'completed_qty': float(row[7] or 0),
                    'batch_no': row[8], 'created_at': str(row[9])[:19] if row[9] else '',
                    'updated_at': str(row[10])[:19] if row[10] else ''
                })

        if task_type in ('all', 'repair'):
            _params = []
            _where = ""
            if status_filter:
                _where += " AND status=%s"
                _params.append(status_filter)
            if operator_filter:
                _where += " AND assigned_to=%s"
                _params.append(operator_filter)
            cur.execute(f"""
                SELECT 'repair' as type, id, order_no, product_name as title, assigned_to as operator,
                       status, quantity, completed_qty, batch_no, created_at, updated_at
                FROM repair_records
                WHERE 1=1{_where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, _params + [page_size, offset])
            for row in cur.fetchall():
                all_tasks.append({
                    'type': 'repair',
                    'id': row[1], 'order_no': row[2], 'title': row[3],
                    'operator': row[4], 'status': row[5],
                    'quantity': float(row[6] or 0), 'completed_qty': float(row[7] or 0),
                    'batch_no': row[8], 'created_at': str(row[9])[:19] if row[9] else '',
                    'updated_at': str(row[10])[:19] if row[10] else ''
                })

        if task_type in ('all', 'outsource'):
            _params = []
            _where = ""
            if status_filter:
                _where += " AND status=%s"
                _params.append(status_filter)
            if operator_filter:
                _where += " AND supplier=%s"
                _params.append(operator_filter)
            cur.execute(f"""
                SELECT 'outsource' as type, id, order_no, product_name as title, supplier as operator,
                       status, quantity, completed_qty, batch_no, created_at, updated_at
                FROM outsource_records
                WHERE 1=1{_where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, _params + [page_size, offset])
            for row in cur.fetchall():
                all_tasks.append({
                    'type': 'outsource',
                    'id': row[1], 'order_no': row[2], 'title': row[3],
                    'operator': row[4], 'status': row[5],
                    'quantity': float(row[6] or 0), 'completed_qty': float(row[7] or 0),
                    'batch_no': row[8], 'created_at': str(row[9])[:19] if row[9] else '',
                    'updated_at': str(row[10])[:19] if row[10] else ''
                })

        if task_type in ('all', 'material'):
            _params = []
            _where = ""
            if status_filter:
                _where += " AND status=%s"
                _params.append(status_filter)
            if operator_filter:
                _where += " AND purchaser=%s"
                _params.append(operator_filter)
            cur.execute(f"""
                SELECT 'material' as type, id, order_no, material_name as title, purchaser as operator,
                       status, quantity, completed_qty, batch_no, created_at, updated_at
                FROM material_records
                WHERE 1=1{_where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, _params + [page_size, offset])
            for row in cur.fetchall():
                all_tasks.append({
                    'type': 'material',
                    'id': row[1], 'order_no': row[2], 'title': row[3],
                    'operator': row[4], 'status': row[5],
                    'quantity': float(row[6] or 0), 'completed_qty': float(row[7] or 0),
                    'batch_no': row[8], 'created_at': str(row[9])[:19] if row[9] else '',
                    'updated_at': str(row[10])[:19] if row[10] else ''
                })

        _count_params = []
        _sub_queries = []
        if task_type in ('all', 'process'):
            _q = "SELECT id FROM process_sub_steps WHERE 1=1"
            if status_filter:
                _q += " AND status=%s"
                _count_params.append(status_filter)
            if operator_filter:
                _q += " AND operator=%s"
                _count_params.append(operator_filter)
            _sub_queries.append(_q)
        if task_type in ('all', 'quality'):
            _q = "SELECT id FROM quality_records WHERE 1=1"
            if status_filter:
                _q += " AND status=%s"
                _count_params.append(status_filter)
            if operator_filter:
                _q += " AND inspector=%s"
                _count_params.append(operator_filter)
            _sub_queries.append(_q)
        if task_type in ('all', 'repair'):
            _q = "SELECT id FROM repair_records WHERE 1=1"
            if status_filter:
                _q += " AND status=%s"
                _count_params.append(status_filter)
            if operator_filter:
                _q += " AND assigned_to=%s"
                _count_params.append(operator_filter)
            _sub_queries.append(_q)
        if task_type in ('all', 'outsource'):
            _q = "SELECT id FROM outsource_records WHERE 1=1"
            if status_filter:
                _q += " AND status=%s"
                _count_params.append(status_filter)
            if operator_filter:
                _q += " AND supplier=%s"
                _count_params.append(operator_filter)
            _sub_queries.append(_q)
        if task_type in ('all', 'material'):
            _q = "SELECT id FROM material_records WHERE 1=1"
            if status_filter:
                _q += " AND status=%s"
                _count_params.append(status_filter)
            if operator_filter:
                _q += " AND purchaser=%s"
                _count_params.append(operator_filter)
            _sub_queries.append(_q)
        _union = " UNION ALL ".join(_sub_queries)
        if not _union:
            total = 0
        else:
            cur.execute(f"SELECT COUNT(*) FROM ({_union}) as combined", _count_params)
            total = cur.fetchone()[0]

    except Exception as e:
        logger.error(f'统一任务查询失败: {e}')
        return jsonify({'code': 500, 'message': '查询失败，请稍后重试'}), 500
    finally:
        conn.close()

    return jsonify({
        'code': 0,
        'data': {
            'tasks': all_tasks,
            'total': total,
            'page': page,
            'page_size': page_size,
            'types': {
                'process': '生产工序',
                'quality': '质检记录',
                'repair': '维修记录',
                'outsource': '外协记录',
                'material': '物料记录'
            }
        }
    })


@dispatch_center_bp.route('/unified-tasks/stats', methods=['GET'])
def unified_tasks_stats():
    """统一任务统计 - 各类型任务数量"""
    stats = {}
    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()

        tables = [
            ('process', 'process_sub_steps', 'operator'),
            ('quality', 'quality_records', 'inspector'),
            ('repair', 'repair_records', 'assigned_to'),
            ('outsource', 'outsource_records', 'supplier'),
            ('material', 'material_records', 'purchaser'),
        ]

        for type_name, table, operator_field in tables:
            cur.execute(f"SELECT status, COUNT(*) FROM {table} GROUP BY status")
            status_counts = {row[0]: row[1] for row in cur.fetchall()}
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            total = cur.fetchone()[0]
            stats[type_name] = {
                'total': total,
                'status': status_counts
            }

        conn.close()
    except Exception as e:
        logger.error(f'统一任务统计失败: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500

    return jsonify({'code': 0, 'data': stats})


@dispatch_center_bp.route('/process_sub_steps/<order_no>', methods=['GET'])
def list_process_sub_steps(order_no):
    try:
        cc = _get_container_center()
        steps = cc.get_sub_steps(order_no)
        return jsonify({'code': 0, 'data': steps})
    except Exception as e:
        logger.error(f"list_process_sub_steps error: {e}")
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


@dispatch_center_bp.route('/process_sub_step_summary/<order_no>', methods=['GET'])
def get_process_sub_step_summary(order_no):
    try:
        cc = _get_container_center()
        summary = cc.get_sub_step_summary(order_no)
        return jsonify({'code': 0, 'data': summary})
    except Exception as e:
        logger.error(f"get_process_sub_step_summary error: {e}")
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})


# ====== 云端/公网IP配置接口 ======

@dispatch_center_bp.route('/cloud/config', methods=['GET', 'POST'])
def cloud_config():
    config_file = DB_PATHS['cloud_config']

    def load_config():
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'cloud_host': '', 'api_key': '', 'enabled': False,
                'enable_group_notification': True, 'enable_notification': True,
                'enable_distribution': True, 'notification_template': ''}

    def save_config(cfg):
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f'保存云端配置失败: {e}')
            return False

    if request.method == 'GET':
        cfg = load_config()
        return jsonify({'code': 0, 'data': cfg})

    data = request.get_json() or {}
    cfg = load_config()

    if 'cloud_host' in data:
        raw = data['cloud_host'].strip().rstrip('/')
        from urllib.parse import urlparse
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            clean_netloc = parsed.netloc.encode('ascii', 'ignore').decode('ascii')
            clean_path = parsed.path if parsed.path else ''
            cfg['cloud_host'] = f"{parsed.scheme}://{clean_netloc}{clean_path}"
        else:
            cfg['cloud_host'] = raw
    if 'api_key' in data:
        raw_key = data['api_key'].strip()
        cfg['api_key'] = raw_key.encode('ascii', 'ignore').decode('ascii').strip()
    if 'enabled' in data:
        cfg['enabled'] = bool(data['enabled'])
    if 'enable_group_notification' in data:
        cfg['enable_group_notification'] = bool(data['enable_group_notification'])
    if 'enable_notification' in data:
        cfg['enable_notification'] = bool(data['enable_notification'])
    if 'enable_distribution' in data:
        cfg['enable_distribution'] = bool(data['enable_distribution'])
    if 'notification_template' in data:
        cfg['notification_template'] = data['notification_template']

    if save_config(cfg):
        logger.info(f'[云端配置] 已更新: host={cfg["cloud_host"]}, enabled={cfg["enabled"]}')
        try:
            cc = _get_container_center()
            cc.enable_notification(cfg.get('enable_notification', True))
            cc.enable_group_notification(cfg.get('enable_group_notification', True))
            cc.enable_distribution(cfg.get('enable_distribution', True))
            tmpl = cfg.get('notification_template', '')
            if tmpl:
                cc.set_notification_template(tmpl)
        except Exception as sync_e:
            logger.warning(f'[云端配置] 同步配置到容器中心失败: {sync_e}')
        return jsonify({'code': 0, 'message': '配置已保存'})
    else:
        return jsonify({'code': 500, 'message': '保存失败'}), 500


@dispatch_center_bp.route('/cloud/status')
def cloud_status():
    try:
        config_file = DB_PATHS['cloud_config']
        cloud_host = ''
        cloud_enabled = False

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    cloud_host = cfg.get('cloud_host', '')
                    cloud_enabled = cfg.get('enabled', False)
            except Exception as e:
                logger.warning(f"加载云端配置文件失败: {e}")

        status = {
            'cloud_enabled': False,
            'cloud_configured': bool(cloud_host),
            'cloud_host': cloud_host,
            'cloud_active': cloud_enabled,
            'poller_status': None,
            'analysis': get_local_poll_analysis()
        }

        try:
            from cloud_poller import get_cloud_poller, CLOUD_POLLER_AVAILABLE
            if CLOUD_POLLER_AVAILABLE:
                status['cloud_enabled'] = True
                poller = get_cloud_poller()
                if poller:
                    status['poller_status'] = poller.get_status()
                else:
                    status['poller_status'] = {'running': False, 'error': '轮询器未初始化'}
        except ImportError:
            pass

        return jsonify({'code': 0, 'data': status})
    except Exception as e:
        logger.error(f'[云端] 获取状态异常: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


def get_local_poll_analysis():
    analysis = {
        'data_flow_events': [],
        'dispatch_commands': [],
        'data_collection': [],
        'sync_operations': [],
        'summary': {}
    }

    try:
        import pymysql
        from pymysql.cursors import DictCursor
        from storage.mysql_storage import MySQLStorage
        conn = MySQLStorage.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT event_type, COUNT(*) as count FROM data_flow_logs GROUP BY event_type ORDER BY count DESC")
            analysis['data_flow_events'] = [{'event_type': r['event_type'], 'count': r['count']} for r in cursor.fetchall()]

            analysis['dispatch_commands'] = []  # 表已删除

            cursor.execute("SELECT data_type, COUNT(*) as count FROM data_collection_records GROUP BY data_type")
            analysis['data_collection'] = [{'data_type': r['data_type'], 'count': r['count']} for r in cursor.fetchall()]

            cursor.execute("SELECT action, COUNT(*) as count FROM sync_logs GROUP BY action")
            analysis['sync_operations'] = [{'action': r['action'], 'count': r['count']} for r in cursor.fetchall()]

            total_events = sum(item['count'] for item in analysis['data_flow_events'])
            total_commands = sum(item['count'] for item in analysis['dispatch_commands'])
            total_collections = sum(item['count'] for item in analysis['data_collection'])
            total_sync = sum(item['count'] for item in analysis['sync_operations'])

            analysis['summary'] = {
                'total_events': total_events,
                'total_commands': total_commands,
                'total_collections': total_collections,
                'total_sync_operations': total_sync,
                'health_score': calculate_health_score(total_events, analysis['dispatch_commands'])
            }
        finally:
            conn.close()

    except Exception as e:
        logger.error(f'[轮询分析] 数据分析异常: {e}')

    return analysis


def calculate_health_score(total_events, dispatch_commands):
    score = 100
    for cmd in dispatch_commands:
        if cmd['status'] == 'failed':
            score -= cmd['count'] * 10
    for cmd in dispatch_commands:
        if cmd['status'] == 'pending':
            score -= min(cmd['count'] * 5, 20)
    if total_events == 0:
        score -= 30
    return max(0, score)


@dispatch_center_bp.route('/cloud/poll-data')
def cloud_poll_data():
    config_file = DB_PATHS['cloud_config']

    try:
        import requests

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    cloud_host = cfg.get('cloud_host', '')
                    api_key = cfg.get('api_key', '')
            except Exception:
                cloud_host = ''
                api_key = ''
        else:
            cloud_host = ''
            api_key = ''

        if not cloud_host:
            return jsonify({'code': 400, 'message': '云端地址未配置'}), 400

        headers = {'X-API-Key': api_key} if api_key else {}

        if '/api/queue/poll' in cloud_host:
            poll_url = cloud_host
        else:
            poll_url = f'{cloud_host}/api/queue/poll'

        response = requests.get(poll_url, headers=headers, timeout=10)
        data = response.json()

        poll_result = {
            'code': data.get('code', -1),
            'count': data.get('count', 0),
            'source': data.get('source', 'cloud'),
            'messages': [],
            'last_poll_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if data.get('code') == 0 and data.get('count', 0) > 0:
            messages = data.get('messages', [])
            for msg in messages[:10]:
                msg_data = msg.get('data', msg)
                poll_result['messages'].append({
                    'id': msg.get('id', 0),
                    'user_id': msg_data.get('user_id', ''),
                    'content': msg_data.get('content', '')[:100],
                    'type': msg_data.get('type', ''),
                    'event': msg_data.get('event', ''),
                    'command_type': msg_data.get('command_type', ''),
                    'timestamp': msg_data.get('timestamp', '')
                })

        return jsonify({'code': 0, 'data': poll_result})

    except requests.exceptions.ConnectionError:
        return jsonify({'code': 503, 'message': '连接云端失败，服务器未响应'})
    except requests.exceptions.Timeout:
        return jsonify({'code': 504, 'message': '连接云端超时'})
    except Exception as e:
        logger.error(f'[轮询] 获取云端数据异常: {e}')
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/cloud/connection-test', methods=['GET'])
def cloud_connection_test():
    config_file = DB_PATHS['cloud_config']

    def load_config():
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    cfg = load_config()
    cloud_host = cfg.get('cloud_host', '')
    api_key = cfg.get('api_key', '').encode('ascii', 'ignore').decode('ascii').strip()

    if not cloud_host:
        return jsonify({'code': 400, 'message': '云端地址未配置'}), 400

    try:
        import requests
        from urllib.parse import urlparse
        safe_host = cloud_host
        if cloud_host:
            parsed = urlparse(cloud_host)
            if parsed.scheme and parsed.netloc:
                clean_netloc = parsed.netloc.encode('ascii', 'ignore').decode('ascii')
                safe_host = f"{parsed.scheme}://{clean_netloc}"
        resp = requests.get(
            f'{safe_host}/health',
            headers={'X-API-Key': api_key},
            timeout=10
        )
        if resp.status_code == 200:
            return jsonify({'code': 0, 'message': '连接成功', 'data': resp.json()})
        else:
            return jsonify({'code': resp.status_code, 'message': f'连接失败: {resp.status_code}'}), 400
    except requests.exceptions.SSLError:
        return jsonify({'code': 400, 'message': 'SSL错误，请检查证书'}), 400
    except requests.exceptions.ConnectionError:
        return jsonify({'code': 400, 'message': '连接失败，请检查地址是否正确'}), 400
    except Exception as e:
        return jsonify({'code': 500, 'message': '测试异常失败，请稍后重试'}), 500


@dispatch_center_bp.route('/scheduler-manager/status', methods=['GET'])
def scheduler_manager_status():
    data = _scheduler_manager.get_status_all()
    return jsonify({'code': 0, 'data': data})


@dispatch_center_bp.route('/scheduler-manager/toggle', methods=['PUT'])
def scheduler_manager_toggle():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name', '')
    enabled = body.get('enabled', True)
    ok, msg = _scheduler_manager.toggle(name, enabled)
    if not ok:
        return jsonify({'code': 400, 'message': msg}), 400
    return jsonify({'code': 0, 'message': '操作成功'})


@dispatch_center_bp.route('/scheduler-manager/interval', methods=['PUT'])
def scheduler_manager_interval():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name', '')
    interval = int(body.get('interval_seconds', 3600))
    if interval < 10:
        return jsonify({'code': 400, 'message': '间隔不能少于10秒'}), 400
    ok, msg = _scheduler_manager.set_interval(name, interval)
    if not ok:
        return jsonify({'code': 400, 'message': msg}), 400
    return jsonify({'code': 0, 'message': '间隔已更新'})


# ============================================================
# 服务管理 API（报工程序、容器中心、调度中心启动/停止/状态）
# ============================================================

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_PYTHON_PATH = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
_SERVER_DEFS = {
    'baogong': {
        'name': '报工程序',
        'script': 'mobile_api_ai/app.py',
        'cwd': 'mobile_api_ai',
        'port': 5008,
    },
    'container': {
        'name': '容器中心',
        'script': 'mobile_api_ai/container_center_api.py',
        'cwd': 'mobile_api_ai',
        'port': 5002,
    },
    'dispatch': {
        'name': '调度中心',
        'script': 'mobile_api_ai/wechat_server.py',
        'cwd': 'mobile_api_ai',
        'port': 5003,
    },
}

_server_processes = {}
_server_processes_lock = threading.Lock()


def _get_server_pid_by_port(port):
    """通过端口查找进程 PID"""
    try:
        import psutil
        for conn in psutil.net_connections():
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                return conn.pid
    except Exception:
        pass
    return None


def _get_server_status(server_key):
    """获取单个服务器状态"""
    info = _SERVER_DEFS[server_key]
    pid = _get_server_pid_by_port(info['port'])
    managed = server_key in _server_processes and _server_processes[server_key].poll() is None
    return {
        'key': server_key,
        'name': info['name'],
        'port': info['port'],
        'running': pid is not None or managed,
        'pid': pid,
        'managed': managed,
    }


@dispatch_center_bp.route('/servers', methods=['GET'])
def server_list():
    """获取所有服务器状态"""
    statuses = []
    for key in _SERVER_DEFS:
        statuses.append(_get_server_status(key))
    return jsonify({'code': 0, 'data': statuses})


@dispatch_center_bp.route('/servers/<server_key>/start', methods=['POST'])
def server_start(server_key):
    """启动指定服务器"""
    if server_key not in _SERVER_DEFS:
        return jsonify({'code': 404, 'message': f'未知服务器: {server_key}'}), 404

    info = _SERVER_DEFS[server_key]
    status = _get_server_status(server_key)
    if status['running']:
        return jsonify({'code': 0, 'message': f'{info["name"]} 已在运行中'})

    script_path = os.path.join(_PROJECT_ROOT, info['script'])
    cwd_path = os.path.join(_PROJECT_ROOT, info['cwd'])

    if not os.path.exists(script_path):
        return jsonify({'code': 500, 'message': f'启动脚本不存在: {script_path}'})

    try:
        proc = subprocess.Popen(
            [_PYTHON_PATH, script_path],
            cwd=cwd_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with _server_processes_lock:
            _server_processes[server_key] = proc

        # 启动日志监控线程
        def _monitor_log(p, key):
            try:
                for line in iter(p.stdout.readline, ''):
                    if not line:
                        break
                    logger.info('[%s] %s', info['name'], line.strip())
            except Exception:
                pass
            finally:
                with _server_processes_lock:
                    if _server_processes.get(key) is p:
                        _server_processes.pop(key, None)

        threading.Thread(target=_monitor_log, args=(proc, server_key), daemon=True).start()

        time.sleep(2)
        if proc.poll() is None:
            logger.info('服务启动成功: %s (PID=%d)', info['name'], proc.pid)
            return jsonify({'code': 0, 'message': f'{info["name"]} 启动成功'})
        else:
            with _server_processes_lock:
                _server_processes.pop(server_key, None)
            return jsonify({'code': 500, 'message': f'{info["name"]} 启动失败'})
    except Exception as e:
        logger.exception('启动 %s 异常', info['name'])
        return jsonify({'code': 500, 'message': '启动异常失败，请稍后重试'})


@dispatch_center_bp.route('/servers/<server_key>/stop', methods=['POST'])
def server_stop(server_key):
    """停止指定服务器"""
    if server_key not in _SERVER_DEFS:
        return jsonify({'code': 404, 'message': f'未知服务器: {server_key}'}), 404

    info = _SERVER_DEFS[server_key]
    pid = _get_server_pid_by_port(info['port'])

    # 优先通过 managed 进程停止
    with _server_processes_lock:
        proc = _server_processes.get(server_key)
        if proc and proc.poll() is None:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(proc.pid), '/F'],
                                   capture_output=True, timeout=5)
                else:
                    os.kill(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=5)
            except Exception:
                try:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(proc.pid), '/F'],
                                       capture_output=True, timeout=3)
                    else:
                        proc.kill()
                except Exception:
                    pass
            _server_processes.pop(server_key, None)
            logger.info('服务已停止(managed): %s', info['name'])
            return jsonify({'code': 0, 'message': f'{info["name"]} 已停止'})

    # 通过端口查找并 kill
    if pid:
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(pid), '/F'],
                               capture_output=True, timeout=5)
            else:
                os.kill(pid, signal.SIGTERM)
            logger.info('服务已停止(port): %s (PID=%d)', info['name'], pid)
            return jsonify({'code': 0, 'message': f'{info["name"]} 已停止'})
        except Exception as e:
            return jsonify({'code': 500, 'message': '停止失败失败，请稍后重试'})

    return jsonify({'code': 0, 'message': f'{info["name"]} 未在运行'})


@dispatch_center_bp.route('/servers/logs', methods=['GET'])
def server_logs():
    """获取最近的服务启动日志"""
    log_file = os.path.join(_PROJECT_ROOT, 'mobile_api_ai', 'logs', 'container_center.log')
    lines = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                lines = all_lines[-200:]
        except Exception:
            pass
    return jsonify({'code': 0, 'data': lines})


@dispatch_center_bp.route('/quality/create', methods=['POST'])
def create_quality_task():
    """
    从主软件接收质检任务，创建调度中心任务并推送通知
    ---
    请求体:
        order_no: 订单号 (必填)
        inspection_type: 质检类型 (终检/首检/巡检)
        inspection_items: 质检项目 (逗号分隔)
        inspector: 质检员
        process_name: 工序名称
        customer_group: 客户群
        quality_record_id: 质检记录ID
    """
    try:
        # 兼容 Flask-Limiter 等中间件消费 body 的场景
        body = request.get_json(silent=True)
        if body is None:
            raw = request.get_data()
            if raw:
                try:
                    body = json.loads(raw.decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    try:
                        body = json.loads(raw.decode('gbk'))
                    except Exception:
                        body = {}
            else:
                body = {}
        order_no = (body.get('order_no') or '').strip()
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no 必填'}), 400

        inspection_type = body.get('inspection_type') or '终检'
        inspection_items = body.get('inspection_items') or ''
        inspector = body.get('inspector') or ''
        process_name = body.get('process_name') or ''
        customer_group = (body.get('customer_group') or '') or _get_customer_group_for_order(order_no)
        quality_record_id = body.get('quality_record_id', 0)

        # T14 迁移: 质检去重检查改查 quality_records
        # 架构依据: ARCHITECTURE_v3.6.md 1.10.2 节
        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                # T14: 改为查询 quality_records 表的 status='pending' 记录
                cursor.execute(
                    "SELECT id FROM quality_records WHERE order_no=%s AND process_name=%s "
                    "AND status='pending' LIMIT 1",
                    (order_no, process_name))
                if cursor.fetchone():
                    return jsonify({'code': 0, 'message': '该工序任务已存在，跳过',
                                    'order_no': order_no, 'task_id': 'dup'}), 200
        except Exception:
            pass  # 去重查询失败不影响主流程

        pkg_id = f"QA-{order_no}-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now().isoformat()

        pkg_dict = {
            'id': pkg_id,
            'title': f'质检任务: {inspection_type} - {order_no}',
            'data_type': 'quality',
            'source': '主软件',
            'priority': 'normal',
            'status': 'pending',
            'related_order': order_no,
            'related_process': process_name,
            'target_operator': inspector or '',
            'content': json.dumps({
                'quality_record_id': quality_record_id,
                'inspection_type': inspection_type,
                'inspection_items': inspection_items,
                'inspector': inspector,
                'process_name': process_name,
                'customer_group': customer_group,
            }, ensure_ascii=False),
            'created_at': now,
            'updated_at': now,
        }

        # T14 迁移完成: 质检任务直接写入 quality_packages 表，不再写入 data_packages
        # 架构依据: ARCHITECTURE_v3.6.md 1.10.2 节
        try:
            with get_connection_context() as conn:
                conn.select_db('container_center')
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO quality_packages
                       (id, title, content, source, priority, status,
                        order_no, related_order, related_process, target_operator, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())""",
                    (pkg_id, pkg_dict['title'], pkg_dict['content'],
                     '主软件', 'normal', 'pending',
                     order_no, order_no, process_name, inspector or ''))
                conn.commit()
                logger.info(f"[质检任务] 已创建 quality_package: {pkg_id} for {order_no}")
        except Exception as e:
            logger.warning(f"[质检任务] 同步quality_packages失败: {e}")

        cc = _get_container_center()
        if cc and cc.is_notification_enabled:
            try:
                msg = _render_template('tmpl_alert_quality', {
                    '订单号': order_no,
                    '标题': f'{inspection_type}质检',
                    '负责人': inspector or '待分配',
                })
                cc.send_group_notification(msg)
            except Exception:
                pass

        return jsonify({'code': 0, 'message': '质检任务已创建', 'data': {'task_id': pkg_id, 'order_no': order_no}})

    except Exception as e:
        logger.error(f"[质检任务] 创建失败: {e}")
        return jsonify({'code': 500, 'message': '创建质检任务失败失败，请稍后重试'}), 500


@dispatch_center_bp.route('/servers/python-path', methods=['GET'])
def server_python_path():
    """获取当前配置的 Python 路径"""
    return jsonify({
        'code': 0,
        'data': {
            'python_path': _PYTHON_PATH,
            'project_root': _PROJECT_ROOT,
        }
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Part 16: 质检与成本同步 (行 8265~8554)
# ═══════════════════════════════════════════════════════════════════════════════

def on_quality_record_completed(order_no: str, process_id: str, result: str, inspector: str) -> tuple:
    """质检记录提交后联动更新 dispatch_cache 流程状态 + 容器中心 + MySQL。

    参数:
        order_no: 订单号
        process_id: 流程ID
        result: 质检结果 (合格/不合格/待复检)
        inspector: 质检员

    返回:
        (success: bool, message: str)
    """
    if result != '合格':
        logger.info(f"[质检联动] {order_no} 质检结果为 {result}，不推进流程")
        return True, f'质检结果: {result}，流程保持当前步骤'

    success = [False]
    msg = ['']

    def updater(data):
        process = next((p for p in data.get('processes', []) if p.get('order_no') == order_no), None)
        if not process:
            msg[0] = '流程不存在'
            return

        flow_type = process.get('flow_type', 'production')
        flow_template = PROCESS_FLOW_TEMPLATES.get(flow_type, PROCESS_FLOW_TEMPLATES['production'])
        steps = process.get('steps') or flow_template['steps']
        current_step = process.get('current_step', 0)

        if current_step >= len(steps) - 1:
            process['status'] = 'completed'
            process['current_step'] = len(steps) - 1
        else:
            next_step_index = current_step + 1
            next_step = steps[next_step_index]
            process['current_step'] = next_step_index
            process['status'] = next_step.get('status_key', 'in_progress')

        process['completed_at_' + str(current_step)] = datetime.now().isoformat()
        process['completed_by_' + str(current_step)] = inspector
        process['updated_at'] = datetime.now().isoformat()
        process['quality_result'] = result
        process['quality_inspector'] = inspector
        process['quality_checked_at'] = datetime.now().isoformat()
        success[0] = True
        msg[0] = f'质检合格，流程已推进到第 {process["current_step"]} 步'

    _dispatch_cache.update_data(updater)

    if not success[0]:
        return False, msg[0]

    status_key = 'completed'
    dc_data = _dispatch_cache.get_data()
    p = next((pp for pp in dc_data.get('processes', []) if pp.get('order_no') == order_no), None)
    if p:
        status_key = p.get('status', 'completed')

    def _async_quality_sync():
        _sync_work_order_status(order_no, p.get('current_step', 0) if p else 0, status_key)
        _sync_to_mysql(order_no, status_key, order_no)
        # 获取质检类型和备注
        quality_type = p.get('quality_type', '终检') if p else '终检'
        quality_remark = p.get('quality_remark', '') if p else ''
        # 获取产品信息
        product_name = ''
        try:
            schedule_result = _get_client().query_documents('schedule', all=True)
            if schedule_result and isinstance(schedule_result, list):
                for item in schedule_result:
                    if item.get('order_no') == order_no:
                        product_name = item.get('product_name', item.get('product', ''))
                        break
        except Exception:
            pass
        _send_wechat_message(
            _render_template('tmpl_quality_completed', {
                '订单号': order_no,
                '质检类型': quality_type,
                '质检结果': result,
                '质检员': inspector,
                '完成时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                '备注': quality_remark or '无',
                '产品': product_name,
            }),
            msg_type='markdown'
        )

    threading.Thread(target=_async_quality_sync, daemon=True).start()

    return True, msg[0]


# ============================================================
# 索引与文档 - 系统架构文档服务
# ============================================================

_ARCHITECTURE_DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      '..', 'docs', 'system_architecture_document.md')


@dispatch_center_bp.route('/documents', methods=['GET'])
def list_documents():
    """获取可用文档索引列表"""
    documents = []
    doc_path = _ARCHITECTURE_DOC_PATH
    if os.path.exists(doc_path):
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            title = first_line.lstrip('#').strip() if first_line.startswith('#') else '系统架构文档'
            documents.append({
                'id': 'system-architecture',
                'title': title,
                'description': '不锈钢自动跟单系统整体架构、数据流、推算逻辑与运算逻辑综合文档',
                'category': '架构设计',
                'updated_at': datetime.fromtimestamp(os.path.getmtime(doc_path)).isoformat(),
                'size': os.path.getsize(doc_path),
            })
        except Exception as e:
            logger.error(f'读取文档索引失败: {e}')

    return jsonify({'code': 0, 'data': documents})


@dispatch_center_bp.route('/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """获取指定文档内容"""
    if doc_id != 'system-architecture':
        return jsonify({'code': 404, 'message': '文档不存在'})

    doc_path = _ARCHITECTURE_DOC_PATH
    if not os.path.exists(doc_path):
        return jsonify({'code': 404, 'message': '文档文件不存在'})

    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            'code': 0,
            'data': {
                'id': 'system-architecture',
                'title': '不锈钢自动跟单系统整体架构文档',
                'content': content,
                'updated_at': datetime.fromtimestamp(os.path.getmtime(doc_path)).isoformat(),
            }
        })
    except Exception as e:
        logger.error(f'读取文档失败: {e}')
        return jsonify({'code': 500, 'message': '读取文档失败失败，请稍后重试'})



# ========== 质检记录（调度中心自有接口，直读DB） ==========
@dispatch_center_bp.route('/quality/detail/<int:record_id>', methods=['GET'])
def get_quality_detail(record_id):
    try:
        from models.quality import QualityDAO
        record = QualityDAO.get_by_id(record_id)
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在'})
        items = QualityDAO.get_record_items(record_id) or []
        return jsonify({'code': 0, 'data': {
            'record': {
                'id': record['id'],
                'order_no': record.get('order_no', ''),
                'inspection_type': record.get('inspection_type', ''),
                'process_name': record.get('process_name', ''),
                'inspector': record.get('inspector', ''),
                'result': record.get('result', ''),
                'review_status': record.get('review_status', ''),
                'record_date': str(record.get('record_date', '')),
                'defect_description': record.get('defect_description', ''),
                'handling_method': record.get('handling_method', ''),
                'rework_version': record.get('rework_version', 0),
            },
            'items': [{
                'inspection_item': i.get('inspection_item', ''),
                'measured_value': i.get('measured_value', ''),
                'standard_value': i.get('standard_value', ''),
                'tolerance': i.get('tolerance', ''),
                'is_passed': i.get('is_passed', True),
            } for i in items]
        }})
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})

@dispatch_center_bp.route('/quality/records', methods=['GET'])
def get_quality_records():
    try:
        result = request.args.get('result', '全部')
        limit = int(request.args.get('limit', 50))
        with get_connection_context() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM container_center.quality_records WHERE 1=1"
            params = []
            if result != '全部':
                sql += " AND result=%s"
                params.append(result)
            sql += " ORDER BY id DESC LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        records = []
        for r in rows:
            # [P1 修复 2026-06-18 Bug #8] inspectionItems 归一化为 array 格式
            # 修复前: 3 种格式混用 - None / "a,b,c" / 数组
            # 修复后: 全部归一为数组
            raw_items = r.get('inspection_items')
            items_normalized = _normalize_inspection_items(raw_items)
            records.append({
                'id': r['id'],
                'order_no': r.get('order_no', ''),
                # [P1 修复 2026-06-18 Bug #7] orderName 补全（= order_no）
                'orderName': r.get('order_no', ''),
                'inspection_type': r.get('inspection_type', ''),
                'process_name': r.get('process_name', ''),
                'inspector': r.get('inspector', ''),
                'result': r.get('result', ''),
                'review_status': r.get('review_status', ''),
                'record_date': str(r.get('record_date')) if r.get('record_date') else '',
                'rework_version': r.get('rework_version', 0) or 0,
                # [P1 修复 2026-06-18 Bug #8] 归一化后的 items
                'inspectionItems': items_normalized,
            })
        return jsonify({'code': 0, 'data': {'records': records, 'total': len(records)}})
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})

def _normalize_inspection_items(raw):
    """[P1 修复 2026-06-18 Bug #8] 归一化 inspection_items 字段
    支持 3 种输入格式: None / "a,b,c" / "['a','b']" / array → 统一返回 array
    """
    if raw is None or raw == '' or raw == 'null':
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        # 尝试 JSON 解析
        s = raw.strip()
        if s.startswith('[') and s.endswith(']'):
            try:
                import json
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        # 兜底：按逗号拆分
        return [x.strip() for x in s.split(',') if x.strip()]
    return []

@dispatch_center_bp.route('/quality/review', methods=['POST'])
def review_quality_record():
    try:
        body = request.get_json(silent=True) or {}
        record_id = body.get('record_id')
        action = body.get('action', 'approved')
        if not record_id:
            return jsonify({'code': 400, 'message': '缺少 record_id'})
        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE container_center.quality_records SET review_status=%s, reviewed_at=NOW() WHERE id=%s",
                (action, record_id))
            conn.commit()
        return jsonify({'code': 0, 'message': '操作成功'})
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})

@dispatch_center_bp.route('/quality/versions/<order_no>', methods=['GET'])
def get_quality_versions(order_no):
    try:
        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM container_center.quality_records WHERE order_no=%s ORDER BY rework_version DESC",
                (order_no,))
            rows = cursor.fetchall()
        return jsonify({'code': 0, 'data': {'records': rows, 'total': len(rows)}})
    except Exception as e:
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"})

# ========== Outbox 消费者（质检报告 → 流程推进） ==========

# ═══════════════════════════════════════════════════════════════════════════════
# Part 17: 报工与同步接口 (行 8555~8922)
# ═══════════════════════════════════════════════════════════════════════════════

import threading, json as _json, time as _time

DispatchContext.get_instance().outbox_running = False

def start_outbox_worker(interval=30):
    """启动 Outbox 后台消费者"""
    # [removed] global DispatchContext.get_instance().outbox_running
    if DispatchContext.get_instance().outbox_running:
        return
    DispatchContext.get_instance().outbox_running = True

    def _consume():
        from models.database import get_connection_context
        while DispatchContext.get_instance().outbox_running:
            try:
                with get_connection_context() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM outbox WHERE retries < 5 ORDER BY created_at LIMIT 10")
                    rows = cursor.fetchall()
                    for row in rows:
                        try:
                            payload = _json.loads(row['payload'])
                            if row['event_type'] == 'quality_reported':
                                _on_quality_record_completed_dict(payload)
                            elif row['event_type'] == 'quality_approved':
                                logger.info('[Outbox] 质检已审核: record_id=%s', payload.get('record_id'))
                            elif row['event_type'] == 'quality_rejected':
                                logger.info('[Outbox] 质检已退回: record_id=%s', payload.get('record_id'))
                            cursor.execute("DELETE FROM outbox WHERE id=%s", (row['id'],))
                            conn.commit()
                        except Exception as e:
                            logger.warning('[Outbox] 处理失败 id=%s: %s', row.get('id'), e)
                            cursor.execute(
                                "UPDATE outbox SET retries=retries+1 WHERE id=%s", (row['id'],))
                            conn.commit()
            except Exception as e:
                logger.warning('[Outbox] 轮询异常: %s', e)
            _time.sleep(interval)

    t = threading.Thread(target=_consume, daemon=True)
    t.start()
    logger.info('[Outbox] 消费者已启动，间隔=%ss', interval)


def _update_quality_record_status(order_no: str, result: str, record_id: int = 0) -> bool:
    """T8 迁移: 更新 quality_records 表状态
    架构依据: ARCHITECTURE_v3.6.md 1.10.2 节 - 任务类型必须使用独立表，禁止混用 data_packages
    """
    new_status = 'completed' if result == '合格' else 'quality_failed'
    try:
        with get_connection_context() as conn:
            conn.select_db('container_center')
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE quality_records SET status=%s, judgment=%s "
                "WHERE order_no=%s AND status NOT IN ('completed','quality_reported')",
                (new_status, result, order_no))
            conn.commit()
            affected = cursor.rowcount
            if affected > 0:
                logger.info(f'[T8] 更新 quality_records: order_no={order_no}, status={new_status}, affected={affected}')
            return True
    except Exception as e:
        logger.warning(f'[T8] 更新 quality_records 失败: {e}')
        return False


def _on_quality_record_completed_dict(payload):
    """质检报告提交 → 推进流程 + 回写桌面端
    T8 迁移: 改为更新 quality_records 表
    架构依据: ARCHITECTURE_v3.6.md 1.10.2 节
    """
    order_no = payload.get('order_no', '')
    result = payload.get('overall_result', '')
    record_id = payload.get('record_id', 0)
    logger.info('[质检流程] record_id=%s order=%s result=%s', record_id, order_no, result)

    # [T8 迁移] 更新 quality_records 状态
    _update_quality_record_status(order_no, result, record_id)

    # 推进生产流程
    if result == '合格':
        _sync_to_mysql(order_no, 'completed')
    else:
        _notify_process_event(order_no, 'quality_failed', {
            'order_no': order_no,
            'defect': result,
        })


# ====== 回填 flow_type 列 ======
@dispatch_center_bp.route('/backfill-flow-type', methods=['POST'])
def api_backfill_flow_type():
    """回填 process_records 表的 flow_type 字段"""
    import pymysql

    conn = None
    try:
        conn = _get_mysql_connection()  # [T4 2026-06-14] 走连接池
        cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE process_records ADD COLUMN flow_type VARCHAR(100) DEFAULT 'production'")
            conn.commit()
            logger.info('[回填] flow_type 列已添加')
        except Exception as e:
            if 'Duplicate' in str(e):
                logger.info('[回填] flow_type 列已存在')
            else:
                raise

        cur.execute("""
            UPDATE process_records
            SET flow_type = COALESCE(
                JSON_UNQUOTE(JSON_EXTRACT(content, '$.flow_type')),
                'production'
            )
            WHERE flow_type IS NULL OR flow_type = ''
        """)
        conn.commit()
        affected = cur.rowcount
        logger.info('[回填] 回填 %d 条', affected)

        cur.execute("SELECT COUNT(*) FROM process_records")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM process_records WHERE flow_type IS NOT NULL AND flow_type != ''")
        filled = cur.fetchone()[0]

        cur.close()
        conn.close()

        return jsonify({
            'code': 0,
            'message': '回填完成',
            'data': {'total': total, 'filled': filled, 'affected': affected}
        })
    except Exception as e:
        logger.warning('[回填] 失败: %s', e)
        if conn:
            conn.close()
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# 桌面端同步接口 (通过 5003 调度中心转发)
#
# [Q-B1 v3.7.3 2026-06-25] 所有 sync 接口已通过 Blueprint url_prefix='/api/dispatch-center'
# 自动获得标准前缀，最终 URL 格式：
#   - /api/dispatch-center/sync/material
#   - /api/dispatch-center/sync/repair
#   - /api/dispatch-center/sync/outsource
#   - /api/dispatch-center/sync/sub-step-report
#   - /api/dispatch-center/sync/quality-record
#
# 内部路由名仍保留 /sync/xxx（Blueprint 自动加前缀），无需手动重复声明
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/sync/material', methods=['POST'])
def api_sync_material():
    """物料状态同步 - 更新 steel_belt.order_materials (支持动态字段扩展 + 字段映射)

    字段映射:
        status -> prep_status
        planned_qty -> required_qty
        completed_qty -> prepared_qty
    """
    ok, err = _check_jwt_auth()
    if not ok:
        return err
    from flask import request
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})

    order_no = body.get('order_no', '')
    if not order_no:
        return jsonify({'code': 1001, 'message': 'order_no 必填'})

    try:
        conn = _get_mysql_connection()
    except Exception as e:
        logger.error('[DispatchCenter] 物料同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500
    try:
        cur = conn.cursor()

        material_field_map = {
            'status': 'prep_status',
            'planned_qty': 'required_qty',
            'completed_qty': 'prepared_qty',
        }
        exclude_fields = {'order_no'}
        update_fields = ['updated_at=NOW()']
        update_values = []
        mapped_fields = {}
        skipped_fields = []

        for key, value in body.items():
            if key in exclude_fields or value is None:
                continue
            mapped_key = material_field_map.get(key, key)
            if mapped_key not in _MATERIAL_SQL_ALLOWED:
                logger.warning('[DispatchCenter] 物料同步跳过非法字段: %s', mapped_key)
                skipped_fields.append(key)
                continue
            update_fields.append(f'{mapped_key}=%s')
            update_values.append(value)
            if mapped_key != key:
                mapped_fields[key] = mapped_key

        if not update_fields:
            conn.close()
            return jsonify({'code': 0, 'message': '无更新字段'})

        # 参数顺序: update_values 中各字段值(按 update_fields 顺序) + WHERE 条件值
        update_values.append(order_no)
        sql = f"UPDATE steel_belt.order_materials SET {', '.join(update_fields)} WHERE order_no=%s"
        cur.execute(sql, update_values)
        conn.commit()
        affected = cur.rowcount
        conn.close()

        logger.info('[DispatchCenter] 物料同步完成: order_no=%s, raw_fields=%s, mapped=%s, affected=%d',
                    order_no, list(body.keys()), mapped_fields, affected)
        return jsonify({'code': 0, 'message': 'ok', 'affected': affected, 'skipped_fields': skipped_fields})
    except Exception as e:
        conn.close()
        logger.error('[DispatchCenter] 物料同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500


@dispatch_center_bp.route('/sync/repair', methods=['POST'])
def api_sync_repair():
    """维修状态同步 - 更新 steel_belt.repair_records (支持动态字段扩展 + 字段映射)

    字段映射:
        target_operator -> assigned_to
    """
    ok, err = _check_jwt_auth()
    if not ok:
        return err
    from flask import request
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})

    order_no = body.get('order_no', '')
    if not order_no:
        return jsonify({'code': 1001, 'message': 'order_no 必填'})

    try:
        conn = _get_mysql_connection()
    except Exception as e:
        logger.error('[DispatchCenter] 维修同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500
    try:
        cur = conn.cursor()

        repair_field_map = {
            'target_operator': 'assigned_to',
        }
        exclude_fields = {'order_no'}
        update_fields = ['updated_at=NOW()']
        update_values = []
        mapped_fields = {}
        skipped_fields = []

        for key, value in body.items():
            if key in exclude_fields or value is None:
                continue
            mapped_key = repair_field_map.get(key, key)
            if mapped_key not in _REPAIR_SQL_ALLOWED:
                logger.warning('[DispatchCenter] 维修同步跳过非法字段: %s', mapped_key)
                skipped_fields.append(key)
                continue
            update_fields.append(f'{mapped_key}=%s')
            update_values.append(value)
            if mapped_key != key:
                mapped_fields[key] = mapped_key

        if not update_fields:
            conn.close()
            return jsonify({'code': 0, 'message': '无更新字段'})

        # 参数顺序: update_values 中各字段值(按 update_fields 顺序) + WHERE 条件值
        update_values.append(order_no)
        sql = f"UPDATE steel_belt.repair_records SET {', '.join(update_fields)} WHERE order_no=%s"
        cur.execute(sql, update_values)
        conn.commit()
        affected = cur.rowcount
        conn.close()

        logger.info('[DispatchCenter] 维修同步完成: order_no=%s, raw_fields=%s, mapped=%s, affected=%d',
                    order_no, list(body.keys()), mapped_fields, affected)
        return jsonify({'code': 0, 'message': 'ok', 'affected': affected, 'skipped_fields': skipped_fields})
    except Exception as e:
        conn.close()
        logger.error('[DispatchCenter] 维修同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500


@dispatch_center_bp.route('/sync/outsource', methods=['POST'])
def api_sync_outsource():
    """外协状态同步 - 更新 steel_belt.outsource_records (支持动态字段扩展)

    请求体:
    {
        "order_no": "ORD-xxx",
        "任何字段": "任何值 (自动同步到 outsource_records 表)"
    }
    """
    ok, err = _check_jwt_auth()
    if not ok:
        return err
    from flask import request
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})

    order_no = body.get('order_no', '')
    if not order_no:
        return jsonify({'code': 1001, 'message': 'order_no 必填'})

    try:
        conn = _get_mysql_connection()
    except Exception as e:
        logger.error('[DispatchCenter] 外协同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500
    try:
        cur = conn.cursor()

        exclude_fields = {'order_no'}
        update_fields = ['updated_at=NOW()']
        update_values = []
        skipped_fields = []

        for key, value in body.items():
            if key not in exclude_fields and value is not None:
                if key not in _OUTER_SQL_ALLOWED:
                    logger.warning('[DispatchCenter] 外协同步跳过非法字段: %s', key)
                    skipped_fields.append(key)
                    continue
                update_fields.append(f'{key}=%s')
                update_values.append(value)

        if not update_fields:
            conn.close()
            return jsonify({'code': 0, 'message': '无更新字段'})

        update_fields.append('updated_at=NOW()')
        # 参数顺序: update_values 中各字段值(按 update_fields 顺序) + WHERE 条件值
        update_values.append(order_no)

        sql = f"UPDATE steel_belt.outsource_records SET {', '.join(update_fields)} WHERE order_no=%s"
        cur.execute(sql, update_values)
        conn.commit()
        affected = cur.rowcount
        conn.close()

        logger.info('[DispatchCenter] 外协同步完成: order_no=%s, affected=%d', order_no, affected)
        return jsonify({'code': 0, 'message': 'ok', 'affected': affected, 'skipped_fields': skipped_fields})
    except Exception as e:
        conn.close()
        logger.error('[DispatchCenter] 外协同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500


@dispatch_center_bp.route('/sync/sub-step-report', methods=['POST'])
def api_sync_sub_step_report():
    """工序报工同步 - 更新 steel_belt.process_sub_steps

    请求体:
    {
        "order_no": "ORD-xxx",
        "step_name": "P06",
        "process_code": "P06",
        "quantity": 100,
        "qualified_qty": 98,
        "operator": "张三",
        "operator_id": "OP001",
        "equipment_name": "设备A",
        "remark": "备注",
        "overtime_hours": 2.5
    }
    """
    from flask import request
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})

    order_no = body.get('order_no', '')
    step_name = body.get('step_name', '') or body.get('process_code', '')
    quantity = body.get('quantity', 0)
    if not order_no or not step_name:
        return jsonify({'code': 1001, 'message': 'order_no 和 step_name 必填'})

    try:
        conn = _get_mysql_connection()
        cur = conn.cursor()

        update_fields = ['updated_at=NOW()']
        update_values = []
        if quantity:
            update_fields.append('completed_qty=%s')
            update_values.append(quantity)
        if body.get('qualified_qty') is not None:
            update_fields.append('qualified_qty=%s')
            update_values.append(body['qualified_qty'])
        if body.get('operator'):
            update_fields.append('target_operator=%s')
            update_values.append(body['operator'])
        if body.get('remark'):
            update_fields.append('remark=%s')
            update_values.append(body['remark'])

        update_values.append(order_no)
        update_values.append(step_name)

        sql = f"""UPDATE steel_belt.process_sub_steps
                   SET {', '.join(update_fields)}
                   WHERE order_no=%s AND process_code=%s"""
        cur.execute(sql, update_values)
        conn.commit()
        affected = cur.rowcount
        conn.close()

        logger.info('[DispatchCenter] 工序报工同步完成: order_no=%s, step=%s, affected=%d',
                    order_no, step_name, affected)
        return jsonify({'code': 0, 'message': 'ok', 'affected': affected})
    except Exception as e:
        logger.error('[DispatchCenter] 工序报工同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Part 18: 同步接口 (行 8923~9000)
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/sync/quality-record', methods=['POST'])
def api_sync_quality_record():
    """质检记录同步 - 更新 steel_belt.quality_records (支持动态字段扩展 + 字段映射)

    字段映射:
        inspection_type -> process_name
        step_name -> process_name
    """
    ok, err = _check_jwt_auth()
    if not ok:
        return err
    from flask import request
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})

    order_no = body.get('order_no', '')
    step_name = body.get('step_name', '') or body.get('inspection_type', '')
    record_id = body.get('record_id', '')
    operation = body.get('operation', 'update')

    if not order_no:
        return jsonify({'code': 1001, 'message': 'order_no 必填'})

    try:
        conn = _get_mysql_connection()
    except Exception as e:
        logger.error('[DispatchCenter] 质检同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500
    try:
        cur = conn.cursor()

        quality_field_map = {
            'inspection_type': 'process_name',
            'step_name': 'process_name',
        }
        exclude_fields = {'order_no', 'step_name', 'inspection_type', 'operation', 'record_id'}
        skipped_fields = []

        if operation == 'withdraw':
            sql = "UPDATE steel_belt.quality_records SET result='pending', updated_at=NOW() WHERE order_no=%s AND process_name=%s"
            cur.execute(sql, (order_no, step_name))
        else:
            update_fields = ['updated_at=NOW()']
            update_values = []
            mapped_fields = {}
            skipped_fields = []

            for key, value in body.items():
                if key in exclude_fields or value is None:
                    continue
                mapped_key = quality_field_map.get(key, key)
                if mapped_key not in _QUALITY_SQL_ALLOWED:
                    logger.warning('[DispatchCenter] 质检同步跳过非法字段: %s', mapped_key)
                    skipped_fields.append(key)
                    continue
                update_fields.append(f'{mapped_key}=%s')
                update_values.append(value)
                if mapped_key != key:
                    mapped_fields[key] = mapped_key

            if not update_fields:
                conn.close()
                return jsonify({'code': 0, 'message': '无更新字段'})

            if record_id:
                sql = f"UPDATE steel_belt.quality_records SET {', '.join(update_fields)} WHERE id=%s"
                update_values.append(record_id)
            else:
                sql = f"UPDATE steel_belt.quality_records SET {', '.join(update_fields)} WHERE order_no=%s AND process_name=%s"
                update_values.extend([order_no, step_name])

            cur.execute(sql, update_values)

        conn.commit()
        affected = cur.rowcount
        conn.close()

        logger.info('[DispatchCenter] 质检同步完成: order_no=%s, step=%s, op=%s, raw=%s, mapped=%s, affected=%d',
                    order_no, step_name, operation, list(body.keys()), mapped_fields, affected)
        return jsonify({'code': 0, 'message': 'ok', 'affected': affected, 'skipped_fields': skipped_fields})
    except Exception as e:
        conn.close()
        logger.error('[DispatchCenter] 质检同步失败: %s', e)
        return jsonify({'code': 500, 'message': '更新失败，请稍后重试'}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Part 20b: 配置接口 (硬迁移 2026-06-20)
# 背景：原 container_center/api/configs.py 中的 /configs/alert_rules 路由随死代码包删除而消失。
#       ContainerCenterClient.get_alert_rules / update_alert_rules 原本调用 5002 /api/v4/configs/alert_rules，
#       硬迁移后必须由 5003 端口接管。存储复用 AlertEngine 已有的 ConfigStore 实例。
# ═══════════════════════════════════════════════════════════════════════════════

@dispatch_center_bp.route('/configs/alert_rules', methods=['GET'])
def api_get_alert_rules():
    """[硬迁移 2026-06-20] 获取告警规则

    替代原 5002 /api/v4/configs/alert_rules (container_center/api/configs.py 已删除)。
    存储：复用 DispatchContext.alert_engine.config_store (ConfigStore，SQLite)。
    """
    from flask import request
    try:
        ctx = DispatchContext.get_instance()
        alert_engine = ctx.alert_engine
        if alert_engine is None or alert_engine.config_store is None:
            logger.warning('[DispatchCenter] AlertEngine 未初始化，alert_rules 返回空')
            return jsonify({'code': 0, 'message': 'success', 'data': {}})
        rules = alert_engine.config_store.get('alert_rules')
        if rules is None:
            return jsonify({'code': 0, 'message': 'success', 'data': {}})
        return jsonify({'code': 0, 'message': 'success', 'data': rules})
    except Exception as e:
        logger.error('[DispatchCenter] get_alert_rules 失败: %s', e)
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


@dispatch_center_bp.route('/configs/alert_rules', methods=['PUT'])
def api_update_alert_rules():
    """[硬迁移 2026-06-20] 更新告警规则

    替代原 5002 /api/v4/configs/alert_rules (container_center/api/configs.py 已删除)。
    存储：复用 DispatchContext.alert_engine.config_store (ConfigStore，SQLite)。
    """
    from flask import request
    try:
        ctx = DispatchContext.get_instance()
        alert_engine = ctx.alert_engine
        if alert_engine is None or alert_engine.config_store is None:
            return jsonify({'code': 503, 'message': 'AlertEngine 未初始化'}), 503
        body = request.get_json(silent=True) or {}
        ok = alert_engine.config_store.set('alert_rules', body)
        if not ok:
            return jsonify({'code': 500, 'message': '保存失败'}), 500
        logger.info('[DispatchCenter] alert_rules 更新成功: keys=%s', list(body.keys()))
        return jsonify({'code': 0, 'message': 'success', 'data': {'updated': True}})
    except Exception as e:
        logger.error('[DispatchCenter] update_alert_rules 失败: %s', e)
        return jsonify({'code': 500, 'message': "操作失败，请稍后重试"}), 500


