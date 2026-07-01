# -*- coding: utf-8 -*-
import logging
import os
from .. import container_cursor
from contextlib import contextmanager

from core.config import BASE_DIR
from sync.mappers.field_mapper import map_operator_to_worker
from sync.sync_log import SyncLog

logger = logging.getLogger(__name__)


@contextmanager

def _ensure_workers_sync_columns():
    try:
        with container_cursor() as cursor:
            cursor.execute("PRAGMA table_info(workers)")
            columns = {row['name'] for row in cursor.fetchall()}
            if 'dc_operator_id' not in columns:
                cursor.execute("ALTER TABLE workers ADD COLUMN dc_operator_id TEXT DEFAULT ''")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE workers ADD COLUMN updated_at TEXT DEFAULT ''")
            if 'enabled' not in columns:
                cursor.execute("ALTER TABLE workers ADD COLUMN enabled INTEGER DEFAULT 1")
    except Exception as e:
        logger.warning('ensure workers sync columns failed (non-fatal): %s', e)


def handle_operator_created(data: dict):
    operator_id = data.get('id', '')
    if not operator_id:
        logger.warning('operator.created event missing id')
        return
    try:
        _ensure_workers_sync_columns()
        mapped = map_operator_to_worker(data)
        with container_cursor() as cursor:
            cursor.execute(
                "SELECT id FROM workers WHERE worker_id = %s OR dc_operator_id = %s",
                (operator_id, operator_id)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE workers SET name=%s, role=%s, department=%s, dc_operator_id=? WHERE id=?",
                    (mapped['name'], mapped['role'], mapped['department'], mapped['dc_operator_id'], existing['id'])
                )
                logger.info('worker updated via operator.created: %s', operator_id)
            else:
                cursor.execute(
                    "INSERT INTO workers (worker_id, name, role, department, dc_operator_id, enabled) VALUES (%s, %s, %s, %s, %s, %s)",
                    (mapped['worker_id'], mapped['name'], mapped['role'], mapped['department'], mapped['dc_operator_id'], 1 if mapped.get('enabled', True) else 0)
                )
                logger.info('worker created via operator.created: %s', operator_id)
        SyncLog.write('operator.created', 'dc_to_cs', operator_id, 'success')
    except Exception as e:
        logger.warning('operator.created sync failed: %s', e)
        SyncLog.write('operator.created', 'dc_to_cs', operator_id, 'failed', str(e))


def handle_operator_updated(data: dict):
    operator_id = data.get('id', '')
    if not operator_id:
        logger.warning('operator.updated event missing id')
        return
    try:
        _ensure_workers_sync_columns()
        with container_cursor() as cursor:
            set_parts = []
            params = []
            if 'name' in data:
                set_parts.append("name=?")
                params.append(data['name'])
            if 'role' in data:
                set_parts.append("role=?")
                params.append(data['role'])
            if 'department' in data:
                set_parts.append("department=?")
                params.append(data['department'])
            if 'enabled' in data:
                set_parts.append("enabled=?")
                params.append(1 if data['enabled'] else 0)
            if not set_parts:
                logger.info('operator.updated: no updatable fields, skipped: %s', operator_id)
                SyncLog.write('operator.updated', 'dc_to_cs', operator_id, 'skipped')
                return
            params.extend([operator_id, operator_id])
            cursor.execute(
                f"UPDATE workers SET {', '.join(set_parts)} WHERE worker_id=? OR dc_operator_id=?",
                params
            )
            if cursor.rowcount > 0:
                logger.info('worker updated via operator.updated: %s fields=%s', operator_id, list(data.keys()))
            else:
                mapped = map_operator_to_worker(data)
                cursor.execute(
                    "INSERT INTO workers (worker_id, name, role, department, dc_operator_id, enabled) VALUES (%s, %s, %s, %s, %s, %s)",
                    (mapped['worker_id'], mapped['name'], mapped['role'], mapped['department'], mapped['dc_operator_id'], 1 if mapped.get('enabled', True) else 0)
                )
                logger.info('worker inserted via operator.updated: %s', operator_id)
        SyncLog.write('operator.updated', 'dc_to_cs', operator_id, 'success')
    except Exception as e:
        logger.warning('operator.updated sync failed: %s', e)
        SyncLog.write('operator.updated', 'dc_to_cs', operator_id, 'failed', str(e))


def handle_operator_deleted(data: dict):
    operator_id = data.get('id', '')
    if not operator_id:
        logger.warning('operator.deleted event missing id')
        return
    try:
        with container_cursor() as cursor:
            cursor.execute(
                "DELETE FROM workers WHERE worker_id=? OR dc_operator_id=?",
                (operator_id, operator_id)
            )
            if cursor.rowcount > 0:
                logger.info('worker deleted via operator.deleted: %s', operator_id)
            else:
                logger.info('worker not found for operator.deleted: %s', operator_id)
        SyncLog.write('operator.deleted', 'dc_to_cs', operator_id, 'success')
    except Exception as e:
        logger.warning('operator.deleted sync failed: %s', e)
        SyncLog.write('operator.deleted', 'dc_to_cs', operator_id, 'failed', str(e))
