import logging

logger = logging.getLogger(__name__)

_ensure_table_cache = set()

SCHEMA_REGISTRY = {
    'process_sub_steps': {
        'columns': {
            'id': 'TEXT PRIMARY KEY',
            'process_id': 'TEXT DEFAULT ""',
            'order_no': 'TEXT NOT NULL',
            'customer_group': 'TEXT DEFAULT ""',
            'step_name': 'TEXT NOT NULL',
            'batch_no': 'TEXT NOT NULL',
            'quantity': 'REAL NOT NULL DEFAULT 0',
            'qualified_qty': 'REAL DEFAULT 0',
            'operator': 'TEXT DEFAULT ""',
            'remark': 'TEXT DEFAULT ""',
            'equipment_name': 'TEXT DEFAULT ""',
            'overtime_hours': 'REAL DEFAULT 0',
            'created_at': 'TEXT NOT NULL',
        },
        'indexes': [
            'CREATE INDEX IF NOT EXISTS idx_sub_steps_order ON process_sub_steps(order_no)',
        ]
    },
    'sub_steps': {
        'columns': {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'step_id': 'TEXT NOT NULL UNIQUE',
            'process_id': 'TEXT',
            'order_no': 'TEXT',
            'customer_group': 'TEXT',
            'step_name': 'TEXT',
            'batch_no': 'TEXT',
            'quantity': 'REAL DEFAULT 0',
            'qualified_qty': 'REAL DEFAULT 0',
            'operator': 'TEXT',
            'remark': 'TEXT',
            'equipment_name': 'TEXT',
            'overtime_hours': 'REAL DEFAULT 0',
            'created_at': 'TEXT',
        },
    },
}


def ensure_table(conn, table_name, use_transaction=True):
    if table_name in _ensure_table_cache:
        return False

    schema = SCHEMA_REGISTRY.get(table_name)
    if not schema:
        raise ValueError(f"Unknown table: {table_name}")

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        cols_def = ', '.join(f'{k} {v}' for k, v in schema['columns'].items())
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({cols_def})')
        for idx in schema.get('indexes', []):
            cursor.execute(idx)
        if use_transaction:
            conn.commit()
        logger.info('auto-created table: %s', table_name)
        _ensure_table_cache.add(table_name)
        return True

    cursor.execute(f'PRAGMA table_info({table_name})')
    existing = {row[1] for row in cursor.fetchall()}

    added = []
    for col_name, col_def in schema['columns'].items():
        if col_name not in existing:
            try:
                cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}')
                added.append(col_name)
            except Exception as e:
                logger.warning('failed to add column %s to %s: %s', col_name, table_name, e)

    for idx in schema.get('indexes', []):
        cursor.execute(idx)

    if added and use_transaction:
        conn.commit()
        logger.info('auto-added columns to %s: %s', table_name, ', '.join(added))

    _ensure_table_cache.add(table_name)

    return bool(added)
