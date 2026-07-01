# -*- coding: utf-8 -*-
"""Backup 4 tables to INSERT statements file"""
import sys
import io
import os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Load .env
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

tables = ['process_sub_steps', 'quality_records', 'material_records', 'outsource_records']

# Generate backup filename
backup_dir = os.path.join(os.path.dirname(__file__), 'backup')
os.makedirs(backup_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = os.path.join(backup_dir, f'backup_4tables_{timestamp}.sql')

print('=' * 70, flush=True)
print(f'Backing up 4 tables...', flush=True)
print(f'Backup file: {backup_file}', flush=True)
print('=' * 70, flush=True)

total_rows = 0
with open(backup_file, 'w', encoding='utf-8') as f:
    f.write(f'-- Backup created: {datetime.now().isoformat()}\n')
    f.write(f'-- Database: container_center\n')
    f.write(f'-- Tables: {", ".join(tables)}\n\n')
    f.write('SET FOREIGN_KEY_CHECKS=0;\n\n')

    for table in tables:
        # Check if table exists
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s",
            (table,))
        if cur.fetchone()[0] == 0:
            print(f'  {table}: not exists, skipping', flush=True)
            continue

        # Get column info
        cur.execute(f"DESCRIBE {table}")
        cols_info = cur.fetchall()
        cols = [c[0] for c in cols_info]
        col_list = ', '.join(f'`{c}`' for c in cols)

        # Get all rows
        cur.execute(f"SELECT {col_list} FROM {table}")
        rows = cur.fetchall()

        print(f'  {table}: {len(rows)} rows', flush=True)
        total_rows += len(rows)

        # Write to file
        f.write(f'-- Table: {table} ({len(rows)} rows)\n')
        f.write(f'DROP TABLE IF EXISTS `{table}`;\n')
        # Get CREATE TABLE statement
        cur.execute(f"SHOW CREATE TABLE {table}")
        create_sql = cur.fetchone()[1]
        f.write(f'{create_sql};\n\n')

        if rows:
            # Write INSERT statements in batches of 100
            for i in range(0, len(rows), 100):
                batch = rows[i:i+100]
                for row in batch:
                    values = []
                    for v in row:
                        if v is None:
                            values.append('NULL')
                        elif isinstance(v, (int, float)):
                            values.append(str(v))
                        else:
                            # String - escape
                            s = str(v).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
                            values.append(f"'{s}'")
                    f.write(f"INSERT INTO `{table}` ({col_list}) VALUES ({', '.join(values)});\n")
                f.write('\n')
        f.write('\n')

    f.write('SET FOREIGN_KEY_CHECKS=1;\n')

print(f'\nTotal: {total_rows} rows backed up', flush=True)
print(f'[OK] Backup saved to: {backup_file}', flush=True)
conn.close()