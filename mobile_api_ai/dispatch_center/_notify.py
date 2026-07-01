# -*- coding: utf-8 -*-
"""
调度中心通知工具层 (v3.6.1)

抽取 _send_wechat_message / _notify_with_template / _notify_process_event 等
通知函数到独立模块，避免 _core.py 臃肿。

设计原则:
1. 纯通知逻辑（不依赖业务查询）
2. 业务数据通过参数传入（解耦）
3. 复用 template_engine 的模板渲染
4. 支持多种通知渠道（群消息/个人消息）

使用方式:
    from ._notify import notify_with_template, notify_process_event
    from ._notify import send_wechat_app_message, build_confirmation_variables
"""
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 微信发送（从 template_engine 二次封装）
# ═══════════════════════════════════════════════════════════════════════════════

def _send_wechat_message(content: str, msg_type: str = 'markdown') -> Tuple[bool, str]:
    """发送微信群消息（markdown/text）

    代理 template_engine._send_wechat_message
    """
    try:
        from template_engine import _send_wechat_message as _impl
        return _impl(content, msg_type)
    except ImportError:
        logger.warning('[微信发送] template_engine 不可用')
        return False, 'template_engine 不可用'
    except Exception as e:
        logger.exception(f'[微信发送] 异常: {e}')
        return False, str(e)


def _send_wechat_app_message(content: str, operator_id: str = None) -> Tuple[bool, str]:
    """发送应用消息到微信（仅通过云端 relay）

    Args:
        content: 消息内容
        operator_id: 接收人 user_id（None = @all）

    Returns:
        (success, error_msg)
    """
    try:
        from cloud_poller import send_to_cloud
        result = send_to_cloud(
            to_user=operator_id or '@all',
            content=content,
            msg_type='text',
            bot_type='app'
        )
        if isinstance(result, bool):
            return result, '' if result else '云端发送返回失败'
        if isinstance(result, dict):
            if result.get('code') == 0 or result.get('result') is True:
                return True, ''
            return False, result.get('message', '发送失败')
        return False, '响应格式异常'
    except Exception as e:
        logger.exception(f'[微信应用消息] 异常: {e}')
        return False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# 模板渲染
# ═══════════════════════════════════════════════════════════════════════════════

def _render_template(template_id: str, variables: dict) -> Optional[str]:
    """渲染消息模板

    代理 template_engine._render_template
    """
    try:
        from template_engine import _render_template as _impl
        return _impl(template_id, variables)
    except ImportError:
        logger.warning('[模板渲染] template_engine 不可用')
        return None
    except Exception as e:
        logger.exception(f'[模板渲染] {template_id} 异常: {e}')
        return None


def build_confirmation_variables(
    order_no: str,
    flow_name: str,
    next_step_name: str,
    operator_name: str,
    product_name: str = '',
    quantity: Any = 0
) -> dict:
    """构建确认通知的模板变量

    Args:
        order_no: 订单号
        flow_name: 流程名称
        next_step_name: 下一步骤名称
        operator_name: 执行人姓名
        product_name: 产品名称（可选）
        quantity: 数量（可选）

    Returns:
        dict: 模板变量字典
    """
    return {
        '订单号': order_no,
        '流程名称': flow_name,
        '当前步骤': next_step_name,
        '执行人': operator_name,
        '产品': product_name,
        '数量': quantity,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 通知主函数
# ═══════════════════════════════════════════════════════════════════════════════

def notify_with_template(
    template_id: str,
    variables: dict,
    target_operator: str = '',
    send_to_group: bool = True
) -> Tuple[bool, str]:
    """使用模板发送通知

    Args:
        template_id: 模板ID
        variables: 模板变量
        target_operator: 目标操作员ID（用于发送个人消息）
        send_to_group: 是否发送到群

    Returns:
        (success, error_msg)
    """
    content = _render_template(template_id, variables)
    if not content:
        return False, "模板渲染内容为空"

    success = True
    if send_to_group:
        ok, err = _send_wechat_message(content, 'markdown')
        if not ok:
            logger.warning(f'[模板通知] 发群失败: {err}')
            success = False

    if target_operator:
        ok, err = _send_wechat_app_message(content, target_operator)
        if not ok:
            logger.warning(f'[模板通知] 发个人失败: {err}')
            success = False

    return success, ''


def notify_process_event(
    template_id: str,
    variables: dict,
    order_no: str = '',
    target_operator: str = '',
    send_to_group: bool = True
) -> Tuple[bool, str]:
    """流程事件通知

    与 notify_with_template 的区别：
    - 这里 template_id 由调用方从模板绑定表中获取后传入
    - 调用方负责根据 event_type 查表

    Args:
        template_id: 模板ID（已确定）
        variables: 模板变量
        order_no: 订单号（仅用于日志，可选）
        target_operator: 目标操作员ID
        send_to_group: 是否发送到群

    Returns:
        (success, error_msg)
    """
    if not template_id:
        return False, "模板ID为空"

    return notify_with_template(
        template_id=template_id,
        variables=variables,
        target_operator=target_operator,
        send_to_group=send_to_group
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷发送函数
# ═══════════════════════════════════════════════════════════════════════════════

def send_simple_message(content: str, target_operator: str = '', msg_type: str = 'markdown') -> Tuple[bool, str]:
    """发送简单文本/markdown 消息（不经过模板渲染）

    Args:
        content: 消息内容
        target_operator: 目标操作员ID（空=发群）
        msg_type: 消息类型 markdown/text

    Returns:
        (success, error_msg)
    """
    if target_operator:
        return _send_wechat_app_message(content, target_operator)
    return _send_wechat_message(content, msg_type)


def send_to_department(department: str, content: str, msg_type: str = 'markdown') -> Dict[str, Any]:
    """发送给部门所有成员

    Args:
        department: 部门名称
        content: 消息内容
        msg_type: 消息类型

    Returns:
        dict: {success_count, fail_count, total}
    """
    result = {'success_count': 0, 'fail_count': 0, 'total': 0, 'errors': []}
    try:
        # 延迟导入避免循环
        from dispatch_center._db import _get_container_center
        cc = _get_container_center()
        if not cc:
            result['errors'].append('容器中心不可用')
            return result

        # 获取部门成员
        members = []
        if hasattr(cc, 'get_department_members'):
            members = cc.get_department_members(department) or []

        result['total'] = len(members)
        for member in members:
            user_id = member.get('user_id') or member.get('id', '')
            if not user_id:
                continue
            ok, err = _send_wechat_app_message(content, user_id)
            if ok:
                result['success_count'] += 1
            else:
                result['fail_count'] += 1
                result['errors'].append(f"{user_id}: {err}")
    except Exception as e:
        logger.exception(f'[部门通知] {department} 异常: {e}')
        result['errors'].append(str(e))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 向后兼容别名（保持 _core.py 旧代码可继续工作）
# ═══════════════════════════════════════════════════════════════════════════════

# 旧代码使用 _send_wechat_message（无下划线私有前缀版本）
send_wechat_message = _send_wechat_message
send_wechat_app_message = _send_wechat_app_message
render_template = _render_template