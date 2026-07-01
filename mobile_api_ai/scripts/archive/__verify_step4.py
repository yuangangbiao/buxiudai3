# -*- coding: utf-8 -*-
"""验证步骤7：init_sync_engine() 初始化"""
import sys
sys.path.insert(0, '.')
from sync.init import init_sync_engine

init_sync_engine()
print('[OK] init_sync_engine() 执行完成')

# 验证 SyncLog.write 可用
from sync.sync_log import SyncLog
SyncLog.write('test.init', 'local', 'verify-001', status='success')
print('[OK] SyncLog.write() 写入验证通过')

# 验证数据是否写入
import sqlite3, os
from config import BASE_DIR
db_path = os.path.join(BASE_DIR, 'wechat_container.db')
conn = sqlite3.connect(db_path)
cur = conn.execute("SELECT * FROM sync_log WHERE record_id='verify-001'")
row = cur.fetchone()
assert row, '写入数据未找到'
print(f'[OK] 数据验证: id={row[0]}, event_type={row[1]}, direction={row[2]}, record_id={row[3]}, status={row[4]}')
conn.close()
