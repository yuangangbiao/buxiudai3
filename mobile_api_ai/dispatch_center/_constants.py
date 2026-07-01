# -*- coding: utf-8 -*-
"""
调度中心常量定义模块

包含所有配置常量、状态映射、流程模板等常量定义。
从 _core.py 提取，保持代码结构清晰。
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ── 状态映射 ──────────────────────────────────────────────────────────────────
STATUS_KEY_TO_MYSQL: Dict[str, str] = {
    'published': '已发布',
    'scheduled': '已排产',
    'confirmed': '已排产',
    'in_production': '生产中',
    'reported': '质检中',
    'qc_passed': '质检通过',
    'completed': '已完成',
}

# ── 调度规则默认值 ─────────────────────────────────────────────────────────────
DISPATCH_RULES_DEFAULT: Dict[str, Any] = {
    'auto_dispatch_timeout': {'label': '自动派单超时(分钟)', 'key': 'AUTO_DISPATCH_TIMEOUT', 'value': 30, 'type': 'number'},
    'reminder_interval': {'label': '提醒间隔(分钟)', 'key': 'REMINDER_INTERVAL', 'value': 15, 'type': 'number'},
    'max_reminders': {'label': '最大提醒次数', 'key': 'MAX_REMINDERS', 'value': 3, 'type': 'number'},
    'auto_reassign_timeout': {'label': '自动转派超时(分钟)', 'key': 'AUTO_REASSIGN_TIMEOUT', 'value': 60, 'type': 'number'},
    'max_operator_tasks': {'label': '操作员最大并发任务', 'key': 'MAX_OPERATOR_TASKS', 'value': 10, 'type': 'number'},
    'enable_auto_dispatch': {'label': '启用自动派单', 'key': 'ENABLE_AUTO_DISPATCH', 'value': True, 'type': 'boolean'},
    'enable_reminder': {'label': '启用超时提醒', 'key': 'ENABLE_REMINDER', 'value': True, 'type': 'boolean'},
    'urgent_priority_boost': {'label': '紧急任务优先派单', 'key': 'URGENT_PRIORITY_BOOST', 'value': True, 'type': 'boolean'},
    'repair_notification_enabled': {'label': '启用报修通知', 'key': 'REPAIR_NOTIFICATION_ENABLED', 'value': True, 'type': 'boolean'},
}

# ── 流程匹配规则 ───────────────────────────────────────────────────────────────
FLOW_MATCHING_RULES_DEFAULT: List[Dict[str, Any]] = [
    {'id': 'fmr_production_1', 'name': '不锈钢网带→生产流程', 'field': 'product_type', 'value': '不锈钢网带', 'flow_type': 'production', 'priority': 10, 'enabled': True},
    {'id': 'fmr_production_2', 'name': '不锈钢丝→生产流程', 'field': 'product_type', 'value': '不锈钢丝', 'flow_type': 'production', 'priority': 10, 'enabled': True},
    {'id': 'fmr_material', 'name': '物料→物料采购流程', 'field': 'product_type', 'value': '物料', 'flow_type': 'material_purchase', 'priority': 10, 'enabled': True},
    {'id': 'fmr_quality', 'name': '质检→质检流程', 'field': 'product_type', 'value': '质检委托', 'flow_type': 'quality', 'priority': 10, 'enabled': True},
    {'id': 'fmr_repair', 'name': '设备报修→维修流程', 'field': 'product_type', 'value': '设备维修', 'flow_type': 'repair', 'priority': 10, 'enabled': True},
]

# ── 产品类型映射 ───────────────────────────────────────────────────────────────
PRODUCT_TYPE_NAMES: Dict[int, str] = {
    11: '人字形网带', 12: '乙字形网带', 13: '平板型网带',
    14: '勾子链网带', 15: '眼镜网带', 16: '马蹄形网带',
    17: '链板式网带', 18: '其他',       19: '冷冻螺旋网',
    20: '螺旋网带',   21: '冷冻网带',   22: '链网',
    23: '弹簧网',
}

# ── 流程模板 ──────────────────────────────────────────────────────────────────
PROCESS_FLOW_TEMPLATES: Dict[str, Dict[str, Any]] = {
    'production': {
        'name': '生产流程',
        'steps': [
            {'name': '工单发布', 'role': '计划部', 'status_key': 'published'},
            {'name': '排产制定', 'role': '生产部', 'status_key': 'scheduled'},
            {'name': '排产确认', 'role': '计划部', 'status_key': 'confirmed'},
            {'name': '生产执行', 'role': '生产部', 'status_key': 'in_production'},
            {'name': '报工完成', 'role': '生产部', 'status_key': 'reported'},
            {'name': '质检审核', 'role': '质检部', 'status_key': 'qc_passed'},
            {'name': '完工入库', 'role': '仓库', 'status_key': 'completed'},
        ],
    },
    'material_purchase': {
        'name': '物料流程',
        'steps': [
            {'name': '物料需求', 'role': '生产部', 'status_key': 'required'},
            {'name': '库存检查', 'role': '系统', 'status_key': 'checked'},
            {'name': '采购审批', 'role': '主管', 'status_key': 'approved'},
            {'name': '采购下单', 'role': '采购部', 'status_key': 'ordered'},
            {'name': '到货入库', 'role': '仓库', 'status_key': 'received'},
            {'name': '领料出库', 'role': '生产部', 'status_key': 'issued'},
        ],
    },
    'quality': {
        'name': '质检流程',
        'steps': [
            {'name': '接收质检任务', 'role': '质检部', 'status_key': 'quality_received'},
            {'name': '检测结果判断', 'role': '质检部', 'status_key': 'quality_judged'},
            {'name': '审核放行', 'role': '质检部', 'status_key': 'quality_approved'},
            {'name': '入库', 'role': '仓库', 'status_key': 'completed'},
        ],
    },
    'repair': {
        'name': '维修流程',
        'steps': [
            {'name': '设备报修', 'role': '维修部', 'status_key': 'repair_reported'},
            {'name': '接单确认', 'role': '维修部', 'status_key': 'repair_confirmed'},
            {'name': '维修执行', 'role': '维修部', 'status_key': 'repair_in_progress'},
            {'name': '验收测试', 'role': '维修部', 'status_key': 'repair_verified'},
            {'name': '完工', 'role': '维修部', 'status_key': 'completed'},
        ],
    },
    'outsource': {
        'name': '外协流程',
        'steps': [
            {'name': '外协发单', 'role': '计划部', 'status_key': 'outsource_created'},
            {'name': '外协确认', 'role': '外协厂', 'status_key': 'outsource_confirmed'},
            {'name': '外协生产', 'role': '外协厂', 'status_key': 'outsource_production'},
            {'name': '外协质检', 'role': '质检部', 'status_key': 'outsource_qc'},
            {'name': '外协回厂', 'role': '仓库', 'status_key': 'outsource_returned'},
            {'name': '质检审核', 'role': '质检部', 'status_key': 'qc_passed'},
            {'name': '入库', 'role': '仓库', 'status_key': 'completed'},
        ],
    },
}

# ── 流程模板绑定 ────────────────────────────────────────────────────────────────
PROCESS_TEMPLATE_DEFAULTS: Dict[str, str] = {
    'process_advance': 'tmpl_process_advance',
    'process_reject': 'tmpl_process_reject',
    'task_assigned': 'tmpl_task_assigned',
    'task_reassign': 'tmpl_task_transfer',
}

# ── 确认步骤配置 ───────────────────────────────────────────────────────────────
CONFIRMATION_REQUIRED_STEPS: Dict[str, str] = {
    'scheduled': 'tmpl_schedule_notify',
    'confirmed': 'tmpl_schedule_complete',
    'reported': 'tmpl_schedule_complete',
    'qc_passed': 'tmpl_process_complete',
    'completed': 'tmpl_process_complete',
}

# ── 确认回复关键词 ───────────────────────────────────────────────────────────────
CONFIRMATION_REPLY_KEYWORDS: List[str] = ['确认', '收到', '好的', 'ok', 'yes', 'y', 'OK', '收到']

# ── 文档配置 ──────────────────────────────────────────────────────────────────
DISPATCH_DOC_ID: str = 'dispatch_center_data'
DISPATCH_DOC_TYPE: str = 'system_config'

# ── 缓存 TTL 配置 ───────────────────────────────────────────────────────────────
CUSTOMER_GROUP_CACHE_TTL: int = 300  # 5分钟
OPERATOR_CACHE_TTL: int = 300  # 5分钟
WORK_ORDER_CACHE_TTL: int = 300  # 5分钟
