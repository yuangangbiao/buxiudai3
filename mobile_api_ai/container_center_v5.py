# -*- coding: utf-8 -*-
"""
容器端数据中转中心 v5.0
集成存储抽象层，支持SQLite/Redis无缝切换
"""
import uuid
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

from core.config import DB_CONNECT_TIMEOUT
from storage_layer import create_storage, BaseStorage, StorageType

# ──────────────────────────────────────────────
# data_type 严格分类契约 v1.0 (RE-006 引入)
# 容器端写入新 data_type,旧值仅在 LEGACY 兼容读取时使用
# ──────────────────────────────────────────────
NEW_DATA_TYPE_FOR_COLLECT = {
    'report':    'process_report',     # 工序报工
    'quality':   'quality_task',       # 质检
    'material':  'material_pickup',    # 领料
    'approval':  'approval',           # 审批
    'repair':    'equipment_repair',   # 报修
    'outsource': 'outsource_task',     # 外协
    'purchase':  'material_buy',       # 采购
}

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 模块级常量（禁止硬编码）
# ──────────────────────────────────────────────
TASK_ID_LENGTH = int(os.getenv('TASK_ID_LENGTH', '8'))
DEFAULT_SOURCE = os.getenv('DEFAULT_SOURCE', 'desktop')
DEFAULT_PRIORITY = os.getenv('DEFAULT_PRIORITY', 'normal')
DEFAULT_ORDER_NO = os.getenv('DEFAULT_ORDER_NO', 'UNKNOWN')
DEFAULT_QUERY_LIMIT = int(os.getenv('DEFAULT_QUERY_LIMIT', '100'))
POOL_STATUS_LIMIT = int(os.getenv('POOL_STATUS_LIMIT', '1000'))
APPROVAL_TITLE_MAX_LEN = int(os.getenv('APPROVAL_TITLE_MAX_LEN', '20'))
DEFAULT_DB_PATH = None  # SQLite 已废弃，不再需要路径

# MySQL 同步配置（中转模式：容器中心负责同步到 MySQL）
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT

STATUS_KEY_TO_MYSQL = {
    'published': '已发布',
    'scheduled': '已排产',
    'confirmed': '已排产',
    'in_production': '生产中',
    'reported': '生产中',
    'qc_passed': '生产中',
    'report_complete': '报工完成',
    'completed': '已完成',
}
DEFAULT_STORAGE_TYPE = os.getenv('CONTAINER_STORAGE_TYPE', 'mysql')
DEMO_DB_PATH = os.getenv('DEMO_DB_PATH', 'demo_v5.db')
DISPATCH_RULE_DEFAULT = os.getenv('DISPATCH_RULE_DEFAULT', 'operator_direct_assign')
DISPATCH_REASON_DEFAULT = os.getenv('DISPATCH_REASON_DEFAULT', '直接指定操作员')

PURCHASE_OPERATORS = os.getenv('PURCHASE_OPERATORS', '').split(',') if os.getenv('PURCHASE_OPERATORS') else []

try:
    from services.notifier import wechat_notifier
    from container_center.desktop_callback import desktop_callback_manager
    WECHAT_NOTIFIER_AVAILABLE = True
    DESKTOP_CALLBACK_AVAILABLE = True
except ImportError:
    WECHAT_NOTIFIER_AVAILABLE = False
    DESKTOP_CALLBACK_AVAILABLE = False
    wechat_notifier = None
    desktop_callback_manager = None

try:
    from services.warehouse_client import get_warehouse_client, WarehouseClient
    WAREHOUSE_CLIENT_AVAILABLE = True
except ImportError:
    WAREHOUSE_CLIENT_AVAILABLE = False
    get_warehouse_client = None
    WarehouseClient = None


class DataType(Enum):
    """数据类型"""
    REPORT = 'report'
    QUALITY = 'quality'
    MATERIAL = 'material'
    APPROVAL = 'approval'
    ORDER = 'order'
    PROCESS = 'process'
    COST = 'cost'
    REPAIR = 'repair'        # 修补 T5 (D3.1)
    OUTSOURCE = 'outsource'  # 修补 T5 (D3.1)


# 修补 T5 (D3.1 决策): 6 种 data_type → 5 种 flow_type 映射表
DATA_TYPE_TO_FLOW_TYPE = {
    DataType.REPORT.value: 'production',
    DataType.QUALITY.value: 'quality',
    DataType.MATERIAL.value: 'material_purchase',
    DataType.APPROVAL.value: 'production',
    DataType.ORDER.value: 'production',
    DataType.PROCESS.value: 'production',
    DataType.COST.value: 'production',
    DataType.REPAIR.value: 'repair',
    DataType.OUTSOURCE.value: 'outsource',
    # 字符串 fallback (老调用方可能不传 enum)
    'repair': 'repair',
    'outsource': 'outsource',
}


def map_data_type_to_flow_type(data_type: str) -> str:
    """D3.1 6→5 映射函数 (模块级, 纯函数, 易测)

    Args:
        data_type: data_type 字符串 (如 'report'/'quality'/'material')

    Returns:
        flow_type 字符串 ('production'/'quality'/'material_purchase'/'repair'/'outsource')
        未知或空 → 兜底 'production'
    """
    if not data_type:
        return 'production'
    return DATA_TYPE_TO_FLOW_TYPE.get(data_type.lower(), 'production')


class DataStatus(Enum):
    """数据状态"""
    PENDING = 'pending'
    DISTRIBUTED = 'distributed'
    ACKNOWLEDGED = 'acknowledged'  # 已确认
    COMPLETED = 'completed'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


