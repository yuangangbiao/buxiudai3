"""
T4 批量替换脚本：将硬编码的 timeout/connect_timeout 值替换为 config 常量
"""
import re
import os

MOBILE_API_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ========== 文件替换规则 ==========
# (file_path_relative, old_str, new_str)
REPLACEMENTS = []

def add(filepath, old, new):
    REPLACEMENTS.append((filepath, old, new))

# =====================================================================
# 1. dispatch_center.py - import at line 73, connects at 6 places + 5 timeouts
# =====================================================================
DC = 'dispatch_center.py'

# Update import line
add(DC,
    'from core.config import ENV_FILE, BASE_DIR, DB_PATHS, SERVICE_URLS, REQUEST_TIMEOUT, SHORT_TIMEOUT',
    'from core.config import ENV_FILE, BASE_DIR, DB_PATHS, SERVICE_URLS, REQUEST_TIMEOUT, SHORT_TIMEOUT, REQUEST_TIMEOUT_LONG, REQUEST_TIMEOUT_NORMAL, DB_CONNECT_TIMEOUT')

# Replace connect_timeout=3
add(DC,
    'conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=3)',
    'conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)')
add(DC,
    'conn = pymysql.connect(**MYSQL_CFG, connect_timeout=3)',
    'conn = pymysql.connect(**MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)')

# Replace environ.get timeout calls
add(DC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '15'))",
    'timeout=REQUEST_TIMEOUT_LONG')
add(DC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '30'))",
    'timeout=REQUEST_TIMEOUT_LONG')
add(DC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '3'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')
add(DC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')

# =====================================================================
# 2. storage_mysql.py - 1 connect_timeout=3, no core.config import
# =====================================================================
SM = 'storage_mysql.py'

# Add import
add(SM,
    'from utils.auto_schema import auto_ensure_schema',
    'from core.config import DB_CONNECT_TIMEOUT\nfrom utils.auto_schema import auto_ensure_schema')

# Replace connect_timeout
add(SM,
    '                connect_timeout=3,',
    '                connect_timeout=DB_CONNECT_TIMEOUT,')

# =====================================================================
# 3. sync_bridge.py - 2 connect_timeout=3, no core.config import
# =====================================================================
SB = 'sync_bridge.py'

# Add import after load_dotenv block
add(SB,
    "MYSQL_CFG = {",
    "from core.config import DB_CONNECT_TIMEOUT\n\nMYSQL_CFG = {")

# Replace connect_timeout=3
add(SB,
    'conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=3)',
    'conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)')

# =====================================================================
# 4. schedule_flow.py - 1 connect_timeout=3 + 2 timeout calls
# =====================================================================
SF = 'schedule_flow.py'

# Update import
add(SF,
    'from core.config import DB_PATHS',
    'from core.config import DB_PATHS, DB_CONNECT_TIMEOUT, REQUEST_TIMEOUT_QUICK, REQUEST_TIMEOUT_FAST')

# Replace connect_timeout=3 at line 1130
add(SF,
    '            connect_timeout=3',
    '            connect_timeout=DB_CONNECT_TIMEOUT')

# Replace timeout calls
add(SF,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))",
    'timeout=REQUEST_TIMEOUT_QUICK')
add(SF,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))",
    'timeout=REQUEST_TIMEOUT_FAST')

# =====================================================================
# 5. container_center_v5.py - 1 connect_timeout=3, no core.config import
# =====================================================================
CC5 = 'container_center_v5.py'

# Add import
add(CC5,
    'from storage_layer import create_storage, BaseStorage, StorageType',
    'from core.config import DB_CONNECT_TIMEOUT\nfrom storage_layer import create_storage, BaseStorage, StorageType')

# Replace connect_timeout
add(CC5,
    'conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=3)',
    'conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)')

# =====================================================================
# 6. container_center_api.py - add imports + replace 3 timeouts
# =====================================================================
CCA = 'container_center_api.py'

# Update import
add(CCA,
    'from core.config import DB_PATHS, REQUEST_TIMEOUT, SHORT_TIMEOUT',
    'from core.config import DB_PATHS, REQUEST_TIMEOUT, SHORT_TIMEOUT, REQUEST_TIMEOUT_NORMAL, REQUEST_TIMEOUT_QUICK')

# Replace timeouts
add(CCA,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '5'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')
add(CCA,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')
add(CCA,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))",
    'timeout=REQUEST_TIMEOUT_QUICK')

# =====================================================================
# 7. wechat_work_bot_v2.py - 1 connect_timeout=3 + 3 timeout calls
# =====================================================================
WWB = 'wechat_work_bot_v2.py'

# Update import
add(WWB,
    'from core.config import DB_PATHS, SERVICE_URLS',
    'from core.config import DB_PATHS, SERVICE_URLS, DB_CONNECT_TIMEOUT, REQUEST_TIMEOUT_FAST, REQUEST_TIMEOUT_NORMAL')

