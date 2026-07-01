# -*- coding: utf-8 -*-
"""
R13 微信消息统一调度器（wechat_msg_dispatcher）

W3 层唯一入口，所有微信通知统一经过此模块发送。

职责：
1. 渲染：调用 template_engine.render_template
2. 查接收人：调用 notification_preset_service.get_receivers_for_scenario
3. 发送：调用 bots.factory.get_bot() -> send_templated_msg
4. 记录：调用 wechat_msg_log.log_send_attempt（幂等）
5. 违规：调用 _log_violation（静默降级）
"""
import logging
import os
import re
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import pymysql

from bots.factory import get_factory
from bots.base import BotType

_logger = logging.getLogger(__name__)


SCENARIO_TMPL_MAP: Dict[str, Dict] = {
    "schedule_overdue": {
        "tmpl_id": "SCHEDULED_OVERDUE_MSG",
        "default_receivers": ["生产主管", "计划员"],
        "description": "排产计划逾期提醒",
    },
    "schedule_created": {
        "tmpl_id": "SCHEDULE_CREATED_MSG",
        "default_receivers": ["生产主管"],
        "description": "新排产计划创建",
    },
    "workorder_created": {
        "tmpl_id": "WORKORDER_CREATED_MSG",
        "default_receivers": ["车间主任", "生产主管"],
        "description": "新工单创建通知",
    },
    "workorder_start": {
        "tmpl_id": "WORKORDER_START_MSG",
        "default_receivers": ["车间主任"],
        "description": "工单开工",
    },
    "workorder_complete": {
        "tmpl_id": "WORKORDER_COMPLETE_MSG",
        "default_receivers": ["质检员", "车间主任"],
        "description": "工单完工",
    },
    "workorder_overdue": {
        "tmpl_id": "WORKORDER_OVERDUE_MSG",
        "default_receivers": ["生产主管", "计划员"],
        "description": "工单逾期提醒",
    },
    "workorder_delayed": {
        "tmpl_id": "WORKORDER_DELAYED_MSG",
        "default_receivers": ["生产主管"],
        "description": "工单延期提醒",
    },
    "quality_check_pass": {
        "tmpl_id": "tmpl_quality_check_pass",
        "default_receivers": ["车间主任", "质检员"],
        "description": "质检通过通知",
    },
    "quality_check_fail": {
        "tmpl_id": "tmpl_quality_check_fail",
        "default_receivers": ["质检员", "生产主管"],
        "description": "质检未通过",
    },
    "quality_task_created": {
        "tmpl_id": "tmpl_quality_task_created",
        "default_receivers": ["质检员", "车间主任"],
        "description": "质检任务创建",
    },
    "quality_task_assigned": {
        "tmpl_id": "tmpl_quality_task_assigned",
        "default_receivers": ["质检员"],
        "description": "质检任务分配",
    },
    "quality_in_progress": {
        "tmpl_id": "tmpl_quality_in_progress",
        "default_receivers": ["车间主任", "生产主管"],
        "description": "质检进行中",
    },
    "quality_approved": {
        "tmpl_id": "tmpl_quality_approved",
        "default_receivers": ["车间主任", "生产主管", "质检员"],
        "description": "质检审核通过",
    },
    "quality_abnormal": {
        "tmpl_id": "tmpl_quality_abnormal",
        "default_receivers": ["质检员", "生产主管", "车间主任"],
        "description": "质检异常告警",
    },
    "quality_rework": {
        "tmpl_id": "tmpl_quality_rework",
        "default_receivers": ["生产主管", "车间主任"],
        "description": "返工通知",
    },
    "quality_recheck": {
        "tmpl_id": "tmpl_quality_recheck",
        "default_receivers": ["质检员", "车间主任"],
        "description": "复检通知",
    },
    "material_low_stock": {
        "tmpl_id": "MATERIAL_LOW_STOCK_MSG",
        "default_receivers": ["采购员", "仓库管理员"],
        "description": "物料库存不足",
    },
    "material_arrival": {
        "tmpl_id": "MATERIAL_ARRIVAL_MSG",
        "default_receivers": ["仓库管理员", "车间主任"],
        "description": "物料到货通知",
    },
    "outsource_send": {
        "tmpl_id": "OUTSOURCE_SEND_MSG",
        "default_receivers": ["外协管理员"],
        "description": "外协发出通知",
    },
    "outsource_return": {
        "tmpl_id": "OUTSOURCE_RETURN_MSG",
        "default_receivers": ["车间主任", "外协管理员"],
        "description": "外协返回通知",
    },
    "cost_alert": {
        "tmpl_id": "COST_ALERT_MSG",
        "default_receivers": ["财务", "生产主管"],
        "description": "成本超支预警",
    },
    "urgent_order": {
        "tmpl_id": "URGENT_ORDER_MSG",
        "default_receivers": ["全员"],
        "description": "紧急工单通知",
    },
    "schedule_update": {
        "tmpl_id": "SCHEDULE_UPDATE_MSG",
        "default_receivers": ["生产主管", "计划员"],
        "description": "排产计划更新",
    },
    "workorder_paused": {
        "tmpl_id": "WORKORDER_PAUSED_MSG",
        "default_receivers": ["车间主任", "生产主管"],
        "description": "工单暂停通知",
    },
    "workorder_resumed": {
        "tmpl_id": "WORKORDER_RESUMED_MSG",
        "default_receivers": ["车间主任"],
        "description": "工单恢复通知",
    },
    "daily_report": {
        "tmpl_id": "DAILY_REPORT_MSG",
        "default_receivers": ["生产主管", "计划员"],
        "description": "每日生产报告",
    },
    "inventory_alert": {
        "tmpl_id": "INVENTORY_ALERT_MSG",
        "default_receivers": ["仓库管理员", "采购员"],
        "description": "库存预警",
    },
    "payment_reminder": {
        "tmpl_id": "PAYMENT_REMINDER_MSG",
        "default_receivers": ["财务"],
        "description": "付款提醒",
    },
    "custom_process_registered": {
        "tmpl_id": "CUSTOM_PROCESS_MSG",
        "default_receivers": ["生产主管"],
        "description": "自定义工序注册通知",
    },
    "system_error": {
        "tmpl_id": "SYSTEM_ERROR_MSG",
        "default_receivers": ["系统管理员"],
        "description": "系统异常通知",
    },
    "schedule_confirm": {
        "tmpl_id": "SCHEDULE_CONFIRM_MSG",
        "default_receivers": ["生产主管", "计划员"],
        "description": "排产确认/拒绝通知",
    },
    "process_workorder_created": {
        "tmpl_id": "tmpl_workorder_created",
        "default_receivers": [],
        "description": "新工单流程已创建（派工时发给工人）",
    },
    "process_schedule_confirmed": {
        "tmpl_id": "tmpl_schedule_confirmed",
        "default_receivers": ["生产主管", "计划员"],
        "description": "排产已确认",
    },
    "process_schedule_rejected": {
        "tmpl_id": "tmpl_schedule_rejected",
        "default_receivers": ["生产主管", "计划员"],
        "description": "排产已拒绝",
    },
    "process_task_assigned": {
        "tmpl_id": "tmpl_task_assigned",
        "default_receivers": [],
        "description": "任务分配通知（派工时发给工人）",
    },
}