class DataPackage:
    """数据包"""

    def __init__(self, data_type: str, title: str, content: Dict,
                 source: str = DEFAULT_SOURCE, priority: str = DEFAULT_PRIORITY,
                 flow_type: str = ''):  # 修补 T5 (F5.1)
        self.id = str(uuid.uuid4())[:TASK_ID_LENGTH].upper()
        self.data_type = data_type
        self.title = title
        self.content = content
        self.source = source
        self.priority = priority
        self.flow_type = flow_type  # 修补 T5 (F5.1) - 与 T1 DDL DEFAULT '' 对齐
        self.status = DataStatus.PENDING.value

        self.created_at = datetime.now()
        self.distributed_at: Optional[datetime] = None
        self.acknowledged_at: Optional[datetime] = None  # 确认时间
        self.completed_at: Optional[datetime] = None
        self.last_reminded_at: Optional[datetime] = None  # 最后提醒时间

        self.target_operator: Optional[str] = None
        self.target_device: Optional[str] = None
        self.is_public: bool = False  # 全员派发

        self.tags: List[str] = []
        self.related_order: Optional[str] = None
        self.related_process: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'data_type': self.data_type,
            'flow_type': self.flow_type,  # 修补 T5 (F5.1)
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'distributed_at': self.distributed_at.isoformat() if self.distributed_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_reminded_at': self.last_reminded_at.isoformat() if self.last_reminded_at else None,
            'target_operator': self.target_operator,
            'target_device': self.target_device,
            'is_public': self.is_public,
            'tags': self.tags,
            'related_order': self.related_order,
            'related_process': self.related_process
        }

    @staticmethod
    def from_dict(data: Dict) -> 'DataPackage':
        pkg = DataPackage(
            data_type=data.get('data_type', 'other'),
            title=data.get('title', ''),
            content=data.get('content', {}),
            source=data.get('source', DEFAULT_SOURCE),
            priority=data.get('priority', DEFAULT_PRIORITY)
        )
        pkg.id = data.get('id', pkg.id)
        pkg.status = data.get('status', DataStatus.PENDING.value)
        
        # 时间字段
        created_at = data.get('created_at')
        pkg.created_at = datetime.fromisoformat(created_at) if created_at and isinstance(created_at, str) else (created_at if isinstance(created_at, datetime) else datetime.now())
        
        distributed_at = data.get('distributed_at')
        pkg.distributed_at = datetime.fromisoformat(distributed_at) if distributed_at else None
        
        acknowledged_at = data.get('acknowledged_at')
        pkg.acknowledged_at = datetime.fromisoformat(acknowledged_at) if acknowledged_at else None
        
        completed_at = data.get('completed_at')
        pkg.completed_at = datetime.fromisoformat(completed_at) if completed_at else None
        
        last_reminded_at = data.get('last_reminded_at')
        pkg.last_reminded_at = datetime.fromisoformat(last_reminded_at) if last_reminded_at else None
        pkg.target_operator = data.get('target_operator')
        pkg.target_device = data.get('target_device')
        pkg.is_public = bool(data.get('is_public', False))
        pkg.tags = data.get('tags', [])
        pkg.related_order = data.get('related_order')
        pkg.related_process = data.get('related_process')

        if data.get('created_at'):
            pkg.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('distributed_at'):
            pkg.distributed_at = datetime.fromisoformat(data['distributed_at'])
        if data.get('completed_at'):
            pkg.completed_at = datetime.fromisoformat(data['completed_at'])

        return pkg


class DataCollector:
    """数据收集器"""

    def __init__(self, storage: BaseStorage, center=None):
        self.storage = storage
        self.center = center
        self.handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        self.handlers['report'] = self._handle_report
        self.handlers['quality'] = self._handle_quality
        self.handlers['material'] = self._handle_material
        self.handlers['approval'] = self._handle_approval
        self.handlers['cost'] = self._handle_cost
        self.handlers['repair'] = self._handle_repair        # 修补 T5 (D3.1)
        self.handlers['outsource'] = self._handle_outsource  # 修补 T5 (D3.1)

    def collect(self, data_type: str, title: str, content: Dict,
               source: str = DEFAULT_SOURCE, **kwargs) -> DataPackage:
        """收集数据"""
        # 修补 T5 (F5.3): flow_type 入参优先, 按 data_type 推断兜底
        # D3.1 6→5 映射: report/approval/order/process/cost → production
        #                  quality → quality
        #                  material → material_purchase
        #                  repair → repair
        #                  outsource → outsource
        #                  未知 → production
        explicit_flow_type = kwargs.get('flow_type', '')
        effective_flow_type = explicit_flow_type or map_data_type_to_flow_type(data_type)
        pkg = DataPackage(
            data_type=data_type,
            title=title,
            content=content,
            source=source,
            priority=kwargs.get('priority', DEFAULT_PRIORITY),
            flow_type=effective_flow_type,  # 修补 T5 (F5.3)
        )

        pkg.target_operator = kwargs.get('operator_id')
        pkg.target_device = kwargs.get('device_id')
        pkg.is_public = bool(kwargs.get('is_public', False))
        pkg.related_order = kwargs.get('order_no') or kwargs.get('related_order') or kwargs.get('order_no') or ''
        pkg.related_process = kwargs.get('process_name') or kwargs.get('related_process')
        pkg.tags = kwargs.get('tags', [])

        self.storage.save_package(pkg.to_dict())
        self.storage.log_sync('COLLECT', pkg.id, f'收集数据: {data_type}')

        # 记录数据流转 - 进入容器
        start_time = time.time()
        self.storage.save_data_flow_log({
            'flow_id': pkg.id,
            'order_no': pkg.related_order,
            'process_name': pkg.related_process,
            'data_type': data_type,
            'source': source,
            'event_type': 'receive',
            'event_name': '数据进入容器',
            'event_detail': f'数据类型: {data_type}, 标题: {title}',
            'from_status': None,
            'to_status': 'pending',
            'target_operator': pkg.target_operator,
            'created_at': datetime.now().isoformat(),
            'duration_ms': int((time.time() - start_time) * 1000)
        })

        handler = self.handlers.get(data_type)
        if handler:
            handler(pkg)
        
        # 数据收集完成后通知桌面端
        if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
            try:
                desktop_callback_manager.notify_data_collected(
                    data_type=data_type,
                    package_id=pkg.id,
                    related_order=pkg.related_order
                )
            except Exception as e:
                logger.warning(f"[收集] 桌面端回调失败: {e}")

        return pkg

    def _handle_report(self, pkg: DataPackage):
        logger.info(f"[收集] 报工数据: {pkg.title}")

    def _handle_quality(self, pkg: DataPackage):
        logger.info(f"[收集] 质检数据: {pkg.title}")

    def _handle_repair(self, pkg: DataPackage):
        """设备报修数据收集(RE-007 修复 T5 D3.1)"""
        logger.info(f"[收集] 报修数据: {pkg.title}")

    def _handle_outsource(self, pkg: DataPackage):
        """外协数据收集(RE-007 修复 T5 D3.1)"""
        logger.info(f"[收集] 外协数据: {pkg.title}")

    def _handle_material(self, pkg: DataPackage):
        logger.info(f"[收集] 物料数据: {pkg.title}")

        material_name = pkg.content.get('material_name', '')
        required_qty = pkg.content.get('quantity', 0)
        unit = pkg.content.get('unit', '件')
        order_no = pkg.related_order or ''

        warehouse_available = WAREHOUSE_CLIENT_AVAILABLE and get_warehouse_client is not None
        warehouse_enabled = False
        stock_result = None

        if warehouse_available:
            warehouse = get_warehouse_client()
            warehouse_enabled = warehouse.is_enabled()
            if warehouse_enabled:
                stock_result = warehouse.check_stock(material_name, required_qty, unit)

        if stock_result is None:
            stock_result = {
                'sufficient': False,
                'current_stock': 0,
                'required': required_qty,
                'shortage': required_qty,
                'message': '仓库接口未配置或不可用，物料默认为0，需人工填写',
                'warehouse_available': False
            }

        if not stock_result.get('warehouse_available'):
            logger.warning(f"[物料] ⚠️ 仓库不可用，物料默认为0，需人工填写: {material_name} 需求{required_qty}{unit}")
            if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
                desktop_callback_manager.enqueue_callback('material_stock_insufficient', {
                    'package_id': pkg.id,
                    'order_no': order_no,
                    'material_name': material_name,
                    'required_qty': required_qty,
                    'current_stock': 0,
                    'shortage': required_qty,
                    'unit': unit,
                    'manual_entry_required': True
                })
            return

        if stock_result.get('sufficient'):
            logger.info(f"[物料] ✅ 库存充足: {material_name} {required_qty}{unit}，当前库存{stock_result.get('current_stock')}{unit}")
            if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
                desktop_callback_manager.enqueue_callback('material_stock_sufficient', {
                    'package_id': pkg.id,
                    'order_no': order_no,
                    'material_name': material_name,
                    'required_qty': required_qty,
                    'current_stock': stock_result.get('current_stock'),
                    'unit': unit
                })
        else:
            current_stock = stock_result.get('current_stock', 0)
            shortage = stock_result.get('shortage', required_qty - current_stock)
            logger.warning(f"[物料] ⚠️ 库存不足: {material_name} 需求{required_qty}{unit}，当前{current_stock}{unit}，缺少{shortage}{unit}")

            if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
                desktop_callback_manager.enqueue_callback('material_stock_insufficient', {
                    'package_id': pkg.id,
                    'order_no': order_no,
                    'material_name': material_name,
                    'required_qty': required_qty,
                    'current_stock': current_stock,
                    'shortage': shortage,
                    'unit': unit
                })

            self._create_purchase_task(pkg, material_name, shortage, unit, current_stock)

            # 物料短缺微信通知
            try:
                from template_engine import _render_template, _send_wechat_message
                msg = _render_template('tmpl_material_shortage', {
                    '物料名称': material_name,
                    '订单号': order_no,
                    '数量': shortage,
                    '单位': unit,
                })
                _send_wechat_message(msg, 'markdown')
            except Exception as e:
                logger.warning(f'[物料] 短缺通知发送失败: {e}')

    def _create_purchase_task(self, material_pkg: DataPackage,
                            material_name: str, shortage: float,
                            unit: str, current_stock: float):
        """创建采购任务并分发给采购人员"""
        order_no = material_pkg.related_order or DEFAULT_ORDER_NO

        if not self.center:
            logger.warning(f'[物料] ⚠️ 容器中心未关联，跳过采购任务创建: {material_name}')
            return

        purchase_pkg = self.center.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['purchase'],
            title=f'采购:{material_name}(缺{shortage}{unit})',
            content={
                'material_name': material_name,
                'required_qty': shortage,
                'unit': unit,
                'order_no': order_no,
                'current_stock': current_stock,
                'purpose': f'订单{order_no}备料缺少物料'
            },
            order_no=order_no,
            priority='high',
            tags=['采购', '物料短缺']
        )

        for operator_id in PURCHASE_OPERATORS:
            self.center.distributor.distribute(purchase_pkg.id, operator_id)

        logger.info(f"[物料] ✅ 采购任务已创建并分发给 {PURCHASE_OPERATORS}: {material_name} x{shortage}{unit}")

        if WECHAT_NOTIFIER_AVAILABLE and wechat_notifier:
            wechat_notifier.notify_low_stock({
                'material_name': material_name,
                'current_stock': current_stock,
                'shortage': shortage,
                'unit': unit,
                'order_no': order_no
            })

    def _handle_approval(self, pkg: DataPackage):
        logger.info(f"[收集] 审批数据: {pkg.title}")

    def _handle_cost(self, pkg: DataPackage):
        logger.info(f"[收集] 成本数据: {pkg.title}")
        order_no = pkg.related_order or pkg.content.get('order_no', '')
        if not order_no:
            logger.warning("[成本] 缺少订单号，跳过核算")
            return

        try:
            from services.cost_service import CostService
            from storage_layer import StorageFactory, StorageType, resolve_storage_type

            default_st = resolve_storage_type()
            storage = StorageFactory.get_instance(default_st)
            if not storage:
                storage = StorageFactory.create(default_st)

            service = CostService(storage)

            action = pkg.content.get('action', 'calculate')
            if action == 'calculate':
                result = service.calculate_order_cost(
                    order_no,
                    customer_name=pkg.content.get('customer_name', ''),
                    product_name=pkg.content.get('product_name', ''),
                    quantity=float(pkg.content.get('quantity', 0)),
                    unit=pkg.content.get('unit', '件')
                )
                logger.info(f"[成本] 订单 {order_no} 核算完成: 总成本={result['total_cost']}, 利润={result['profit']}")

            elif action == 'add_detail':
                service.add_cost_detail({
                    'order_no': order_no,
                    'cost_type': pkg.content.get('cost_type', 'other'),
                    'source_type': pkg.content.get('source_type', 'auto_cost'),
                    'source_id': pkg.content.get('source_id', ''),
                    'description': pkg.content.get('description', ''),
                    'quantity': float(pkg.content.get('quantity', 0)),
                    'unit': pkg.content.get('unit', ''),
                    'unit_price': float(pkg.content.get('unit_price', 0)),
                    'amount': float(pkg.content.get('amount', 0)),
                    'operator_id': pkg.content.get('operator_id', 'system')
                })
                logger.info(f"[成本] 订单 {order_no} 成本明细已添加")

            elif action == 'set_revenue':
                service.set_revenue(order_no, float(pkg.content.get('revenue', 0)))
                logger.info(f"[成本] 订单 {order_no} 收入已设置")

            if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
                desktop_callback_manager.enqueue_callback('order_cost_updated', {
                    'order_no': order_no,
                    'action': action,
                    'package_id': pkg.id
                })

        except Exception as e:
            logger.error(f"[成本] 处理失败 (订单 {order_no}): {e}")


