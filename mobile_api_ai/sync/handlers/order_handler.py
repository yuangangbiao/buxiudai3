# -*- coding: utf-8 -*-
import logging
import os
from .. import mysql_cursor
from contextlib import contextmanager

from core.config import BASE_DIR
from sync.mappers.field_mapper import map_process_to_order
from sync.sync_log import SyncLog

logger = logging.getLogger(__name__)



@contextmanager


def _ensure_orders_sync_columns():
    try:
        with mysql_cursor() as cursor:
            cursor.execute("PRAGMA table_info(orders)")
            columns = {row['name'] for row in cursor.fetchall()}
            if 'dc_process_id' not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN dc_process_id TEXT DEFAULT ''")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE orders ADD COLUMN updated_at TEXT DEFAULT ''")
    except Exception as e:
        logger.warning('ensure orders sync columns failed (non-fatal): %s', e)


def handle_process_created(data: dict):
    process_id = data.get('id', '')
    order_no = data.get('order_no', '')
    if not process_id and not order_no:
        logger.warning('process.created event missing id/order_no')
        return
    try:
        _ensure_orders_sync_columns()
        mapped = map_process_to_order(data)
        with mysql_cursor() as cursor:
            cursor.execute(
                "SELECT id FROM orders WHERE order_no = %s",
                (mapped['order_no'],)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE orders SET dc_process_id=%s, status=%s, product_name=%s, quantity=%s, current_step=%s, flow_type=%s, remark=%s, updated_at=? WHERE order_no=?",
                    (mapped['dc_process_id'], mapped['status'], mapped['product_name'], mapped['quantity'], mapped['current_step'], mapped['flow_type'], mapped['remark'], mapped['updated_at'], mapped['order_no'])
                )
                logger.info('order updated via process.created: %s', mapped['order_no'])
            else:
                cursor.execute(
                    "INSERT INTO orders (order_no, dc_process_id, status, product_name, quantity, current_step, flow_type, remark, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (mapped['order_no'], mapped['dc_process_id'], mapped['status'], mapped['product_name'], mapped['quantity'], mapped['current_step'], mapped['flow_type'], mapped['remark'], mapped['updated_at'])
                )
                logger.info('order created via process.created: %s', mapped['order_no'])
        SyncLog.write('process.created', 'dc_to_cs', process_id, 'success')
    except Exception as e:
        logger.warning('process.created sync failed: %s', e)
        SyncLog.write('process.created', 'dc_to_cs', process_id, 'failed', str(e))


def handle_process_updated(data: dict):
    process_id = data.get('id', '')
    order_no = data.get('order_no', '')
    if not process_id and not order_no:
        logger.warning('process.updated event missing id/order_no')
        return
    try:
        _ensure_orders_sync_columns()
        mapped = map_process_to_order(data)
        with mysql_cursor() as cursor:
            cursor.execute(
                "UPDATE orders SET dc_process_id=%s, status=%s, product_name=%s, quantity=%s, current_step=%s, flow_type=%s, remark=%s, updated_at=? WHERE order_no=?",
                (mapped['dc_process_id'], mapped['status'], mapped['product_name'], mapped['quantity'], mapped['current_step'], mapped['flow_type'], mapped['remark'], mapped['updated_at'], mapped['order_no'])
            )
            if cursor.rowcount > 0:
                logger.info('order status updated via process.updated: %s status=%s',
                            mapped['order_no'], mapped['status'])
            else:
                cursor.execute(
                    "INSERT IGNORE INTO orders (order_no, dc_process_id, status, product_name, quantity, current_step, flow_type, remark, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (mapped['order_no'], mapped['dc_process_id'], mapped['status'], mapped['product_name'], mapped['quantity'], mapped['current_step'], mapped['flow_type'], mapped['remark'], mapped['updated_at'])
                )
                logger.info('order inserted via process.updated: %s', mapped['order_no'])
        SyncLog.write('process.updated', 'dc_to_cs', process_id, 'success')
    except Exception as e:
        logger.warning('process.updated sync failed: %s', e)
        SyncLog.write('process.updated', 'dc_to_cs', process_id, 'failed', str(e))
