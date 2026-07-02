# -*- coding: utf-8 -*-
import os, shutil
from datetime import datetime

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
ARCHIVE = os.path.join(PROJECT_ROOT, 'archive', f'scripts_c5_{datetime.now().strftime("%Y%m%d")}')
os.makedirs(ARCHIVE, exist_ok=True)

targets = [
    'mobile_api_ai/scripts/check/check_db.py',
    'mobile_api_ai/scripts/list_all_orders.py',
    'mobile_api_ai/scripts/list_all_orders3.py',
    'mobile_api_ai/migrations/0610_data_packages_flow_type.py',
    'mobile_api_ai/migrations/__pre_tests__/test_0610_data_packages_flow_type.py',
    'mobile_api_ai/__pre_tests__/test_dispatch_task_flow_type.py',
    'mobile_api_ai/__pre_tests__/test_5_center_integration.py',
    'mobile_api_ai/tests/pre_release/test_0610_data_packages_flow_type.py',
    'mobile_api_ai/tests/pre_release/test_5_center_integration.py',
    'scripts/tools/_check_process_records.py',
    'scripts/tools/_query_container_db.py',
    'tests/integration/data_source/test_data_source_direct.py',
    'tests/integration/sync/test_independent_tables_sync.py',
]
moved = 0
for rel in targets:
    src = os.path.join(PROJECT_ROOT, rel)
    if not os.path.exists(src):
        continue
    dst = os.path.join(ARCHIVE, rel.replace('/', '__'))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    print(f'✅ {rel}')
    moved += 1
print(f'\n共移动 {moved} 个文件')
