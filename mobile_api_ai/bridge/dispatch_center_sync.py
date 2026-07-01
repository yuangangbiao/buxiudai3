# -*- coding: utf-8 -*-
"""统一 5003 调度中心同步调用

[P0-K 修复 2026-06-24] 跨库同步无原子保证修复
=========================================
**修复前风险**：
  业务事务（process_sub_steps / orders / material_records 等）提交成功
  → 后续 5003 同步 HTTP 调用失败
  → 业务主库有数据、5003 桌面端没数据 → 数据漂移
  → 用户看到订单状态不一致

**修复方案**：outbox 兜底
  1. 业务事务照常 commit（不影响主流程）
  2. send() 先尝试直连 5003（实时性，~10ms）
  3. 直连失败 → 写入 sync_outbox 表（持久化事件）
  4. outbox worker 每 30s 消费一次 → 重试 5003 同步
  5. 重试 5 次后转 dead 状态 → 触发死信告警（P0-M 已实现）

**优势**：
  - 业务侧零改动（所有 send_* 包装函数自动受益）
  - 实时性保留（直连成功路径不变）
  - 失败兜底（outbox worker 异步重试）
  - 死信告警（5 次失败后微信通知值班）
"""
import os, urllib.request, json as _json, logging

logger = logging.getLogger(__name__)

DISPATCH_CENTER_URL = os.getenv('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')


def _write_to_outbox(endpoint: str, payload: dict) -> bool:
    """[P0-K] 直连 5003 失败时写 outbox 兜底

    Returns:
        True=outbox 写入成功（worker 会兜底重试），False=写入失败（数据漂移风险）
    """
    try:
        from outbox_writer import publish_event
        action = f'sync.{endpoint}'  # e.g. sync.sub-step-report
        # 用 order_no 作为 record_id（所有 endpoint 都有这个字段）
        record_id = (
            payload.get('order_no', '')
            or payload.get('id', '')
            or payload.get('record_id', '')
        )
        ok = publish_event(
            action=action,
            record_id=str(record_id),
            payload=payload,
            target_db='dispatch_center',
            max_retries=5,
        )
        if ok:
            logger.info('[DispatchCenterSync] outbox 兜底写入成功: %s', action)
        else:
            logger.error('[DispatchCenterSync] outbox 兜底也失败: %s', action)
        return ok
    except Exception as e:
        logger.error('[DispatchCenterSync] outbox 兜底异常: %s', e)
        return False


def send(endpoint: str, payload: dict, timeout: float = 5) -> bool:
    """向 5003 调度中心发送同步通知

    [P0-K 修复 2026-06-24] 直连失败时自动写 outbox 兜底

    Args:
        endpoint: 同步端点，如 'sub-step-report' / 'quality-record'
        payload:  同步数据
        timeout:  直连超时

    Returns:
        True = 同步已可靠送达（直连成功 或 outbox 写入成功）
        False = 直连失败且 outbox 写入失败（极端情况，触发告警日志）
    """
    # 1) 尝试直连 5003（实时性优先）
    try:
        url = f'{DISPATCH_CENTER_URL}/api/dispatch-center/sync/{endpoint}'
        data = _json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=timeout)
        logger.info('[DispatchCenterSync] 同步成功: %s', endpoint)
        return True
    except Exception as e:
        logger.warning('[DispatchCenterSync] 直连 5003 失败: %s, 改走 outbox 兜底: %s', endpoint, e)

    # 2) 直连失败 → 写 outbox 兜底（持久化重试）
    return _write_to_outbox(endpoint, payload)


def send_material_update(order_no: str, **kwargs) -> bool:
    """物料状态同步"""
    payload = {'order_no': order_no, **kwargs}
    return send('material', payload)


def send_repair_update(order_no: str, **kwargs) -> bool:
    """维修状态同步"""
    payload = {'order_no': order_no, **kwargs}
    return send('repair', payload)


def send_outsource_update(order_no: str, **kwargs) -> bool:
    """外协状态同步"""
    payload = {'order_no': order_no, **kwargs}
    return send('outsource', payload)


def send_sub_step_report(order_no: str, step_name: str = '', process_code: str = '',
                        quantity: float = 0, qualified_qty: float = None,
                        operator: str = '', operator_id: str = '',
                        equipment_name: str = '', remark: str = '',
                        overtime_hours: float = 0, **kwargs) -> bool:
    """工序报工同步"""
    payload = {
        'order_no': order_no,
        'step_name': step_name or process_code,
        'process_code': process_code,
        'quantity': quantity,
        'qualified_qty': qualified_qty,
        'operator': operator,
        'operator_id': operator_id,
        'equipment_name': equipment_name,
        'remark': remark,
        'overtime_hours': overtime_hours,
        **kwargs
    }
    return send('sub-step-report', payload)


def send_quality_record(order_no: str, step_name: str = '', record_id: str = '',
                       operation: str = 'update', **kwargs) -> bool:
    """质检记录同步 - 支持动态字段扩展

    示例:
        send_quality_record(
            order_no='ORD-xxx',
            step_name='Q01',
            result='合格',
            defect_description='无',
            defect_qty=0,
            inspector='张三',
            **extra_fields  # 支持任意额外字段
        )
    """
    payload = {
        'order_no': order_no,
        'step_name': step_name,
        'record_id': record_id,
        'operation': operation,
        **kwargs
    }
    return send('quality-record', payload)
