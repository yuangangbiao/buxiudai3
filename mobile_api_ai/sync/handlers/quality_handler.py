# -*- coding: utf-8 -*-
import json
import logging
import os
from .. import mysql_cursor
from contextlib import contextmanager

from core.config import BASE_DIR
from sync.sync_log import SyncLog

logger = logging.getLogger(__name__)



@contextmanager


def _ensure_quality_table():
    try:
        with mysql_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_records (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    package_id TEXT NOT NULL,
                    order_no TEXT NOT NULL,
                    result TEXT DEFAULT 'pass',
                    inspection_type TEXT DEFAULT '巡检',
                    defect_description TEXT DEFAULT '',
                    inspector TEXT DEFAULT '',
                    inspection_items TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    synced_at TEXT DEFAULT (datetime('now','localtime'))
                )
            ''')
    except Exception as e:
        logger.warning('ensure quality_records table failed (non-fatal): %s', e)


def handle_quality_updated(data: dict):
    order_no = data.get('order_no', '')
    inspector = data.get('inspector', '') or data.get('inspector_id', '')
    inspection_type = data.get('inspection_type', '巡检')
    result = data.get('result', 'pass')
    defect_desc = data.get('defect_description', '')
    inspection_items = data.get('inspection_items', [])
    package_id = data.get('package_id', '')
    created_at = data.get('created_at', '')
    if not order_no:
        logger.warning('quality.updated event missing order_no')
        return
    try:
        _ensure_quality_table()
        with mysql_cursor() as cursor:
            cursor.execute(
                "INSERT INTO quality_records (package_id, order_no, result, inspection_type, defect_description, inspector, inspection_items, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    package_id,
                    order_no,
                    result,
                    inspection_type,
                    defect_desc,
                    inspector,
                    json.dumps(inspection_items, ensure_ascii=False),
                    created_at
                )
            )
        logger.info('quality record synced to chengsheng.db: order=%s result=%s', order_no, result)
        SyncLog.write('quality.updated', 'dc_to_cs', package_id or order_no, 'success')
    except Exception as e:
        logger.warning('quality.updated sync failed: %s', e)
        SyncLog.write('quality.updated', 'dc_to_cs', package_id or order_no, 'failed', str(e))
