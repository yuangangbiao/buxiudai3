import logging
from typing import List, Optional

from .mysql_router import MySQLRouter

logger = logging.getLogger(__name__)


class IndexStore:
    def __init__(self, router=None):
        self.router = router or MySQLRouter()
        self._init_tables()

    def _init_tables(self):
        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tbl_indexes (
                        id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                        doc_type    VARCHAR(255) NOT NULL,
                        doc_id      VARCHAR(255) NOT NULL,
                        key_name    VARCHAR(255) NOT NULL,
                        key_value   VARCHAR(255) NOT NULL
                    )
                """)
                try:
                    cur.execute("CREATE INDEX idx_indexes_lookup ON tbl_indexes(doc_type, key_name)")
                except Exception:
                    pass
                try:
                    cur.execute("CREATE INDEX idx_indexes_doc_id ON tbl_indexes(doc_id)")
                except Exception:
                    pass

    def set_index(self, doc_type: str, doc_id: str, key_name: str,
                  key_value: str) -> bool:
        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                """REPLACE INTO tbl_indexes (doc_type, doc_id, key_name, key_value)
                   VALUES (%s, %s, %s, %s)""",
                (doc_type, doc_id, key_name, key_value)
            )
        return True

    def set_indexes(self, doc_type: str, doc_id: str,
                    index_map: dict) -> bool:
        with self.router.get_db_cursor(doc_type) as cur:
            for key_name, key_value in index_map.items():
                cur.execute(
                    """REPLACE INTO tbl_indexes (doc_type, doc_id, key_name, key_value)
                       VALUES (%s, %s, %s, %s)""",
                    (doc_type, doc_id, key_name, str(key_value))
                )
        return True

    def delete_indexes(self, doc_type: str, doc_id: str) -> bool:
        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                "DELETE FROM tbl_indexes WHERE doc_type = %s AND doc_id = %s",
                (doc_type, doc_id)
            )
        return True

    def delete_index(self, doc_type: str, doc_id: str,
                     key_name: str) -> bool:
        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                "DELETE FROM tbl_indexes WHERE doc_type = %s AND doc_id = %s AND key_name = %s",
                (doc_type, doc_id, key_name)
            )
        return True

    def query_by_index(self, doc_type: str, key_name: str,
                       key_value: str) -> List[str]:
        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                """SELECT doc_id FROM tbl_indexes
                   WHERE doc_type = %s AND key_name = %s AND key_value = %s
                   ORDER BY id""",
                (doc_type, key_name, key_value)
            )
            return [row['doc_id'] for row in cur.fetchall()]

    def get_index_value(self, doc_type: str, doc_id: str,
                        key_name: str) -> Optional[str]:
        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                """SELECT key_value FROM tbl_indexes
                   WHERE doc_type = %s AND doc_id = %s AND key_name = %s""",
                (doc_type, doc_id, key_name)
            )
            row = cur.fetchone()
            return row['key_value'] if row else None

    def get_all_indexes(self, doc_type: str, doc_id: str) -> dict:
        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                "SELECT key_name, key_value FROM tbl_indexes WHERE doc_type = %s AND doc_id = %s",
                (doc_type, doc_id)
            )
            return {row['key_name']: row['key_value'] for row in cur.fetchall()}
