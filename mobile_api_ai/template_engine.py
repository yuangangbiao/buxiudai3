# -*- coding: utf-8 -*-
"""
消息模板引擎 — 独立模块 (无 Flask/DB 副作用)

提供:
  - 30+ 内置消息模板 (MESSAGE_TEMPLATES_DEFAULT)
  - 中英变量双向映射 (VARIABLE_CN_TO_EN / VAR_EN_TO_CN)
  - 模板渲染 (_render_template)
  - 消息发送 (_send_wechat_message)

所有消息发送模块统一从此导入。
"""
import re
import sys
import logging
from dbutils.pooled_db import PooledDB
import pymysql

logger = logging.getLogger(__name__)

# MySQL 连接池 (全局单例)
_mysql_pool = None

def _get_mysql_pool():
    global _mysql_pool
    if _mysql_pool is None:
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        _mysql_pool = PooledDB(
            creator=pymysql,
            mincached=1, maxcached=5, maxconnections=10,
            **CONTAINER_MYSQL_CFG,
            connect_timeout=DB_CONNECT_TIMEOUT, blocking=False,
        )
    return _mysql_pool

VARIABLE_CN_TO_EN = {
    '操作员': 'operator_name', '任务标题': 'task_title', '订单号': 'order_no',
    '工序': 'process_name', '数量': 'quantity', '提醒次数': 'reminder_count',
    '已用分钟': 'elapsed_minutes', '优先级': 'priority', '原负责人': 'old_operator',
    '新负责人': 'new_operator', '原截止时间': 'old_deadline', '新截止时间': 'new_deadline',
    '延期原因': 'delay_reason', '流程名称': 'flow_type', '产品': 'product_name',
    '发起人': 'initiator', '当前步骤': 'current_step', '下一步骤': 'next_step',
    '执行人': 'executor', '完成时间': 'completed_at', '超时分钟': 'timeout_minutes',
    '客户': 'customer_name', '逾期天数': 'overdue_days', '质量问题': 'quality_issue',
    '检测环节': 'inspection_stage', '质检员': 'qc_inspector', '物料名称': 'material_name',
    '短缺数量': 'shortage_qty', '单位': 'unit', '影响描述': 'impact_desc',
    '到货数量': 'arrival_qty', '供应商': 'supplier', '到货时间': 'arrival_time',
    '当前库存': 'current_stock', '安全库存': 'safety_stock', '可用天数': 'available_days',
    '截止时间': 'deadline', '原排产计划': 'old_schedule', '新排产计划': 'new_schedule',
    '变更原因': 'change_reason', '外协单号': 'outsource_no', '发出时间': 'send_time',
    '预计返回': 'expected_return', '实收数量': 'received_qty', '收货时间': 'receive_time',
    '质检结果': 'qc_result', '设备名称': 'equipment_name', '报修人': 'reporter',
    '报修时间': 'report_time', '故障描述': 'fault_desc', '紧急程度': 'urgency',
    '维修人': 'repairer', '维修结果': 'repair_result', '耗时(小时)': 'repair_hours',
    '求助人': 'help_requester', '问题描述': 'problem_desc', '协助人': 'helper',
    '解决时间': 'resolve_time', '解决方案': 'solution', '退回步骤': 'reject_step',
    '退回原因': 'reject_reason', '操作人': 'operator', '部门': 'department',
    '报工时间': 'submit_time', '最低库存': 'lowest_stock',
    '提交部门': 'submitted_by', '提交时间': 'submitted_at',
    '确认人': 'confirmed_by', '确认时间': 'confirmed_at',
    '拒绝人': 'reject_by', '拒绝原因': 'reject_cause',
    '拒绝时间': 'reject_time', '排产明细': 'schedule_detail',
    '预计完成': 'estimated_complete', '总天数': 'total_days',
    '成功数': 'success_count', '总数': 'total_count',
    '状态': 'status_key',
    '交期': 'delivery_date', '发布时间': 'published_at', '通知时间': 'notified_at',
    '要求完成时间': 'required_complete',

}