# Replace connect_timeout
add(WWB,
    'conn = pymysql.connect(**_REPORT_MYSQL_CFG, connect_timeout=3)',
    'conn = pymysql.connect(**_REPORT_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)')

# Replace timeout calls
add(WWB,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))",
    'timeout=REQUEST_TIMEOUT_FAST')
add(WWB,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')

# =====================================================================
# 8. config_center.py - 3 timeout calls, no core.config import
# =====================================================================
CC = 'config_center.py'

# Add import
add(CC,
    'from dotenv import set_key',
    'from core.config import REQUEST_TIMEOUT_FAST, REQUEST_TIMEOUT_NORMAL\nfrom dotenv import set_key')

# Replace connect_timeout (it uses REQUEST_TIMEOUT_FAST as connect_timeout)
add(CC,
    "connect_timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))",
    'connect_timeout=REQUEST_TIMEOUT_FAST')
add(CC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))",
    'timeout=REQUEST_TIMEOUT_FAST')
add(CC,
    "connect_timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')), read_timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))",
    'connect_timeout=REQUEST_TIMEOUT_FAST, read_timeout=REQUEST_TIMEOUT_NORMAL')

# =====================================================================
# 9. wechat_cloud.py - many timeout calls, no core.config import
# =====================================================================
WC = 'wechat_cloud.py'

# Add import
add(WC,
    'from logging_setup import setup_daily_logger, cleanup_old_logs, read_log',
    'from core.config import REQUEST_TIMEOUT_FAST, REQUEST_TIMEOUT_NORMAL, REQUEST_TIMEOUT_LONG\nfrom logging_setup import setup_daily_logger, cleanup_old_logs, read_log')

# Replace all timeout calls in wechat_cloud.py
add(WC,
    "timeout=int(os.environ.get('DEFAULT_REQUEST_TIMEOUT', '30'))",
    'timeout=REQUEST_TIMEOUT_LONG')
add(WC,
    "timeout=int(os.environ.get('DEFAULT_REQUEST_TIMEOUT', '10'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')
add(WC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '10'))",
    'timeout=REQUEST_TIMEOUT_FAST')
add(WC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))",
    'timeout=REQUEST_TIMEOUT_NORMAL')
add(WC,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '30'))",
    'timeout=REQUEST_TIMEOUT_LONG')

# =====================================================================
# 10. wechat_message_store.py - 1 timeout call, no core.config import
# =====================================================================
WMS = 'wechat_message_store.py'

# Add import
add(WMS,
    'from contextlib import contextmanager',
    'from core.config import REQUEST_TIMEOUT_NORMAL\nfrom contextlib import contextmanager')

# Replace timeout
add(WMS,
    "self._conn = sqlite3.connect(db_path, check_same_thread=False, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))",
    'self._conn = sqlite3.connect(db_path, check_same_thread=False, timeout=REQUEST_TIMEOUT_NORMAL)')

# =====================================================================
# 11. container_center_client.py - 1 timeout, no core.config import
# =====================================================================
CCC = 'container_center_client.py'

# Add import (after threading import)
add(CCC,
    'import threading',
    'from core.config import REQUEST_TIMEOUT_NORMAL\nimport threading')

# Replace timeout
add(CCC,
    "self.request_timeout = request_timeout or int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))",
    'self.request_timeout = request_timeout or REQUEST_TIMEOUT_NORMAL')

# =====================================================================
# 12. container_api_server.py - 1 timeout call
# =====================================================================
CAS = 'container_api_server.py'

# Add import from core.config (already has `import config`)
add(CAS,
    'import config  # 提前加载配置（设置 sys.path）',
    'import config  # 提前加载配置（设置 sys.path）\nfrom core.config import REQUEST_TIMEOUT_FAST')

# Replace timeout
add(CAS,
    "timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))",
    'timeout=REQUEST_TIMEOUT_FAST')

# =====================================================================
# Execute replacements
# =====================================================================
def execute():
    success = 0
    skipped = 0
    errors = []

    for rel_path, old, new in REPLACEMENTS:
        full_path = os.path.join(MOBILE_API_DIR, rel_path)
        if not os.path.exists(full_path):
            errors.append(f"FILE NOT FOUND: {rel_path}")
            continue

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Count occurrences
        count = content.count(old)
        if count == 0:
            skipped += 1
            continue

        content = content.replace(old, new)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        success += 1
        print(f"[OK] {rel_path}: replaced {count} occurrence(s)")

    if errors:
        print("\n=== ERRORS ===")
        for e in errors:
            print(f"  {e}")

    print(f"\nDone. {success} replacements applied, {skipped} skipped (pattern not found).")

if __name__ == '__main__':
    execute()