class DataDistributor:
    """数据分发器"""

    def __init__(self, storage: BaseStorage):
        self.storage = storage
        self.push_callbacks: List[Callable] = []

    def add_push_callback(self, callback: Callable):
        self.push_callbacks.append(callback)

    def distribute(self, package_id: str, operator_id: str = None, device_id: str = None) -> bool:
        """分发数据包

        Args:
            package_id: 数据包ID
            operator_id: 目标操作员ID（可选）
            device_id: 目标设备编号（可选，用于设备运转监测）
        """
        start_time = time.time()

        pkg_dict = self.storage.get_package(package_id)
        if not pkg_dict:
            return False

        if pkg_dict.get('status') != DataStatus.PENDING.value:
            return False

        pkg = DataPackage.from_dict(pkg_dict)
        old_status = pkg.status
        pkg.status = DataStatus.DISTRIBUTED.value
        pkg.distributed_at = datetime.now()

        if operator_id:
            pkg.target_operator = operator_id
        if device_id:
            pkg.target_device = device_id

        if pkg.data_type == 'repair' and not pkg.target_operator:
            from container_config import container_config
            cat_id = pkg.content.get('category_id', '') if isinstance(pkg.content, dict) else ''
            cat = container_config.get_repair_category(cat_id)
            if cat:
                pkg.target_operator = cat.assigned_operator_id
                logger.info(f"[分发] 报修路由到指定负责人: {pkg.target_operator} ({cat.name})")

        # 修补 T5 (F5.4): flow_type 路由 (与 data_type 路由并存, flow_type 优先)
        # 5 种 flow_type 分支:
        #   production    → 走 production 通用流程 (无需特殊处理)
        #   quality       → 走 quality 流程 (质检部默认)
        #   material_purchase → 走 material 流程 (采购部默认)
        #   outsource     → 走 outsource 流程 (外协厂默认, 由 content.outsource_factory 决定)
        #   repair        → 走 repair 流程 (已由 L502-508 处理)
        effective_flow_type = pkg.flow_type or map_data_type_to_flow_type(pkg.data_type)
        if effective_flow_type == 'outsource' and not pkg.target_operator:
            # 外协任务: 从 content 读取外协厂, 若无则标记为待分配
            outsource_factory = pkg.content.get('outsource_factory', '') if isinstance(pkg.content, dict) else ''
            if outsource_factory:
                pkg.target_operator = outsource_factory
                logger.info(f"[分发] 外协任务路由到外协厂: {pkg.target_operator}")
            else:
                logger.info(f"[分发] 外协任务待分配 (无外协厂指定)")

        # 检查是否已存在同工单同工序的调度指令，防重复发布
        existing = self.storage.get_dispatch_commands_by_order_process(
            pkg.related_order, pkg.related_process
        ) if pkg.related_order and pkg.related_process else []
        if existing:
            command_id = existing[0]['command_id']
        else:
            command_id = str(uuid.uuid4())[:8].upper()

        dispatch_command = {
            'command_id': command_id,
            'command_type': 'dispatch',
            'target_type': 'operator',
            'target_id': pkg.target_operator,
            'operator_id': pkg.target_operator,
            'device_id': pkg.target_device,
            'order_no': pkg.related_order,
            'process_name': pkg.related_process,
            'command_data': {
                'package_id': pkg.id,
                'data_type': pkg.data_type,
                'title': pkg.title
            },
            'priority': pkg.priority,
            'status': 'completed',
            'created_at': datetime.now().isoformat(),
            'executed_at': datetime.now().isoformat(),
            'result': 'success'
        }
        self.storage.save_dispatch_command(dispatch_command)

        self.storage.save_package(pkg.to_dict())
        device_info = f', 设备: {pkg.target_device}' if pkg.target_device else ''
        self.storage.log_sync('DISTRIBUTE', pkg.id, f'分发给: {pkg.target_operator}{device_info}')

        # 记录数据流转 - 分发
        self.storage.save_data_flow_log({
            'flow_id': pkg.id,
            'order_no': pkg.related_order,
            'process_name': pkg.related_process,
            'data_type': pkg.data_type,
            'source': pkg.source,
            'event_type': 'distribute',
            'event_name': '数据分配',
            'event_detail': f'分配给: {pkg.target_operator}',
            'from_status': old_status,
            'to_status': 'distributed',
            'command_id': command_id,
            'dispatch_rule': DISPATCH_RULE_DEFAULT,
            'target_operator': pkg.target_operator,
            'operator_selection_reason': DISPATCH_REASON_DEFAULT,
            'created_at': datetime.now().isoformat(),
            'duration_ms': int((time.time() - start_time) * 1000)
        })

        for callback in self.push_callbacks:
            try:
                callback(pkg)
            except Exception as e:
                logger.error(f"推送回调失败: {e}")

        return True

    def distribute_batch(self, package_ids: List[str]) -> int:
        count = 0
        for pid in package_ids:
            if self.distribute(pid):
                count += 1
        return count

    def auto_distribute_pending(self, operator_id: str = None) -> int:
        pending = self.storage.get_packages(status=DataStatus.PENDING.value)

        if operator_id:
            pending = [p for p in pending if p.get('target_operator') == operator_id or not p.get('target_operator')]

        count = 0
        for pkg_dict in pending:
            if self.distribute(pkg_dict.get('id')):
                count += 1

        return count


