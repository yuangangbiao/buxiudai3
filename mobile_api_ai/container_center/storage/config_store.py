import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .mysql_router import MySQLRouter

logger = logging.getLogger(__name__)

SYSTEM_DB = 'system'


class ConfigStore:
    def __init__(self, router=None):
        self.router = router or MySQLRouter()
        self._init_tables()

    def _init_tables(self):
        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_configs (
                    config_name VARCHAR(128) PRIMARY KEY,
                    config_data LONGTEXT NOT NULL,
                    version     INTEGER DEFAULT 1,
                    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    def get(self, config_name: str) -> Optional[Any]:
        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute(
                "SELECT config_data FROM tbl_configs WHERE config_name = %s",
                (config_name,)
            )
            row = cur.fetchone()
            if row is None:
                return None
            try:
                return json.loads(row['config_data'])
            except (json.JSONDecodeError, TypeError):
                return row['config_data']

    def get_with_meta(self, config_name: str) -> Optional[Dict]:
        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute(
                "SELECT * FROM tbl_configs WHERE config_name = %s",
                (config_name,)
            )
            row = cur.fetchone()
            if row is None:
                return None
            result = dict(row)
            try:
                result['config_data'] = json.loads(result['config_data'])
            except (json.JSONDecodeError, TypeError):
                pass
            return result

    def set(self, config_name: str, config_data: Any) -> bool:
        now = self._now()
        data_json = json.dumps(config_data, ensure_ascii=False, default=str)

        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute(
                """INSERT INTO tbl_configs (config_name, config_data, version, updated_at)
                   VALUES (%s, %s, 1, %s)
                   ON CONFLICT(config_name) DO UPDATE SET
                       config_data = excluded.config_data,
                       version = version + 1,
                       updated_at = excluded.updated_at""",
                (config_name, data_json, now)
            )
        return True

    def delete(self, config_name: str) -> bool:
        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute(
                "DELETE FROM tbl_configs WHERE config_name = %s",
                (config_name,)
            )
            return cur.rowcount > 0

    def list_names(self) -> list:
        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute(
                "SELECT config_name FROM tbl_configs ORDER BY config_name"
            )
            return [row['config_name'] for row in cur.fetchall()]

    def get_all(self) -> dict:
        with self.router.get_db_cursor_by_name(SYSTEM_DB) as cur:
            cur.execute(
                "SELECT config_name, config_data FROM tbl_configs ORDER BY config_name"
            )
            result = {}
            for row in cur.fetchall():
                try:
                    result[row['config_name']] = json.loads(row['config_data'])
                except (json.JSONDecodeError, TypeError):
                    result[row['config_name']] = row['config_data']
            return result