VARIABLE_CN_TO_EN.update({
    '亏损额': 'loss_amount', '人工成本': 'labor_cost', '其他成本': 'other_cost',
    '利润': 'profit', '利润率': 'profit_margin', '剩余': 'remaining',
    '外协成本': 'outsource_cost', '总成本': 'total_cost', '排产方案': 'schedule_plan',
    '收入': 'revenue', '材料成本': 'material_cost', '累计完成': 'cumulative_done',
    '计划完成': 'planned_completion', '费用成本': 'expense_cost', '超时天数': 'timeout_days',
})
VAR_EN_TO_CN = {v: k for k, v in VARIABLE_CN_TO_EN.items()}

MESSAGE_TEMPLATES_DEFAULT = [
    {
        'id': 'tmpl_task_assigned', 'name': '任务分配通知', 'category': 'task',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '您有新的任务',
        'content': '**{操作员}** 您有新的任务！\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n工序: {工序}\n数量: {数量}\n━━━━━━━━━━━━━━━━━━━━\n请及时确认处理！',
    },
    {
        'id': 'tmpl_task_reminder', 'name': '任务超时提醒', 'category': 'task',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '任务待处理提醒',
        'content': '⏰ **任务超时提醒** (第{提醒次数}次)\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n已等待: {已用分钟}分钟\n━━━━━━━━━━━━━━━━━━━━\n请尽快处理！',
    },
    {
        'id': 'tmpl_task_completed', 'name': '任务完成通知', 'category': 'task',
        'channels': ['wechat_group'],
        'title': '任务已完成',
        'content': '✅ **任务完成**\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n操作员: {操作员}\n数量: {数量}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_task_urgent', 'name': '紧急任务通知', 'category': 'task',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '🚨 紧急任务',
        'content': '🚨 **紧急任务，请立即处理！**\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n工序: {工序}\n数量: {数量}\n紧急程度: {优先级}\n━━━━━━━━━━━━━━━━━━━━\n请马上确认并执行！',
    },
    {
        'id': 'tmpl_task_transfer', 'name': '任务转派通知', 'category': 'task',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '任务已转派',
        'content': '🔄 **任务转派通知**\n━━━━━━━━━━━━━━━━━━━━\n原负责人: {原负责人}\n新负责人: {新负责人}\n任务: {任务标题}\n订单: {订单号}\n━━━━━━━━━━━━━━━━━━━━\n请确认接收！',
    },
    {
        'id': 'tmpl_task_delay', 'name': '任务延期通知', 'category': 'task',
        'channels': ['wechat_group'],
        'title': '任务延期预警',
        'content': '⏰ **任务延期预警**\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n原计划: {原截止时间}\n新计划: {新截止时间}\n延期原因: {延期原因}\n━━━━━━━━━━━━━━━━━━━━\n请知悉！',
    },
    {
        'id': 'tmpl_process_start', 'name': '流程启动通知', 'category': 'process',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '新流程已启动',
        'content': '🚀 **流程已启动**\n━━━━━━━━━━━━━━━━━━━━\n流程: {流程名称}\n订单: {订单号}\n产品: {产品}\n发起人: {发起人}\n━━━━━━━━━━━━━━━━━━━━\n请相关部门知悉！',
    },
    {
        'id': 'tmpl_process_advance', 'name': '流程推进通知', 'category': 'process',
        'channels': ['wechat_group'],
        'title': '流程已推进',
        'content': '📍 **流程推进通知**\n━━━━━━━━━━━━━━━━━━━━\n流程: {流程名称}\n订单: {订单号}\n当前阶段: {当前步骤}\n下一步: {下一步骤}\n执行人: {执行人}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_process_complete', 'name': '流程完成通知', 'category': 'process',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '流程已完成',
        'content': '🎉 **流程已完成**\n━━━━━━━━━━━━━━━━━━━━\n流程: {流程名称}\n订单: {订单号}\n产品: {产品}\n完成时间: {完成时间}\n━━━━━━━━━━━━━━━━━━━━\n请相关人员确认！',
    },
    {
        'id': 'tmpl_alert_timeout', 'name': '任务超时告警', 'category': 'alert',
        'channels': ['wechat_group'],
        'title': '任务超时告警',
        'content': '⚠️ **任务超时告警**\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n操作员: {操作员}\n超时: {超时分钟} 分钟\n━━━━━━━━━━━━━━━━━━━━\n请及时处理或转派！',
    },
    {
        'id': 'tmpl_alert_overdue', 'name': '订单逾期告警', 'category': 'alert',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '订单逾期预警',
        'content': '🚨 **订单逾期告警**\n━━━━━━━━━━━━━━━━━━━━\n订单号: {订单号}\n客户: {客户}\n逾期天数: {逾期天数} 天\n产品: {产品}\n━━━━━━━━━━━━━━━━━━━━\n请紧急处理！',
    },
    {
        'id': 'tmpl_alert_quality', 'name': '质量问题告警', 'category': 'alert',
        'channels': ['wechat_group'],
        'title': '质量异常通知',
        'content': '🔍 **质量异常告警**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n问题类型: {质量问题}\n发现环节: {检测环节}\n负责人: {质检员}\n━━━━━━━━━━━━━━━━━━━━\n请及时处理！',
    },
    {
        'id': 'tmpl_material_shortage', 'name': '物料短缺通知', 'category': 'material',
        'channels': ['wechat_group'],
        'title': '物料短缺预警',
        'content': '⚠️ **物料短缺**\n━━━━━━━━━━━━━━━━━━━━\n物料: {物料名称}\n订单: {订单号}\n短缺: {短缺数量} {单位}\n预计影响: {影响描述}\n━━━━━━━━━━━━━━━━━━━━\n请及时采购！',
    },
    {
        'id': 'tmpl_material_arrival', 'name': '物料到货通知', 'category': 'material',
        'channels': ['wechat_group'],
        'title': '物料已到货',
        'content': '📦 **物料到货通知**\n━━━━━━━━━━━━━━━━━━━━\n物料: {物料名称}\n数量: {到货数量} {单位}\n供应商: {供应商}\n到货时间: {到货时间}\n━━━━━━━━━━━━━━━━━━━━\n请及时验收入库！',
    },
    {
        'id': 'tmpl_material_lowstock', 'name': '库存不足预警', 'category': 'material',
        'channels': ['wechat_group'],
        'title': '库存不足提醒',
        'content': '📉 **库存不足预警**\n━━━━━━━━━━━━━━━━━━━━\n物料: {物料名称}\n当前库存: {当前库存} {单位}\n安全库存: {安全库存} {单位}\n可用天数: {可用天数} 天\n━━━━━━━━━━━━━━━━━━━━\n请尽快补充！',
    },
    {
        'id': 'tmpl_schedule_notify', 'name': '排产通知', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产制定通知',
        'content': '⏰ **排产制定通知**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n数量: {数量}\n要求完成: {截止时间}\n━━━━━━━━━━━━━━━━━━━━\n请生产部门尽快制定排产计划！',
    },
    {
        'id': 'tmpl_schedule_change', 'name': '排产变更通知', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产计划变更',
        'content': '📋 **排产变更通知**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n原计划: {原排产计划}\n新计划: {新排产计划}\n变更原因: {变更原因}\n━━━━━━━━━━━━━━━━━━━━\n请知悉！',
    },
    {
        'id': 'tmpl_schedule_reminder', 'name': '排产超时提醒', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产超时提醒',
        'content': '⚠️ **排产超时提醒**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n数量: {数量} {单位}\n要求完成: {截止时间}\n已超时: {超时天数} 天\n━━━━━━━━━━━━━━━━━━━━\n请尽快处理排产！',
    },
    {
        'id': 'tmpl_schedule_complete', 'name': '排产完成确认', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产已确认完成',
        'content': '✅ **排产已确认完成**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n数量: {数量} {单位}\n排产方案: {排产方案}\n计划完成: {计划完成}\n确认人: {确认人}\n━━━━━━━━━━━━━━━━━━━━\n请按排产计划执行！',
    },
    {
        'id': 'tmpl_outsource_send', 'name': '外协发出通知', 'category': 'other',
        'channels': ['wechat_group'],
        'title': '外协已发出',
        'content': '🚚 **外协发出通知**\n━━━━━━━━━━━━━━━━━━━━\n外协单号: {外协单号}\n物料: {物料名称}\n数量: {数量}\n供应商: {供应商}\n发出时间: {发出时间}\n预计返回: {预计返回}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_outsource_receive', 'name': '外协收货通知', 'category': 'other',
        'channels': ['wechat_group'],
        'title': '外协已收货',
        'content': '📥 **外协收货通知**\n━━━━━━━━━━━━━━━━━━━━\n外协单号: {外协单号}\n物料: {物料名称}\n实收数量: {实收数量}\n收货时间: {收货时间}\n质检结果: {质检结果}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_repair_report', 'name': '设备报修通知', 'category': 'other',
        'channels': ['wechat_group'],
        'title': '设备报修',
        'content': '🔧 **设备报修通知**\n━━━━━━━━━━━━━━━━━━━━\n设备: {设备名称}\n报修人: {报修人}\n报修时间: {报修时间}\n故障描述: {故障描述}\n紧急程度: {紧急程度}\n━━━━━━━━━━━━━━━━━━━━\n请维修人员及时处理！',
    },
    {
        'id': 'tmpl_repair_complete', 'name': '维修完成通知', 'category': 'other',
        'channels': ['wechat_group'],
        'title': '维修已完成',
        'content': '✅ **维修完成通知**\n━━━━━━━━━━━━━━━━━━━━\n设备: {设备名称}\n维修人: {维修人}\n完成时间: {完成时间}\n维修结果: {维修结果}\n耗时: {耗时(小时)} 小时\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_help_request', 'name': '求助请求通知', 'category': 'other',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '操作员求助',
        'content': '🆘 **求助请求**\n━━━━━━━━━━━━━━━━━━━━\n发起人: {求助人}\n所在工序: {工序}\n订单: {订单号}\n问题描述: {问题描述}\n━━━━━━━━━━━━━━━━━━━━\n请相关人员协助！',
    },
    {
        'id': 'tmpl_help_complete', 'name': '求助解决通知', 'category': 'other',
        'channels': ['wechat_app'],
        'title': '问题已解决',
        'content': '💡 **问题已解决**\n━━━━━━━━━━━━━━━━━━━━\n发起人: {求助人}\n协助人: {协助人}\n解决时间: {解决时间}\n解决方案: {解决方案}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_process_reject', 'name': '流程退回通知', 'category': 'process',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '流程退回',
        'content': '🔙 **流程退回**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n退回步骤: {退回步骤}\n退回原因: {退回原因}\n操作人: {操作人}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_cost_calculated', 'name': '成本核算通知', 'category': 'cost',
        'channels': ['wechat_group'],
        'title': '订单成本已核算',
        'content': '💰 **订单成本核算结果**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n客户: {客户}\n产品: {产品}\n数量: {数量}\n━━━━━━━━━━━━━━━━━━━━\n材料: ¥{材料成本:.2f}\n人工: ¥{人工成本:.2f}\n费用: ¥{费用成本:.2f}\n外协: ¥{外协成本:.2f}\n其他: ¥{其他成本:.2f}\n━━━━━━━━━━━━━━━━━━━━\n总成本: ¥{总成本:.2f}\n收入: ¥{收入:.2f}\n利润: ¥{利润:.2f}\n利润率: {利润率:.1f}%\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_cost_loss_warning', 'name': '亏损预警', 'category': 'cost',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '订单亏损预警',
        'content': '🔴 **订单亏损预警**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n客户: {客户}\n产品: {产品}\n总成本: ¥{总成本:.2f}\n收入: ¥{收入:.2f}\n亏损: ¥{亏损额:.2f}\n━━━━━━━━━━━━━━━━━━━━\n请紧急关注处理！',
    },
    {
        'id': 'tmpl_cost_low_margin', 'name': '低利润提醒', 'category': 'cost',
        'channels': ['wechat_group'],
        'title': '低利润提醒',
        'content': '🟡 **低利润提醒**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n客户: {客户}\n利润率: {利润率:.1f}%\n利润: ¥{利润:.2f}\n━━━━━━━━━━━━━━━━━━━━\n建议关注成本控制。',
    },
    {
        'id': 'tmpl_cost_profitable', 'name': '高利润订单通知', 'category': 'cost',
        'channels': ['wechat_group'],
        'title': '高利润订单',
        'content': '🟢 **高利润订单**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n客户: {客户}\n产品: {产品}\n利润率: {利润率:.1f}%\n利润: ¥{利润:.2f}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_inventory_alert', 'name': '库存预警', 'category': 'material',
        'channels': ['wechat_group'],
        'title': '库存不足',
        'content': '⚠️ **库存预警**\n━━━━━━━━━━━━━━━━━━━━\n物料: {物料名称}\n当前库存: {当前库存} {单位}\n最低库存: {最低库存} {单位}\n━━━━━━━━━━━━━━━━━━━━\n库存不足，请及时采购！',
    },
    {
        'id': 'tmpl_report_submitted', 'name': '报工提交通知', 'category': 'task',
        'channels': ['wechat_group'],
        'title': '报工已提交',
        'content': '📝 **报工提交**\n━━━━━━━━━━━━━━━━━━━━\n订单号: {订单号}\n工序: {工序}\n数量: {数量}\n操作员: {操作员}\n时间: {报工时间}\n━━━━━━━━━━━━━━━━━━━━\n报工已提交！',
    },
    # RE-002 T4: 新增报工实际数量通知模板
    {
        'id': 'tmpl_report_actual', 'name': '实际报工通知', 'category': 'task',
        'channels': ['wechat_group'],
        'title': '实际报工',
        'content': '📊 **实际报工**\n━━━━━━━━━━━━━━━━━━━━\n订单号: {订单号}\n工序: {工序}\n本次数量: {数量}\n累计完成: {累计完成}\n剩余: {剩余}\n操作员: {操作员}\n时间: {报工时间}\n━━━━━━━━━━━━━━━━━━━━\n实际报工已记录！',
    },
    {
        'id': 'tmpl_repair_reminder', 'name': '维修提醒', 'category': 'other',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '维修待处理',
        'content': '🔧 **维修提醒**\n━━━━━━━━━━━━━━━━━━━━\n设备: {设备名称}\n故障: {故障描述}\n报修人: {报修人}\n报修时间: {报修时间}\n━━━━━━━━━━━━━━━━━━━━\n请及时处理维修！',
    },
    {
        'id': 'tmpl_schedule_submitted', 'name': '排产已提交通知', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产已提交',
        'content': '✅ **排产已提交**\n━━━━━━━━━━━━━━━━━━━━\n工单: {订单号}\n客户: {客户}\n产品: {产品}\n数量: {数量} {单位}\n提交部门: {提交部门}\n提交时间: {提交时间}\n━━━━━━━━━━━━━━━━━━━━\n📋 排产计划:\n{排产明细}\n━━━━━━━━━━━━━━━━━━━━\n预计完成: {预计完成}\n总天数: {总天数}\n━━━━━━━━━━━━━━━━━━━━\n请桌面端确认排产信息！',
    },
    {
        'id': 'tmpl_schedule_confirmed', 'name': '排产已确认通知', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产已确认',
        'content': '🎉 **排产已确认**\n━━━━━━━━━━━━━━━━━━━━\n工单: {订单号}\n客户: {客户}\n产品: {产品}\n数量: {数量} {单位}\n开始日期: {开始日期}\n结束日期: {结束日期}\n工期: {工期}\n确认人: {确认人}\n确认时间: {确认时间}\n━━━━━━━━━━━━━━━━━━━━\n排产计划已生效，请按计划执行！',
    },
    {
        'id': 'tmpl_schedule_rejected', 'name': '排产已拒绝通知', 'category': 'schedule',
        'channels': ['wechat_group'],
        'title': '排产已拒绝',
        'content': '❌ **排产已拒绝**\n━━━━━━━━━━━━━━━━━━━━\n工单: {订单号}\n客户: {客户}\n产品: {产品}\n数量: {数量} {单位}\n拒绝人: {拒绝人}\n拒绝原因: {拒绝原因}\n拒绝时间: {拒绝时间}\n━━━━━━━━━━━━━━━━━━━━\n请生产部门重新制定排产计划！',
    },
    {
        'id': 'tmpl_task_cancelled', 'name': '任务取消通知', 'category': 'task',
        'channels': ['wechat_group'],
        'title': '任务已取消',
        'content': '❌ **任务已取消**\n━━━━━━━━━━━━━━━━━━━━\n任务: {任务标题}\n订单: {订单号}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_batch_assign', 'name': '批量派单通知', 'category': 'task',
        'channels': ['wechat_group'],
        'title': '批量派单完成',
        'content': '📦 **批量派单完成**\n━━━━━━━━━━━━━━━━━━━━\n操作员: {操作员}\n成功: {成功数}/{总数}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_workorder_created', 'name': '工单创建通知', 'category': 'process',
        'channels': ['wechat_group'],
        'title': '新工单已创建',
        'content': '📋 **新工单流程已创建**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n数量: {数量}\n客户: {客户}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_quality_completed', 'name': '质检完成通知', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '质检完成',
        'content': '✅ **质检完成**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n质检类型: {质检类型}\n质检结果: {质检结果}\n质检员: {质检员}\n完成时间: {完成时间}\n━━━━━━━━━━━━━━━━━━━━\n{备注}\n━━━━━━━━━━━━━━━━━━━━',
    },
    {
        'id': 'tmpl_quality_check_pass', 'name': '质检通过通知', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '✅ 质检通过',
        'content': '✅ **质检通过**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n质检类型: {质检类型}\n质检项目: {质检项目}\n质检员: {质检员}\n通过时间: {通过时间}\n━━━━━━━━━━━━━━━━━━━━\n产品合格，可以进入下一工序。',
    },
    {
        'id': 'tmpl_quality_check_fail', 'name': '质检未通过通知', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '❌ 质检未通过',
        'content': '❌ **质检未通过**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n质检类型: {质检类型}\n不合格项目: {不合格项目}\n不合格原因: {不合格原因}\n质检员: {质检员}\n检测时间: {检测时间}\n━━━━━━━━━━━━━━━━━━━━\n请及时处理质量问题！',
    },
    {
        'id': 'tmpl_quality_task_created', 'name': '质检任务创建', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '📋 质检任务已创建',
        'content': '📋 **质检任务已创建**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n质检类型: {质检类型}\n质检项目: {质检项目}\n创建时间: {创建时间}\n━━━━━━━━━━━━━━━━━━━━\n请质检员及时接收任务。',
    },
    {
        'id': 'tmpl_quality_task_assigned', 'name': '质检任务分配', 'category': '质检',
        'channels': ['wechat_app'],
        'title': '📌 质检任务已分配',
        'content': '📌 **质检任务已分配**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n质检类型: {质检类型}\n质检员: {质检员}\n分配时间: {分配时间}\n━━━━━━━━━━━━━━━━━━━━\n请及时处理。',
    },
    {
        'id': 'tmpl_quality_in_progress', 'name': '质检进行中', 'category': '质检',
        'channels': ['wechat_group'],
        'title': '🔍 质检进行中',
        'content': '🔍 **质检进行中**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n质检类型: {质检类型}\n质检员: {质检员}\n开始时间: {开始时间}\n━━━━━━━━━━━━━━━━━━━━\n质检进行中，请等待结果。',
    },
    {
        'id': 'tmpl_quality_approved', 'name': '质检审核通过', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '✅ 质检审核通过',
        'content': '✅ **质检审核通过**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n审核人: {审核人}\n审核时间: {审核时间}\n备注: {备注}\n━━━━━━━━━━━━━━━━━━━━\n质检审核已完成，流程继续推进。',
    },
    {
        'id': 'tmpl_quality_abnormal', 'name': '质检异常告警', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '⚠️ 质检异常',
        'content': '⚠️ **质检异常告警**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n异常类型: {异常类型}\n异常描述: {异常描述}\n发现环节: {发现环节}\n负责人: {负责人}\n发现时间: {发现时间}\n━━━━━━━━━━━━━━━━━━━━\n请及时处理！',
    },
    {
        'id': 'tmpl_quality_rework', 'name': '返工通知', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '🔧 需要返工',
        'content': '🔧 **需要返工**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n返工原因: {返工原因}\n返工要求: {返工要求}\n质检员: {质检员}\n通知时间: {通知时间}\n━━━━━━━━━━━━━━━━━━━━\n请按要求进行返工处理。',
    },
    {
        'id': 'tmpl_quality_recheck', 'name': '复检通知', 'category': '质检',
        'channels': ['wechat_group', 'wechat_app'],
        'title': '🔄 需要复检',
        'content': '🔄 **需要复检**\n━━━━━━━━━━━━━━━━━━━━\n订单: {订单号}\n产品: {产品}\n复检原因: {复检原因}\n原质检结果: {原质检结果}\n复检要求: {复检要求}\n质检员: {质检员}\n通知时间: {通知时间}\n━━━━━━━━━━━━━━━━━━━━\n请安排复检。',
    },

]

