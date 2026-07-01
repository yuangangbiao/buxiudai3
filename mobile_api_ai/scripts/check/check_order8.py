import os
import sys
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _project_root)
# [F6 P7 物理清理 2026-06-10] SQLiteStorage 已物理移除, 改走 MySQLStorage 直连
from storage.mysql_storage import MySQLStorage
storage = MySQLStorage()
storage.connect()

print('=== 搜索订单8相关任务 ===')
packages = storage.get_packages(limit=100)
for pkg in packages:
    content = pkg.get('content', {})
    order_no = content.get('order_no', '') or pkg.get('related_order', '')
    if '8' in str(order_no) or '8' in str(pkg.get('title', '')):
        print(f"ID: {pkg.get('id')}")
        print(f"  Status: {pkg.get('status')}")
        print(f"  Target: {pkg.get('target_operator')}")
        print(f"  Title: {pkg.get('title')}")
        print(f"  Order: {order_no}")
        print(f"  Process: {content.get('process_name', '')}")
        print()