def _humanize_vars(context: Dict) -> Dict:
    """
    将变量名转换为中文友好格式，用于日志和调试。

    示例: {"loss_amount": 1234} -> {"亏损额": 1234}
    """
    try:
        from mobile_api_ai.template_engine import VAR_EN_TO_CN
    except Exception:
        try:
            from core.template_engine import VAR_EN_TO_CN
        except Exception:
            return context

    result = {}
    for k, v in context.items():
        result[VAR_EN_TO_CN.get(k, k)] = v
    return result


def _render_template(tmpl_id: str, context: Dict) -> str:
    """
    渲染消息模板。
    失败时返回空字符串（由调用方写违规日志）。
    """
    try:
        from mobile_api_ai.template_engine import render_template
        return render_template(tmpl_id, context)
    except Exception as e:
        _logger.warning(f'[{tmpl_id}] 模板渲染失败: {e}')
        return ""


_VIOLATION_TABLE_CREATED = False


def _ensure_violation_table(cursor):
    """确保 violation_log 表存在（幂等建表）"""
    global _VIOLATION_TABLE_CREATED
    if _VIOLATION_TABLE_CREATED:
        return
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violation_log (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            scenario VARCHAR(100) NOT NULL COMMENT '触发场景',
            violation_type VARCHAR(100) NOT NULL COMMENT '违规类型',
            severity VARCHAR(20) DEFAULT 'WARN' COMMENT '严重程度',
            order_no VARCHAR(100) DEFAULT '' COMMENT '关联订单号',
            detail TEXT COMMENT '违规详情',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_scenario (scenario),
            INDEX idx_created (created_at),
            INDEX idx_order (order_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='违规日志'
    """)
    _VIOLATION_TABLE_CREATED = True


def _log_violation(
    scenario: str,
    violation_type: str,
    severity: str = "WARN",
    order_no: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """
    记录违规到 violation_log（静默降级）。
    """
    try:
        import os
        # [T11 2026-06-14] 走 shim 连接池
        from core.db_compat import get_conn
        conn = get_conn()
        try:
            cursor = conn.cursor()
            _ensure_violation_table(cursor)
            cursor.execute("""
                INSERT INTO violation_log
                    (scenario, violation_type, severity, order_no, detail)
                VALUES (%s, %s, %s, %s, %s)
            """, (scenario, violation_type, severity, order_no, detail))
            conn.commit()
            cursor.close()
        except Exception as ie:
            conn.close()
            raise ie
    except Exception as e:
        _logger.exception('[violation_log] 记录失败: %r', e)
        raise


def _log_wechat_msg(
    scenario: str,
    tmpl_id: str,
    content: str,
    operators: List[str],
    status: str,
    err_msg: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    记录消息发送尝试到 wechat_msg_log（幂等+静默降级）。

    Returns:
        (success, msg_hash)
    """
    try:
        from mobile_api_ai.wechat_msg_log import log_send_attempt
        success = log_send_attempt(
            scenario=scenario,
            tmpl_id=tmpl_id,
            content=content,
            operators=operators,
            status=status,
            err_msg=err_msg,
        )
        if success:
            import hashlib
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            msg_hash = hashlib.sha256(f"{scenario}|{content_hash}".encode('utf-8')).hexdigest()
            return True, msg_hash
        return False, ""
    except Exception as e:
        _logger.exception('[wechat_msg_log] 记录失败: %r', e)
        raise


def _get_receivers(scenario: str) -> List[str]:
    """
    获取某场景的接收人列表。
    优先级：notification_preset_service > SCENARIO_TMPL_MAP.default_receivers
    """
    try:
        from mobile_api_ai.notification_preset_service import get_receivers_for_scenario
        receivers = get_receivers_for_scenario(scenario)
        if receivers:
            return receivers
    except Exception as e:
        _logger.debug('[get_receivers] preset查询降级: %s', e)

    return SCENARIO_TMPL_MAP.get(scenario, {}).get("default_receivers", [])


def _validate_scenario(scenario: str) -> bool:
    """验证场景名格式。"""
    return bool(re.match(r'^[a-z_]+$', scenario))


def _validate_context(scenario: str, context: Dict) -> Optional[str]:
    """
    验证 context 中是否有必要字段。
    Returns: None=合法，str=错误信息
    """
    if not context:
        return "context 为空"

    essential = {
        "workorder_created": ["工单号", "产品名称", "数量"],
        "workorder_start": ["工单号", "工序名称"],
        "workorder_complete": ["工单号", "工序名称"],
        "workorder_overdue": ["工单号", "逾期天数"],
        "schedule_overdue": ["计划号", "逾期天数"],
        "material_low_stock": ["物料名称", "当前库存", "安全库存"],
    }
    required = essential.get(scenario, [])
    missing = [f for f in required if f not in context and _to_en(f) not in context]
    if missing:
        return f"缺少必要字段: {', '.join(missing)}"
    return None


_EN_TO_CN_VAR = {
    "工单号": "order_no", "产品名称": "product_name", "数量": "quantity",
    "工序名称": "process_name", "逾期天数": "overdue_days",
    "计划号": "schedule_no", "物料名称": "material_name",
    "当前库存": "current_stock", "安全库存": "safety_stock",
}


def _to_en(cn: str) -> str:
    return _EN_TO_CN_VAR.get(cn, cn)


def send_templated(
    scenario: str,
    context: Dict,
    bot_type: BotType = BotType.APP,
    force_receivers: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """
    R13 W3 统一入口：发送模板消息。

    Args:
        scenario: 场景名（如 schedule_overdue / workorder_created）
        context: 变量字典，支持中文键或英文键
        bot_type: 使用哪个机器人（APP=应用通知 / GROUP=群通知）
        force_receivers: 强制指定接收人（覆盖预设）

    Returns:
        (success: bool, message: str)
        - success=True / message="发送成功" 或 "已存在（幂等），跳过"
        - success=False / message=错误原因
    """
    if not _validate_scenario(scenario):
        _log_violation(scenario, "invalid_scenario", "ERROR", detail=f"非法场景名: {scenario}")
        return False, f"非法场景名: {scenario}"

    if scenario not in SCENARIO_TMPL_MAP:
        _log_violation(scenario, "no_scenario", "ERROR", detail=f"场景未在 SCENARIO_TMPL_MAP 注册: {scenario}")
        return False, f"场景未注册: {scenario}"

    validation_error = _validate_context(scenario, context)
    if validation_error:
        _log_violation(scenario, "missing_context_field", "WARN", detail=validation_error)

    tmpl_id = SCENARIO_TMPL_MAP[scenario]["tmpl_id"]

    content = _render_template(tmpl_id, context)
    if not content:
        _log_violation(scenario, "msg_render_fail", "ERROR",
                       order_no=context.get("order_no") or context.get("工单号"),
                       detail=f"tmpl_id={tmpl_id}")
        return False, f"模板渲染失败: {tmpl_id}"

    if not content.strip():
        _log_violation(scenario, "empty_content", "ERROR", detail="渲染后内容为空")
        return False, "消息内容为空"

    receivers = force_receivers
    if not receivers:
        try:
            from mobile_api_ai.notification_preset_service import NotificationPresetService
            svc = NotificationPresetService()
            receivers = _get_receivers(scenario)
            if svc.get_force_by_assignee(scenario):
                assignee = context.get('操作员') or context.get('operator_id') or context.get('质检员') or context.get('执行人')
                if assignee and assignee not in receivers:
                    receivers = receivers + [assignee]
                    _logger.info(f'[send_templated] force_by_assignee=true，追加执行人: {assignee}，接收人: {receivers}')
        except Exception as e:
            _logger.debug('[send_templated] force_by_assignee 查询降级: %s', e)
            receivers = _get_receivers(scenario)
    if not receivers:
        _log_violation(scenario, "invalid_receivers", "WARN",
                       order_no=context.get("order_no") or context.get("工单号"),
                       detail=f"无接收人: scenario={scenario}")
        receivers = SCENARIO_TMPL_MAP[scenario].get("default_receivers", [])

    _log_wechat_msg(scenario, tmpl_id, content, receivers, status="pending")

    try:
        bot = get_factory().get_bot_by_type(bot_type)
        if not bot:
            _log_violation(scenario, "bot_unavailable", "ERROR",
                           order_no=context.get("order_no") or context.get("工单号"),
                           detail=f"机器人不可用: {bot_type}")
            _log_wechat_msg(scenario, tmpl_id, content, receivers, status="fail", err_msg="bot unavailable")
            return False, f"机器人不可用: {bot_type}"

        if hasattr(bot, 'send_templated_msg'):
            result = bot.send_templated_msg(tmpl_id, receivers, context)
            if result.get("success"):
                _log_wechat_msg(scenario, tmpl_id, content, receivers, status="success")
                return True, "发送成功"
            else:
                err = result.get("error", "unknown")
                _log_violation(scenario, "send_fail", "ERROR",
                               order_no=context.get("order_no") or context.get("工单号"),
                               detail=err)
                _log_wechat_msg(scenario, tmpl_id, content, receivers, status="fail", err_msg=err)
                return False, f"发送失败: {err}"
        else:
            user_ids = "|".join(receivers) if receivers else ""
            sent = bot.send_text(content, user_id=user_ids)
            if sent:
                _log_wechat_msg(scenario, tmpl_id, content, receivers, status="success")
                return True, "发送成功"
            else:
                _log_violation(scenario, "send_fail", "ERROR",
                               order_no=context.get("order_no") or context.get("工单号"),
                               detail="send_text returned False")
                _log_wechat_msg(scenario, tmpl_id, content, receivers, status="fail", err_msg="send_text failed")
                return False, "发送失败"

    except Exception as e:
        _logger.error(f'[{scenario}] 发送异常: {e}')
        _log_violation(scenario, "send_exception", "CRITICAL",
                       order_no=context.get("order_no") or context.get("工单号"),
                       detail=str(e))
        _log_wechat_msg(scenario, tmpl_id, content, receivers, status="fail", err_msg=str(e))
        return False, f"发送异常: {e}"
