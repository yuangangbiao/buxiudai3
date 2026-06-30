# -*- coding: utf-8 -*-
"""
常量定义文件
包含系统中所有硬编码的常量值
"""
from enum import Enum


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "待确认"
    CONFIRMED = "待排产"
    PENDING_PUBLISH = "待发布"
    PUBLISHED = "已发布"
    SCHEDULED = "已排产"
    PRODUCTION = "生产中"
    QC = "质检中"
    FINISHED = "已完成"
    PENDING_SHIP = "待发货"
    SHIPPED = "已发货"
    CANCELLED = "已取消"


class ProductionStatus(Enum):
    """生产状态枚举"""
    PENDING = "待开始"
    IN_PROGRESS = "生产中"
    COMPLETED = "已完成"
    PENDING_PUBLISH = "待发布"
    SCHEDULED = "已排产"
    PAUSED = "已暂停"


class ProcessStatus(Enum):
    """工序状态枚举"""
    PENDING = "待开始"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    OUTSOURCE = "外协"


class QualityStatus(Enum):
    """质检状态枚举"""
    PENDING = "待质检"
    IN_PROGRESS = "质检中"
    PASSED = "已通过"
    FAILED = "未通过"


class ShipmentStatus(Enum):
    """发货状态枚举"""
    PENDING = "待发货"
    COMPLETED = "已发货"
    RECEIVED = "已收货"


class FinishedGoodsStatus(Enum):
    """成品库存状态枚举"""
    IN_STOCK = "在库"
    OUTBOUND = "已出库"


class InventoryStatus(Enum):
    """库存状态枚举"""
    IN_STOCK = "在库"
    OUT_OF_STOCK = "已出库"


class PriorityLevel(Enum):
    """优先级枚举"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


# 状态映射
STATUS_MAPPING = {
    "order": {
        "PENDING": OrderStatus.PENDING.value,
        "CONFIRMED": OrderStatus.CONFIRMED.value,
        "PENDING_PUBLISH": OrderStatus.PENDING_PUBLISH.value,
        "PUBLISHED": OrderStatus.PUBLISHED.value,
        "SCHEDULED": OrderStatus.SCHEDULED.value,
        "PRODUCTION": OrderStatus.PRODUCTION.value,
        "QC": OrderStatus.QC.value,
        "FINISHED": OrderStatus.FINISHED.value,
        "PENDING_SHIP": OrderStatus.PENDING_SHIP.value,
        "SHIPPED": OrderStatus.SHIPPED.value,
        "CANCELLED": OrderStatus.CANCELLED.value
    },
    "production": {
        "PENDING": ProductionStatus.PENDING.value,
        "IN_PROGRESS": ProductionStatus.IN_PROGRESS.value,
        "COMPLETED": ProductionStatus.COMPLETED.value
    },
    "process": {
        "PENDING": ProcessStatus.PENDING.value,
        "IN_PROGRESS": ProcessStatus.IN_PROGRESS.value,
        "COMPLETED": ProcessStatus.COMPLETED.value,
        "OUTSOURCE": ProcessStatus.OUTSOURCE.value
    },
    "quality": {
        "PENDING": QualityStatus.PENDING.value,
        "IN_PROGRESS": QualityStatus.IN_PROGRESS.value,
        "PASSED": QualityStatus.PASSED.value,
        "FAILED": QualityStatus.FAILED.value
    },
    "shipment": {
        "PENDING": ShipmentStatus.PENDING.value,
        "COMPLETED": ShipmentStatus.COMPLETED.value
    },
    "finished_goods": {
        "IN_STOCK": FinishedGoodsStatus.IN_STOCK.value,
        "OUTBOUND": FinishedGoodsStatus.OUTBOUND.value
    },
    "inventory": {
        "IN_STOCK": InventoryStatus.IN_STOCK.value,
        "OUT_OF_STOCK": InventoryStatus.OUT_OF_STOCK.value
    }
}

# 优先级映射
PRIORITY_MAPPING = {
    "HIGH": PriorityLevel.HIGH.value,
    "MEDIUM": PriorityLevel.MEDIUM.value,
    "LOW": PriorityLevel.LOW.value
}

# 优先级数值映射
PRIORITY_VALUE_MAPPING = {
    "高": 1,
    "中": 5,
    "低": 10
}

# 单位常量
UNITS = {
    "length": "米",
    "width": "mm",
    "diameter": "mm",
    "area": "平方米",
    "weight": "公斤",
    "price": "元/米",
    "total_price": "元"
}

# 模板类型
TEMPLATE_TYPES = {
    "ORDER": "订单模板",
    "MATERIAL": "物料模板",
    "PROCESS": "工序模板",
    "MATERIAL_RULES": "物料规则模板"
}

# 模块名称
MODULES = {
    "ORDERS": "订单管理",
    "PRODUCTION": "生产排单",
    "PROCESS": "工序管理",
    "QUALITY": "质检管理",
    "INVENTORY": "库存管理",
    "SHIPMENT": "发货管理",
    "MATERIAL_PREP": "物料准备"
}

# 颜色标签
COLOR_TAGS = {
    "PENDING": "pending",
    "CONFIRMED": "confirmed",
    "IN_PROGRESS": "doing",
    "COMPLETED": "done",
    "CANCELLED": "cancelled",
    "FAILED": "failed"
}

# 计量单位选项
MEASUREMENT_UNITS = [
    "米", "平方米", "公斤", "个", "卷", "套", "批"
]

# 生产工艺选项
PRODUCTION_PROCESSES = [
    "编织", "焊接", "冲压", "切割", "组装", "电镀", "喷涂"
]
