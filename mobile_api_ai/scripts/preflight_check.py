# -*- coding: utf-8 -*-
"""
启动前校验 — 必须全部通过才能启动服务
用法: python scripts/preflight_check.py
      退出码 0 = 通过, 非 0 = 失败
"""
import os, sys, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '.env'), override=True)

import pymysql
from pymysql.cursors import DictCursor

HOST = os.getenv('MYSQL_HOST', 'localhost')
PORT = int(os.getenv('MYSQL_PORT', 3306))
USER = os.getenv('MYSQL_USER', 'root')
PASSWORD = os.getenv('MYSQL_PASSWORD', '')
STEEL_BELT_DB = os.getenv('MYSQL_DATABASE', 'steel_belt')
CC_DB = os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center')

errors = []
warnings = []

def _conn(db):
    return pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD,
                           database=db, charset='utf8mb4', cursorclass=DictCursor,
                           connect_timeout=5)

def check_table(db, table, required_cols):
    """检查表存在且包含必填列"""
    conn = _conn(db)
    try:
        cur = conn.cursor()
        cur.execute(f"SHOW TABLES LIKE '{table}'")
        if not cur.fetchone():
            errors.append(f'{db}.{table} 表不存在')
            return
        cur.execute(f"DESCRIBE `{table}`")
        cols = {r['Field'] for r in cur.fetchall()}
        for col in required_cols:
            if col not in cols:
                errors.append(f'{db}.{table} 缺列: {col}')
    finally:
        conn.close()

# ════════════════════════════════════════
# 检查 1: steel_belt 关键表
# ════════════════════════════════════════
check_table(STEEL_BELT_DB, 'sync_queue', ['id', 'order_no', 'step_name', 'status', 'retry_count'])
check_table(STEEL_BELT_DB, 'production_orders', ['id', 'order_no', 'status'])
check_table(STEEL_BELT_DB, 'process_records', ['id', 'process_code', 'status'])
check_table(STEEL_BELT_DB, 'process_sub_steps', ['id', 'order_no', 'step_name'])

# ════════════════════════════════════════
# 检查 2: container_center 关键表
# ════════════════════════════════════════
check_table(CC_DB, 'data_packages', ['id', 'order_no', 'data_type', 'related_order'])
check_table(CC_DB, 'process_records', ['id', 'order_no', 'status'])

# ════════════════════════════════════════
# 检查 3: sync_bridge.py 连接正确性
# ════════════════════════════════════════
try:
    sync_bridge_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sync_bridge.py')
    with open(sync_bridge_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "database=MYSQL_CFG['database']" not in content:
        errors.append('sync_bridge.py: _get_mysql_connection() 未连接 steel_belt')
except Exception as e:
    warnings.append(f'无法检查 sync_bridge.py: {e}')

# ════════════════════════════════════════
# 检查 4: JSON 字段安全模式扫描
# ════════════════════════════════════════
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JSON_RISK_PATTERNS = [
    # 只检测 .get('content') or {} — 这是 MySQL TEXT 列最常见的陷阱
    # content 是 JSON 字符串时为 truthy，or {} 不触发，后续 dict 操作会崩
    (".get('content') or {}", "content 是 JSON 字符串时 or {} 不触发，需先 json.loads"),
]

EXCLUDE_DIRS = {'build', '__pycache__', '.git', 'logs', 'dist', 'venv', 'env',
                'scripts', 'tests', 'specs', 'docs', 'node_modules'}

for root, dirs, files in os.walk(APP_DIR):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(fpath, APP_DIR)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                source = f.read()
            for pattern, desc in JSON_RISK_PATTERNS:
                if pattern in source:
                    warnings.append(f'{rel}: {desc}')
                    break
        except Exception:
            pass

# ════════════════════════════════════════
# 输出结果（仅失败时打印）
# ════════════════════════════════════════

if warnings:
    for w in warnings:
        print(f'  [WARN] {w}', file=sys.stderr)

if errors:
    print(f'[校验] {len(errors)} 项未通过:', file=sys.stderr)
    for e in errors:
        print(f'  - {e}', file=sys.stderr)
    print(f'请先修复再启动。参考: mobile_api_ai/fix_missing_tables.sql', file=sys.stderr)
    sys.exit(1)

sys.exit(0)
