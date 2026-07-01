# -*- coding: utf-8 -*-
import logging
import os
from .. import mysql_cursor, container_cursor
from contextlib import contextmanager
from datetime import datetime

import requests
from circuit_breaker_integration import circuit_protected
from core.config import BASE_DIR

from schema_auto import ensure_table
from sync.sync_log import SyncLog

logger = logging.getLogger(__name__)


@contextmanager


@contextmanager


def _sync_to_container_db(data: dict):
    """sync sub_step record to container_center MySQL (process_sub_steps table)

    [F6 v4.0 标注] 本函数属于 "legacy 事件流同步" 路径（source='legacy'），
    故意绕过 save_process_sub_step 的"3 键去重 + operator 追加"逻辑。
    原因：事件流来自老 wechat_container.db 的回灌，每条事件都带完整物理报工
    字段（qualified_qty / equipment_name / overtime_hours / remark 等），且
    去重诉求是"按主键 id 幂等"——这与 v4.0 的派工去重语义不同，故保留
    INSERT IGNORE 的简单幂等保护。
    """
    try:
        with container_cursor() as cursor:
            conn = cursor.connection
            ensure_table(conn, 'process_sub_steps', use_transaction=False)
            # [F6 v4.0 标注] INSERT IGNORE 仅按主键 id 幂等,不应用 3 键去重
            cursor.execute(
                'INSERT IGNORE INTO process_sub_steps '
                '(id, process_id, order_no, step_name, batch_no, quantity, qualified_qty, operator, remark, equipment_name, overtime_hours, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (
                    data.get('id', ''),
                    data.get('process_id', ''),
                    data.get('order_no', ''),
                    data.get('step_name', ''),
                    data.get('batch_no', ''),
                    float(data.get('quantity', 0) or 0),
                    float(data.get('qualified_qty', data.get('quantity', 0)) or 0),
                    data.get('operator', ''),
                    data.get('remark', ''),
                    data.get('equipment_name', ''),
                    float(data.get('overtime_hours', 0) or 0),
                    data.get('created_at', datetime.now().isoformat())
                )
            )
            logger.info('sub_step synced to wechat_container.db: %s/%s qty=%s qualified=%s',
                        data.get('order_no', '?'), data.get('step_name', '?'),
                        data.get('quantity', 0), data.get('qualified_qty', data.get('quantity', 0)))
            SyncLog.write('sub_step.created', 'legacy_to_container',
                          data.get('id', ''), 'success')
    except Exception as e:
        logger.warning('sync to wechat_container.db failed: %s', e)
        SyncLog.write('sub_step.created', 'legacy_to_container',
                      data.get('id', ''), 'failed', str(e))


def _sync_to_chengsheng_db(data: dict):
    """sync sub_step record to chengsheng.db"""
    try:
        with mysql_cursor() as cursor:
            conn = cursor.connection
            ensure_table(conn, 'sub_steps', use_transaction=False)
            cursor.execute(
                'INSERT IGNORE INTO sub_steps '
                '(step_id, process_id, order_no, customer_group, step_name, batch_no, quantity, qualified_qty, operator, remark, equipment_name, overtime_hours, created_at) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (
                    data.get('id', ''),
                    data.get('process_id', ''),
                    data.get('order_no', ''),
                    data.get('customer_group', ''),
                    data.get('step_name', ''),
                    data.get('batch_no', ''),
                    float(data.get('quantity', 0) or 0),
                    float(data.get('qualified_qty', data.get('quantity', 0)) or 0),
                    data.get('operator', ''),
                    data.get('remark', ''),
                    data.get('equipment_name', ''),
                    float(data.get('overtime_hours', 0) or 0),
                    data.get('created_at', datetime.now().isoformat())
                )
            )
            logger.info('sub_step synced to chengsheng.db: %s/%s qty=%s qualified=%s',
                        data.get('order_no', '?'), data.get('step_name', '?'),
                        data.get('quantity', 0), data.get('qualified_qty', data.get('quantity', 0)))
            SyncLog.write('sub_step.created', 'container_to_cs',
                          data.get('id', ''), 'success')
    except Exception as e:
        logger.warning('sync to chengsheng.db failed: %s', e)
        SyncLog.write('sub_step.created', 'container_to_cs',
                      data.get('id', ''), 'failed', str(e))


@circuit_protected("sync_advance_check")
def _call_internal_advance_check(data: dict):
    """call internal API to trigger process advance check after sync"""
    process_id = data.get('process_id')
    step_name = data.get('step_name')
    if not process_id or not step_name:
        return

    internal_url = os.environ.get('INTERNAL_API_URL', 'http://localhost:5002')
    try:
        resp = requests.post(
            f'{internal_url}/api/internal/check-advance',
            json={
                'process_id': process_id,
                'step_name': step_name
            },
            timeout=5
        )
        if resp.status_code == 200:
            logger.info('advance check completed: process_id=%s', process_id)
    except Exception as e:
        logger.warning('advance check request failed(non-fatal): %s', e)


def handle_sub_step_created(data: dict):
    """
    Event handler for sub_step.created event.

    - If source is 'legacy': sync to container_center.process_sub_steps (legacy 兼容路径)
    - Otherwise (from container_center_api): sync to chengsheng.db
    - Always call internal API for advance check after sync
    """
    source = data.get('_source', '')
    if source == 'legacy':
        _sync_to_container_db(data)
    else:
        _sync_to_chengsheng_db(data)
    _call_internal_advance_check(data)
    _update_process_record_status(data)


def _update_process_record_status(data: dict):
    """报工回写后更新 steel_belt.process_records 状态"""
    process_id = data.get('process_id', '')
    if not process_id or not process_id.startswith('PR-'):
        return
    record_id = process_id.replace('PR-', '')
    if not record_id.isdigit():
        return
    try:
        quantity = float(data.get('quantity', 0) or 0)
        qualified_qty = float(data.get('qualified_qty', quantity) or 0)
        work_hours = float(data.get('overtime_hours', data.get('hours', 0)) or 0)
        with mysql_cursor() as cursor:
            conn = cursor.connection
            cursor.execute(
                'UPDATE process_records SET completed_qty = COALESCE(completed_qty,0) + %s, '
                'qualified_qty = COALESCE(qualified_qty,0) + %s, '
                'work_hours = COALESCE(work_hours,0) + %s, '
                'status = CASE WHEN COALESCE(completed_qty,0) + %s >= planned_qty THEN %s ELSE %s END, '
                'updated_at = NOW() '
                'WHERE id = %s',
                (quantity, qualified_qty, work_hours,
                 quantity, '已完成', '进行中', int(record_id))
            )
            logger.info('process_record status updated: id=%s qty=+%s', record_id, quantity)
    except Exception as e:
        logger.warning('update process_record status failed: %s', e)

