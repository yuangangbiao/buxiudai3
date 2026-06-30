# -*- coding: utf-8 -*-
"""
枚举定义模块 - 业务领域枚举类型

提供所有业务枚举类，每个枚举类包含 values() 类方法返回所有值列表，
以及 from_string() 类方法实现安全字符串转换。
"""

from enum import Enum


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None


class ProductionStatus(Enum):
    """生产状态枚举"""
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    DISPATCHED = "DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    REPORTED = "REPORTED"
    QC_PASSED = "QC_PASSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None


class ProcessStatus(Enum):
    """工序状态枚举"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None


class QualityResult(Enum):
    """质检结果枚举"""
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None


class InventoryChange(Enum):
    """库存变更类型枚举"""
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None


class Priority(Enum):
    """优先级枚举"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None


class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "PENDING"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"

    @classmethod
    def values(cls):
        """返回所有枚举值的列表"""
        return [item.value for item in cls]

    @classmethod
    def from_string(cls, s):
        """安全地将字符串转换为枚举值，失败时返回 None"""
        if not s:
            return None
        try:
            return cls(s.upper())
        except (ValueError, AttributeError):
            return None