class DataAnalyzer:
    """数据分析器"""

    def __init__(self, storage: BaseStorage):
        self.storage = storage
        self.analyzer_rules: Dict[str, Callable] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        self.analyzer_rules['report'] = self._analyze_report
        self.analyzer_rules['quality'] = self._analyze_quality
        self.analyzer_rules['material'] = self._analyze_material
        self.analyzer_rules['approval'] = self._analyze_approval

    def receive_return(self, package_id: str, return_data: Dict) -> Dict:
        """接收回传数据并分析"""
        pkg_dict = self.storage.get_package(package_id)
        if not pkg_dict:
            return {'success': False, 'error': '数据包不存在'}

        pkg = DataPackage.from_dict(pkg_dict)
        pkg.status = DataStatus.COMPLETED.value
        pkg.completed_at = datetime.now()
        self.storage.save_package(pkg.to_dict())

        analyzer = self.analyzer_rules.get(pkg.data_type)
        if analyzer:
            analyzed = analyzer(pkg, return_data)
        else:
            analyzed = {'success': True, 'data': return_data}

        write_back_cmd = self._generate_write_back_command(pkg, return_data, analyzed)

        self.storage.save_return_record(package_id, return_data, analyzed, write_back_cmd)
        self.storage.log_sync('RETURN', package_id, f'回传完成: {analyzed.get("message", "")}')

        return {
            'success': True,
            'package_id': package_id,
            'analyzed': analyzed,
            'write_back_cmd': write_back_cmd
        }

    def _analyze_report(self, pkg: DataPackage, return_data: Dict) -> Dict:
        completed_qty = return_data.get('completed_qty', 0)
        status = return_data.get('status', '进行中')
        actual_qty = pkg.content.get('actual_qty', 0) if pkg.content else 0

        content_order_no = pkg.content.get('order_no', pkg.related_order)
        return {
            'success': True,
            'message': f'报工完成: {completed_qty}米',
            'data': {
                'order_no': content_order_no,
                'process_name': pkg.related_process,
                'completed_qty': completed_qty,
                'actual_qty': actual_qty,
                'status': status,
                'completed_at': datetime.now().isoformat()
            }
        }

    def _analyze_quality(self, pkg: DataPackage, return_data: Dict) -> Dict:
        result = return_data.get('result', '合格')
        content_order_no = pkg.content.get('order_no', pkg.related_order)

        return {
            'success': True,
            'message': f'质检完成: {result}',
            'data': {
                'order_no': content_order_no,
                'inspection_type': pkg.content.get('inspection_type'),
                'result': result,
                'completed_at': datetime.now().isoformat()
            }
        }

    def _analyze_material(self, pkg: DataPackage, return_data: Dict) -> Dict:
        delivered_qty = return_data.get('delivered_qty', 0)
        content_order_no = pkg.content.get('order_no', pkg.related_order)

        return {
            'success': True,
            'message': f'领料完成: {delivered_qty}',
            'data': {
                'order_no': content_order_no,
                'material_name': pkg.content.get('material_name'),
                'delivered_qty': delivered_qty,
                'completed_at': datetime.now().isoformat()
            }
        }

    def _analyze_approval(self, pkg: DataPackage, return_data: Dict) -> Dict:
        decision = return_data.get('decision', 'approved')
        content_order_no = pkg.content.get('order_no', pkg.related_order)

        return {
            'success': True,
            'message': f'审批: {decision}',
            'data': {
                'order_no': content_order_no,
                'approval_id': pkg.content.get('approval_id'),
                'decision': decision,
                'completed_at': datetime.now().isoformat()
            }
        }

    def _generate_write_back_command(self, pkg: DataPackage,
                                     return_data: Dict,
                                     analyzed: Dict) -> Dict:
        content_order_no = pkg.content.get('order_no', pkg.related_order)
        cmd = {
            'action': f'{pkg.data_type}_completed',
            'package_id': pkg.id,
            'order_no': content_order_no,
            'data': analyzed.get('data', {}),
            'source': 'container',
            'timestamp': datetime.now().isoformat(),
            'db_write_needed': True
        }

        if pkg.data_type == 'report':
            cmd['db_table'] = 'production_process_records'
            cmd['db_where'] = {'id': pkg.content.get('record_id')}
            cmd['db_set'] = {
                'completed_qty': analyzed['data'].get('completed_qty'),
                'actual_qty': analyzed['data'].get('actual_qty'),
                'status': analyzed['data'].get('status')
            }
        elif pkg.data_type == 'quality':
            cmd['db_table'] = 'quality_records'
            cmd['db_where'] = {'order_id': pkg.content.get('order_id')}
            cmd['db_set'] = {'result': analyzed['data'].get('result')}
        elif pkg.data_type == 'material':
            cmd['db_table'] = 'material_records'
            cmd['db_where'] = {'id': pkg.content.get('record_id')}
            cmd['db_set'] = {'delivered_qty': analyzed['data'].get('delivered_qty')}
        elif pkg.data_type == 'approval':
            cmd['db_table'] = 'approval_records'
            cmd['db_where'] = {'id': pkg.content.get('approval_id')}
            cmd['db_set'] = {'decision': analyzed['data'].get('decision')}

        return cmd


