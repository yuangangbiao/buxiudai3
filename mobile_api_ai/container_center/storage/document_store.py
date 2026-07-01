import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .mysql_router import MySQLRouter

logger = logging.getLogger(__name__)


class DocumentStore:
    def __init__(self, router=None):
        self.router = router or MySQLRouter()
        self._init_tables()

    def _init_tables(self):
        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tbl_documents (
                        id          VARCHAR(64) PRIMARY KEY,
                        doc_type    VARCHAR(64) NOT NULL,
                        doc_data    LONGTEXT NOT NULL,
                        status      VARCHAR(32) DEFAULT 'pending',
                        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                try:
                    cur.execute("CREATE INDEX idx_documents_type_status ON tbl_documents(doc_type, status)")
                except Exception:
                    pass
                try:
                    cur.execute("CREATE INDEX idx_documents_updated ON tbl_documents(updated_at)")
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
        d = dict(row)
        try:
            d['doc_data'] = json.loads(d['doc_data'])
        except (json.JSONDecodeError, TypeError):
            pass
        return d

    def create(self, doc_type: str, data: dict, doc_id: Optional[str] = None,
               status: str = 'pending') -> Dict:
        now = self._now()
        doc_id = doc_id or self._new_id()
        doc_data_json = json.dumps(data, ensure_ascii=False, default=str)

        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                """INSERT INTO tbl_documents (id, doc_type, doc_data, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (doc_id, doc_type, doc_data_json, status, now, now)
            )

        return {
            'id': doc_id,
            'doc_type': doc_type,
            'doc_data': data,
            'status': status,
            'created_at': now,
            'updated_at': now,
        }

    def get(self, doc_id: str, doc_type: Optional[str] = None) -> Optional[Dict]:
        if doc_type:
            with self.router.get_db_cursor(doc_type) as cur:
                cur.execute(
                    "SELECT * FROM tbl_documents WHERE id = %s", (doc_id,)
                )
                row = cur.fetchone()
            return self._row_to_dict(row)

        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                cur.execute(
                    "SELECT * FROM tbl_documents WHERE id = %s", (doc_id,)
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
        return None

    def update(self, doc_id: str, fields: dict, doc_type: Optional[str] = None) -> bool:
        now = self._now()

        if doc_type:
            with self.router.get_db_cursor(doc_type) as cur:
                cur.execute(
                    "SELECT doc_data FROM tbl_documents WHERE id = %s", (doc_id,)
                )
                row = cur.fetchone()
                if not row:
                    return False
                current_data = json.loads(row['doc_data']) if row['doc_data'] else {}
                current_data.update(fields)
                updated_json = json.dumps(current_data, ensure_ascii=False, default=str)
                cur.execute(
                    "UPDATE tbl_documents SET doc_data = %s, updated_at = %s WHERE id = %s",
                    (updated_json, now, doc_id)
                )
            return True

        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                cur.execute(
                    "SELECT doc_data FROM tbl_documents WHERE id = %s", (doc_id,)
                )
                row = cur.fetchone()
                if row:
                    current_data = json.loads(row['doc_data']) if row['doc_data'] else {}
                    current_data.update(fields)
                    updated_json = json.dumps(current_data, ensure_ascii=False, default=str)
                    cur.execute(
                        "UPDATE tbl_documents SET doc_data = %s, updated_at = %s WHERE id = %s",
                        (updated_json, now, doc_id)
                    )
                    return True
        return False

    def update_status(self, doc_id: str, status: str,
                      doc_type: Optional[str] = None) -> bool:
        now = self._now()

        if doc_type:
            with self.router.get_db_cursor(doc_type) as cur:
                cur.execute(
                    "UPDATE tbl_documents SET status = %s, updated_at = %s WHERE id = %s",
                    (status, now, doc_id)
                )
                return cur.rowcount > 0

        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                cur.execute(
                    "UPDATE tbl_documents SET status = %s, updated_at = %s WHERE id = %s",
                    (status, now, doc_id)
                )
                if cur.rowcount > 0:
                    return True
        return False

    def delete(self, doc_id: str, doc_type: Optional[str] = None) -> bool:
        if doc_type:
            with self.router.get_db_cursor(doc_type) as cur:
                cur.execute("DELETE FROM tbl_documents WHERE id = %s", (doc_id,))
                return cur.rowcount > 0

        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                cur.execute("DELETE FROM tbl_documents WHERE id = %s", (doc_id,))
                if cur.rowcount > 0:
                    return True
        return False

    def query(self, doc_type: str, status: Optional[str] = None,
              q: Optional[str] = None, page: int = 1, size: int = 50,
              sort: str = '-updated_at') -> Dict:
        conditions = ["doc_type = %s"]
        params = [doc_type]

        if status:
            conditions.append("status = %s")
            params.append(status)

        if q:
            conditions.append("doc_data LIKE %s")
            params.append(f'%{q}%')

        where_clause = " AND ".join(conditions)

        if sort.startswith('-'):
            order_col = sort[1:]
            order_dir = "DESC"
        else:
            order_col = sort
            order_dir = "ASC"

        allowed_sort_cols = {'created_at', 'updated_at', 'status', 'doc_type'}
        if order_col not in allowed_sort_cols:
            order_col = 'updated_at'
            order_dir = 'DESC'

        offset = (page - 1) * size

        with self.router.get_db_cursor(doc_type) as cur:
            cur.execute(
                f"SELECT COUNT(*) as cnt FROM tbl_documents WHERE {where_clause}",
                params
            )
            total = cur.fetchone()['cnt']

            cur.execute(
                f"SELECT * FROM tbl_documents WHERE {where_clause} "
                f"ORDER BY {order_col} {order_dir} LIMIT %s OFFSET %s",
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

    def query_all(self, q: Optional[str] = None, page: int = 1,
                  size: int = 50) -> Dict:
        all_results = []
        for db_name in self.router.get_all_db_names():
            with self.router.get_db_cursor_by_name(db_name) as cur:
                if q:
                    cur.execute(
                        "SELECT * FROM tbl_documents WHERE doc_data LIKE %s "
                        "ORDER BY updated_at DESC",
                        (f'%{q}%',)
                    )
                else:
                    cur.execute(
                        "SELECT * FROM tbl_documents ORDER BY updated_at DESC"
                    )
                for row in cur.fetchall():
                    all_results.append(self._row_to_dict(row))

        all_results.sort(key=lambda x: x.get('updated_at', ''), reverse=True)

        total = len(all_results)
        offset = (page - 1) * size
        page_items = all_results[offset:offset + size]
        total_pages = max(1, (total + size - 1) // size)

        return {
            'data': page_items,
            'page': page,
            'size': size,
            'total': total,
            'total_pages': total_pages,
        }

    def get_packages(self, doc_type: str = 'work_order', status: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        result = self.query(doc_type=doc_type, status=status, size=limit)
        return result['data']

    def get_package(self, pkg_id: str, doc_type: Optional[str] = None) -> Optional[Dict]:
        return self.get(pkg_id, doc_type)

    def save_package(self, data: dict, doc_type: str = 'work_order',
                     status: str = 'pending') -> Dict:
        pkg_id = data.get('id')
        return self.create(doc_type=doc_type, data=data, doc_id=pkg_id, status=status)

    def update_package(self, pkg_id: str, fields: dict,
                       doc_type: Optional[str] = None) -> bool:
        return self.update(pkg_id, fields, doc_type)

    def update_package_status(self, pkg_id: str, status: str,
                              doc_type: Optional[str] = None) -> bool:
        return self.update_status(pkg_id, status, doc_type)

    def delete_package(self, pkg_id: str, doc_type: Optional[str] = None) -> bool:
        return self.delete(pkg_id, doc_type)
