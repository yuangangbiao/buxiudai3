# -*- coding: utf-8 -*-
import logging
from contextlib import contextmanager
from core.db import get_direct_connection
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT

logger = logging.getLogger(__name__)


class SyncLog:

    @staticmethod
    def _get_cfg() -> dict:
        return CONTAINER_MYSQL_CFG

    @staticmethod
    @contextmanager
    def _get_cursor():
        cfg = SyncLog._get_cfg()
        conn = get_direct_connection(
            **cfg,
            connect_timeout=DB_CONNECT_TIMEOUT
        )
        cursor = None
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception(f"Database operation failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def ensure_table():
        with SyncLog._get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(64),
                    direction VARCHAR(16),
                    record_id VARCHAR(128),
                    status VARCHAR(32) DEFAULT 'success',
                    error_msg TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("sync_log table ensured")

    @staticmethod
    def write(event_type: str, direction: str, record_id: str,
              status: str = 'success', error_msg: str = None):
        with SyncLog._get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO sync_log (event_type, direction, record_id, status, error_msg) "
                "VALUES (%s, %s, %s, %s, %s)",
                (event_type, direction, record_id, status, error_msg)
            )
            logger.info(f"SyncLog written: {event_type}/{direction}/{record_id} -> {status}")