class ContainerCenter:
    """
    容器端数据中转中心 v5.0
    使用存储抽象层，支持SQLite/Redis切换
    """

    def __init__(self, storage_config: Dict = None):
        if storage_config is None:
            storage_config = {'type': DEFAULT_STORAGE_TYPE, 'db_path': DEFAULT_DB_PATH}
        # 禁止 SQLite — 迁移后仅允许 MySQL
        if storage_config.get('type') == 'sqlite':
            db_path = storage_config.get('db_path', '')
            if not os.path.exists(db_path):
                raise RuntimeError(
                    f'SQLite 文件已迁移到 MySQL，不再支持 SQLite 模式。\n'
                    f'缺失文件: {db_path}\n'
                    f'请确认 .env 中 CONTAINER_STORAGE_TYPE=mysql 已设置'
                )
        # 环境变量强制覆盖 type
        if os.getenv('CONTAINER_STORAGE_TYPE'):
            storage_config['type'] = os.getenv('CONTAINER_STORAGE_TYPE')
            if storage_config['type'] == 'mysql' and 'db_path' in storage_config:
                del storage_config['db_path']

        self.storage = create_storage(storage_config)
        self._validate_storage_contract(self.storage)
        self.collector = DataCollector(self.storage, center=self)
        self.distributor = DataDistributor(self.storage)
        self.analyzer = DataAnalyzer(self.storage)

        self.distributor.add_push_callback(self._on_distribute)

        # 消息发送总开关（调度中心控制，默认开启）
        self._enable_notification = True

        # 群聊推送（开关由调度中心控制，默认开启）
        self.group_notifier = None
        self._enable_group_notification = True

        # 分发开关（调度中心控制，默认开启）
        self._enable_distribution = True

        # 消息模板（调度中心定制）
        self._notification_template = ''

    @staticmethod
    def _validate_storage_contract(storage):
        """容器中心存储后端接口契约校验 — 任何后端都必须通过"""
        required = [
            'connect', 'disconnect', 'health_check',
            'load_enterprise_structure', 'save_enterprise_structure', 'get_enterprise_structure',
            'get_all_process_records', 'get_process_record', 'save_process_record',
            'get_process_records', 'get_process_records_by_work_order',
            'save_package', 'get_packages', 'get_package', 'delete_package',
            'update_package', 'update_package_status', 'cleanup_expired_packages',
            'get_sub_steps_by_process', 'save_process_sub_step', 'save_sub_step',
            'get_sub_step_summary', 'get_last_sub_step',
            'get_all_workers', 'save_worker', 'delete_worker',
            'get_attendance', 'get_attendance_by_date', 'upsert_attendance',
            'save_dispatch_command', 'get_dispatch_commands_by_order_process',
            'save_return_record',
            'save_data_flow_log', 'log_sync',
        ]
        missing = [m for m in required if not callable(getattr(storage, m, None))]
        if missing:
            msg = f'[ContainerCenter] 存储后端不符合接口契约，缺少 {len(missing)} 个方法: {missing}'
            logger.error(msg)
            raise RuntimeError(msg)
        logger.info('[ContainerCenter] 存储后端接口契约校验通过 (%d 个方法)', len(required))

    def set_group_notifier(self, notifier: Callable):
        self.group_notifier = notifier

    def enable_notification(self, enabled: bool = True):
        self._enable_notification = enabled

    @property
    def is_notification_enabled(self) -> bool:
        return self._enable_notification

    def enable_group_notification(self, enabled: bool = True):
        self._enable_group_notification = enabled

    @property
    def is_group_notification_enabled(self) -> bool:
        return self._enable_notification and self._enable_group_notification and self.group_notifier is not None

    def enable_distribution(self, enabled: bool = True):
        self._enable_distribution = enabled

    @property
    def is_distribution_enabled(self) -> bool:
        return self._enable_distribution

    def set_notification_template(self, template: str):
        self._notification_template = template

    @property
    def notification_template(self) -> str:
        return self._notification_template

    def send_group_notification(self, message: str):
        if not self.is_group_notification_enabled:
            logger.debug('[群聊通知] 群聊推送未启用或未配置，已跳过')
            return
        try:
            self.group_notifier(message)
            logger.info('[群聊通知] 群聊推送成功')
        except Exception as e:
            logger.warning(f'[群聊通知] 群聊推送失败: {e}')

    def _on_distribute(self, pkg: DataPackage):
        if not self._enable_distribution and not self._enable_notification:
            logger.debug(f"[分发] 分发与通知均已关闭，跳过回调: {pkg.id}")
            return

        logger.info(f"[分发] {pkg.title} -> {pkg.target_operator}")

        if not self._enable_distribution:
            logger.debug(f"[分发] 分发已关闭，跳过企业微信与桌面端通知: {pkg.id}")
            return

        if not self._enable_notification:
            logger.debug(f"[分发] 通知已关闭，跳过发送: {pkg.id}")
            return

        # 企业微信通知（通过调度中心中转 → cloud_poller → 云端5006 → 企业微信）
        try:
            import requests
            dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
            msg_content = (
                f"📋 您有新的任务！\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"任务ID: {pkg.id}\n"
                f"任务: {pkg.title}\n"
                f"订单: {pkg.related_order or '-'}\n"
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"请及时处理"
            )
            requests.post(
                f'{dispatch_url}/api/dispatch-center/messages/send',
                json={
                    'content': msg_content,
                    'channels': ['wechat_app'],
                    'operator_id': pkg.target_operator,
                },
                timeout=3
            )
        except Exception as e:
            logger.warning(f"[分发] 企业微信通知失败: {e}")

        # 桌面端回调
        if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
            try:
                desktop_callback_manager.notify_task_assigned(
                    task_id=pkg.id,
                    operator_id=pkg.target_operator,
                    task_title=pkg.title,
                    related_order=pkg.related_order
                )
            except Exception as e:
                logger.warning(f"[分发] 桌面端回调失败: {e}")

    def collect_report(self, order_no: str, process_name: str,
                      record_id: int, operator_id: str,
                      planned_qty: int, **kwargs) -> DataPackage:
        # 构建内容，包含所有必要字段
        content = {
            'record_id': record_id,
            'planned_qty': planned_qty,
            'order_no': order_no,
            'order_no': kwargs.get('order_no', ''),
            'process_name': process_name,
        }
        # 添加可选字段
        if kwargs.get('customer'):
            content['customer'] = kwargs['customer']
        if kwargs.get('tech_params'):
            content['tech_params'] = kwargs['tech_params']
        if kwargs.get('unit'):
            content['unit'] = kwargs['unit']
        if kwargs.get('priority'):
            content['priority'] = kwargs['priority']

        return self.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['report'],
            title=f'报工：{process_name}',
            content=content,
            order_no=order_no,
            process_name=process_name,
            operator_id=operator_id,
            **kwargs
        )

    def collect_quality(self, order_no: str, order_id: int,
                        inspector_id: str, inspection_type: str,
                        **kwargs) -> DataPackage:
        return self.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['quality'],
            title=f'质检:{inspection_type}',
            content={'order_id': order_id, 'inspection_type': inspection_type},
            order_no=order_no,
            operator_id=inspector_id,
            **kwargs
        )

    def collect_material(self, order_no: str, material_name: str,
                        quantity: int, operator_id: str,
                        unit: str = '件', spec: str = '', **kwargs) -> DataPackage:
        return self.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['material'],
            title=f'领料：{material_name} {spec}',
            content={'material_name': material_name, 'spec': spec, 'quantity': quantity, 'unit': unit},
            order_no=order_no,
            operator_id=operator_id,
            **kwargs
        )

    def collect_approval(self, order_no: str, approval_id: int,
                        approver_id: str, reason: str,
                        **kwargs) -> DataPackage:
        return self.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['approval'],
            title=f'审批：{reason[:APPROVAL_TITLE_MAX_LEN]}',
            content={'approval_id': approval_id, 'reason': reason},
            order_no=order_no,
            operator_id=approver_id,
            **kwargs
        )

    def collect_repair(self, category_id: str, category_name: str,
                      description: str, reporter_id: str = '',
                      **kwargs) -> DataPackage:
        pkg = self.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['repair'],
            title=f'报修：{category_name}',
            content={
                'category_id': category_id,
                'category_name': category_name,
                'description': description
            },
            order_no='',
            operator_id=reporter_id,
            **kwargs
        )

        # 设备报修微信通知
        try:
            from template_engine import _render_template, _send_wechat_message
            msg = _render_template('tmpl_repair_report', {
                '设备名称': category_name,
                '报修时间': datetime.now().strftime('%Y-%m-%d %H:%M'),
                '故障描述': description,
                '维修人': reporter_id or '待分配',
            })
            _send_wechat_message(msg, 'markdown')
        except Exception as e:
            logger.warning(f'[报修] 通知发送失败: {e}')

        return pkg

    def collect_outsource(self, order_no: str, process_name: str,
                         process_seq: int, planned_qty: int,
                         outsource_remark: str = '',
                         operator_id: str = '', **kwargs) -> DataPackage:
        """收集外协任务"""
        from container_config import container_config
        cfg = container_config.get_outsourc_config()
        target_op = operator_id or cfg.default_operator_id
        return self.collector.collect(
            data_type=NEW_DATA_TYPE_FOR_COLLECT['outsource'],
            title=f'外协:{process_name}',
            content={
                'process_name': process_name,
                'process_seq': process_seq,
                'planned_qty': planned_qty,
                'outsource_remark': outsource_remark,
                'fee': None,
            },
            order_no=order_no,
            operator_id=target_op,
            target_operator=target_op,
            priority='high',
            **kwargs
        )

    def acknowledge_task(self, package_id: str, operator_id: str = None) -> Dict:
        """
        确认任务接收
        
        Args:
            package_id: 任务ID
            operator_id: 操作员ID（可选，验证用）
        
        Returns:
            确认结果
        """
        pkg_dict = self.storage.get_package(package_id)
        if not pkg_dict:
            return {'success': False, 'message': '任务不存在'}
        
        # 验证操作员（如果提供）
        if operator_id and pkg_dict.get('target_operator') != operator_id:
            return {'success': False, 'message': '无权确认此任务'}
        
        # 检查状态，只能确认已分发的任务
        current_status = pkg_dict.get('status')
        if current_status != DataStatus.DISTRIBUTED.value:
            return {'success': False, 'message': f'任务状态不正确: {current_status}'}
        
        # 更新状态为已确认
        pkg_dict['status'] = DataStatus.ACKNOWLEDGED.value
        pkg_dict['acknowledged_at'] = datetime.now().isoformat()
        self.storage.save_package(pkg_dict)

        # 记录日志
        self.storage.log_sync('ACKNOWLEDGE', package_id, f'任务已确认: {operator_id or "未知"}')

        # 记录数据流转 - 确认
        start_time = time.time()
        self.storage.save_data_flow_log({
            'flow_id': package_id,
            'order_no': pkg_dict.get('related_order'),
            'process_name': pkg_dict.get('related_process'),
            'data_type': pkg_dict.get('data_type'),
            'source': pkg_dict.get('source'),
            'event_type': 'acknowledge',
            'event_name': '任务确认',
            'event_detail': f'操作员: {operator_id or "未知"}',
            'from_status': 'distributed',
            'to_status': 'acknowledged',
            'target_operator': operator_id or pkg_dict.get('target_operator'),
            'created_at': datetime.now().isoformat(),
            'duration_ms': int((time.time() - start_time) * 1000)
        })

        # 通知桌面端
        if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
            try:
                desktop_callback_manager.notify_task_acknowledged(
                    task_id=package_id,
                    operator_id=operator_id or pkg_dict.get('target_operator'),
                    task_title=pkg_dict.get('title', '任务')
                )
            except Exception as e:
                logger.warning(f"[确认] 桌面端回调失败: {e}")
        
        return {
            'success': True,
            'message': '任务已确认',
            'task_id': package_id,
            'acknowledged_at': pkg_dict['acknowledged_at']
        }
    
    def get_unacknowledged_tasks(self, operator_id: str = None) -> List[Dict]:
        """
        获取未确认的任务
        
        Args:
            operator_id: 操作员ID（可选）
        
        Returns:
            未确认任务列表
        """
        filters = {'status': DataStatus.DISTRIBUTED.value}
        if operator_id:
            filters['operator'] = operator_id
        pkg_dicts = self.storage.get_packages(**filters)
        return pkg_dicts
    
    def get_all_tasks(self, limit: int = DEFAULT_QUERY_LIMIT) -> List[Dict]:
        """
        获取所有任务
        
        Args:
            limit: 返回数量限制
        
        Returns:
            所有任务列表（按创建时间倒序）
        """
        pkg_dicts = self.storage.get_packages(limit=limit)
        return pkg_dicts
    
    def receive_return(self, package_id: str, return_data: Dict) -> Dict:
        start_time = time.time()

        result = self.analyzer.receive_return(package_id, return_data)

        pkg_dict = self.storage.get_package(package_id)
        if pkg_dict:
            # 记录数据流转 - 完成
            self.storage.save_data_flow_log({
                'flow_id': package_id,
                'order_no': pkg_dict.get('related_order'),
                'process_name': pkg_dict.get('related_process'),
                'data_type': pkg_dict.get('data_type'),
                'source': pkg_dict.get('source'),
                'event_type': 'complete',
                'event_name': '任务完成',
                'event_detail': f'完成结果: {result.get("analyzed", {}).get("message", "成功")}',
                'from_status': 'acknowledged',
                'to_status': 'completed',
                'result': result.get('success', False),
                'created_at': datetime.now().isoformat(),
                'duration_ms': int((time.time() - start_time) * 1000)
            })

            # 企业微信通知
            if WECHAT_NOTIFIER_AVAILABLE and wechat_notifier:
                try:
                    wechat_notifier.notify_task_completed(
                        task_id=package_id,
                        operator_id=pkg_dict.get('target_operator'),
                        task_title=pkg_dict.get('title', '任务'),
                        result=result.get('analyzed', {}).get('message', '完成')
                    )
                except Exception as e:
                    logger.warning(f"[完成] 企业微信通知失败: {e}")
            
            # 桌面端回调
            if DESKTOP_CALLBACK_AVAILABLE and desktop_callback_manager:
                try:
                    desktop_callback_manager.notify_task_completed(
                        task_id=package_id,
                        operator_id=pkg_dict.get('target_operator'),
                        task_title=pkg_dict.get('title', '任务'),
                        result=result
                    )
                except Exception as e:
                    logger.warning(f"[完成] 桌面端回调失败: {e}")

            # 群聊推送（按开关控制）
            if self.is_group_notification_enabled:
                content = pkg_dict.get('content', {})
                order_no = pkg_dict.get('related_order') or content.get('order_no', '')
                process_name = pkg_dict.get('related_process') or content.get('process_name', '')
                operator_name = content.get('operator_name', '')
                completed_qty = return_data.get('completed_qty') or content.get('completed_qty', 0)
                qualified_qty = return_data.get('qualified_qty') or content.get('qualified_qty', 0)
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

                msg = f"""
✅ 报工完成
━━━━━━━━━━━━━━━━━━
👤 操作员：{operator_name}
📦 订单：{order_no}
🔧 工序：{process_name}
📊 完成数量：{completed_qty}
✅ 合格数量：{qualified_qty}
⏰ 时间：{now_str}
"""
                self.send_group_notification(msg.strip())

        return result

    def get_pending_for_operator(self, operator_id: str) -> List[DataPackage]:
        pkg_dicts = self.storage.get_packages(
            status=DataStatus.DISTRIBUTED.value,
            operator=operator_id
        )
        return [DataPackage.from_dict(p) for p in pkg_dicts]

    def get_task_by_order(self, order_no: str, process: str = None) -> Optional[Dict]:
        """根据订单号获取任务，可选按工序过滤"""
        packages = self.storage.get_packages(
            related_order=order_no,
            limit=DEFAULT_QUERY_LIMIT
        )

        if not packages:
            return None

        # 如果没有指定工序，返回第一个
        if not process:
            return packages[0]

        # 按工序过滤，支持模糊匹配（去除空格后比较）
        process_normalized = process.replace(' ', '').replace('　', '')

        for pkg in packages:
            pkg_process = pkg.get('content', {}).get('process_name', '')
            pkg_process_normalized = pkg_process.replace(' ', '').replace('　', '')

            if pkg_process_normalized == process_normalized:
                return pkg

        # 如果没找到完全匹配的，返回第一个
        return packages[0]

    def get_task(self, task_id: str) -> Optional[Dict]:
        """根据任务ID获取任务"""
        return self.storage.get_package(task_id)

    def get_tasks_by_order(self, order_no: str) -> List[Dict]:
        """根据订单号获取所有任务"""
        packages = self.storage.get_packages(
            related_order=order_no,
            limit=DEFAULT_QUERY_LIMIT
        )
        return packages

    def get_tasks_by_operator(self, operator_id: str) -> List[Dict]:
        """根据操作员ID获取任务"""
        packages = self.storage.get_packages(
            operator=operator_id,
            limit=DEFAULT_QUERY_LIMIT
        )
        return packages

    def update_task_progress(self, task_id: str, quantity: int, operator_id: str = None) -> bool:
        """更新任务进度"""
        pkg_dict = self.storage.get_package(task_id)
        if not pkg_dict:
            return False

        current_qty = pkg_dict.get('completed_qty', 0)
        new_qty = current_qty + quantity
        pkg_dict['completed_qty'] = new_qty

        if 'content' in pkg_dict:
            pkg_dict['content']['completed_qty'] = new_qty

        self.storage.update_package(task_id, pkg_dict)
        return True

    def complete_task(self, task_id: str, data: Dict) -> bool:
        """完成任务"""
        pkg_dict = self.storage.get_package(task_id)
        if not pkg_dict:
            return False

        pkg_dict['status'] = DataStatus.COMPLETED.value
        pkg_dict['completed_at'] = datetime.now().isoformat()
        pkg_dict['completed_qty'] = data.get('completed_qty', 0)

        self.storage.update_package(task_id, pkg_dict)
        return True

    def get_pool_status(self) -> Dict:
        all_packages = self.storage.get_packages(limit=POOL_STATUS_LIMIT)
        by_type = {}
        by_status = {}

        for pkg in all_packages:
            dtype = pkg.get('data_type', 'other')
            status = pkg.get('status', 'unknown')
            by_type[dtype] = by_type.get(dtype, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            'total': len(all_packages),
            'by_type': by_type,
            'by_status': by_status,
            'pending': by_status.get(DataStatus.PENDING.value, 0),
            'distributed': by_status.get(DataStatus.DISTRIBUTED.value, 0),
            'completed': by_status.get(DataStatus.COMPLETED.value, 0)
        }

    def health_check(self) -> Dict:
        return self.storage.health_check()

    def add_sub_step(self, record: Dict) -> bool:
        """添加子步骤记录（分批入库/发货）"""
        return self.storage.save_sub_step(record)

    def get_sub_steps(self, order_no: str) -> List[Dict]:
        """获取流程的所有子步骤"""
        return self.storage.get_sub_steps_by_process(order_no)

    def get_sub_step_summary(self, order_no: str) -> Dict:
        """获取子步骤汇总"""
        return self.storage.get_sub_step_summary(order_no)

    def get_last_sub_step(self, order_no: str) -> Optional[Dict]:
        """获取流程的最后一条子步骤记录"""
        return self.storage.get_last_sub_step(order_no)

    # ───── workers 代理 ─────

    def get_all_workers(self) -> List[Dict]:
        return self.storage.get_all_workers()

    def get_worker_by_name(self, name: str) -> Optional[Dict]:
        """按姓名查操作员 [F16 T16.3 修复] enterprise_structure 表已 F6 P9 DROP, 改用 JSON"""
        try:
            # [F16 T16.3 修复] 走 storage helper 读 JSON, 替代直连 SQLite enterprise_structure
            es = self.storage.load_enterprise_structure() or {}
            users = es.get('users', [])
            if not isinstance(users, list):
                users = []
            for u in users:
                if not isinstance(u, dict):
                    continue
                if u.get('name') == name:
                    return u
            return None
        except Exception:
            pass
        return None

    def save_worker(self, worker: Dict) -> bool:
        return self.storage.save_worker(worker)

    def delete_worker(self, username: str) -> bool:
        return self.storage.delete_worker(username)

    # ───── attendance 代理 ─────

    def get_attendance(self, worker: str, date: str) -> Optional[Dict]:
        return self.storage.get_attendance(worker, date)

    def get_attendance_by_date(self, date: str) -> List[Dict]:
        return self.storage.get_attendance_by_date(date)

    def upsert_attendance(self, worker: str, date: str, check_in: str = '', check_out: str = '', status: str = '未签到') -> bool:
        return self.storage.upsert_attendance(worker, date, check_in, check_out, status)

    # ───── enterprise_structure 代理 ─────

    def save_enterprise_structure(self, data: Dict) -> bool:
        return self.storage.save_enterprise_structure(data)

    def load_enterprise_structure(self) -> Optional[Dict]:
        return self.storage.load_enterprise_structure()

    def sync_schedule_to_mysql(self, order_no: str, lead_time: int, completed_step_status: str = 'confirmed'):
        """容器中心负责将排产数据同步到 MySQL production_orders 表（主系统表，非 cc_ 表）"""
        if not order_no:
            return
        mysql_status = STATUS_KEY_TO_MYSQL.get(completed_step_status)
        if not mysql_status:
            logger.warning(f"[容器中心MySQL同步] {order_no}: 未识别的状态 key={completed_step_status}")
            return
        wo_no = order_no
        try:
            from core.db import get_direct_connection
            conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
            c = conn.cursor()
            c.execute("SELECT id, status, order_id FROM production_orders WHERE order_no=%s", (wo_no,))
            po = c.fetchone()
            if po:
                plan_start = datetime.now().strftime('%Y-%m-%d')
                plan_end = (datetime.now() + timedelta(days=int(lead_time))).strftime('%Y-%m-%d')
                c.execute("UPDATE production_orders SET status=%s, plan_start=%s, plan_end=%s, actual_start=COALESCE(actual_start, NOW()), updated_at=NOW() WHERE id=%s",
                          (mysql_status, plan_start, plan_end, po['id']))
                logger.info(f"[容器中心MySQL同步] {order_no}: status={mysql_status}, plan={plan_start}~{plan_end}")
            else:
                c.execute("SELECT id, order_no FROM orders WHERE order_no=%s", (order_no,))
                o_row = c.fetchone()
                if o_row:
                    plan_start = datetime.now().strftime('%Y-%m-%d')
                    plan_end = (datetime.now() + timedelta(days=int(lead_time))).strftime('%Y-%m-%d')
                    c.execute(
                        "INSERT INTO production_orders (order_no, order_id, status, plan_start, plan_end, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,NOW(),NOW())",
                        (o_row.get('order_no', order_no), o_row['id'], mysql_status, plan_start, plan_end)
                    )
                    logger.info(f"[容器中心MySQL同步] {order_no}: production_orders 新插入, status={mysql_status}")
            c.execute("SELECT id, status FROM orders WHERE order_no=%s", (order_no,))
            o = c.fetchone()
            if not o and po and po.get('order_id'):
                c.execute("SELECT id, status, order_no FROM orders WHERE id=%s", (po['order_id'],))
                o = c.fetchone()
            if o:
                order_new_status = STATUS_KEY_TO_MYSQL.get(completed_step_status, '已排产')
                if o['status'] != order_new_status:
                    c.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (order_new_status, o['id']))
                    logger.info(f"[容器中心MySQL同步] {order_no}: orders status={order_new_status}")
            conn.commit()
            self._sync_process_records_to_mysql(conn, wo_no)
            conn.close()
        except ImportError:
            logger.warning("[容器中心MySQL同步] pymysql 未安装，跳过")
        except Exception as e:
            logger.warning(f"[容器中心MySQL同步] {order_no} 失败: {e}")

    def _sync_process_records_to_mysql(self, mysql_conn, order_no: str):
        """将容器中心 process_records 同步到 MySQL process_records 表"""
        try:
            sqlite_recs = self.storage.get_process_records_by_work_order(order_no)
            if not sqlite_recs:
                logger.info(f"[容器中心MySQL同步] {order_no}: 无 process_records，跳过")
                return
            c = mysql_conn.cursor()
            for rec in sqlite_recs:
                process_name = rec.get('process_name', '')
                steps = rec.get('steps', [])
                c.execute("SELECT id FROM production_orders WHERE order_no=%s", (order_no,))
                po_row = c.fetchone()
                if not po_row:
                    continue
                production_id = po_row[0]
                if steps and isinstance(steps, list):
                    for idx, step in enumerate(steps):
                        step_name = step if isinstance(step, str) else (step.get('name', '') or step.get('process_name', ''))
                        if not step_name:
                            continue
                        c.execute(
                            "SELECT id FROM process_records WHERE production_id=%s AND process_name=%s",
                            (production_id, step_name)
                        )
                        existing = c.fetchone()
                        if not existing:
                            from core.config import get_process_code, get_process_seq
                            pcode = get_process_code(step_name)
                            dseq = get_process_seq(step_name)
                            c.execute(
                                "INSERT INTO process_records (production_id, process_name, process_code, process_seq, display_seq, planned_qty, status, worker, unit) "
                                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                (production_id, step_name, pcode, idx + 1, dseq,
                                 rec.get('quantity', 0), 'pending',
                                 rec.get('operator', ''), rec.get('unit', '件'))
                            )
                            logger.info(f"[容器中心MySQL同步] {order_no}: process_records 新增(工序={step_name})")
            mysql_conn.commit()
        except Exception as e:
            logger.warning(f"[容器中心MySQL同步] process_records 同步失败: {e}")

    def shutdown(self):
        """关闭容器中心"""
        self.storage.disconnect()


