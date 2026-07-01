import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .mysql_router import MySQLRouter

logger = logging.getLogger(__name__)

ALERT_DB = 'orders'


class AlertStore:
    def __init__(self, router=None):
        self.router = router or MySQLRouter()
        self._init_tables()

    def _init_tables(self):
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_alerts (
                    id          VARCHAR(64) PRIMARY KEY,
                    alert_type  VARCHAR(255) NOT NULL,
                    doc_id      VARCHAR(255),
                    title       VARCHAR(255) NOT NULL,
                    content     LONGTEXT NOT NULL,
                    level       VARCHAR(32) NOT NULL DEFAULT 'WARNING',
                    dismissed   INT DEFAULT 0,
                    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cur.execute("CREATE INDEX idx_alerts_type ON tbl_alerts(alert_type)")
            except Exception:
                pass
            try:
                cur.execute("CREATE INDEX idx_alerts_dismissed ON tbl_alerts(dismissed)")
            except Exception:
                pass
            try:
                cur.execute("CREATE INDEX idx_alerts_created ON tbl_alerts(created_at)")
            except Exception:
                pass

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _new_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _row_to_dict(row) -> Optional[Dict]:
        if row is None:
            return None
        return dict(row)

    def create(self, alert_type: str, title: str, content: str,
               doc_id: Optional[str] = None,
               level: str = 'WARNING',
               alert_id: Optional[str] = None) -> Dict:
        now = self._now()
        alert_id = alert_id or self._new_id()

        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                """INSERT INTO tbl_alerts (id, alert_type, doc_id, title, content, level, dismissed, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, 0, %s)""",
                (alert_id, alert_type, doc_id, title, content, level, now)
            )

        return {
            'id': alert_id,
            'alert_type': alert_type,
            'doc_id': doc_id,
            'title': title,
            'content': content,
            'level': level,
            'dismissed': 0,
            'created_at': now,
        }

    def get(self, alert_id: str) -> Optional[Dict]:
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                "SELECT * FROM tbl_alerts WHERE id = %s", (alert_id,)
            )
            return self._row_to_dict(cur.fetchone())

    def dismiss(self, alert_id: str) -> bool:
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                "UPDATE tbl_alerts SET dismissed = 1 WHERE id = %s",
                (alert_id,)
            )
            return cur.rowcount > 0

    def acknowledge(self, alert_id: str, operator_id: str = '') -> bool:
        """确认告警"""
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                "UPDATE tbl_alerts SET acknowledged_at=NOW(), acknowledged_by=%s WHERE id=%s",
                (operator_id, alert_id)
            )
            return cur.rowcount > 0

    def update(self, alert_id: str, fields: dict) -> bool:
        """通用字段更新"""
        if not fields:
            return False
        sets = ', '.join(f'{k}=%s' for k in fields)
        vals = list(fields.values()) + [alert_id]
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(f"UPDATE tbl_alerts SET {sets} WHERE id=%s", vals)
            return cur.rowcount > 0

    def delete(self, alert_id: str) -> bool:
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                "DELETE FROM tbl_alerts WHERE id = %s", (alert_id,)
            )
            return cur.rowcount > 0

    def query(self, alert_type: Optional[str] = None,
              level: Optional[str] = None,
              dismissed: Optional[int] = None,
              page: int = 1, size: int = 50) -> Dict:
        conditions = []
        params = []

        if alert_type:
            conditions.append("alert_type = %s")
            params.append(alert_type)
        if level:
            conditions.append("level = %s")
            params.append(level)
        if dismissed is not None:
            conditions.append("dismissed = %s")
            params.append(dismissed)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        offset = (page - 1) * size

        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                f"SELECT COUNT(*) as cnt FROM tbl_alerts {where_clause}",
                params
            )
            total = cur.fetchone()['cnt']

            cur.execute(
                f"SELECT * FROM tbl_alerts {where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [size, offset]
            )
            rows = cur.fetchall()

        items = [self._row_to_dict(r) for r in rows]
        total_pages = max(1, (total + size - 1) // size)

        return {
            'data': items,
            'page': page,
            'size': size,
            'total': total,
            'total_pages': total_pages,
        }

    def get_undismissed(self, alert_type: Optional[str] = None,
                        limit: int = 100) -> List[Dict]:
        conditions = ["dismissed = 0"]
        params = []

        if alert_type:
            conditions.append("alert_type = %s")
            params.append(alert_type)

        where_clause = "WHERE " + " AND ".join(conditions)

        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute(
                f"SELECT * FROM tbl_alerts {where_clause} ORDER BY created_at DESC LIMIT ?",
                params + [limit]
            )
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_statistics(self) -> Dict:
        with self.router.get_db_cursor_by_name(ALERT_DB) as cur:
            cur.execute("""
                SELECT alert_type, level, COUNT(*) as cnt
                FROM tbl_alerts
                WHERE dismissed = 0
                GROUP BY alert_type, level
            """)
            stats = {}
            for row in cur.fetchall():
                key = f"{row['alert_type']}_{row['level']}"
                stats[key] = row['cnt']
            return stats
