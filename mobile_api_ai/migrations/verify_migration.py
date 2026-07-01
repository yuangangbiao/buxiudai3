# -*- coding: utf-8 -*-
"""Verify migration result"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
if not os.path.exists(env_file):
    env_file = os.path.join(os.path.dirname(__file__), '..', 'mobile_api_ai', '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

import pymysql
conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('CONTAINER_MYSQL_DATABASE', 'container_center'),
    charset='utf8mb4'
)
cur = conn.cursor()

print('=' * 70, flush=True)
print('Migration Verification', flush=True)
print('=' * 70, flush=True)

# 1. Row counts after migration
tables = ['process_sub_steps', 'quality_records', 'material_records', 'outsource_records']
print('\n[1] Row counts after cleanup:', flush=True)
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f'  {table}: {count} rows', flush=True)

# 2. Verify indexes
print('\n[2] Unique indexes:', flush=True)
expected_indexes = [
    ('process_sub_steps', 'uk_active_task'),
    ('quality_records',   'uk_active_quality'),
    ('material_records',  'uk_active_material'),
    ('outsource_records', 'uk_active_outsource'),
]
for table, idx in expected_indexes:
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema=DATABASE() AND table_name=%s AND index_name=%s",
        (table, idx))
    exists = cur.fetchone()[0] > 0
    status = '[OK]' if exists else '[FAIL]'
    print(f'  {status} {table}.{idx}', flush=True)

# 3. Test constraint: try to insert duplicate
print('\n[3] Test constraint (insert duplicate):', flush=True)

# First check id column type
cur.execute("DESCRIBE process_sub_steps")
print('  Columns:', flush=True)
for col_info in cur.fetchall()[:6]:
    print(f'    {col_info}', flush=True)

# Use VARCHAR id
import uuid
test_id_1 = 'TEST-' + uuid.uuid4().hex[:8]
test_id_2 = 'TEST-' + uuid.uuid4().hex[:8]
try:
    cur.execute("""
        INSERT INTO process_sub_steps
        (id, order_no, step_name, status, created_at, quantity)
        VALUES (%s, 'TEST-ORDER-001', 'TEST-STEP', 'pending', NOW(), 1)
    """, (test_id_1,))
    print(f'  Inserted first row: id={test_id_1}', flush=True)

    # Try to insert duplicate (same order_no, step_name, status)
    cur.execute("""
        INSERT INTO process_sub_steps
        (id, order_no, step_name, status, created_at, quantity)
        VALUES (%s, 'TEST-ORDER-001', 'TEST-STEP', 'pending', NOW(), 1)
    """, (test_id_2,))
    print(f'  [FAIL] Duplicate was allowed!', flush=True)
except pymysql.err.IntegrityError as e:
    err_msg = str(e)
    if 'Duplicate entry' in err_msg:
        print(f'  [OK] Constraint works! Duplicate blocked: {err_msg[:80]}', flush=True)
    else:
        print(f'  [WARN] Other IntegrityError: {err_msg[:80]}', flush=True)
except Exception as e:
    print(f'  [WARN] Other error: {str(e)[:100]}', flush=True)

# Clean up test data
cur.execute("DELETE FROM process_sub_steps WHERE order_no='TEST-ORDER-001'")
conn.commit()
print(f'  Test data cleaned up', flush=True)

# 4. Check no duplicates remain
print('\n[4] Verify no duplicates remain:', flush=True)
cur.execute("""
    SELECT order_no, step_name, status, COUNT(*) as cnt
    FROM process_sub_steps
    WHERE status IN ('pending', 'in_progress', 'distributed')
    GROUP BY order_no, step_name, status
    HAVING cnt > 1
""")
remaining_dups = cur.fetchall()
if remaining_dups:
    print(f'  [WARN] {len(remaining_dups)} duplicate groups still exist:', flush=True)
    for row in remaining_dups[:5]:
        print(f'    {row}', flush=True)
else:
    print(f'  [OK] No duplicates remain in active statuses', flush=True)

# 5. Status distribution
print('\n[5] Status distribution in process_sub_steps:', flush=True)
cur.execute("SELECT status, COUNT(*) FROM process_sub_steps GROUP BY status ORDER BY COUNT(*) DESC")
for status, count in cur.fetchall():
    print(f'  {status}: {count}', flush=True)

conn.close()
print('\n[Done] Verification complete', flush=True)