def demo():
    """演示"""
    logger.info("=" * 60)
    logger.info("容器端数据中转中心 v5.0 (存储抽象层)")
    logger.info("=" * 60)

    center = ContainerCenter({'type': DEFAULT_STORAGE_TYPE, 'db_path': DEMO_DB_PATH})

    logger.info("[1] 健康检查:")
    logger.info(f"  {center.health_check()}")

    logger.info("[2] 收集数据...")
    pkg1 = center.collect_report('ORD202604001', '编织', 103, 'OP001', 100)
    logger.info(f"  报工: {pkg1.id}")

    pkg2 = center.collect_quality('ORD202604001', 1, 'OP004', '终检')
    logger.info(f"  质检: {pkg2.id}")

    pkg3 = center.collect_material('ORD202604001', '不锈钢丝', 50, 'OP003')
    logger.info(f"  物料: {pkg3.id}")

    logger.info("[3] 容器状态:")
    status = center.get_pool_status()
    logger.info(f"  总计: {status['total']}, 待分发: {status['pending']}")

    logger.info("[4] 分发任务...")
    center.distributor.distribute(pkg1.id, 'OP001')
    center.distributor.distribute(pkg2.id, 'OP004')
    center.distributor.distribute(pkg3.id, 'OP003')

    logger.info("[5] 回传数据...")
    result1 = center.receive_return(pkg1.id, {'completed_qty': 100, 'status': '已完成'})
    logger.info(f"  报工分析: {result1.get('analyzed', {}).get('message')}")

    logger.info("[6] 最终状态:")
    status = center.get_pool_status()
    logger.info(f"  待分发: {status['pending']}, 已分发: {status['distributed']}, 已完成: {status['completed']}")

    center.shutdown()
    logger.info("")
    logger.info("=" * 60)
    logger.info("演示完成！")
    logger.info("=" * 60)


if __name__ == '__main__':
    demo()
