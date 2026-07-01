# -*- coding: utf-8 -*-
"""验证步骤6：SyncLog 数据表创建"""
import sys
sys.path.insert(0, '.')
from sync.sync_log import SyncLog

SyncLog.ensure_table()

import sqlite3
import os
from config import BASE_DIR

db_path = os.path.join(BASE_DIR, 'wechat_container.db')
conn = sqlite3.connect(db_path)
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_log'")
row = cur.fetchone()
assert row, 'sync_log 表不存在'
conn.close()
print(f'[OK] SyncLog ensure_table: 表 sync_log 已创建 (db={db_path})')

# 验证表结构
conn2 = sqlite3.connect(db_path)
cur2 = conn2.execute("PRAGMA table_info(sync_log)")
cols = {row[1]: row[2] for row in cur2.fetchall()}
print(f'[OK] 表结构: {cols}')
assert 'event_type' in cols, '缺少 event_type 列'
assert 'direction' in cols, '缺少 direction 列'
assert 'record_id' in cols, '缺少 record_id 列'
assert 'status' in cols, '缺少 status 列'
assert 'created_at' in cols, '缺少 created_at 列'
print('[OK] 表结构完整 - 所有必需列已存在')
conn2.close()
