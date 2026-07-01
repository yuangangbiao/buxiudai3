# -*- coding: utf-8 -*-
"""
[v3.7.6] dispatch_center.publisher

替代 desktop_container_integration.get_integration() 的新接口。

迁移:
    旧: from desktop_container_integration import get_integration
        integration = get_integration()
    新: from mobile_api_ai.dispatch_center.publisher import get_publisher
        publisher = get_publisher('report')

[v3.7.6 补齐] 添加:
    - QualityPublisher（替代 publish_quality_task）
    - 任务查询方法（get_all_tasks, get_task_by_id, get_task_count）
    - is_available 属性
    - 熔断器状态接口
"""
import logging
import threading
import time
from typing import Optional, Dict, Any, List
from collections import deque

logger = logging.getLogger(__name__)


# ============ 熔断器实现 ============

class CircuitBreaker:
    """[v3.7.6] 简单熔断器

    状态:
        CLOSED: 正常
        OPEN: 熔断（拒绝请求）
        HALF_OPEN: 半开（试探性放行）

    触发条件: 连续失败次数超过阈值
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = 'CLOSED'
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """通过熔断器调用函数"""
        with self._lock:
            if self._state == 'OPEN':
                # 检查是否到达恢复时间
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = 'HALF_OPEN'
                else:
                    raise RuntimeError('熔断器 OPEN：拒绝请求')

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self._state == 'HALF_OPEN':
                    self._state = 'CLOSED'
                    self._failures = 0
                else:
                    self._failures = 0
            return result
        except Exception as e:
            with self._lock:
                self._failures += 1
                self._last_failure_time = time.time()
                if self._failures >= self.failure_threshold:
                    self._state = 'OPEN'
            raise

    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        with self._lock:
            return {
                'state': self._state,
                'failures': self._failures,
                'threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout,
            }


# ============ 任务存储（双轨: 内存 + DB）============
# [v3.7.6] 替代原 get_all_tasks / get_task_by_id / get_task_count
# [v3.7.8] 新增 DB 模式（环境变量 DISPATCH_CENTER_USE_DB=1 启用）
#
# 工作模式:
#   - DISPATCH_CENTER_USE_DB 未设置 → 内存模式 (默认)
#       适用: 单元测试、单进程 demo、DB 未就绪环境
#   - DISPATCH_CENTER_USE_DB=1 → DB 模式
#       适用: 生产环境（多进程/多实例/重启可恢复）
#       DB 失败时自动 fallback 内存（业务不中断）+ ERROR 日志
#
# 详见 docs/v3.7.7/PRODUCTION_STORAGE_MIGRATION.md
#      docs/v3.7.8/ddl/dispatch_center_tasks.sql
import os as _os
_USE_DB = _os.environ.get('DISPATCH_CENTER_USE_DB') == '1'

_task_store: Dict[str, Dict[str, Any]] = {}
_task_lock = threading.Lock()


def _store_task(task_id: str, task_type: str, payload: Dict[str, Any]) -> None:
    """存储任务（双轨: DB 优先 + 内存 fallback）

    [v3.7.8] 工作流:
        1. 若 DISPATCH_CENTER_USE_DB=1, 调用 _store_task_production
        2. DB 写入失败 → 内存 fallback + ERROR 日志（业务不中断）
        3. 若 DB 未启用 → 直接走内存
    """
    if _USE_DB:
        try:
            _store_task_production(task_id, task_type, payload)
            return
        except Exception as e:
            logger.error(
                f'[publisher] DB 存储失败 task_id={task_id} type={task_type}: {e}'
                f' | fallback 内存存储'
            )
    with _task_lock:
        _task_store[task_id] = {
            'id': task_id,
            'type': task_type,
            'payload': payload,
        }


def _store_task_production(task_id: str, task_type: str, payload: Dict[str, Any]) -> None:
    """[v3.7.8] DB 模式存储任务 - 写入 dispatch_center_tasks 表

    使用 core.db_compat.get_conn() 走连接池（默认 CONTAINER_MYSQL_CFG）
    数据库: container_center
    表 DDL: docs/v3.7.8/ddl/dispatch_center_tasks.sql

    异常策略:
        - pymysql.Error / 网络错误 → 上抛, 由 _store_task 决定 fallback
        - JSON 序列化失败 → ValueError 上抛
    """
    import json
    from core.db_compat import get_conn

    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    sql = (
        'INSERT INTO dispatch_center_tasks (id, type, payload) '
        'VALUES (%s, %s, %s) '
        'ON DUPLICATE KEY UPDATE '
        'type=VALUES(type), payload=VALUES(payload)'
    )
    with get_conn() as (conn, cur):
        cur.execute(sql, (task_id, task_type, payload_json))


# ============ BasePublisher ============

class BasePublisher:
    """发布器基类"""

    def __init__(self, name: str = 'base'):
        self.name = name
        self._circuit_breaker = CircuitBreaker()
        self._available = True

    @property
    def is_available(self) -> bool:
        """[v3.7.6] 替代原 is_available 属性"""
        return self._available and self._circuit_breaker.get_status()['state'] != 'OPEN'

    def publish(self, payload: Dict[str, Any]) -> bool:
        """发布消息（子类重写）"""
        logger.debug(f'[{self.name}] publish: {payload}')
        return True

    def recall(self, target_id: str) -> bool:
        """撤回消息（子类重写）"""
        logger.debug(f'[{self.name}] recall: {target_id}')
        return True

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """[v3.7.6] 获取熔断器状态"""
        return self._circuit_breaker.get_status()


# ============ 具体 Publisher 实现 ============

class ReportPublisher(BasePublisher):
    """报工发布器（替代 publish_report_task）"""

    def __init__(self):
        super().__init__(name='report')

    def publish(self, payload: Dict[str, Any]) -> bool:
        """发布报工任务

        Args:
            payload: 包含 order_no, process_name, quantity 等字段

        Returns:
            True if successful
        """
        try:
            logger.debug(f'[report] publish_report_task: {payload}')
            task_id = payload.get('order_no', 'unknown')
            _store_task(task_id, 'report', payload)
            return True
        except Exception as e:
            logger.exception('[report] publish_report_task failed')
            return False

    # [v3.7.7.1 兼容层] 恢复 desktop_container_integration.py 的旧 API 签名
    # 原因: service 文件还在调用 publish_report_task(order_no=..., process_name=..., ...)
    #       新 publisher.py 只提供 publish(payload)，运行时 AttributeError
    def publish_report_task(self,
                            order_no: str,
                            process_name: str,
                            customer_name: str = '',
                            product_type: str = '',
                            quantity: int = 0,
                            unit: str = '',
                            planned_qty: int = 0,
                            process_status: str = '待开始',
                            operator_id: str = 'OP001',
                            operator_name: str = '',
                            priority: str = 'normal',
                            is_outsource: bool = False,
                            **kwargs) -> Optional[str]:
        """[v3.7.7.1 兼容] 兼容旧 API 签名

        调用方式: publish_report_task(order_no=..., process_name=..., ...)
        """
        payload = {
            'order_no': order_no,
            'process_name': process_name,
            'customer_name': customer_name,
            'product_type': product_type,
            'quantity': quantity,
            'unit': unit,
            'planned_qty': planned_qty,
            'process_status': process_status,
            'operator_id': operator_id,
            'operator_name': operator_name,
            'priority': priority,
            'is_outsource': is_outsource,
            **kwargs,
        }
        if self.publish(payload):
            return order_no
        return None


class MaterialPublisher(BasePublisher):
    """物料发布器（替代 publish_material_task）"""

    def __init__(self):
        super().__init__(name='material')

    def publish(self, payload: Dict[str, Any]) -> bool:
        """发布用料需求"""
        try:
            logger.debug(f'[material] publish_material_task: {payload}')
            task_id = payload.get('order_no', 'unknown')
            _store_task(task_id, 'material', payload)
            return True
        except Exception as e:
            logger.exception('[material] publish_material_task failed')
            return False

    # [v3.7.7.1 兼容层] 恢复 desktop_container_integration.py 的旧 API 签名
    def publish_material_task(self,
                               order_no: str,
                               materials: List[Dict[str, Any]],
                               process_name: str = '',
                               customer_name: str = '',
                               order_id: int = 0,
                               process_id: int = 0,
                               priority: str = 'normal',
                               **kwargs) -> Optional[str]:
        """[v3.7.7.1 兼容] 兼容旧 API 签名"""
        payload = {
            'order_no': order_no,
            'materials': materials,
            'process_name': process_name,
            'customer_name': customer_name,
            'order_id': order_id,
            'process_id': process_id,
            'priority': priority,
            **kwargs,
        }
        if self.publish(payload):
            return order_no
        return None


class QualityPublisher(BasePublisher):
    """[v3.7.6 新增] 质检发布器（替代 publish_quality_task）"""

    def __init__(self):
        super().__init__(name='quality')

    def publish(self, payload: Dict[str, Any]) -> bool:
        """发布质检任务"""
        try:
            logger.debug(f'[quality] publish_quality_task: {payload}')
            task_id = payload.get('order_no', 'unknown')
            _store_task(task_id, 'quality', payload)
            return True
        except Exception as e:
            logger.exception('[quality] publish_quality_task failed')
            return False

    # [v3.7.7.1 兼容层] 恢复 desktop_container_integration.py 的旧 API 签名
    def publish_quality_task(self,
                             order_no: str,
                             customer_name: str = '',
                             product_type: str = '',
                             inspection_type: str = '终检',
                             operator_id: str = 'OP004',
                             operator_name: str = '',
                             priority: str = 'high',
                             **kwargs) -> Optional[str]:
        """[v3.7.7.1 兼容] 兼容旧 API 签名"""
        payload = {
            'order_no': order_no,
            'customer_name': customer_name,
            'product_type': product_type,
            'inspection_type': inspection_type,
            'operator_id': operator_id,
            'operator_name': operator_name,
            'priority': priority,
            **kwargs,
        }
        if self.publish(payload):
            return order_no
        return None


class TaskRecallPublisher(BasePublisher):
    """任务撤回发布器"""

    def __init__(self):
        super().__init__(name='task_recall')

    def recall(self, task_id: str) -> bool:
        """撤回任务（双轨: DB 优先 + 内存 fallback）"""
        logger.info(f'[task_recall] 撤回任务: {task_id}')
        if _USE_DB:
            try:
                from core.db_compat import get_conn
                with get_conn() as (conn, cur):
                    cur.execute(
                        'DELETE FROM dispatch_center_tasks WHERE id=%s',
                        (task_id,)
                    )
                    if cur.rowcount > 0:
                        return True
            except Exception as e:
                logger.error(f'[task_recall] DB 删除失败 task_id={task_id}: {e}')
        with _task_lock:
            if task_id in _task_store:
                del _task_store[task_id]
                return True
            return False


# ============ 任务查询方法（替代 get_all_tasks / get_task_by_id / get_task_count）============

def get_all_tasks() -> List[Dict[str, Any]]:
    """[v3.7.8] 获取所有任务（双轨: DB 或 内存）"""
    if _USE_DB:
        try:
            import json
            from core.db_compat import get_conn
            with get_conn() as (conn, cur):
                cur.execute(
                    'SELECT id, type, payload, created_at, updated_at '
                    'FROM dispatch_center_tasks ORDER BY created_at DESC'
                )
                rows = cur.fetchall()
                result = []
                for row in rows:
                    payload = row[2]
                    if isinstance(payload, (bytes, str)):
                        try:
                            payload = json.loads(payload)
                        except (ValueError, TypeError):
                            pass
                    result.append({
                        'id': row[0],
                        'type': row[1],
                        'payload': payload,
                        'created_at': row[3].isoformat() if row[3] else None,
                        'updated_at': row[4].isoformat() if row[4] else None,
                    })
                return result
        except Exception as e:
            logger.error(f'[publisher] get_all_tasks DB 失败, fallback 内存: {e}')
    with _task_lock:
        return list(_task_store.values())


def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """[v3.7.8] 按 ID 查询任务（双轨: DB 或 内存）"""
    if _USE_DB:
        try:
            import json
            from core.db_compat import get_conn
            with get_conn() as (conn, cur):
                cur.execute(
                    'SELECT id, type, payload, created_at, updated_at '
                    'FROM dispatch_center_tasks WHERE id=%s',
                    (task_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                payload = row[2]
                if isinstance(payload, (bytes, str)):
                    try:
                        payload = json.loads(payload)
                    except (ValueError, TypeError):
                        pass
                return {
                    'id': row[0],
                    'type': row[1],
                    'payload': payload,
                    'created_at': row[3].isoformat() if row[3] else None,
                    'updated_at': row[4].isoformat() if row[4] else None,
                }
        except Exception as e:
            logger.error(f'[publisher] get_task_by_id DB 失败 task_id={task_id}, fallback 内存: {e}')
    with _task_lock:
        return _task_store.get(task_id)


def get_task_count() -> Dict[str, int]:
    """[v3.7.8] 获取任务统计（双轨: DB 或 内存）"""
    if _USE_DB:
        try:
            from core.db_compat import get_conn
            with get_conn() as (conn, cur):
                cur.execute('SELECT COUNT(*) FROM dispatch_center_tasks')
                total = cur.fetchone()[0]
                cur.execute(
                    'SELECT type, COUNT(*) FROM dispatch_center_tasks GROUP BY type'
                )
                by_type = {row[0]: row[1] for row in cur.fetchall()}
                return {'total': total, **by_type}
        except Exception as e:
            logger.error(f'[publisher] get_task_count DB 失败, fallback 内存: {e}')
    with _task_lock:
        total = len(_task_store)
        by_type = {}
        for task in _task_store.values():
            t = task.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
        return {'total': total, **by_type}


# ============ 工厂函数 ============

# 全局单例
_report_publisher: Optional[ReportPublisher] = None
_material_publisher: Optional[MaterialPublisher] = None
_quality_publisher: Optional[QualityPublisher] = None
_task_recall_publisher: Optional[TaskRecallPublisher] = None


def get_publisher(publisher_type: str = 'report') -> BasePublisher:
    """获取发布器

    Args:
        publisher_type: 'report' / 'material' / 'quality' / 'task_recall'

    Returns:
        发布器实例
    """
    global _report_publisher, _material_publisher, _quality_publisher, _task_recall_publisher

    if publisher_type == 'report':
        if _report_publisher is None:
            _report_publisher = ReportPublisher()
        return _report_publisher
    elif publisher_type == 'material':
        if _material_publisher is None:
            _material_publisher = MaterialPublisher()
        return _material_publisher
    elif publisher_type == 'quality':
        if _quality_publisher is None:
            _quality_publisher = QualityPublisher()
        return _quality_publisher
    elif publisher_type == 'task_recall':
        if _task_recall_publisher is None:
            _task_recall_publisher = TaskRecallPublisher()
        return _task_recall_publisher
    else:
        raise ValueError(f'未知 publisher_type: {publisher_type}')


# 兼容旧 API（v3.7.4）
def get_integration():
    """兼容旧 API：返回默认 report publisher

    [v3.7.4 过渡] 此函数将在 v3.7.8 删除，请改用 get_publisher()
    """
    import warnings
    warnings.warn(
        "get_integration() 已废弃，请改用 get_publisher()",
        DeprecationWarning,
        stacklevel=2
    )
    return get_publisher('report')


__all__ = [
    'BasePublisher',
    'ReportPublisher',
    'MaterialPublisher',
    'QualityPublisher',  # v3.7.6 新增
    'TaskRecallPublisher',
    'CircuitBreaker',  # v3.7.6 新增
    'get_publisher',
    'get_integration',  # 兼容
    'get_all_tasks',  # v3.7.6 新增
    'get_task_by_id',  # v3.7.6 新增
    'get_task_count',  # v3.7.6 新增
]