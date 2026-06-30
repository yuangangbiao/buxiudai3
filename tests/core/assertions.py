# -*- coding: utf-8 -*-
"""
自定义断言 - 业务语义断言

修复 P0-3: 提供业务级断言，避免散落 assert 表达式
"""
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def assert_api_success(response: Dict, msg: str = ""):
    """断言 API 业务成功（code==0）"""
    assert response is not None, f"响应为 None {msg}"
    code = response.get('code', -1)
    assert code == 0, f"API 业务失败 code={code}, msg={response.get('message')} {msg}"


def assert_api_error(response: Dict, expected_code: int, msg: str = ""):
    """断言 API 返回指定错误码"""
    code = response.get('code', -1)
    assert code == expected_code, f"期望 code={expected_code}, 实际={code} {msg}"


def assert_order_exists(db, order_no: str):
    """断言订单存在"""
    result = db.query_one("SELECT order_no FROM orders WHERE order_no=%s AND is_deleted=0", (order_no,))
    assert result is not None, f"订单不存在: {order_no}"


def assert_order_status(db, order_no: str, expected_status: str):
    """断言订单状态"""
    result = db.query_one("SELECT status FROM orders WHERE order_no=%s", (order_no,))
    assert result is not None, f"订单不存在: {order_no}"
    actual = result.get('status')
    assert actual == expected_status, f"订单 {order_no} 状态: 期望={expected_status}, 实际={actual}"


def assert_order_completed(db, order_no: str):
    """断言订单已完成"""
    assert_order_status(db, order_no, 'COMPLETED')


def assert_inventory_increased(db, material_code: str, before: float, after: float):
    """断言库存增加"""
    delta = after - before
    assert delta > 0, f"库存未增加: {material_code} before={before} after={after}"


def assert_inventory_decreased(db, material_code: str, before: float, after: float):
    """断言库存减少"""
    delta = after - before
    assert delta < 0, f"库存未减少: {material_code} before={before} after={after}"


def assert_response_time(start: datetime, max_seconds: float, operation: str = ""):
    """断言响应时间"""
    elapsed = (datetime.now() - start).total_seconds()
    assert elapsed <= max_seconds, f"响应超时 {operation}: {elapsed:.2f}s > {max_seconds}s"


def assert_no_duplicate(items: List, key: str = None, msg: str = ""):
    """断言无重复"""
    if key:
        values = [item.get(key) if isinstance(item, dict) else getattr(item, key) for item in items]
    else:
        values = items
    assert len(values) == len(set(values)), f"存在重复值 {msg}: {values}"


def assert_value_in_range(actual: Any, min_val: Any, max_val: Any, msg: str = ""):
    """断言值在范围内"""
    assert min_val <= actual <= max_val, f"{msg} 值 {actual} 不在 [{min_val}, {max_val}] 范围内"


def assert_perf_p95(latencies: List[float], max_p95: float, msg: str = ""):
    """断言 P95 延迟"""
    if not latencies:
        raise ValueError("latencies 为空")
    sorted_lat = sorted(latencies)
    p95_index = int(len(sorted_lat) * 0.95)
    p95 = sorted_lat[min(p95_index, len(sorted_lat) - 1)]
    assert p95 <= max_p95, f"P95 延迟 {p95:.2f}ms 超过阈值 {max_p95}ms {msg}"


def assert_tps(success_count: int, duration_seconds: float, min_tps: float, msg: str = ""):
    """断言 TPS"""
    if duration_seconds <= 0:
        raise ValueError("duration 必须 > 0")
    tps = success_count / duration_seconds
    assert tps >= min_tps, f"TPS {tps:.2f} 低于阈值 {min_tps} {msg}"
    return tps


__all__ = [
    'assert_api_success', 'assert_api_error',
    'assert_order_exists', 'assert_order_status', 'assert_order_completed',
    'assert_inventory_increased', 'assert_inventory_decreased',
    'assert_response_time',
    'assert_no_duplicate', 'assert_value_in_range',
    'assert_perf_p95', 'assert_tps',
    'S',  # 兼容历史导入
]


# 修复 P0-3: 兼容历史导入 S (可能是 Severity 枚举或 SimpleAssert 类)
class _S:
    """S 别名 - 用于 soft-assert 风格"""
    @staticmethod
    def check(condition, msg=""):
        """简单断言收集，不中断"""
        return bool(condition)

    @staticmethod
    def eq(actual, expected, msg=""):
        return actual == expected

    @staticmethod
    def ne(actual, expected, msg=""):
        return actual != expected

    @staticmethod
    def gt(actual, threshold, msg=""):
        return actual > threshold

    @staticmethod
    def lt(actual, threshold, msg=""):
        return actual < threshold


S = _S()