# ====================================================
# 变量解析与模板渲染
# ====================================================

def _resolve_variables(variables: dict) -> dict:
    """双向变量解析: 中文key <-> 英文key"""
    resolved = {}
    for key, value in variables.items():
        resolved[key] = value
        cn_key = VAR_EN_TO_CN.get(key)
        if cn_key and cn_key not in variables:
            resolved[cn_key] = value
        en_key = VARIABLE_CN_TO_EN.get(key)
        if en_key and en_key not in variables:
            resolved[en_key] = value
    return resolved


def _render_template(template_id: str, variables: dict) -> str:
    """渲染模板 — MySQL优先 + 内置兜底 + 白名单正则"""
    content = None

    # 1. 优先 MySQL (可通过 emergency-fallback 关闭)
    if not getattr(sys.modules[__name__], '_fallback_only', False):
        try:
            pool = _get_mysql_pool()
            conn = pool.connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    'SELECT content FROM message_templates WHERE id=%s AND is_active=1',
                    (template_id,))
                row = cur.fetchone()
                if row:
                    content = row[0]
                cur.close()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("MySQL 模板查询失败, 降级内置: %s", e)

    # 2. MySQL 无/关闭 → 降级内置
    if not content:
        template = next((t for t in MESSAGE_TEMPLATES_DEFAULT if t.get('id') == template_id), None)
        if not template:
            logger.warning("模板 %s 不存在", template_id)
            return ''
        content = template['content']

    resolved = _resolve_variables(variables)

    # 1. 正常替换 (None -> 空字符串), 支持 {key} 和 {key:fmt}
    for key, value in resolved.items():
        if value is None:
            content = re.sub(r'\{\s*' + re.escape(key) + r'(?::[^}]*)?\}', '', content)
        else:
            content = re.sub(r'\{\s*' + re.escape(key) + r'(?::[^}]*)?\}', str(value), content)

    # 2. 白名单兜底: 只清洗模板中存在但未传入的变量
    known_vars = set(re.findall(
        r'\{([\u4e00-\u9fff\u3400-\u4dbf\w]+)(?::[^}]+)?\}', content))
    unmatched = known_vars - set(resolved.keys())
    for var in unmatched:
        content = re.sub(r'\{' + re.escape(var) + r'(:[^}]+)?\}', '—', content)

    return content


def _send_wechat_message(content: str, msg_type: str = 'text'):
    """发送消息到微信群（走本地 GroupBot 直发，WECHAT_WORK_BOT_URL 配置在 .env）"""
    try:
        from bots.factory import get_factory
        group_bot = get_factory().get_group_bot()
        if not group_bot:
            return False, '群机器人未配置 WECHAT_WORK_BOT_URL'
        if msg_type == 'markdown':
            ok = group_bot.send_markdown(content)
        else:
            ok = group_bot.send_text(content)
        return (True, '') if ok else (False, '发送失败')
    except Exception as e:
        return False, str(e)
